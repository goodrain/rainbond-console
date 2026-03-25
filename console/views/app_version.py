# coding: utf-8
"""应用版本"""

from console.exception.main import ServiceHandleException
from console.services.app_version_service import app_version_service
from console.utils.reqparse import parse_item
from console.utils.response import MessageResponse
from console.views.base import ApplicationView


class AppVersionOverviewView(ApplicationView):
    def get(self, request, group_id, *args, **kwargs):
        overview = app_version_service.get_overview(self.tenant, self.region, self.user, self.app)
        return MessageResponse(msg="success", bean=overview)


class AppVersionSnapshotListView(ApplicationView):
    def get(self, request, group_id, *args, **kwargs):
        versions = app_version_service.list_snapshot_versions(self.app.ID)
        return MessageResponse(
            msg="success",
            list=versions,
            bean={"has_template": bool(app_version_service.get_relation(self.app.ID))}
        )

    def post(self, request, group_id, *args, **kwargs):
        version = parse_item(request, "version", default="")
        version_alias = parse_item(request, "version_alias", default="")
        app_version_info = parse_item(request, "app_version_info", default="")
        share_service_list = parse_item(request, "share_service_list", default=None)
        share_plugin_list = parse_item(request, "share_plugin_list", default=None)
        share_k8s_resources = parse_item(request, "share_k8s_resources", default=None)
        version = app_version_service.create_snapshot(
            self.tenant, self.region, self.user, self.app, version=version, version_alias=version_alias,
            app_version_info=app_version_info,
            share_info={
                "share_service_list": share_service_list,
                "share_plugin_list": share_plugin_list,
                "share_k8s_resources": share_k8s_resources,
            }
        )
        msg_show = "创建快照成功"
        if version and version.get("created") is False:
            msg_show = "当前没有新的变更，无需创建快照"
        return MessageResponse(msg="success", msg_show=msg_show, bean=version)


class AppVersionSnapshotDetailView(ApplicationView):
    def get(self, request, group_id, version_id, *args, **kwargs):
        detail = app_version_service.get_snapshot_detail(self.app.ID, version_id)
        if not detail:
            raise ServiceHandleException("snapshot not found", "快照不存在", status_code=404)
        return MessageResponse(msg="success", bean=detail)

    def delete(self, request, group_id, version_id, *args, **kwargs):
        app_version_service.delete_snapshot(self.app.ID, version_id)
        return MessageResponse(msg="success", msg_show="删除成功")


class AppVersionSnapshotRollbackView(ApplicationView):
    def post(self, request, group_id, version_id, *args, **kwargs):
        record = app_version_service.rollback_snapshot(self.tenant, self.region, self.user, self.app, version_id)
        if not record:
            raise ServiceHandleException("snapshot rollback not supported", "当前快照暂不支持回滚", status_code=400)
        return MessageResponse(msg="success", msg_show="回滚任务已创建", bean=record)


class AppVersionRollbackRecordListView(ApplicationView):
    def get(self, request, group_id, *args, **kwargs):
        records = app_version_service.list_rollback_records(self.tenant_name, self.region_name, self.app.ID)
        return MessageResponse(msg="success", list=records)


class AppVersionRollbackRecordDetailView(ApplicationView):
    def get(self, request, group_id, record_id, *args, **kwargs):
        record = app_version_service.get_rollback_record(self.tenant_name, self.region_name, self.app.ID, record_id)
        if not record:
            raise ServiceHandleException("rollback record not found", "回滚记录不存在", status_code=404)
        return MessageResponse(msg="success", bean=record)
