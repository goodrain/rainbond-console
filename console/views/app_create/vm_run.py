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
from console.services.app_config import volume_service
from console.services.app import app_service
from console.services.virtual_machine import vms
from console.views.base import RegionTenantHeaderView
from www.utils.return_message import general_message
from console.services.group_service import group_service

logger = logging.getLogger("default")
PUBLIC_VM_IMAGE_NAMES = {"centos7.9", "anolisos7.9", "deepin20.9", "ubuntu23.10"}


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
        source_type = request.data.get("source_type", "")
        asset_id = request.data.get("asset_id", "")
        template_id = request.data.get("template_id", "")
        template_version_id = request.data.get("template_version_id", "")
        event_id = request.data.get("event_id", "")
        vm_url = request.data.get("vm_url", "")
        boot_mode = request.data.get("boot_mode", "")
        gpu_enabled = request.data.get("gpu_enabled", False)
        gpu_resources = request.data.get("gpu_resources", [])
        usb_enabled = request.data.get("usb_enabled", False)
        usb_resources = request.data.get("usb_resources", [])
        network_mode = request.data.get("network_mode", "random")
        network_name = request.data.get("network_name", "")
        fixed_ip = request.data.get("fixed_ip", "")
        os_family = request.data.get("os_family", "")
        runtime_config = {
            "gpu_enabled": gpu_enabled,
            "gpu_resources": gpu_resources,
            "usb_enabled": usb_enabled,
            "usb_resources": usb_resources,
            "network_mode": network_mode,
            "network_name": network_name,
            "fixed_ip": fixed_ip,
            "os_family": os_family
        }
        if k8s_component_name and app_service.is_k8s_component_name_duplicate(group_id, k8s_component_name):
            raise ErrK8sComponentNameExists
        try:
            vms.validate_vm_runtime_config(runtime_config)
            asset = None
            template_payload = None
            guest_os_name = ""
            if event_id != "" or vm_url != "":
                asset = vm_repo.get_vm_image_instance_by_tenant_id_and_name(self.tenant.tenant_id, image_name)
                if asset:
                    if image_name in PUBLIC_VM_IMAGE_NAMES:
                        image = asset.image_url
                        asset_id = asset.ID
                    else:
                        raise ErrVMImageNameExists
                else:
                    image = self.tenant.namespace + ":" + image_name
                    resolved_source_type = source_type
                    if not resolved_source_type:
                        if event_id:
                            resolved_source_type = "upload"
                        elif image_name in PUBLIC_VM_IMAGE_NAMES:
                            resolved_source_type = "public"
                        else:
                            resolved_source_type = "url"
                    asset = vms.create_vm_image_asset(
                        self.tenant.tenant_id,
                        image_name,
                        image,
                        source_type=resolved_source_type,
                        source_uri=vm_url or "/grdata/package_build/temp/events/{}".format(event_id),
                        arch=arch,
                        os_name=image_name,
                        build_event_id=event_id,
                        is_public_template=resolved_source_type == "public",
                        boot_mode=boot_mode,
                        extra={
                            "created_from": "vm_run"
                        })
                    asset_id = asset.ID
                guest_os_name = getattr(asset, "os_name", "") or image_name
            else:
                if template_version_id:
                    try:
                        template_payload = vms.resolve_vm_template_for_create(
                            self.tenant.tenant_id, template_id, template_version_id
                        )
                    except ValueError as err:
                        return Response(general_message(409, "vm template not ready", str(err)), status=409)
                    if not template_payload:
                        return Response(general_message(404, "vm template not found", "虚拟机模板不存在"), status=404)
                    image = template_payload["image_url"]
                    asset_id = template_payload.get("asset_id") or asset_id
                    image_name = image_name or self.template_name_from_payload(template_payload)
                    runtime_snapshot = template_payload.get("runtime_snapshot", {})
                    if "boot_mode" not in request.data and runtime_snapshot.get("boot_mode"):
                        boot_mode = runtime_snapshot.get("boot_mode")
                    for key in (
                            "network_mode", "network_name", "fixed_ip", "os_family", "gpu_enabled", "gpu_resources",
                            "usb_enabled", "usb_resources"):
                        if key not in request.data and key in runtime_snapshot:
                            runtime_config[key] = runtime_snapshot.get(key)
                    guest_os_name = (
                        template_payload.get("os_name") or
                        runtime_snapshot.get("os_name") or
                        image_name
                    )
                if asset_id:
                    asset = vm_repo.get_vm_image_instance_by_id(self.tenant.tenant_id, asset_id)
                if not asset and image_name:
                    asset = vm_repo.get_vm_image_instance_by_tenant_id_and_name(self.tenant.tenant_id, image_name)
                if not template_payload and asset and not vms.is_vm_asset_ready(asset):
                    return Response(general_message(409, "vm image not ready", "虚拟机镜像导出尚未完成，请稍后再试"), status=409)
                if not template_payload:
                    image = asset.image_url if asset else ""
                if asset:
                    asset_id = asset.ID
                    if not guest_os_name:
                        guest_os_name = getattr(asset, "os_name", "") or image_name
                if not image:
                    return Response(general_message(404, "vm image not found", "虚拟机镜像不存在"), status=404)
            code, msg_show, new_service = app_service.create_vm_run_app(
                self.response_region, self.tenant, self.user, service_cname, k8s_component_name, image, arch, event_id, vm_url)
            if code != 200:
                return Response(general_message(code, "service create fail", msg_show), status=code)
            # The VM component is only persisted in console at this point.
            # Region-side service registration happens later and will sync these attrs.
            vms.save_vm_runtime_config(
                self.tenant.tenant_id,
                new_service.service_id,
                {
                    **runtime_config,
                    "asset_id": asset_id,
                    "template_id": template_payload.get("template_id") if template_payload else "",
                    "template_version_id": template_payload.get("template_version_id") if template_payload else "",
                    "disk_layout": template_payload.get("disk_layout") if template_payload else [],
                    "boot_mode": boot_mode,
                    "os_name": guest_os_name
                })
            if template_payload:
                for disk in template_payload.get("data_disks", []):
                    settings = {
                        "volume_capacity": self.bytes_to_gib(disk.get("size_bytes"))
                    }
                    volume_service.add_service_volume(
                        self.tenant,
                        new_service,
                        "/disk",
                        "vm-file",
                        disk.get("disk_key") or "disk",
                        "",
                        settings,
                        self.user.nick_name,
                        mode=None
                    )
                vms.save_vm_disk_imports(
                    self.tenant.tenant_id,
                    new_service.service_id,
                    template_payload.get("data_disks", [])
                )
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

    @staticmethod
    def bytes_to_gib(value):
        try:
            size_bytes = int(value or 0)
        except (TypeError, ValueError):
            size_bytes = 0
        if size_bytes <= 0:
            return 10
        gib = size_bytes // (1024 * 1024 * 1024)
        if size_bytes % (1024 * 1024 * 1024) != 0:
            gib += 1
        return gib or 10

    @staticmethod
    def template_name_from_payload(payload):
        return "template-image-{}".format(payload.get("template_version_id"))
