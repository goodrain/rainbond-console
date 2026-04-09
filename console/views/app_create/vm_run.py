# -*- coding: utf8 -*-
"""
  Created by leon on 18/1/5.
"""
import logging

from django.views.decorators.cache import never_cache
from rest_framework.response import Response
from console.exception.bcode import ErrK8sComponentNameExists, ErrVMImageNameExists
from console.exception.main import ResourceNotEnoughException
from console.repositories.virtual_machine import vm_repo
from console.services.app import app_service
from console.services.virtual_machine import vms
from console.views.base import RegionTenantHeaderView
from www.utils.return_message import general_message
from console.services.group_service import group_service

logger = logging.getLogger("default")


class VMRunCreateView(RegionTenantHeaderView):
    @never_cache
    def post(self, request, *args, **kwargs):
        """
        vm image 创建组件
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: group_id
              description: 组id
              required: true
              type: string
              paramType: form
            - name: service_cname
              description: 组件名称
              required: true
              type: string
              paramType: form
            - name: docker_cmd
              description: docker运行命令
              required: true
              type: string
              paramType: form
            - name: image_type
              description: 创建方式 docker_run或docker_image
              required: true
              type: string
              paramType: form

        """
        group_id = request.data.get("group_id", -1)
        service_cname = request.data.get("service_cname", None)
        k8s_component_name = request.data.get("k8s_component_name", "")
        arch = request.data.get("arch", "amd64")
        image_name = request.data.get("image_name", "")
        clone_source_name = request.data.get("clone_source_name", "")
        event_id = request.data.get("event_id", "")
        vm_url = request.data.get("vm_url", "")
        gpu_enabled = request.data.get("gpu_enabled", False)
        gpu_resources = request.data.get("gpu_resources", [])
        usb_enabled = request.data.get("usb_enabled", False)
        usb_resources = request.data.get("usb_resources", [])
        network_mode = request.data.get("network_mode", "random")
        network_name = request.data.get("network_name", "")
        fixed_ip = request.data.get("fixed_ip", "")
        runtime_config = {
            "gpu_enabled": gpu_enabled,
            "gpu_resources": gpu_resources,
            "usb_enabled": usb_enabled,
            "usb_resources": usb_resources,
            "network_mode": network_mode,
            "network_name": network_name,
            "fixed_ip": fixed_ip
        }
        if k8s_component_name and app_service.is_k8s_component_name_duplicate(group_id, k8s_component_name):
            raise ErrK8sComponentNameExists
        try:
            vms.validate_vm_runtime_config(runtime_config)
            if clone_source_name:
                image = vm_repo.get_vm_image_by_tenant_id_and_name(self.tenant.tenant_id, image_name)
                if image.exists():
                    raise ErrVMImageNameExists
                cloned = vms.clone_vm_image(self.tenant.tenant_id, clone_source_name, image_name)
                if not cloned:
                    return Response(general_message(404, "vm image clone fail", "原始镜像不存在"), status=404)
                image = cloned.image_url
            elif event_id != "" or vm_url != "":
                image = vm_repo.get_vm_image_by_tenant_id_and_name(self.tenant.tenant_id, image_name)
                if image.exists():
                    if image_name == "centos7.9" or image_name == "anolisos7.9" \
                            or image_name == "deepin20.9" or image_name == "ubuntu23.10":
                        image = vm_repo.get_vm_image_url_by_tenant_id_and_name(self.tenant.tenant_id, image_name)
                    else:
                        raise ErrVMImageNameExists
                else:
                    image = self.tenant.namespace + ":" + image_name
                    vm_repo.create_vm_image(
                        tenant_id=self.tenant.tenant_id,
                        name=image_name,
                        image_url=image,
                    )
            else:
                image = vm_repo.get_vm_image_url_by_tenant_id_and_name(self.tenant.tenant_id, image_name)
                if not image:
                    return Response(general_message(404, "vm image not found", "虚拟机镜像不存在"), status=404)
            code, msg_show, new_service = app_service.create_vm_run_app(
                self.response_region, self.tenant, self.user, service_cname, k8s_component_name, image, arch, event_id, vm_url)
            if code != 200:
                return Response(general_message(code, "service create fail", msg_show), status=code)
            vms.save_vm_runtime_config(
                self.tenant.tenant_id,
                new_service.service_id,
                runtime_config)
            code, msg_show = group_service.add_service_to_group(self.tenant, self.response_region, group_id,
                                                                new_service.service_id)
            if code != 200:
                logger.debug("service.create", msg_show)
            result = general_message(200, "success", "创建成功", bean=new_service.to_dict())
        except ResourceNotEnoughException as re:
            raise re
        except ValueError as err:
            return Response(general_message(400, "invalid vm runtime config", str(err)), status=400)
        return Response(result, status=result["code"])
