# coding: utf-8
"""存放应用升级细节"""
import json

from django.db import DatabaseError
from django.db import transaction
from django.db.models import Q

from console.exception.main import AbortRequest
from console.exception.main import RbdAppNotFound
from console.exception.main import RecordNotFound
from console.models import AppUpgradeRecord
from console.models import RainbondCenterApp
from console.models import ServiceSourceInfo
from console.models import ServiceUpgradeRecord
from console.models import UpgradeStatus
from console.repositories.app import service_repo
from console.repositories.event_repo import event_repo
from console.repositories.market_app_repo import rainbond_app_repo
from console.repositories.upgrade_repo import upgrade_repo
from www.apiclient.regionapibaseclient import RegionApiBaseHttpClient


class UpgradeService(object):
    def get_or_create_upgrade_record(self, tenant_id, group_id, group_key):
        """获取或创建升级记录"""
        recode_kwargs = {
            "tenant_id": tenant_id,
            "group_id": group_id,
            "group_key": group_key,
        }
        try:
            app_record = upgrade_repo.get_app_not_upgrade_record(
                status__lt=UpgradeStatus.UPGRADED.value,
                **recode_kwargs
            )
        except AppUpgradeRecord.DoesNotExist:
            from console.services.group_service import group_service
            service_group_keys = group_service.get_group_service_sources(group_id).values_list('group_key', flat=True)
            if group_key not in set(service_group_keys or []):
                raise AbortRequest(
                    msg="the rainbond app is not in the group",
                    msg_show="该组中没有这个云市应用",
                    status_code=404
                )
            app = rainbond_app_repo.get_rainbond_app_qs_by_key(group_key).first()
            if not app:
                raise AbortRequest(
                    msg="No rainbond app found",
                    msg_show="没有找到此云市应用",
                    status_code=404
                )
            app_record = upgrade_repo.create_app_upgrade_record(
                group_name=app.group_name,
                **recode_kwargs
            )
        return app_record

    def get_app_not_upgrade_record(self, tenant_id, group_id, group_key):
        """获取未完成升级记录"""
        recode_kwargs = {
            "tenant_id": tenant_id,
            "group_id": int(group_id),
            "group_key": group_key,
        }
        try:
            return upgrade_repo.get_app_not_upgrade_record(
                status__lt=UpgradeStatus.UPGRADED.value,
                **recode_kwargs
            )
        except AppUpgradeRecord.DoesNotExist:
            return AppUpgradeRecord()

    def get_app_upgrade_versions(self, tenant, group_id, group_key):
        """获取云市应用可升级版本列表"""
        from console.services.group_service import group_service
        from console.services.market_app_service import market_app_service

        # 查询某一个云市应用下的所有服务
        services = group_service.get_rainbond_services(group_id, group_key)
        versions = set()

        # 查询可升级的应用
        for service in services:
            service_version = market_app_service.list_upgradeable_versions(tenant, service)
            versions |= set(service_version or [])

        # 查询新增应用的版本
        service_keys = services.values_list('service_key', flat=True)
        service_keys = set(service_keys) if service_keys else set()
        app_qs = rainbond_app_repo.get_rainbond_app_qs_by_key(group_key=group_key)
        add_versions = self.query_the_version_of_the_add_service(app_qs, service_keys)

        versions |= add_versions

        return versions

    def get_old_version(self, group_key, service_ids):
        """获取旧版本版本号"""
        versions = ServiceSourceInfo.objects.filter(
            group_key=group_key,
            service_id__in=service_ids,
        ).values_list('version', flat=True) or []

        app = RainbondCenterApp.objects.filter(
            group_key=group_key,
            version__in=versions
        ).order_by('create_time').first()
        return app.version if app else ''

    def query_the_version_of_the_add_service(self, app_qs, service_keys):
        """查询增加服务的版本
        :param app_qs: 所有版本的应用
        :type service_keys: set
        :rtype: set
        """
        version_app_template_mapping = {
            app.version: self.parse_app_template(app.app_template)
            for app in app_qs
        }
        return {
            version
            for version, parse_app_template in version_app_template_mapping.items()
            if self.get_new_services(parse_app_template, service_keys)
        }

    @staticmethod
    def get_new_services(parse_app_template, service_keys):
        """获取新添加的服务信息
        :type parse_app_template: dict
        :type service_keys: set
        :rtype: dict
        """
        new_service_keys = set(parse_app_template.keys()) - set(service_keys)
        return {
            key: parse_app_template[key]
            for key in new_service_keys
        }

    @staticmethod
    def parse_app_template(app_template):
        """解析app_template， 返回service_key与service_info映射"""
        return {
            app['service_key']: app
            for app in json.loads(app_template)['apps']
        }

    @staticmethod
    def get_service_changes(service, tenant, version):
        """获取服务更新信息"""
        from console.services.app_actions.properties_changes import PropertiesChanges

        try:
            pc = PropertiesChanges(service)
            return pc.get_property_changes(tenant.enterprise_id, version)
        except RecordNotFound as e:
            AbortRequest(msg=str(e))
        except RbdAppNotFound as e:
            AbortRequest(msg=str(e))

    def get_add_services(self, services, group_key, version):
        """获取新增服务"""
        service_keys = services.values_list('service_key', flat=True)
        service_keys = set(service_keys) if service_keys else set()
        app = rainbond_app_repo.get_rainbond_app_by_key_version(group_key=group_key, version=version)
        return self.get_new_services(self.parse_app_template(app.app_template), service_keys).values()

    def synchronous_upgrade_status(self, tenant, record):
        """ 同步升级状态
        :type tenant: www.models.main.Tenants
        :type record: AppUpgradeRecord
        """
        from console.services.app_actions import event_service

        # 升级中，回滚中 才需要同步
        synchronization_type = {UpgradeStatus.UPGRADING.value, UpgradeStatus.ROLLING.value}

        if record.status not in synchronization_type:
            return

        # 回滚时只同步升级类型的记录
        q = Q(upgrade_type=ServiceUpgradeRecord.UpgradeType.UPGRADE.value
              ) if record.status == UpgradeStatus.ROLLING.value else Q()

        service_records = record.service_upgrade_records.filter(q).all()

        event_service_mapping = {
            record.event_id: record
            for record in service_records
            if record.status in synchronization_type and record.event_id
        }
        events = event_repo.get_events_by_event_ids(event_service_mapping.keys())
        # 去数据中心同步事件
        event_service.sync_region_service_event_status(tenant.region, tenant.tenant_name, events)

        for event in events:
            service_record = event_service_mapping[event.event_id]
            self._change_service_record_status(event, service_record)

        service_status = set(service_records.values_list('status', flat=True))
        judging_status = {
            # 升级中
            UpgradeStatus.UPGRADING.value: self._judging_status_upgrading,
            # 回滚中
            UpgradeStatus.ROLLING.value: self._judging_status_rolling,
        }

        status = judging_status[record.status](service_status)
        if status:
            upgrade_repo.change_app_record_status(record, status)

    @staticmethod
    def create_add_service_record(app_record, events, add_service_infos):
        """创建新增服务升级记录"""
        service_id_event_mapping = {
            event.service_id: event
            for event in events
        }
        services = service_repo.get_services_by_service_ids_and_group_key(
            app_record.group_key,
            service_id_event_mapping.keys()
        )
        for service in services:
            upgrade_repo.create_service_upgrade_record(
                app_record, service, service_id_event_mapping[service.service_id],
                add_service_infos[service.service_key],
                upgrade_type=ServiceUpgradeRecord.UpgradeType.ADD.value
            )

    @staticmethod
    def market_service_and_create_backup(tenant, service, version):
        """创建服务升级接口并创建备份"""
        from console.services.app_actions.app_deploy import MarketService

        market_service = MarketService(tenant, service, version)
        market_service.create_backup()
        return market_service

    @staticmethod
    def upgrade_database(market_services):
        """升级数据库数据"""
        from console.services.app_actions.app_deploy import PropertyType
        try:
            with transaction.atomic():
                for market_service in market_services:
                    market_service.set_changes()
                    market_service.set_properties(PropertyType.ORDINARY.value)
                    market_service.modify_property()
                    market_service.sync_region_property()

                for market_service in market_services:
                    market_service.set_properties(PropertyType.DEPENDENT.value)
                    market_service.modify_property()
                    market_service.sync_region_property()
        except (DatabaseError, RegionApiBaseHttpClient.CallApiError) as e:
            for market_service in market_services:
                market_service.restore_backup()
            raise AbortRequest(msg=str(e))

    def send_upgrade_request(self, market_services, tenant, user, app_record, service_infos):
        """向数据中心发送更新请求"""
        from console.services.app_actions.app_deploy import AppDeployService

        for market_service in market_services:
            app_deploy_service = AppDeployService()
            app_deploy_service.set_impl(market_service)
            code, msg, event = app_deploy_service.execute(
                tenant,
                market_service.service,
                user,
                True,
                app_record.version
            )

            upgrade_repo.create_service_upgrade_record(
                app_record,
                market_service.service,
                event,
                service_infos[market_service.service.service_id],
                self._get_sync_upgrade_status(code, event)
            )

    @staticmethod
    def _get_sync_upgrade_status(code, event):
        """通过异步请求状态判断升级状态"""
        if code == 200 and event:
            status = UpgradeStatus.UPGRADING.value
        elif code == 200 and not event:
            status = UpgradeStatus.UPGRADED.value
        else:
            status = UpgradeStatus.UPGRADE_FAILED.value
        return status

    @staticmethod
    def _change_service_record_status(event, service_record):
        """变更服务升级记录状态"""
        operation = {
            # 升级中
            UpgradeStatus.UPGRADING.value: {
                "success": UpgradeStatus.UPGRADED.value,
                "failure": UpgradeStatus.UPGRADE_FAILED.value,
                "timeout": UpgradeStatus.UPGRADED.value,
            },
            # 回滚中
            UpgradeStatus.ROLLING.value: {
                "success": UpgradeStatus.ROLLBACK.value,
                "failure": UpgradeStatus.ROLLBACK_FAILED.value,
                "timeout": UpgradeStatus.ROLLBACK.value,
            },
        }
        status = operation.get(service_record.status, {}).get(event.status)
        if status:
            upgrade_repo.change_service_record_status(service_record, status)

    @staticmethod
    def _judging_status_upgrading(service_status):
        """判断升级状态"""
        status = None
        if UpgradeStatus.UPGRADING.value in service_status:
            return
        elif service_status == {UpgradeStatus.UPGRADE_FAILED.value, UpgradeStatus.UPGRADED.value}:
            status = UpgradeStatus.PARTIAL_UPGRADED.value
        elif service_status == {UpgradeStatus.UPGRADED.value}:
            status = UpgradeStatus.UPGRADED.value
        elif service_status == {UpgradeStatus.UPGRADE_FAILED.value}:
            status = UpgradeStatus.UPGRADE_FAILED.value
        return status

    @staticmethod
    def _judging_status_rolling(service_status):
        """判断回滚状态"""
        status = None
        if UpgradeStatus.ROLLING.value in service_status:
            return
        elif len(service_status) > 1 and service_status <= {
            UpgradeStatus.ROLLBACK_FAILED.value,
            UpgradeStatus.ROLLBACK.value,
            UpgradeStatus.UPGRADED.value,
        }:
            status = UpgradeStatus.PARTIAL_ROLLBACK.value
        elif service_status == {UpgradeStatus.ROLLBACK.value}:
            status = UpgradeStatus.ROLLBACK.value
        elif service_status == {UpgradeStatus.ROLLBACK_FAILED.value}:
            status = UpgradeStatus.ROLLBACK_FAILED.value
        return status

    @staticmethod
    def market_service_and_restore_backup(tenant, service, version):
        """创建服务回滚接口并回滚数据库"""
        from console.services.app_actions.app_deploy import MarketService

        market_service = MarketService(tenant, service, version)
        market_service.auto_restore = False
        market_service.restore_backup()
        return market_service

    def send_rolling_request(self, market_services, tenant, user, app_record, service_records):
        """向数据中心发送回滚请求"""
        from console.services.app_actions.app_deploy import AppDeployService

        for market_service in market_services:
            app_deploy_service = AppDeployService()
            app_deploy_service.set_impl(market_service)
            code, msg, event = app_deploy_service.execute(
                tenant,
                market_service.service,
                user,
                True,
                app_record.version
            )
            service_record = service_records.get(service_id=market_service.service.service_id)
            upgrade_repo.change_service_record_status(
                service_record,
                self._get_sync_rolling_status(code, event)
            )
            # 改变event id
            if code == 200:
                service_record.event_id = event.event_id if event else ''
                service_record.save()

    @staticmethod
    def _get_sync_rolling_status(code, event):
        """通过异步请求状态判断回滚状态"""
        if code == 200 and event:
            status = UpgradeStatus.ROLLING.value
        elif code == 200 and not event:
            status = UpgradeStatus.ROLLBACK.value
        else:
            status = UpgradeStatus.ROLLBACK_FAILED.value
        return status

    @staticmethod
    def serialized_upgrade_record(app_record):
        """序列化升级记录
        :type : AppUpgradeRecord
        """
        return dict(
            service_record=[
                {
                    "status": service_record.status,
                    "update_time": service_record.update_time,
                    "event_id": service_record.event_id,
                    "update": json.loads(service_record.update),
                    "app_upgrade_record": service_record.app_upgrade_record_id,
                    "service_cname": service_record.service_cname,
                    "create_time": service_record.create_time,
                    "service_id": service_record.service_id,
                    "upgrade_type": service_record.upgrade_type,
                    "ID": service_record.ID
                }
                for service_record in app_record.service_upgrade_records.all()
            ],
            **app_record.to_dict()
        )


upgrade_service = UpgradeService()
