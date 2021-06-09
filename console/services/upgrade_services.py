# coding: utf-8
"""存放组件升级细节"""
import json
import logging
from copy import deepcopy
from datetime import datetime
from enum import Enum

from console.exception.main import (AbortRequest, AccountOverdueException, RbdAppNotFound, RecordNotFound,
                                    ResourceNotEnoughException, ServiceHandleException)
from console.models.main import (AppUpgradeRecord, RainbondCenterAppVersion, ServiceSourceInfo, ServiceUpgradeRecord,
                                 UpgradeStatus)
from console.repositories.app import service_repo
from console.repositories.market_app_repo import rainbond_app_repo
from console.repositories.upgrade_repo import upgrade_repo
from console.services.app import app_market_service
from console.services.app_actions.exception import ErrServiceSourceNotFound
from console.services.app_actions.properties_changes import (PropertiesChanges, get_upgrade_app_template)
from console.services.group_service import group_service
from django.db import transaction
from django.db.models import Q
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import TenantEnterprise, TenantEnterpriseToken, Tenants

region_api = RegionInvokeApi()
logger = logging.getLogger("default")


class UpgradeType(Enum):
    UPGRADE = 'upgrade'
    ADD = 'add'


class UpgradeService(object):
    def get_enterprise_access_token(self, enterprise_id, access_target):
        enter = TenantEnterprise.objects.get(enterprise_id=enterprise_id)
        try:
            return TenantEnterpriseToken.objects.get(enterprise_id=enter.pk, access_target=access_target)
        except TenantEnterpriseToken.DoesNotExist:
            return None

    def get_or_create_upgrade_record(self, tenant_id, group_id, group_key, upgrade_group_id, is_from_cloud, market_name):
        """获取或创建升级记录"""
        recode_kwargs = {
            "tenant_id": tenant_id,
            "group_id": group_id,
            "group_key": group_key,
            "create_time": datetime.now(),
            "is_from_cloud": is_from_cloud,
            "market_name": market_name,
            "upgrade_group_id": upgrade_group_id,
        }
        try:
            return upgrade_repo.get_app_not_upgrade_record(status__lt=UpgradeStatus.UPGRADED.value, **recode_kwargs)
        except AppUpgradeRecord.DoesNotExist:
            from console.services.group_service import group_service
            tenant = Tenants.objects.get(tenant_id=tenant_id)
            service_group_keys = group_service.get_group_service_sources(group_id).values_list('group_key', flat=True)
            if group_key in set(service_group_keys or []):
                if not is_from_cloud:
                    app = rainbond_app_repo.get_rainbond_app_qs_by_key(tenant.enterprise_id, group_key)
                    if not app:
                        raise ServiceHandleException(
                            msg="the rainbond app is not in the group", msg_show="该应用中没有这个云市组件", status_code=404)
                    app_name = app.app_name
                else:
                    market = app_market_service.get_app_market_by_name(tenant.enterprise_id, market_name, raise_exception=True)
                    app = app_market_service.get_market_app_model(market, group_key)
                    app_name = app.app_name
                app_record = upgrade_repo.create_app_upgrade_record(group_name=app_name, **recode_kwargs)
                return app_record
            else:
                raise AbortRequest(msg="the app model is not in the group", msg_show="该应用中没有这个应用模型", status_code=404)

    def get_or_create_upgrade_record_new(self, tenant, region_name, application, app_model_key, upgrade_group_id):
        from console.services.market_app_service import market_app_service
        record = upgrade_repo.get_last_upgrade_record(tenant, application.ID, upgrade_group_id)
        if record:
            self.synchronous_upgrade_status(tenant, region_name, record)
            # not start upgrade or upgrading record.
            if record.status in [UpgradeStatus.UPGRADING.value, UpgradeStatus.NOT.value, UpgradeStatus.ROLLING.value]:
                return record
        current_version, template_update_time, install_from_cloud, market = market_app_service.get_current_version(
            tenant.enterprise_id, app_model_key, application.ID, upgrade_group_id)
        if install_from_cloud:
            app, _ = app_market_service.cloud_app_model_to_db_model(market, app_model_key, None)
        else:
            app, _ = rainbond_app_repo.get_rainbond_app_and_version(tenant.enterprise_id, app_model_key, None)
        if not app:
            raise ServiceHandleException(msg="app is not exist", msg_show="应用市场应用不存在，无法进行升级")
        recode_kwargs = {
            "tenant_id": tenant.tenant_id,
            "group_id": application.ID,
            "group_key": app_model_key,
            "group_name": app.app_name,
            "create_time": datetime.now(),
            "is_from_cloud": install_from_cloud,
            "market_name": market.name if market else "",
            "upgrade_group_id": upgrade_group_id,
            "old_version": current_version,
        }
        return upgrade_repo.create_app_upgrade_record(**recode_kwargs)

    def get_app_not_upgrade_record(self, tenant_id, group_id, group_key):
        """获取未完成升级记录"""
        recode_kwargs = {
            "tenant_id": tenant_id,
            "group_id": int(group_id),
            "group_key": group_key,
        }
        try:
            return upgrade_repo.get_app_not_upgrade_record(status__lt=UpgradeStatus.UPGRADED.value, **recode_kwargs)
        except AppUpgradeRecord.DoesNotExist:
            return AppUpgradeRecord()

    def get_old_version(self, group_key, service_ids, cloud_version):
        """获取旧版本版本号"""

        versions = ServiceSourceInfo.objects.filter(
            group_key=group_key,
            service_id__in=service_ids,
        ).values_list(
            'version', flat=True) or []

        app = RainbondCenterAppVersion.objects.filter(app_id=group_key, version__in=versions).order_by('-create_time').first()
        if app and app.version:
            return app.version
        elif cloud_version and len(versions) >= 1:
            return versions[0]
        else:
            return ''

    def query_the_version_of_the_add_service(self, app_qs, service_keys):
        """查询增加组件的版本
        :param app_qs: 所有版本的组件
        :type service_keys: set
        :rtype: set
        """
        version_app_template_mapping = {app.version: self.parse_app_template(app.app_template) for app in app_qs}
        return {
            version
            for version, parse_app_template in list(version_app_template_mapping.items())
            if self.get_new_services(parse_app_template, service_keys)
        }

    @staticmethod
    def get_new_services(parse_app_template, service_keys):
        """获取新添加的组件信息
        :type parse_app_template: dict
        :type service_keys: set
        :rtype: dict
        """
        new_service_keys = set(parse_app_template.keys()) - set(service_keys)
        return {key: parse_app_template[key] for key in new_service_keys}

    @staticmethod
    def parse_app_template(app_template):
        """解析app_template， 返回service_key与service_info映射"""
        return {app['service_key']: app for app in json.loads(app_template)['apps']}

    @staticmethod
    def get_service_changes(service, tenant, version, services):
        """获取组件更新信息"""
        from console.services.app_actions.properties_changes import \
            PropertiesChanges
        try:
            pc = PropertiesChanges(service, tenant, all_component_one_model=services)
            upgrade_template = get_upgrade_app_template(tenant, version, pc)
            model_component, changes = pc.get_property_changes(template=upgrade_template, level="app")
            return pc.current_version, model_component, changes
        except (RecordNotFound, ErrServiceSourceNotFound) as e:
            AbortRequest(msg=str(e))
        except RbdAppNotFound as e:
            AbortRequest(msg=str(e))

    def get_add_services(self, enterprise_id, services, group_key, version, market_name=None):
        """获取新增组件"""
        app_template = None
        if services:
            service_keys = services.values_list('service_key', flat=True)
            service_keys = set(service_keys) if service_keys else set()
            if not market_name:
                app = rainbond_app_repo.get_rainbond_app_by_key_version(group_key=group_key, version=version)
                if app:
                    app_template = app.app_template
            else:
                market = app_market_service.get_app_market_by_name(enterprise_id, market_name, raise_exception=True)
                app = app_market_service.get_market_app_model_version(market, group_key, version, get_template=True)
                if app:
                    app_template = app.template
            if app_template:
                return list(self.get_new_services(self.parse_app_template(app_template), service_keys).values())
        else:
            return []

    def synchronous_upgrade_status(self, tenant, region_name, record):
        """ 同步升级状态
        :type tenant: www.models.main.Tenants
        :type record: AppUpgradeRecord
        """
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
            for record in service_records if record.status in synchronization_type and record.event_id
        }
        event_ids = list(event_service_mapping.keys())
        body = region_api.get_tenant_events(region_name, tenant.tenant_name, event_ids)
        events = body.get("list", [])
        for event in events:
            service_record = event_service_mapping[event["EventID"]]
            self._change_service_record_status(event["Status"], service_record)

        service_status = set(service_records.values_list('status', flat=True) or [])
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
        """创建新增组件升级记录"""
        service_id_event_mapping = {events[key]: key for key in events}
        services = service_repo.get_services_by_service_ids_and_group_key(app_record.group_key,
                                                                          list(service_id_event_mapping.keys()))
        for service in services:
            upgrade_repo.create_service_upgrade_record(
                app_record,
                service,
                service_id_event_mapping[service.service_id],
                add_service_infos[service.service_key],
                upgrade_type=ServiceUpgradeRecord.UpgradeType.ADD.value)

    @staticmethod
    def market_service_and_create_backup(tenant,
                                         service,
                                         version,
                                         all_component_one_model=None,
                                         component_change_info=None,
                                         app_version=None):
        """创建组件升级接口并创建备份"""
        from console.services.app_actions.app_deploy import MarketService

        market_service = MarketService(tenant, service, version, all_component_one_model, component_change_info, app_version)
        market_service.create_backup()
        return market_service

    @staticmethod
    def upgrade_database(market_services):
        """升级数据库数据"""
        from console.services.app_actions.app_deploy import PropertyType
        try:
            with transaction.atomic():
                for market_service in market_services:
                    logger.debug("upgrade component {} ORDINARY attribute".format(market_service.service.service_alias))
                    start = datetime.now()
                    market_service.set_changes()
                    market_service.set_properties(PropertyType.ORDINARY.value)
                    market_service.modify_property()
                    market_service.sync_region_property()
                    logger.debug("upgrade component {0} ORDINARY attribute take time {1}".format(
                        market_service.service.service_alias,
                        datetime.now() - start))

                for market_service in market_services:
                    logger.debug("upgrade component {} DEPENDENT attribute".format(market_service.service.service_alias))
                    start = datetime.now()
                    market_service.set_properties(PropertyType.DEPENDENT.value)
                    market_service.modify_property()
                    market_service.sync_region_property()
                    logger.debug("upgrade component {0} DEPENDENT attribute take time {1}".format(
                        market_service.service.service_alias,
                        datetime.now() - start))
        except ServiceHandleException as e:
            logger.exception(e)
            for market_service in market_services:
                market_service.restore_backup()
            e.msg_show = "升级时发送错误:{0}, 已升级组件已自动回滚，但新增组件不会进行删除，请手动处理".format(e.msg_show)
            raise e
        except Exception as e:
            logger.exception(e)
            for market_service in market_services:
                market_service.restore_backup()
            raise ServiceHandleException(msg="upgrade app failure", msg_show="升级时发送错误, 已升级组件已自动回滚，但新增组件不会进行删除，请手动处理")

    def send_upgrade_request(self, market_services, tenant, user, app_record, service_infos, oauth_instance):
        """向数据中心发送更新请求"""
        from console.services.app_actions.app_deploy import AppDeployService

        for market_service in market_services:
            event_id = ""
            if market_service.changes:
                app_deploy_service = AppDeployService()
                app_deploy_service.set_impl(market_service)
                code, msg, event_id = app_deploy_service.execute(
                    tenant, market_service.service, user, True, app_record.version, oauth_instance=oauth_instance)
            else:
                # set record is UPGRADED
                code = 200
            upgrade_repo.create_service_upgrade_record(app_record, market_service.service, event_id,
                                                       service_infos[market_service.service.service_id],
                                                       self._get_sync_upgrade_status(code, event_id))

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
    def _change_service_record_status(event_status, service_record):
        """变更组件升级记录状态"""
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
        status = operation.get(service_record.status, {}).get(event_status)
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
        elif service_status == {}:
            status = UpgradeStatus.UPGRADED.value
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
        elif service_status == {}:
            status = UpgradeStatus.ROLLBACK.value
        return status

    @staticmethod
    def market_service_and_restore_backup(tenant, service, version):
        """创建组件回滚接口并回滚数据库"""
        from console.services.app_actions.app_deploy import MarketService

        # TODO: set app template init MarketService
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
            code, msg, event_id = app_deploy_service.execute(tenant, market_service.service, user, True, app_record.version)
            service_record = service_records.get(service_id=market_service.service.service_id)
            upgrade_repo.change_service_record_status(service_record, self._get_sync_rolling_status(code, event_id))
            # 改变event id
            if code == 200:
                service_record.event_id = event_id
                service_record.save()

    @staticmethod
    def _get_sync_rolling_status(code, event_id):
        """通过异步请求状态判断回滚状态"""
        if code == 200 and event_id:
            status = UpgradeStatus.ROLLING.value
        elif code == 200 and not event_id:
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
            service_record=[{
                "status": service_record.status,
                "update_time": service_record.update_time,
                "event_id": service_record.event_id,
                "update": json.loads(service_record.update) if service_record.update else None,
                "app_upgrade_record": service_record.app_upgrade_record_id,
                "service_cname": service_record.service_cname,
                "create_time": service_record.create_time,
                "service_id": service_record.service_id,
                "upgrade_type": service_record.upgrade_type,
                "ID": service_record.ID,
                "service_key": service_record.service.service_key
            } for service_record in app_record.service_upgrade_records.all()],
            **app_record.to_dict())

    def get_upgrade_info(self, team, services, app_model_id, app_model_version, market_name):
        # 查询某一个云市应用下的所有组件
        upgrade_info = {}
        for service in services:
            _, _, changes = upgrade_service.get_service_changes(service, team, app_model_version, services)
            if not changes:
                continue
            upgrade_info[service.service_id] = changes

        add_info = {
            service_info['service_key']: service_info
            for service_info in upgrade_service.get_add_services(team.enterprise_id, services, app_model_id, app_model_version,
                                                                 market_name)
        }
        return upgrade_info, add_info

    @transaction.atomic()
    def openapi_upgrade_app_models(self, user, team, region_name, oauth_instance, app_id, data):
        from console.services.market_app_service import market_app_service
        update_versions = data["update_versions"]
        for update_version in update_versions:
            app_model_id = update_version["app_model_id"]
            app_model_version = update_version["app_model_version"]
            market_name = update_version["market_name"]
            # TODO: get upgrade component will set upgrade_group_id.
            # Otherwise, there is a problem with multiple installs and upgrades of an application.
            services = group_service.get_rainbond_services(int(app_id), app_model_id)
            if not services:
                continue
            exist_component = services.first()
            pc = PropertiesChanges(exist_component, team, all_component_one_model=services)
            recode_kwargs = {
                "tenant_id": team.tenant_id,
                "group_id": int(app_id),
                "group_key": app_model_id,
                "is_from_cloud": bool(market_name),
                "market_name": market_name,
            }

            # 获取升级信息
            upgrade_info, add_info = self.get_upgrade_info(team, services, app_model_id, app_model_version, market_name)

            # 生成升级记录
            app_record = self.get_or_create_upgrade_record(**recode_kwargs)
            self.synchronous_upgrade_status(team, region_name, app_record)
            app_record = AppUpgradeRecord.objects.get(ID=app_record.ID)

            # 处理新增的组件
            install_info = {}
            if add_info:
                old_app = app_market_service.get_market_app_model_version(
                    pc.market, app_model_id, app_model_version, get_template=True)
                new_app = deepcopy(old_app)
                # mock app信息
                template = json.loads(new_app.template)
                template['apps'] = list(add_info.values())
                new_app.template = json.dumps(template)

                # 查询某一个云市应用下的所有组件
                try:
                    install_info = market_app_service.install_service_when_upgrade_app(
                        team, region_name, user, app_id, new_app, old_app, services, True,
                        exist_component.tenant_service_group_id, pc.install_from_cloud, pc.market_name)
                except ResourceNotEnoughException as re:
                    raise re
                except AccountOverdueException as re:
                    logger.exception(re)
                    raise ServiceHandleException(
                        msg="resource is not enough", msg_show=re.message, status_code=412, error_code=10406)
                upgrade_service.create_add_service_record(app_record, install_info['events'], add_info)

            app_record.version = app_model_version
            app_record.old_version = pc.current_version
            app_record.save()
            # 处理升级组件
            upgrade_services = service_repo.get_services_by_service_ids_and_group_key(app_model_id, list(upgrade_info.keys()))
            market_services = [
                self.market_service_and_create_backup(team, service, app_record.version, upgrade_services)
                for service in upgrade_services
            ]
            # 处理依赖关系
            if add_info:
                market_app_service.save_service_deps_when_upgrade_app(
                    team,
                    install_info['service_key_dep_key_map'],
                    install_info['key_service_map'],
                    install_info['apps'],
                    install_info['app_map'],
                )

            upgrade_service.upgrade_database(market_services)
            upgrade_service.send_upgrade_request(market_services, team, user, app_record, upgrade_info, oauth_instance)
            upgrade_repo.change_app_record_status(app_record, UpgradeStatus.UPGRADING.value)


upgrade_service = UpgradeService()
