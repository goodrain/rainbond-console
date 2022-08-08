from console.services.yaml_k8s_resource import yaml_k8s_resource
from console.views.base import RegionTenantHeaderView
from rest_framework.response import Response

from www.utils.return_message import general_message


class YamlResourceName(RegionTenantHeaderView):
    def get(self, request, *args, **kwargs):
        event_id = request.GET.get("event_id")
        app_id = request.GET.get("group_id")
        namespace = self.tenant.namespace
        tenant_id = self.tenant.tenant_id
        region_id = self.region.region_id
        enterprise_id = self.enterprise.enterprise_id
        res = yaml_k8s_resource.yaml_k8s_resource_name(event_id, app_id, tenant_id, namespace, region_id, enterprise_id)
        return Response(general_message(200, "success", "查询成功", list=res), status=200)


class YamlResourceDetailed(RegionTenantHeaderView):
    def get(self, request, *args, **kwargs):
        event_id = request.GET.get("event_id")
        app_id = request.GET.get("group_id")
        namespace = self.tenant.namespace
        tenant_id = self.tenant.tenant_id
        region_id = self.region.region_id
        enterprise_id = self.enterprise.enterprise_id
        res = yaml_k8s_resource.yaml_k8s_resource_detailed(event_id, app_id, tenant_id, namespace, region_id, enterprise_id)
        return Response(general_message(200, "success", "查询成功", list=res), status=200)

    def post(self, request, *args, **kwargs):
        event_id = request.data.get("event_id")
        app_id = request.data.get("group_id")
        namespace = self.tenant.namespace
        tenant = self.tenant
        enterprise_id = self.enterprise.enterprise_id
        res = yaml_k8s_resource.yaml_k8s_resource_import(event_id, app_id, tenant, namespace, self.region, enterprise_id,
                                                         self.user)
        return Response(general_message(200, "success", "查询成功", list=res), status=200)
