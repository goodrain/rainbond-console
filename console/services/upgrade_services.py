# coding: utf-8
"""存放组件升级细节"""
import json
import logging
from copy import deepcopy
from datetime import datetime
from enum import Enum
from json.decoder import JSONDecodeError

from console.exception.bcode import (ErrAppUpgradeDeployFailed, ErrAppUpgradeRecordCanNotDeploy, ErrLastRecordUnfinished)
from console.exception.bcode import ErrAppUpgradeRecordCanNotRollback
from console.exception.bcode import ErrAppUpgradeWrongStatus
# exception
from console.exception.main import (AbortRequest, AccountOverdueException, RbdAppNotFound, RecordNotFound,
                                    ResourceNotEnoughException, ServiceHandleException)
# model
from console.models.main import (AppUpgradeRecord, AppUpgradeRecordType, ServiceUpgradeRecord, UpgradeStatus)
from www.models.main import TenantServiceInfo
# repository
from console.repositories.app import service_repo
from console.repositories.group import tenant_service_group_repo
from console.repositories.market_app_repo import rainbond_app_repo
from console.repositories.app import app_market_repo
from console.repositories.app import service_source_repo
from console.repositories.upgrade_repo import (component_upgrade_record_repo, upgrade_repo)
# service
from console.services.app import app_market_service
from console.services.app_actions import app_manage_service
from console.services.app_actions.exception import ErrServiceSourceNotFound
from console.services.app_actions.properties_changes import (PropertiesChanges, get_upgrade_app_template)
from console.services.group_service import group_service
from console.services.market_app.app_restore import AppRestore
# market app
from console.services.market_app.app_upgrade import AppUpgrade
from console.services.market_app.component_group import ComponentGroup
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
# www
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import ServiceGroup, Tenants

region_api = RegionInvokeApi()
logger = logging.getLogger("default")


class UpgradeType(Enum):
    UPGRADE = 'upgrade'
    ADD = 'add'


