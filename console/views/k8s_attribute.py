# -*- coding: utf8 -*-

from rest_framework.response import Response

from console.exception.main import AbortRequest
from console.views.app_config.base import AppBaseView
from console.services.k8s_attribute import k8s_attribute_service
from www.utils.return_message import general_message


class ComponentK8sAttributeView(AppBaseView):
    def get(self, request, name, *args, **kwargs):
        attributes = k8s_attribute_service.get_by_component_ids_and_name(self.service.service_id, name)
        return Response(general_message(200, "success", "查询成功", list=attributes))

    def put(self, request, name, *args, **kwargs):
        attribute = request.data.get("attribute", {})
        if name != attribute.get("name", ""):
            raise AbortRequest(400, "参数错误")
        attribute['operator'] = self.user.nick_name
        k8s_attribute_service.update_k8s_attribute(self.tenant, self.service, self.region_name, attribute)
        return Response(general_message(200, "success", "修改成功"))

    def delete(self, request, name, *args, **kwargs):
        k8s_attribute_service.delete_k8s_attribute(self.tenant, self.service, self.region_name, name,self.user.nick_name)
        return Response(general_message(200, "success", "删除成功"))


class ComponentK8sAttributeListView(AppBaseView):
    def get(self, request, *args, **kwargs):
        attributes = k8s_attribute_service.list_by_component_ids([self.service.service_id])
        return Response(general_message(200, "success", "查询成功", list=attributes))

    def post(self, request, *args, **kwargs):
        attribute = request.data.get("attribute", {})
        attribute['operator'] = self.user.nick_name
        k8s_attribute_service.create_k8s_attribute(self.tenant, self.service, self.region_name, attribute)
        attribute['operator'] = self.user.nick_name
        return Response(general_message(200, "success", "创建成功"))
