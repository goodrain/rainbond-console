# -*- coding: utf8 -*-
from django.views.decorators.cache import never_cache
from rest_framework.response import Response

from console.services.app import app_service
from console.services.virtual_machine import vms
from console.views.app_config.base import AppBaseView
from console.views.base import RegionTenantHeaderView
from www.utils.return_message import general_message


class AppVMTemplateView(AppBaseView):
    @never_cache
    def post(self, request, *args, **kwargs):
        template_name = request.data.get("name", "")
        description = request.data.get("description", "")
        include_data_disks = request.data.get("include_data_disks", True)
        if not template_name:
            return Response(general_message(400, "vm template name required", "请填写模板名称"), status=400)
        status_map = app_service.get_service_status(self.tenant, self.service)
        vm_status = status_map.get("status", "")
        try:
            template = vms.save_vm_template(
                self.service,
                self.response_region,
                self.tenant.tenant_name,
                template_name=template_name,
                vm_status=vm_status,
                description=description,
                include_data_disks=include_data_disks
            )
        except ValueError as err:
            return Response(general_message(409, "vm template forbidden", str(err)), status=409)
        result = general_message(200, "success", "模板任务已启动", bean=template)
        return Response(result, status=result["code"])


class VirtualMachineTemplateListView(RegionTenantHeaderView):
    @never_cache
    def get(self, request, *args, **kwargs):
        data = vms.list_vm_templates(self.tenant.tenant_id)
        result = general_message(200, "success", "查询成功", list=data)
        return Response(result, status=result["code"])


class VirtualMachineTemplateManageView(RegionTenantHeaderView):
    @never_cache
    def get(self, request, *args, **kwargs):
        template_id = kwargs.get("template_id")
        template = vms.get_vm_template_detail(self.tenant.tenant_id, template_id)
        if not template:
            return Response(general_message(404, "vm template not found", "虚拟机模板不存在"), status=404)
        result = general_message(200, "success", "查询成功", bean=template)
        return Response(result, status=result["code"])

    @never_cache
    def put(self, request, *args, **kwargs):
        template_id = kwargs.get("template_id")
        disabled = bool(request.data.get("disabled"))
        template = vms.set_vm_template_disabled(self.tenant.tenant_id, template_id, disabled)
        if not template:
            return Response(general_message(404, "vm template not found", "虚拟机模板不存在"), status=404)
        result = general_message(200, "success", "更新成功", bean=template)
        return Response(result, status=result["code"])


class VirtualMachineTemplateVersionRetryView(RegionTenantHeaderView):
    @never_cache
    def post(self, request, *args, **kwargs):
        template_id = kwargs.get("template_id")
        version_id = kwargs.get("version_id")
        try:
            version = vms.retry_vm_template_version(
                tenant_id=self.tenant.tenant_id,
                template_id=template_id,
                version_id=version_id,
                region_name=self.response_region,
                tenant_name=self.tenant.tenant_name
            )
        except ValueError as err:
            return Response(general_message(409, "vm template retry forbidden", str(err)), status=409)
        if not version:
            return Response(general_message(404, "vm template version not found", "虚拟机模板版本不存在"), status=404)
        result = general_message(200, "success", "模板重试已启动", bean=version)
        return Response(result, status=result["code"])
