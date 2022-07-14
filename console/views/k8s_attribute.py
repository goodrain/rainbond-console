# -*- coding: utf8 -*-

from rest_framework.response import Response

from console.views.app_config.base import AppBaseView
from console.services.k8s_attribute import k8s_attribute_service
from www.utils.return_message import general_message


class ComponentK8sAttributeView(AppBaseView):
    def get(self, request, *args, **kwargs):
        attributes = k8s_attribute_service.list_by_component_ids([self.service.service_id])
        return Response(general_message(200, "success", "查询成功", list=attributes))

    def put(self, request, *args, **kwargs):
        attributes = request.data.get("list", [])
        k8s_attribute_service.create_or_update_attributes(self.tenant, self.service, self.region_name, attributes)
        return Response(general_message(200, "success", "修改成功"))