class UpgradeService(object):
    def __init__(self):
        self.status_tables = {
            UpgradeStatus.UPGRADING.value: {
                "success": UpgradeStatus.UPGRADED.value,
                "failure": UpgradeStatus.UPGRADE_FAILED.value,
                "timeout": UpgradeStatus.UPGRADED.value,
            },
            UpgradeStatus.ROLLING.value: {
                "success": UpgradeStatus.ROLLBACK.value,
                "failure": UpgradeStatus.ROLLBACK_FAILED.value,
                "timeout": UpgradeStatus.ROLLBACK.value,
            },
        }

    def upgrade(self, tenant, region, user, app, version, record: AppUpgradeRecord, component_keys=None):
        """
        Upgrade application market applications
        """
        if not record.can_upgrade():
            raise ErrAppUpgradeWrongStatus
        component_group = tenant_service_group_repo.get_component_group(record.upgrade_group_id)

        app_template_source = self._app_template_source(record.group_id, record.group_key, record.upgrade_group_id)
        app_template = self._app_template(user.enterprise_id, component_group.group_key, version, app_template_source)

        app_upgrade = AppUpgrade(
            tenant.enterprise_id,
            tenant,
            region,
            user,
            app,
            version,
            component_group,
            app_template,
            app_template_source.is_install_from_cloud(),
            app_template_source.get_market_name(),
            record,
            component_keys,
            is_deploy=True)
        record = app_upgrade.upgrade()
        app_template_name = component_group.group_alias
        return self.serialized_upgrade_record(record), app_template_name

    def upgrade_component(self, tenant, region, user, app, component: TenantServiceInfo, version):
        component_group = tenant_service_group_repo.get_component_group(component.upgrade_group_id)
        app_template_source = service_source_repo.get_service_source(component.tenant_id, component.component_id)
        app_template = self._app_template(user.enterprise_id, component_group.group_key, version, app_template_source)

        app_upgrade = AppUpgrade(
            tenant.enterprise_id,
            tenant,
            region,
            user,
            app,
            version,
            component_group,
            app_template,
            app_template_source.is_install_from_cloud(),
            app_template_source.get_market_name(),
            component_keys=[component.service_key],
            is_deploy=True,
            is_upgrade_one=True)
        app_upgrade.upgrade()

    def restore(self, tenant, region, user, app, record: AppUpgradeRecord):
        if not record.can_rollback():
            raise ErrAppUpgradeRecordCanNotRollback

        component_group = tenant_service_group_repo.get_component_group(record.upgrade_group_id)
        app_restore = AppRestore(tenant, region, user, app, component_group, record)
        record, component_group = app_restore.restore()
        return self.serialized_upgrade_record(record), component_group.group_alias

    @staticmethod
    def _app_template_source(app_id, app_model_key, upgrade_group_id):
        components = group_service.get_rainbond_services(app_id, app_model_key, upgrade_group_id)
        if not components:
            raise AbortRequest("components not found", "找不到组件", status_code=404, error_code=404)
        component = components[0]
        component_source = service_source_repo.get_service_source(component.tenant_id, component.service_id)
        return component_source

    @staticmethod
    def _app_template(enterprise_id, app_model_key, version, app_template_source):
        if not app_template_source.is_install_from_cloud():
            _, app_version = rainbond_app_repo.get_rainbond_app_and_version(enterprise_id, app_model_key, version)
        else:
            market = app_market_repo.get_app_market_by_name(
                enterprise_id, app_template_source.get_market_name(), raise_exception=True)
            _, app_version = app_market_service.cloud_app_model_to_db_model(market, app_model_key, version)

        if not app_version:
            raise AbortRequest("app template not found", "找不到应用模板", status_code=404, error_code=404)

        try:
            app_template = json.loads(app_version.app_template)
            app_template["update_time"] = app_version.update_time
            return app_template
        except JSONDecodeError:
            raise AbortRequest("invalid app template", "该版本应用模板已损坏, 无法升级")

    def get_property_changes(self, tenant, region, user, app, upgrade_group_id, version):
        component_group = tenant_service_group_repo.get_component_group(upgrade_group_id)

        app_template_source = self._app_template_source(app.app_id, component_group.group_key, upgrade_group_id)
        app_template = self._app_template(user.enterprise_id, component_group.group_key, version, app_template_source)

        app_upgrade = AppUpgrade(user.enterprise_id, tenant, region, user, app, version, component_group, app_template,
                                 app_template_source.is_install_from_cloud(), app_template_source.get_market_name())

        return app_upgrade.app_property_changes, app_upgrade.changes()

    @staticmethod
    def get_latest_upgrade_record(tenant: Tenants, app: ServiceGroup, upgrade_group_id=None, record_type=None):
        if upgrade_group_id:
            # check upgrade_group_id
            tenant_service_group_repo.get_component_group(upgrade_group_id)
        record = upgrade_repo.get_last_upgrade_record(tenant.tenant_id, app.app_id, upgrade_group_id, record_type)
        return record.to_dict() if record else None

    @transaction.atomic
    def create_upgrade_record(self, enterprise_id, tenant: Tenants, app: ServiceGroup, upgrade_group_id):
        component_group = tenant_service_group_repo.get_component_group(upgrade_group_id)

        # If there are unfinished record, it is not allowed to create new record
        last_record = upgrade_repo.get_last_upgrade_record(tenant.tenant_id, app.ID, upgrade_group_id)
        if last_record and not last_record.is_finished():
            raise ErrLastRecordUnfinished

        component_group = ComponentGroup(enterprise_id, component_group)
        app_template_source = component_group.app_template_source()

        # create new record
        record = {
            "tenant_id": tenant.tenant_id,
            "group_id": app.app_id,
            "group_key": component_group.app_model_key,
            "group_name": app.app_name,
            "create_time": datetime.now(),
            "is_from_cloud": component_group.is_install_from_cloud(),
            "market_name": app_template_source.get_market_name(),
            "upgrade_group_id": upgrade_group_id,
            "old_version": component_group.version,
            "record_type": AppUpgradeRecordType.UPGRADE.value,
        }
        record = upgrade_repo.create_app_upgrade_record(**record)
        return record.to_dict()

    def list_records(self, tenant_name, region_name, app_id, record_type=None, page=1, page_size=10):
        # list records and pagination
        records = upgrade_repo.list_records_by_app_id(app_id, record_type)
        records = records.exclude(Q(status=1))
        paginator = Paginator(records, page_size)
        records = paginator.page(page)

        self.sync_unfinished_records(tenant_name, region_name, records)

        return [record.to_dict() for record in records], paginator.count

    def sync_unfinished_records(self, tenant_name, region_name, records):
        for record in records:
            if record.is_finished:
                continue
            # synchronize the last unfinished record
            self.sync_record(tenant_name, region_name, record)
            break

    def sync_record(self, tenant_name, region_name, record: AppUpgradeRecord):
        # list component records
        component_records = component_upgrade_record_repo.list_by_app_record_id(record.ID)
        # filter out the finished records
        unfinished = {record.event_id: record for record in component_records if not record.is_finished()}
        # list events
        event_ids = [event_id for event_id in unfinished.keys()]
        body = region_api.get_tenant_events(region_name, tenant_name, event_ids)
        events = body.get("list", [])

        for event in events:
            component_record = unfinished.get(event["EventID"])
            if not component_record:
                continue
            self._update_component_record_status(component_record, event["Status"])

        self._update_app_record_status(record, component_records)

        # save app record and component records
        self.save_upgrade_record(record, component_records)

    def deploy(self, tenant, region_name, user, record: AppUpgradeRecord):
        if not record.can_deploy():
            raise ErrAppUpgradeRecordCanNotDeploy

        # failed events
        component_records = component_upgrade_record_repo.list_by_app_record_id(record.ID)
        component_records = [record for record in component_records]
        failed_component_records = {
            record.event_id: record
            for record in component_records if record.status in
            [UpgradeStatus.PARTIAL_UPGRADED.value, UpgradeStatus.PARTIAL_ROLLBACK.value, UpgradeStatus.DEPLOY_FAILED.value]
        }

        component_ids = [record.service_id for record in failed_component_records.values()]

        try:
            events = app_manage_service.batch_operations(tenant, region_name, user, "deploy", component_ids)
            status = UpgradeStatus.UPGRADING.value \
                if record.record_type == UpgradeType.UPGRADE.value else UpgradeStatus.ROLLING.value
            upgrade_repo.change_app_record_status(record, status)
        except ServiceHandleException as e:
            upgrade_repo.change_app_record_status(record, UpgradeStatus.DEPLOY_FAILED.value)
            raise ErrAppUpgradeDeployFailed(e.msg)
        except Exception as e:
            upgrade_repo.change_app_record_status(record, UpgradeStatus.DEPLOY_FAILED.value)
            raise e
        self._update_component_records(record, failed_component_records.values(), events)

    @staticmethod
    def save_upgrade_record(app_upgrade_record, component_upgrade_records):
        app_upgrade_record.save()
        component_upgrade_record_repo.bulk_update(component_upgrade_records)

    def get_app_upgrade_record(self, tenant_name, region_name, record_id):
        record = upgrade_repo.get_by_record_id(record_id)
        if not record.is_finished():
            self.sync_record(tenant_name, region_name, record)
        return self.serialized_upgrade_record(record)

    @staticmethod
    def list_rollback_record(upgrade_record: AppUpgradeRecord):
        records = upgrade_repo.list_by_rollback_records(upgrade_record.ID)
        return [record.to_dict() for record in records]

    @staticmethod
    def _update_component_records(app_record: AppUpgradeRecord, component_records, events):
        if not events:
            return
        event_ids = {event["service_id"]: event["event_id"] for event in events}
        status = UpgradeStatus.UPGRADING.value \
            if app_record.record_type == UpgradeType.UPGRADE.value else UpgradeStatus.ROLLING.value
        for component_record in component_records:
            event_id = event_ids.get(component_record.service_id)
            if not event_id:
                continue
            component_record.status = status
            component_record.event_id = event_id
        component_upgrade_record_repo.bulk_update(component_records)

    def _update_component_record_status(self, record: ServiceUpgradeRecord, event_status):
        if event_status == "":
            return
        status_table = self.status_tables.get(record.status, {})
        if not status_table:
            logger.warning("unexpected component upgrade record status: {}".format(record.status))
            return
        status = status_table.get(event_status)
        if not status:
            logger.warning("unexpected event status: {}".format(event_status))
            return
        record.status = status

    def _update_app_record_status(self, app_record, component_records):
        if self._is_upgrade_status_unfinished(component_records):
            return
        if self._is_upgrade_status_failed(component_records):
            if app_record.record_type == AppUpgradeRecordType.ROLLBACK.value:
                app_record.status = UpgradeStatus.ROLLBACK_FAILED.value
            else:
                app_record.status = UpgradeStatus.UPGRADE_FAILED.value
            return
        if self._is_upgrade_status_success(component_records):
            if app_record.record_type == AppUpgradeRecordType.ROLLBACK.value:
                app_record.status = UpgradeStatus.ROLLBACK.value
            else:
                app_record.status = UpgradeStatus.UPGRADED.value
            return
        # partial
        if app_record.record_type == AppUpgradeRecordType.UPGRADE.value:
            app_record.status = UpgradeStatus.PARTIAL_UPGRADED.value
        if app_record.record_type == AppUpgradeRecordType.ROLLBACK.value:
            app_record.status = UpgradeStatus.PARTIAL_ROLLBACK.value

    @staticmethod
    def _is_upgrade_status_unfinished(component_records):
        for component_record in component_records:
            if component_record.status in [UpgradeStatus.NOT.value, UpgradeStatus.UPGRADING.value, UpgradeStatus.ROLLING.value]:
                return True
            return False

    @staticmethod
    def _is_upgrade_status_failed(component_records):
        for component_record in component_records:
            if component_record.status not in [UpgradeStatus.ROLLBACK_FAILED.value, UpgradeStatus.UPGRADE_FAILED.value]:
                return False
            return True

    @staticmethod
    def _is_upgrade_status_success(component_records):
        for component_record in component_records:
            if component_record.status in [UpgradeStatus.UPGRADING.value, UpgradeStatus.ROLLING.value]:
                return False
            return True

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
                    app = rainbond_app_repo.get_rainbond_app_by_app_id(group_key)
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
