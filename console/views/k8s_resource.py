# -*- coding: utf8 -*-

from typing import Any

from rest_framework.request import Request
from rest_framework.response import Response

from console.services.enterprise_first_deploy_service import enterprise_first_deploy_service
from console.services.k8s_resource import k8s_resource_service
from console.views.base import ApplicationView
from www.utils.return_message import general_message


class AppK8ResourceView(ApplicationView):
    def get(self, request: Request, name: str, *args: Any, **kwargs: Any) -> Response:
        resource_id = request.GET.get("id")
        # NOTE: resource_id from request params is Optional; service expects str (legacy mismatch, backlog).
        state = k8s_resource_service.get_k8s_resource(self.enterprise.enterprise_id, self.tenant_name, str(self.app_id),
                                                      self.region_name, name, resource_id)  # type: ignore[arg-type]

        return Response(general_message(200, "success", "查询成功", list=state))

    def put(self, request: Request, name: str, *args: Any, **kwargs: Any) -> Response:
        resource_yaml = request.data.get("resource_yaml", {})
        resource_id = request.data.get("id")
        state = k8s_resource_service.update_k8s_resource(self.enterprise.enterprise_id, self.tenant_name, str(self.app_id),
                                                         resource_yaml, self.region_name, name,
                                                         resource_id)  # type: ignore[arg-type]
        if state == 2:
            return Response(general_message(200, "success", "修改成功"))
        return Response(general_message(400, "failed", "修改失败"))

    def delete(self, request: Request, name: str, *args: Any, **kwargs: Any) -> Response:
        resource_id = request.data.get("id")
        result = k8s_resource_service.delete_k8s_resource(
            self.enterprise.enterprise_id,
            self.tenant_name,
            str(self.app_id),
            self.region_name,
            name,
            resource_id,  # type: ignore[arg-type]
            cascade_crd=bool(request.data.get("cascade_crd", False)),
            is_enterprise_admin=self.is_enterprise_admin)
        return Response(general_message(200, "success", "删除成功", bean=result))


class AppK8sResourceDeletionImpactView(ApplicationView):
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        resource_ids = request.data.get("ids")
        impact = k8s_resource_service.preview_delete_k8s_resources(self.enterprise.enterprise_id, self.tenant_name,
                                                                   str(self.app_id), self.region_name, resource_ids)
        return Response(general_message(200, "success", "查询成功", bean=impact))


class AppK8sResourceReconcileView(ApplicationView):
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        result = k8s_resource_service.reconcile_k8s_resources(self.enterprise.enterprise_id, self.tenant_name, str(self.app_id),
                                                              self.region_name)
        return Response(general_message(200, "success", "同步成功", bean=result))


class LegacyAppK8sResourceDeletionImpactView(AppK8sResourceDeletionImpactView, AppK8ResourceView):
    """Keep legacy POST preview requests alongside operations on the named resource."""


class LegacyAppK8sResourceReconcileView(AppK8sResourceReconcileView, AppK8ResourceView):
    """Keep legacy POST reconciliation alongside operations on the named resource."""


class AppK8sResourceListView(ApplicationView):
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        k8s_resource = k8s_resource_service.list_by_app_id(self.app_id)
        k8s_dict = k8s_resource.values()
        return Response(general_message(200, "success", "查询成功", list=k8s_dict))

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        resource_yaml = request.data.get("resource_yaml", {})
        tracker = enterprise_first_deploy_service.safe_begin_deploy_tracking(
            enterprise_id=self.enterprise.enterprise_id,
            tenant_name=self.tenant_name,
            region_name=self.region_name,
            deploy_type=enterprise_first_deploy_service.DEPLOY_TYPE_K8S_RESOURCE,
            operator=getattr(self.user, "nick_name", ""),
            source_language="k8s-resource",
            trigger="k8s_resource_create",
            app_context=enterprise_first_deploy_service.build_service_app_context(
                getattr(self, "app", None), component_count=0),
            workload_context=enterprise_first_deploy_service.build_k8s_resource_workload_context(resource_yaml))
        try:
            k8s_resource_service.create_k8s_resource(self.enterprise.enterprise_id, self.tenant_name, self.app_id,
                                                     resource_yaml, self.region_name)
            enterprise_first_deploy_service.safe_mark_success(tracker)
        except Exception as exc:
            enterprise_first_deploy_service.safe_mark_failure(
                tracker,
                reason=str(exc),
                failure_stage=enterprise_first_deploy_service.FAILURE_STAGE_PREFLIGHT)
            raise
        return Response(general_message(200, "success", "创建成功"))

    def delete(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        resource_ids = request.data.get("ids")
        result = k8s_resource_service.batch_delete_k8s_resource(self.enterprise.enterprise_id,
                                                                self.tenant_name,
                                                                str(self.app_id),
                                                                self.region_name,
                                                                resource_ids,
                                                                cascade_crd=bool(request.data.get("cascade_crd", False)),
                                                                is_enterprise_admin=self.is_enterprise_admin)
        return Response(general_message(200, "success", "删除成功", bean=result))
