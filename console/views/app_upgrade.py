# coding: utf-8
"""升级从云市安装的应用"""
import logging
from enum import Enum

from console.exception.main import ServiceHandleException
from console.repositories.upgrade_repo import upgrade_repo
from console.services.group_service import group_service
from console.services.market_app_service import market_app_service
from console.services.upgrade_services import upgrade_service
from console.utils.reqparse import parse_argument, parse_item
from console.utils.response import MessageResponse
from console.views.base import ApplicationView, RegionTenantHeaderView, AppUpgradeRecordView
# model
from console.models.main import AppUpgradeRecordType

logger = logging.getLogger('default')


class GroupAppView(RegionTenantHeaderView):
    def get(self, request, group_id, *args, **kwargs):
        """查询当前应用下的应用模版列表及可升级性"""
        group_id = int(group_id)
        group = group_service.get_group_or_404(self.tenant, self.response_region, group_id)
        apps = []
        try:
            apps = market_app_service.get_market_apps_in_app(self.response_region, self.tenant, group)
        except ServiceHandleException as e:
            if e.status_code != 404:
                raise e
        return MessageResponse(msg="success", list=apps)


class AppUpgradeVersion(RegionTenantHeaderView):
    def get(self, request, group_id, *args, **kwargs):
        """获取安装的应用模版的可升级版本"""
        group_key = parse_argument(
            request, 'group_key', value_type=str, required=True, error='group_key is a required parameter')

        upgrade_group_id = parse_argument(
            request, 'upgrade_group_id', default=None, value_type=int, error='upgrade_group_id is a required parameter')

        if upgrade_group_id == 0 or upgrade_group_id == "0":
            upgrade_group_id = None
        # get app model upgrade versions
        versions = market_app_service.get_models_upgradeable_version(self.tenant.enterprise_id, group_key, group_id,
                                                                     upgrade_group_id)
        return MessageResponse(msg="success", list=list(versions))


class AppLastUpgradeRecordView(ApplicationView):
    def get(self, request, app_id, *args, **kwargs):
        upgrade_group_id = parse_argument(request, "upgrade_group_id")
        record_type = parse_argument(request, "record_type")
        record = upgrade_service.get_latest_upgrade_record(self.team, self.app, upgrade_group_id, record_type)
        return MessageResponse(msg="success", bean=record)


class AppUpgradeRecordsView(ApplicationView):
    def get(self, request, app_id, *args, **kwargs):
        page = parse_argument(request, 'page', value_type=int, default=1)
        page_size = parse_argument(request, 'page_size', value_type=int, default=10)
        records, total = upgrade_service.list_records(self.tenant_name, self.region_name, self.app_id,
                                                      AppUpgradeRecordType.UPGRADE.value, page, page_size)
        return MessageResponse(msg="success", bean={"total": total}, list=records)

    def post(self, request, app_id, *args, **kwargs):
        upgrade_group_id = parse_item(request, 'upgrade_group_id', required=True)
        record = upgrade_service.create_upgrade_record(self.user.enterprise_id, self.tenant, self.app, upgrade_group_id)
        return MessageResponse(msg="success", bean=record)


class AppUpgradeRecordDetailView(RegionTenantHeaderView):
    def get(self, request, group_id, record_id, *args, **kwargs):
        record = upgrade_service.get_app_upgrade_record(self.tenant_name, self.region_name, record_id)
        return MessageResponse(msg="success", bean=record)


class UpgradeType(Enum):
    UPGRADE = 'upgrade'
    ADD = 'add'


class AppUpgradeInfoView(ApplicationView):
    def get(self, request, group_id, *args, **kwargs):
        upgrade_group_id = parse_argument(
            request, 'upgrade_group_id', default=None, value_type=int, error='upgrade_group_id is a required parameter')
        version = parse_argument(request, 'version', value_type=str, required=True, error='version is a required parameter')
        changes = upgrade_service.get_property_changes(self.tenant, self.region_name, self.user, self.app, upgrade_group_id,
                                                       version)
        return MessageResponse(msg="success", list=changes)


class AppUpgradeRollbackView(AppUpgradeRecordView):
    def post(self, request, group_id, record_id, *args, **kwargs):
        record = upgrade_service.restore(self.tenant, self.region_name, self.user, self.app, self.app_upgrade_record)
        return MessageResponse(msg="success", bean=record)


class AppUpgradeDetailView(ApplicationView):
    def get(self, request, upgrade_group_id, *args, **kwargs):
        record_id = parse_argument(
            request, 'record_id', value_type=str, required=True, error='record_id is a required parameter')
        record = upgrade_repo.get_by_record_id(record_id)
        # get app model upgrade versions
        versions = market_app_service.list_app_upgradeable_versions(self.tenant.enterprise_id, record)
        return MessageResponse(msg="success", bean={'record': record.to_dict(), 'versions': versions})


class AppUpgradeComponentListView(ApplicationView):
    def get(self, request, upgrade_group_id, *args, **kwargs):
        # same as app_key or group_key
        app_model_key = parse_argument(
            request, 'app_model_key', value_type=str, required=True, error='app_model_key is a required parameter')
        components = market_app_service.list_rainbond_app_components(self.user.enterprise_id, self.tenant, self.app_id,
                                                                     app_model_key, upgrade_group_id)
        return MessageResponse(msg="success", list=components)


class AppUpgradeView(AppUpgradeRecordView):
    def post(self, request, app_id, record_id, *args, **kwargs):
        version = parse_item(request, "version", required=True)
        # It is not yet possible to upgrade based on services, which is user-specified attribute changes
        components = parse_item(request, "services", default=[])
        component_keys = [cpt["service"]["service_key"] for cpt in components]
        record = upgrade_service.upgrade(
            self.tenant,
            self.region_name,
            self.user,
            version,
            self.app_upgrade_record,
            component_keys,
        )
        return MessageResponse(msg="success", msg_show="升级成功", bean=record)


class AppUpgradeDeployView(AppUpgradeRecordView):
    def post(self, request, app_id, record_id, *args, **kwargs):
        upgrade_service.deploy(self.tenant, self.region_name, self.user, self.app_upgrade_record)
        return MessageResponse(msg="success", msg_show="部署成功")


class AppRollbackRecordsView(AppUpgradeRecordView):
    def get(self, request, app_id, upgrade_record_id, *args, **kwargs):
        records = upgrade_service.list_rollback_record(self.app_upgrade_record)
        return MessageResponse(msg="success", msg_show="获取成功", list=records)
