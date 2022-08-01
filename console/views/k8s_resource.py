# -*- coding: utf8 -*-

from rest_framework.response import Response

from console.services.k8s_resource import k8s_resource_service
from console.views.base import ApplicationView
from www.utils.return_message import general_message


class AppK8ResourceView(ApplicationView):
    def get(self, request, name, *args, **kwargs):
        resources = k8s_resource_service.get_by_app_id_and_name(self.app_id, name)
        resources = resources.values()
        return Response(general_message(200, "success", "查询成功", list=resources))

    def put(self, request, name, *args, **kwargs):
        resource_yaml = request.data.get("resource_yaml", {})
        resource_id = request.data.get("id")
        success = k8s_resource_service.update_k8s_resource(self.enterprise.enterprise_id, self.tenant_name, str(self.app_id),
                                                           resource_yaml, self.region_name, name, resource_id)
        if success == 2:
            return Response(general_message(200, "success", "修改成功"))
        return Response(general_message(400, "success", "修改失败"))

    def delete(self, request, name, *args, **kwargs):
        resource_id = request.data.get("id")
        k8s_resource_service.delete_k8s_resource(self.enterprise.enterprise_id, self.tenant_name, str(self.app_id),
                                                 self.region_name, name, resource_id)
        return Response(general_message(200, "success", "删除成功"))


class AppK8sResourceListView(ApplicationView):
    def get(self, request, *args, **kwargs):
        k8s_resource = k8s_resource_service.list_by_app_id(self.app_id)
        k8s_dict = k8s_resource.values()
        return Response(general_message(200, "success", "查询成功", list=k8s_dict))

    def post(self, request, *args, **kwargs):
        resource_yaml = request.data.get("resource_yaml", {})
        k8s_resource_service.create_k8s_resource(self.enterprise.enterprise_id, self.tenant_name, self.app_id, resource_yaml,
                                                 self.region_name)
        return Response(general_message(200, "success", "创建成功"))
