import logging
import json

from datetime import datetime
from typing import Any, Optional, Tuple

from console.exception.main import ServiceHandleException
from console.models.main import ComponentK8sAttributes
from console.repositories.k8s_attribute import k8s_attribute_repo
from console.services.vm_boot_source import (
    build_vm_runtime_image_name,
    requires_vm_source_build,
    resolve_vm_boot_source as resolve_vm_boot_source_binding,
)
from console.repositories.virtual_machine import vm_repo
from www.apiclient.regionapi import RegionInvokeApi
from www.apiclient.regionapibaseclient import RegionApiBaseHttpClient
from www.models.main import (
    Tenants,
    TenantServiceInfo,
    VirtualMachineImage,
)

region_api = RegionInvokeApi()
logger = logging.getLogger("default")

INTERNAL_VM_IMAGE_SOURCE_TYPES = ("upload", "url", "public", "clone")
INTERNAL_REGISTRY_HOSTS = ("goodrain.me", "rbd-hub:5000")

VM_RUNTIME_ATTR_SPECS = {
    "vm_os_name": "string",
    "vm_gpu_enabled": "string",
    "vm_gpu_resources": "json",
    "vm_gpu_count": "string",
    "vm_usb_enabled": "string",
    "vm_usb_resources": "json",
    "vm_asset_id": "string",
    "vm_asset_clone_source": "string",
    "vm_boot_mode": "string",
    "vm_boot_source_format": "string",
    "vm_disk_layout": "json",
}
VM_RUNTIME_MANAGED_KEYS = set(VM_RUNTIME_ATTR_SPECS.keys())
VM_RUNTIME_LIST_KEYS = ("vm_gpu_resources", "vm_usb_resources")
VM_DISK_IMPORT_ATTR_NAME = "vm_disk_imports"
VM_DISK_ASSET_KIND = "disk"
VM_DISK_ROLE_ROOT = "root"
VM_DISK_ROLE_DATA = "data"
VM_DISK_ROLE_INSTALLER = "installer"
VM_DISK_SOURCE_KIND_VOLUME = "volume"
VM_DISK_SOURCE_KIND_INSTALLER = "installer_media"
VM_DISK_SOURCE_KIND_CONTAINER_DISK = "container_disk"
VM_DISK_DEVICE_DISK = "disk"
VM_DISK_DEVICE_CDROM = "cdrom"
VM_DISK_DEVICE_LUN = "lun"
VM_DISK_INSTALLER_KEY = "vmimage"
VM_DISK_ROOT_KEY = "disk"
VM_DISK_PATH_TO_DEVICE_TYPE = {
    "/disk": VM_DISK_DEVICE_DISK,
    "/cdrom": VM_DISK_DEVICE_CDROM,
    "/lun": VM_DISK_DEVICE_LUN,
}


class VirtualMachineService(object):
    def ensure_vm_platform_running(self, enterprise_id: Optional[str], region_name: str) -> None:
        from console.services.platform_plugin_service import platform_plugin_service

        if not enterprise_id or not region_name:
            raise ServiceHandleException(
                msg="missing vm platform guard context",
                msg_show="虚拟机功能状态校验失败，请联系管理员",
                status_code=500,
            )
        platform_plugin_service.ensure_vm_plugin_running(enterprise_id, region_name)

    def resolve_vm_boot_source(self, tenant: Tenants, image_name: str, image_url: str, source_uri: str = "") -> Any:
        return resolve_vm_boot_source_binding(tenant, image_name, image_url, source_uri=source_uri)

    def create_vm_export(self, tenant: Tenants, service: TenantServiceInfo, name: str = "",
                         description: str = "") -> dict:
        export_name = str(name or getattr(service, "service_id", "") or "").strip()
        if not export_name:
            raise ValueError("vm export name is required")
        _, body = region_api.create_vm_export(
            service.service_region,
            tenant.tenant_name,
            service.service_alias,
            {
                "name": export_name,
                "description": description or "",
            }
        )
        return body.get("bean", {}) if isinstance(body, dict) else {}

    def get_vm_export(self, tenant: Tenants, service: TenantServiceInfo, name: str) -> dict:
        export_name = str(name or "").strip()
        if not export_name:
            raise ValueError("vm export name is required")
        _, body = region_api.get_vm_export(
            service.service_region,
            tenant.tenant_name,
            service.service_alias,
            export_name,
        )
        return body.get("bean", {}) if isinstance(body, dict) else {}

    def set_vm_fixed_pod_ip(self, tenant: Tenants, service: TenantServiceInfo, enabled: bool) -> dict:
        _, body = region_api.set_vm_fixed_pod_ip(
            service.service_region,
            tenant.tenant_name,
            service.service_alias,
            {"enabled": bool(enabled)}
        )
        bean = body.get("bean", {}) if isinstance(body, dict) else {}
        self._persist_vm_fixed_pod_ip_state(service, bean, enabled)
        return bean

    def list_vm_image(self, tenant_id: str, region_name: Optional[str] = None,
                      tenant_name: Optional[str] = None) -> list:
        vm_images = list(vm_repo.get_vm_images_by_tenant_id(tenant_id))
        source_ids = [vm_image.source_asset_id for vm_image in vm_images if vm_image.source_asset_id]
        source_map = {}
        if source_ids:
            source_map = {
                image.ID: image
                for image in VirtualMachineImage.objects.filter(tenant_id=tenant_id, ID__in=source_ids)
            }
        # NOTE: source_asset_id is an int model field (Optional); dict.get tolerates None at runtime.
        return [
            self.serialize_vm_image(vm_image, source_map.get(vm_image.source_asset_id))  # type: ignore[arg-type]
            for vm_image in vm_images
        ]

    def get_vm_asset(self, tenant_id: str, asset_id: str, region_name: Optional[str] = None,
                     tenant_name: Optional[str] = None) -> Optional[dict]:
        vm_image = vm_repo.get_vm_image_instance_by_id(tenant_id, asset_id)
        if not vm_image:
            return None
        source_asset = None
        if vm_image.source_asset_id:
            # NOTE: source_asset_id is an int model field used as a str identifier (.ID-as-str pattern).
            source_asset = vm_repo.get_vm_image_instance_by_id(
                tenant_id, vm_image.source_asset_id)  # type: ignore[arg-type]
        return self.serialize_vm_image(vm_image, source_asset)

    def create_vm_image_asset(self, tenant_id: str, name: str, image_url: str,
                              **params: Any) -> VirtualMachineImage:
        payload = self._normalize_asset_payload({
            "tenant_id": tenant_id,
            "name": name,
            "image_url": image_url,
            **params
        })
        logger.info(
            "vm asset create prepared: tenant_id=%s name=%s source_type=%s format=%s image=%s source_uri=%s build_event_id=%s",
            tenant_id,
            payload.get("name", ""),
            payload.get("source_type", ""),
            payload.get("format", ""),
            payload.get("image_url", ""),
            payload.get("source_uri", ""),
            payload.get("build_event_id", ""),
        )
        return vm_repo.create_vm_image(**payload)

    def get_vm_capabilities(self, region_name: str, tenant_name: str) -> dict:
        _, body = region_api.get_vm_capabilities(region_name, tenant_name)
        # NOTE: regionapi returns Optional[Dict]; .get is unguarded (potential latent None-bug).
        return body.get("bean", {})  # type: ignore[union-attr]

    def delete_vm_image(self, tenant_id: str, asset_id: str, region_name: Optional[str] = None,
                        tenant_name: Optional[str] = None) -> Tuple[int, dict]:
        vm_image = vm_repo.get_vm_image_instance_by_id(tenant_id, asset_id)
        if not vm_image:
            return 0, {}
        if self.get_vm_asset_reference_count(tenant_id, vm_image) > 0:
            raise ValueError("vm asset is still referenced")
        self.delete_vm_image_manifest_if_needed(tenant_id, vm_image, region_name, tenant_name)
        return vm_repo.delete_vm_image_by_id(tenant_id, asset_id)

    def delete_vm_image_manifest_if_needed(self, tenant_id: str, vm_image: VirtualMachineImage,
                                           region_name: Optional[str] = None,
                                           tenant_name: Optional[str] = None) -> bool:
        if not self.should_delete_vm_image_manifest(tenant_id, vm_image, region_name, tenant_name):
            return False
        try:
            region_api.delete_registry_image_manifest(region_name, tenant_name, vm_image.image_url)  # type: ignore[arg-type]
            return True
        except ServiceHandleException:
            raise
        except RegionApiBaseHttpClient.CallApiError as err:
            body = err.body if isinstance(err.body, dict) else {}
            raise ServiceHandleException(
                msg="delete vm image manifest failed",
                msg_show=body.get("msg_show") or body.get("msg") or "底层镜像删除失败，请稍后重试",
                status_code=getattr(err, "status", 500) or 500,
                error_code=body.get("code") or getattr(err, "status", 500),
                bean=body.get("bean") if isinstance(body, dict) else None)

    def should_delete_vm_image_manifest(self, tenant_id: str, vm_image: VirtualMachineImage,
                                        region_name: Optional[str] = None,
                                        tenant_name: Optional[str] = None) -> bool:
        if not region_name or not tenant_name or not vm_image or not vm_image.image_url:
            return False
        if vm_repo.get_vm_image_count_by_image_url(tenant_id, vm_image.image_url) > 1:
            return False
        return self.is_internal_vm_registry_image(vm_image)

    def is_internal_vm_registry_image(self, vm_image: VirtualMachineImage) -> bool:
        image_url = str(getattr(vm_image, "image_url", "") or "").strip()
        if not image_url or image_url.startswith(("http://", "https://", "/")):
            return False
        source_type = str(getattr(vm_image, "source_type", "") or "").strip().lower()
        host = self.extract_registry_host(image_url)
        if host and host not in INTERNAL_REGISTRY_HOSTS:
            return False
        if source_type in INTERNAL_VM_IMAGE_SOURCE_TYPES:
            return True
        source_uri = str(getattr(vm_image, "source_uri", "") or "").strip()
        return source_uri.startswith(("http://", "https://", "/grdata/"))

    def extract_registry_host(self, image_url: str) -> str:
        image_name = image_url.rsplit(":", 1)[0] if ":" in image_url.rsplit("/", 1)[-1] else image_url
        first_segment = image_name.split("/", 1)[0]
        if first_segment == "localhost" or "." in first_segment or ":" in first_segment:
            return first_segment.lower()
        return ""

    def get_vm_current_pod_ip(self, tenant: Tenants, service: TenantServiceInfo) -> str:
        if getattr(service, "extend_method", "") != "vm" or not tenant:
            return ""
        try:
            body = region_api.get_service_pods(
                service.service_region,
                tenant.tenant_name,
                service.service_alias,
                tenant.enterprise_id  # type: ignore[arg-type]
            )
        except Exception as err:
            logger.exception(err)
            return ""

        bean = body.get("bean", {}) if isinstance(body, dict) else {}
        if not isinstance(bean, dict):
            return ""

        def pick_pod_ip(pods: Any, running_only: bool = False) -> str:
            for pod in pods or []:
                if not isinstance(pod, dict):
                    continue
                pod_ip = str(pod.get("pod_ip") or "").strip()
                if not pod_ip:
                    continue
                pod_status = str(pod.get("pod_status") or "").strip().lower()
                if running_only and pod_status != "running":
                    continue
                return pod_ip
            return ""

        for running_only in (True, False):
            for group_key in ("new_pods", "old_pods"):
                pod_ip = pick_pod_ip(bean.get(group_key), running_only=running_only)
                if pod_ip:
                    return pod_ip
        return ""

    def get_vm_profile(self, service: TenantServiceInfo, connections: Optional[dict] = None,
                       current_pod_ip: str = "", runtime_status: Optional[dict] = None) -> dict:
        if getattr(service, "extend_method", "") != "vm":
            return {}
        runtime = self.get_vm_runtime_config(service.service_id)
        asset = self.get_vm_asset_for_service(service, runtime.get("asset_id"))
        vm_connections = dict(connections or {
            "vnc_url": "",
            "console_url": ""
        })
        if not current_pod_ip:
            vm_connections["vnc_url"] = ""
            vm_connections["console_url"] = ""
        return {
            "asset": self.serialize_vm_image(asset) if asset else self._build_vm_profile_asset_fallback(service, runtime),
            "runtime": runtime,
            "runtime_status": runtime_status or {},
            "current_pod_ip": current_pod_ip or "",
            "network": self.get_vm_network_profile(service.service_id, current_pod_ip=current_pod_ip),
            "connections": vm_connections
        }

    def get_vm_network_profile(self, service_id: str, current_pod_ip: str = "") -> dict:
        attrs = {
            attr.name: attr.attribute_value
            for attr in k8s_attribute_repo.get_by_component_id(service_id)
            if attr.name in ("vm_fixed_ip_enabled", "vm_fixed_ip")
        }
        fixed_ip_enabled = self._as_bool(attrs.get("vm_fixed_ip_enabled"))
        fixed_ip = str(attrs.get("vm_fixed_ip") or "").strip()
        return {
            "mode": "pod",
            "fixed_ip_enabled": fixed_ip_enabled,
            "fixed_ip": fixed_ip if fixed_ip_enabled else "",
            "current_pod_ip": current_pod_ip or "",
            "hot_update_supported": not fixed_ip_enabled,
            "live_migration_supported": not fixed_ip_enabled,
        }

    def list_vm_disks(self, service: TenantServiceInfo, volumes: Optional[list] = None) -> list:
        if not service or getattr(service, "extend_method", "") != "vm":
            return []
        runtime = self.get_vm_runtime_config(service.service_id)
        asset = self.get_vm_asset_for_service(service, runtime.get("asset_id"))
        runtime["boot_source_format"] = self._resolve_vm_boot_source_format_for_runtime(runtime, asset)
        volume_items = self._build_vm_volume_disk_items(volumes or [])
        layout = self._resolve_vm_disk_layout_for_service(runtime, asset, volume_items)
        return self._merge_vm_disk_layout_items(layout, volume_items, runtime, asset)

    def validate_vm_disk_layout(self, service: TenantServiceInfo, volumes: Any, disk_layout: Any) -> list:
        if not service or getattr(service, "extend_method", "") != "vm":
            raise ValueError("only vm service supports disk layout")
        runtime = self.get_vm_runtime_config(service.service_id)
        current_items = self.list_vm_disks(service, volumes)
        normalized = self._normalize_vm_disk_layout_items(disk_layout)
        if not normalized:
            raise ValueError("vm disk layout cannot be empty")

        current_volume_keys = {
            self._compound_vm_disk_key(item)
            for item in current_items
            if item.get("source_kind") == VM_DISK_SOURCE_KIND_VOLUME
        }
        normalized_keys = {
            self._compound_vm_disk_key(item)
            for item in normalized
        }
        missing_volume_keys = current_volume_keys - normalized_keys
        if missing_volume_keys:
            raise ValueError("volume-backed disks cannot be removed from vm disk layout")

        first = normalized[0]
        if not self._is_vm_root_disk_item(first) and not self._is_vm_installer_disk_item(first):
            raise ValueError("first vm disk must be root disk or installer media")

        root_items = [item for item in normalized if self._is_vm_root_disk_item(item)]
        if not root_items:
            raise ValueError("vm disk layout requires root disk")

        normalized_has_installer = any(self._is_vm_installer_disk_item(item) for item in normalized)
        current_has_installer = any(self._is_vm_installer_disk_item(item) for item in current_items)
        if normalized_has_installer and not current_has_installer:
            raise ValueError("installer media is not available for this vm")

        if (
                not normalized_has_installer and
                current_has_installer and
                str(runtime.get("boot_source_format") or "").lower() != "iso"
        ):
            raise ValueError("installer media can only be removed from iso-based vm")

        for item in normalized:
            if item.get("source_kind") != VM_DISK_SOURCE_KIND_CONTAINER_DISK:
                continue
            if item.get("device_type") != VM_DISK_DEVICE_CDROM:
                raise ValueError("container disk media must use cdrom device type")
            if not str(item.get("image") or "").strip():
                raise ValueError("container disk media requires image")

        return normalized

    def save_vm_disk_layout(self, tenant_id: str, service_id: str, disk_layout: Any,
                            sync_context: Optional[dict] = None) -> list:
        normalized = self._normalize_vm_disk_layout_items(disk_layout)
        self._persist_managed_k8s_attribute(
            tenant_id,
            service_id,
            "vm_disk_layout",
            "json",
            json.dumps(normalized),
            sync_context=sync_context or self._get_vm_attr_sync_context(service_id)
        )
        return normalized

    def build_initial_vm_disk_layout(self, boot_source_format: str = "", asset: Any = None,
                                     restore_plan: Optional[dict] = None) -> list:
        source_format = str(boot_source_format or "").strip().lower()
        if restore_plan and restore_plan.get("disk_layout"):
            return self._normalize_vm_disk_layout_items(restore_plan.get("disk_layout"))

        base_layout = [
            {
                "disk_key": VM_DISK_ROOT_KEY,
                "disk_name": "system-disk",
                "disk_role": VM_DISK_ROLE_ROOT,
                "device_type": VM_DISK_DEVICE_DISK,
                "source_kind": VM_DISK_SOURCE_KIND_VOLUME,
                "order_index": 0,
            }
        ]
        if source_format == "iso":
            base_layout.insert(0, {
                "disk_key": VM_DISK_INSTALLER_KEY,
                "disk_name": "installer-media",
                "disk_role": VM_DISK_ROLE_INSTALLER,
                "device_type": VM_DISK_DEVICE_CDROM,
                "source_kind": VM_DISK_SOURCE_KIND_INSTALLER,
                "order_index": 0,
            })
            base_layout[1]["order_index"] = 1
        return self._normalize_vm_disk_layout_items(base_layout)

    def is_vm_asset_ready(self, asset: Any) -> bool:
        if not asset:
            return False
        return bool(getattr(asset, "status", "") == "ready" and getattr(asset, "image_url", ""))

    def get_vm_asset_for_service(self, service: TenantServiceInfo,
                                 asset_id: Any = None) -> Optional[VirtualMachineImage]:
        tenant_id = getattr(service, "tenant_id", "")
        if asset_id:
            asset = vm_repo.get_vm_image_instance_by_id(tenant_id, asset_id)
            if asset:
                return asset
        return vm_repo.get_vm_image_instance_by_tenant_id_and_image_url(tenant_id, getattr(service, "image", ""))

    def get_vm_runtime_config(self, service_id: str) -> dict:
        attrs = {attr.name: attr.attribute_value for attr in k8s_attribute_repo.get_by_component_id(service_id)}
        return {
            "asset_id": self._to_int(attrs.get("vm_asset_id")),
            "asset_clone_source": attrs.get("vm_asset_clone_source", ""),
            "boot_mode": attrs.get("vm_boot_mode", ""),
            "boot_source_format": attrs.get("vm_boot_source_format", ""),
            "disk_layout": self._as_list_of_dicts(attrs.get("vm_disk_layout")),
            "os_name": attrs.get("vm_os_name", ""),
            "gpu_enabled": self._as_bool(attrs.get("vm_gpu_enabled")),
            "gpu_resources": self._as_list(attrs.get("vm_gpu_resources")),
            "gpu_count": self._to_int(
                attrs.get("vm_gpu_count"),
                1 if self._as_bool(attrs.get("vm_gpu_enabled")) else 0
            ),
            "usb_enabled": self._as_bool(attrs.get("vm_usb_enabled")),
            "usb_resources": self._as_list(attrs.get("vm_usb_resources")),
        }

    def save_vm_runtime_config(self, tenant_id: str, service_id: str, runtime_config: dict,
                               sync_context: Optional[dict] = None) -> None:
        self.validate_vm_runtime_config(runtime_config)
        attrs = self._build_vm_runtime_attrs(runtime_config)
        current_attrs = {
            attr.name: attr
            for attr in k8s_attribute_repo.get_by_component_id(service_id)
            if attr.name in VM_RUNTIME_MANAGED_KEYS
        }
        sync_context = sync_context or self._get_vm_attr_sync_context(service_id)
        for name in VM_RUNTIME_MANAGED_KEYS:
            value = attrs.get(name)
            if value is None:
                if name in current_attrs:
                    self._persist_managed_k8s_attribute(
                        tenant_id,
                        service_id,
                        name,
                        VM_RUNTIME_ATTR_SPECS[name],
                        None,
                        sync_context=sync_context
                    )
                continue
            self._persist_managed_k8s_attribute(
                tenant_id,
                service_id,
                name,
                VM_RUNTIME_ATTR_SPECS[name],
                value,
                sync_context=sync_context
            )

    def save_vm_disk_imports(self, tenant_id: str, service_id: str, disk_imports: Any) -> dict:
        normalized = self._normalize_vm_disk_imports(disk_imports)
        logger.info(
            "vm disk imports prepared: tenant_id=%s service_id=%s disk_count=%s volumes=%s",
            tenant_id,
            service_id,
            len(normalized),
            ",".join(sorted(normalized.keys())),
        )
        self._persist_managed_k8s_attribute(
            tenant_id,
            service_id,
            VM_DISK_IMPORT_ATTR_NAME,
            "json",
            json.dumps(normalized) if normalized else None,
            sync_context=self._get_vm_attr_sync_context(service_id)
        )
        return normalized

    def validate_vm_runtime_config(self, runtime_config: dict) -> None:
        gpu_enabled = self._as_bool(runtime_config.get("gpu_enabled"))
        gpu_resources = self._as_list(runtime_config.get("gpu_resources"))
        if gpu_enabled and not gpu_resources:
            raise ValueError("gpu_enabled requires gpu_resources")
        gpu_count = self._to_int(runtime_config.get("gpu_count"), 1 if gpu_enabled else 0)
        if gpu_enabled and (gpu_count is None or gpu_count < 1):
            raise ValueError("gpu_enabled requires gpu_count")
        # NOTE: prior guard raises when gpu_enabled and gpu_count is None; non-None here (guarded invariant).
        if gpu_enabled and gpu_count > 1 and len(gpu_resources) != 1:  # type: ignore[operator]
            raise ValueError("gpu_count greater than 1 requires exactly one gpu resource")

        usb_enabled = self._as_bool(runtime_config.get("usb_enabled"))
        usb_resources = self._as_list(runtime_config.get("usb_resources"))
        if usb_enabled and not usb_resources:
            raise ValueError("usb_enabled requires usb_resources")

    def serialize_vm_image(self, vm_image: Optional[VirtualMachineImage],
                           source_asset: Optional[VirtualMachineImage] = None) -> dict:
        if not vm_image:
            return {}
        if vm_image.source_asset_id and not source_asset:
            # NOTE: source_asset_id is an int model field used as a str identifier (.ID-as-str pattern).
            source_asset = vm_repo.get_vm_image_instance_by_id(
                vm_image.tenant_id, vm_image.source_asset_id)  # type: ignore[arg-type]
        extra = self._load_json(vm_image.extra_json, {})
        disks = extra.get("disks", [])
        display_name = (
            extra.get("display_name") or
            extra.get("source_service_cname") or
            extra.get("source_service_alias") or
            vm_image.name
        )
        references = self.get_vm_asset_references(vm_image.tenant_id, vm_image)
        return {
            "id": vm_image.ID,
            "name": vm_image.name,
            "display_name": display_name,
            "image_url": vm_image.image_url,
            "source_type": vm_image.source_type or "existing",
            "source_uri": vm_image.source_uri or vm_image.image_url,
            "arch": vm_image.arch or "amd64",
            "os_name": vm_image.os_name or "",
            "format": vm_image.format or self._infer_asset_format(vm_image.source_uri, vm_image.image_url, vm_image.name),
            "size_bytes": int(vm_image.size_bytes or 0),
            "checksum": vm_image.checksum or "",
            "status": vm_image.status or "ready",
            "build_event_id": vm_image.build_event_id or "",
            "source_asset_id": vm_image.source_asset_id,
            "clone_mode": vm_image.clone_mode or "",
            "is_public_template": bool(vm_image.is_public_template),
            "boot_mode": vm_image.boot_mode or "",
            "storage_backend": vm_image.storage_backend or "",
            "labels": self._load_json(vm_image.labels_json, {}),
            "extra": extra,
            "asset_kind": extra.get("asset_kind", VM_DISK_ASSET_KIND),
            "disk_count": extra.get("disk_count", len(disks) if disks else 0),
            "source_service_id": extra.get("source_service_id", ""),
            "disks": disks,
            "reference_count": len(references),
            "references": references,
            "source_asset": {
                "id": source_asset.ID,
                "name": source_asset.name
            } if source_asset else None,
            "create_time": self._format_datetime(getattr(vm_image, "create_time", None)),
            "update_time": self._format_datetime(getattr(vm_image, "update_time", None)),
        }

    def _build_vm_profile_asset_fallback(self, service: TenantServiceInfo, runtime: Optional[dict]) -> dict:
        runtime = runtime or {}
        root_disk = self._extract_root_disk_payload(template_payload={"vm": {"disk_layout": runtime.get("disk_layout") or []}})
        if not root_disk:
            return {}
        source_type = self._normalize_vm_profile_source_type(root_disk.get("source_type"))
        source_uri = root_disk.get("source_uri") or root_disk.get("image_url") or ""
        image_url = root_disk.get("image_url") or getattr(service, "image", "") or ""
        image_name = self._extract_vm_profile_asset_name(root_disk.get("image_url") or image_url)
        display_name = (
            image_name or
            getattr(service, "service_cname", "") or
            root_disk.get("disk_name") or
            root_disk.get("disk_key") or
            ""
        )
        return {
            "id": None,
            "name": image_name,
            "display_name": display_name,
            "image_url": image_url,
            "source_type": source_type,
            "source_uri": source_uri,
            "arch": getattr(service, "arch", "") or "amd64",
            "os_name": runtime.get("os_name", "") or "",
            "format": (
                root_disk.get("format") or
                runtime.get("boot_source_format") or
                self._infer_asset_format(source_uri, image_url, image_name)
            ),
            "size_bytes": 0,
            "checksum": root_disk.get("checksum") or "",
            "status": "ready",
            "build_event_id": "",
            "source_asset_id": None,
            "clone_mode": "",
            "is_public_template": False,
            "boot_mode": runtime.get("boot_mode", "") or "",
            "storage_backend": "",
            "labels": {},
            "extra": {},
            "asset_kind": VM_DISK_ASSET_KIND,
            "disk_count": 1,
            "source_service_id": "",
            "disks": [],
            "reference_count": 0,
            "source_asset": None,
            "create_time": "",
            "update_time": "",
        }

    def _normalize_vm_profile_source_type(self, source_type: Any) -> str:
        normalized = str(source_type or "").strip().lower()
        if normalized in ("public", "upload", "clone", "existing"):
            return normalized
        if normalized in ("http", "http-artifact", "url"):
            return "url"
        if normalized == "registry":
            return "existing"
        return "existing"

    def _extract_vm_profile_asset_name(self, image_url: Any) -> str:
        value = str(image_url or "").strip()
        if not value:
            return ""
        if "/" in value:
            return value.rsplit("/", 1)[-1]
        if ":" in value:
            return value.rsplit(":", 1)[-1]
        return value

    def get_vm_asset_reference_count(self, tenant_id: str, vm_image: VirtualMachineImage) -> int:
        return self.get_vm_asset_reference_services(tenant_id, vm_image).count()

    def get_vm_asset_reference_services(self, tenant_id: str, vm_image: VirtualMachineImage) -> Any:
        # Incomplete VM rows are transient and should not block asset deletion or inflate catalog references.
        active_vm_services = TenantServiceInfo.objects.filter(
            tenant_id=tenant_id,
            extend_method="vm",
            create_status="complete")
        active_vm_service_ids = active_vm_services.values_list("service_id", flat=True)
        explicit_service_ids = ComponentK8sAttributes.objects.filter(
            tenant_id=tenant_id,
            component_id__in=active_vm_service_ids,
            name="vm_asset_id",
            attribute_value=str(vm_image.ID)).values_list("component_id", flat=True)
        if explicit_service_ids.exists():
            return active_vm_services.filter(service_id__in=explicit_service_ids).order_by("service_alias")
        bound_service_ids = ComponentK8sAttributes.objects.filter(
            tenant_id=tenant_id,
            component_id__in=active_vm_service_ids,
            name="vm_asset_id").values_list("component_id", flat=True)
        return active_vm_services.exclude(service_id__in=bound_service_ids).filter(
            image=vm_image.image_url).order_by("service_alias")

    def get_vm_asset_references(self, tenant_id: str, vm_image: VirtualMachineImage) -> list:
        return [
            self.serialize_vm_asset_reference_service(service)
            for service in self.get_vm_asset_reference_services(tenant_id, vm_image)
        ]

    def serialize_vm_asset_reference_service(self, service: TenantServiceInfo) -> dict:
        group_id = getattr(service, "tenant_service_group_id", 0) or 0
        service_alias = getattr(service, "service_alias", "") or ""
        service_cname = getattr(service, "service_cname", "") or ""
        service_id = getattr(service, "service_id", "") or ""
        return {
            "service_id": service_id,
            "component_id": service_id,
            "service_alias": service_alias,
            "service_cname": service_cname,
            "display_name": service_cname or service_alias or service_id,
            "group_id": group_id,
            "app_id": group_id,
            "region_name": getattr(service, "service_region", "") or "",
        }

    def _build_vm_runtime_attrs(self, runtime_config: dict) -> dict:
        attrs = {}
        os_name = runtime_config.get("os_name")
        if os_name not in (None, ""):
            attrs["vm_os_name"] = str(os_name)

        gpu_enabled = self._as_bool(runtime_config.get("gpu_enabled"))
        gpu_resources = self._as_list(runtime_config.get("gpu_resources"))
        if gpu_enabled and gpu_resources:
            attrs["vm_gpu_enabled"] = "true"
            attrs["vm_gpu_resources"] = json.dumps(gpu_resources)
            attrs["vm_gpu_count"] = str(self._to_int(runtime_config.get("gpu_count"), 1) or 1)

        usb_enabled = self._as_bool(runtime_config.get("usb_enabled"))
        usb_resources = self._as_list(runtime_config.get("usb_resources"))
        if usb_enabled and usb_resources:
            attrs["vm_usb_enabled"] = "true"
            attrs["vm_usb_resources"] = json.dumps(usb_resources)

        asset_id = runtime_config.get("asset_id")
        if asset_id not in (None, ""):
            attrs["vm_asset_id"] = str(asset_id)

        disk_layout = runtime_config.get("disk_layout")
        if disk_layout not in (None, "", []):
            attrs["vm_disk_layout"] = json.dumps(disk_layout)

        clone_source = runtime_config.get("clone_source_id") or runtime_config.get("clone_source_name")
        if clone_source not in (None, ""):
            attrs["vm_asset_clone_source"] = str(clone_source)

        boot_mode = runtime_config.get("boot_mode")
        if boot_mode:
            attrs["vm_boot_mode"] = str(boot_mode)

        boot_source_format = runtime_config.get("boot_source_format")
        if boot_source_format not in (None, ""):
            attrs["vm_boot_source_format"] = str(boot_source_format)

        return attrs

    def infer_vm_boot_source_format(self, asset: Any = None, template_payload: Optional[dict] = None,
                                    image_name: str = "", image_url: str = "", source_uri: str = "") -> str:
        root_disk = self._extract_root_disk_payload(asset=asset, template_payload=template_payload)
        if root_disk:
            inferred = root_disk.get("format") or self._infer_asset_format(
                root_disk.get("source_uri"),
                root_disk.get("image_url"),
                root_disk.get("disk_name"),
                root_disk.get("disk_key"),
                image_name,
            )
            return inferred or "disk"
        if asset:
            inferred = getattr(asset, "format", "") or self._infer_asset_format(
                getattr(asset, "source_uri", ""),
                getattr(asset, "image_url", ""),
                getattr(asset, "name", ""),
                source_uri,
                image_url,
                image_name,
            )
            if inferred:
                return inferred
        inferred = self._infer_asset_format(source_uri, image_url, image_name)
        if inferred:
            return inferred
        return ""

    def _resolve_vm_boot_source_format_for_runtime(self, runtime: Optional[dict] = None, asset: Any = None) -> str:
        runtime = runtime or {}
        source_format = str(runtime.get("boot_source_format") or "").strip().lower()
        if source_format:
            return source_format
        inferred = self.infer_vm_boot_source_format(asset=asset)
        return str(inferred or "").strip().lower()

    def build_vm_create_disk_imports(self, asset: Any = None, template_payload: Optional[dict] = None,
                                     image_name: str = "", image_url: str = "", source_uri: str = "",
                                     boot_source_format: str = "") -> list:
        imports = []
        root_import = self._build_vm_root_disk_import(
            asset=asset,
            template_payload=template_payload,
            image_name=image_name,
            image_url=image_url,
            source_uri=source_uri,
            boot_source_format=boot_source_format,
        )
        if root_import:
            imports.append(root_import)
        if template_payload:
            imports.extend([
                disk for disk in (template_payload.get("data_disks") or [])
                if disk.get("image_url")
            ])
        logger.info(
            "vm create disk imports resolved: image_name=%s source_uri=%s root_import=%s disk_count=%s boot_source_format=%s",
            image_name,
            source_uri,
            bool(root_import),
            len(imports),
            str(boot_source_format or self.infer_vm_boot_source_format(
                asset=asset,
                template_payload=template_payload,
                image_name=image_name,
                image_url=image_url,
                source_uri=source_uri,
            ) or "").strip().lower(),
        )
        return imports

    def resolve_vm_boot_mode(self,
                             requested_boot_mode: str = "",
                             asset: Any = None,
                             template_payload: Optional[dict] = None,
                             runtime_config: Optional[dict] = None,
                             image_name: str = "",
                             image_url: str = "",
                             source_uri: str = "",
                             boot_source_format: str = "") -> str:
        boot_mode = self._normalize_vm_boot_mode(requested_boot_mode)
        if boot_mode:
            return boot_mode

        source_format = (boot_source_format or self.infer_vm_boot_source_format(
            asset=asset,
            template_payload=template_payload,
            image_name=image_name,
            image_url=image_url,
            source_uri=source_uri,
        ) or "").strip().lower()
        if source_format == "iso":
            return ""

        runtime_snapshot = (template_payload or {}).get("runtime_snapshot") or {}
        boot_mode = self._normalize_vm_boot_mode(runtime_snapshot.get("boot_mode"))
        if boot_mode:
            return boot_mode

        if asset:
            boot_mode = self._normalize_vm_boot_mode(getattr(asset, "boot_mode", ""))
            if boot_mode:
                return boot_mode

            extra = self._load_json(getattr(asset, "extra_json", ""), {})
            boot_mode = self._normalize_vm_boot_mode((extra.get("runtime_snapshot") or {}).get("boot_mode"))
            if boot_mode:
                return boot_mode

        guest_os_family = self._infer_vm_guest_os_family(runtime_config=runtime_config, asset=asset, image_name=image_name)
        if guest_os_family != "windows":
            return ""

        return "uefi"

    def _build_vm_root_disk_import(self, asset: Any = None, template_payload: Optional[dict] = None,
                                   image_name: str = "", image_url: str = "", source_uri: str = "",
                                   boot_source_format: str = "") -> Optional[dict]:
        resolved_boot_source_format = str(boot_source_format or self.infer_vm_boot_source_format(
            asset=asset,
            template_payload=template_payload,
            image_name=image_name,
            image_url=image_url,
            source_uri=source_uri,
        ) or "").strip().lower()
        if resolved_boot_source_format == "iso":
            return None

        root_disk = self._extract_root_disk_payload(asset=asset, template_payload=template_payload)
        if root_disk:
            restore_url = root_disk.get("image_url") or ""
            source_type = self._resolve_vm_disk_source_type(
                root_disk.get("source_type"),
                restore_url,
                root_disk.get("source_uri"),
            )
            if not self._is_supported_vm_restore_source(source_type, restore_url):
                return None
            return {
                "volume_name": "disk",
                "disk_key": root_disk.get("disk_key") or "rootdisk",
                "disk_name": root_disk.get("disk_name") or root_disk.get("disk_key") or "rootdisk",
                "image_url": restore_url,
                "source_uri": root_disk.get("source_uri") or "",
                "format": root_disk.get("format") or resolved_boot_source_format or "",
                "checksum": root_disk.get("checksum") or "",
                "source_type": source_type,
            }

        restore_url = self._resolve_root_restore_url(asset=asset, image_url=image_url, source_uri=source_uri)
        if not self._is_http_source(restore_url):
            registry_image = self._resolve_root_registry_image(asset=asset, image_url=image_url)
            if not registry_image or not resolved_boot_source_format:
                return None
            return {
                "volume_name": "disk",
                "disk_key": "rootdisk",
                "disk_name": "rootdisk",
                "image_url": registry_image,
                "source_uri": self._resolve_root_source_uri(asset=asset, source_uri=source_uri, fallback=registry_image),
                "format": resolved_boot_source_format or "",
                "checksum": "",
                "source_type": "registry",
            }
        return {
            "volume_name": "disk",
            "disk_key": "rootdisk",
            "disk_name": "rootdisk",
            "image_url": restore_url,
            "source_uri": "",
            "format": resolved_boot_source_format or "",
            "checksum": "",
            "source_type": "http",
        }

    def _extract_root_disk_payload(self, asset: Any = None,
                                   template_payload: Optional[dict] = None) -> Optional[dict]:
        if template_payload:
            vm_payload = template_payload.get("vm") or {}
            disk_layout = vm_payload.get("disk_layout") or template_payload.get("disk_layout") or []
            for disk in disk_layout:
                if str(disk.get("disk_role", "")).lower() == "root":
                    return {
                        "disk_key": disk.get("disk_key") or "rootdisk",
                        "disk_name": disk.get("disk_name") or disk.get("disk_key") or "rootdisk",
                        "image_url": disk.get("image") or disk.get("image_url") or "",
                        "source_uri": disk.get("source_uri") or "",
                        "source_type": disk.get("source_type") or "",
                        "format": disk.get("format") or "",
                        "checksum": disk.get("checksum") or "",
                    }
        if asset:
            extra = self._load_json(getattr(asset, "extra_json", ""), {})
            for disk in extra.get("disks", []):
                if str(disk.get("disk_role", "")).lower() == "root":
                    return {
                        "disk_key": disk.get("disk_key") or "rootdisk",
                        "disk_name": disk.get("disk_name") or disk.get("disk_key") or "rootdisk",
                        "image_url": disk.get("download_url") or disk.get("image_url") or "",
                        "source_uri": disk.get("source_uri") or disk.get("export_name") or "",
                        "source_type": disk.get("source_type") or "",
                        "format": disk.get("format") or "",
                        "checksum": disk.get("checksum") or "",
                    }
        return None

    def _resolve_root_restore_url(self, asset: Any = None, image_url: str = "", source_uri: str = "") -> Any:
        candidates = []
        if asset:
            candidates.extend([
                getattr(asset, "image_url", ""),
                getattr(asset, "source_uri", ""),
            ])
        candidates.extend([image_url, source_uri])
        for candidate in candidates:
            if self._is_http_source(candidate):
                return candidate
        return ""

    def _resolve_root_registry_image(self, asset: Any = None, image_url: str = "") -> str:
        candidates = []
        if asset:
            candidates.append(getattr(asset, "image_url", ""))
        candidates.append(image_url)
        for candidate in candidates:
            value = str(candidate or "").strip()
            if not value or self._is_http_source(value) or value.startswith("/grdata/"):
                continue
            return value
        return ""

    def _resolve_root_source_uri(self, asset: Any = None, source_uri: str = "", fallback: str = "") -> str:
        if asset:
            value = str(getattr(asset, "source_uri", "") or "").strip()
            if value:
                return value
        value = str(source_uri or "").strip()
        return value or fallback

    def _normalize_vm_boot_mode(self, value: Any) -> str:
        return str(value or "").strip().lower()

    def _infer_vm_guest_os_family(self, runtime_config: Optional[dict] = None, asset: Any = None,
                                  image_name: str = "") -> str:
        runtime_config = runtime_config or {}
        explicit = str(runtime_config.get("os_family") or "").strip().lower()
        if explicit in ("windows", "linux"):
            return explicit

        hints = [
            runtime_config.get("os_name", ""),
            getattr(asset, "os_name", "") if asset else "",
        ]
        merged_hint = " ".join([str(item or "") for item in hints]).strip().lower()
        if "windows" in merged_hint:
            return "windows"
        return ""

    def _is_http_source(self, value: Any) -> bool:
        value = str(value or "").strip().lower()
        return value.startswith("http://") or value.startswith("https://")

    def _is_registry_source(self, value: Any) -> bool:
        value = str(value or "").strip().lower()
        return value.startswith("docker://")

    def _resolve_vm_disk_source_type(self, source_type: Any, image_url: Any = "", source_uri: Any = "") -> str:
        normalized = str(source_type or "").strip().lower()
        if normalized:
            return normalized
        if self._is_http_source(image_url) or self._is_http_source(source_uri):
            return "http"
        if self._is_registry_source(image_url) or self._is_registry_source(source_uri):
            return "registry"
        return ""

    def _is_supported_vm_restore_source(self, source_type: Any, image_url: Any) -> bool:
        source_type = str(source_type or "").strip().lower()
        if source_type == "registry":
            return bool(str(image_url or "").strip())
        return self._is_http_source(image_url)

    def _is_region_resource_missing_error(self, err: Any) -> bool:
        if isinstance(err, RegionApiBaseHttpClient.CallApiError):
            if getattr(err, "status", None) == 404:
                return True
            message = getattr(err, "message", {}) or {}
            if isinstance(message, dict) and message.get("httpcode") == 404:
                return True
        if isinstance(err, ServiceHandleException):
            if getattr(err, "status_code", None) == 404:
                return True
            raw = getattr(err, "msg", None)
            if isinstance(raw, dict) and raw.get("httpcode") == 404:
                return True
        return False

    def _normalize_vm_disk_imports(self, disk_imports: Any) -> dict:
        normalized = {}
        for disk in disk_imports or []:
            volume_name = disk.get("volume_name") or disk.get("disk_key") or disk.get("disk_name")
            image_url = disk.get("image_url") or ""
            if not volume_name or not image_url:
                continue
            volume_name = str(volume_name)
            normalized[volume_name] = {
                "volume_name": volume_name,
                "disk_key": disk.get("disk_key") or volume_name,
                "disk_name": disk.get("disk_name") or volume_name,
                "image_url": image_url,
                "source_uri": disk.get("source_uri") or "",
                "format": disk.get("format") or "",
                "checksum": disk.get("checksum") or "",
                "source_type": disk.get("source_type") or self._resolve_vm_disk_source_type(
                    disk.get("source_type"), image_url, disk.get("source_uri")),
            }
        return normalized

    def _build_vm_volume_disk_items(self, volumes: Any) -> list:
        items = []
        for index, volume in enumerate(volumes or []):
            volume_data = volume.to_dict() if hasattr(volume, "to_dict") else dict(volume)
            volume_name = str(volume_data.get("volume_name") or "").strip()
            if not volume_name:
                continue
            volume_path = str(volume_data.get("volume_path") or "").strip()
            device_type = self._resolve_vm_device_type(volume_path)
            device_path = "/{}".format(device_type)
            items.append({
                "disk_key": volume_name,
                "disk_name": volume_name,
                "disk_role": VM_DISK_ROLE_ROOT if volume_name == VM_DISK_ROOT_KEY else VM_DISK_ROLE_DATA,
                "device_type": device_type,
                "device_path": device_path,
                "source_kind": VM_DISK_SOURCE_KIND_VOLUME,
                "order_index": index,
                "boot": False,
                "deletable": volume_name != VM_DISK_ROOT_KEY,
                "ID": volume_data.get("ID") or volume_data.get("id"),
                "volume_id": volume_data.get("ID") or volume_data.get("id"),
                "volume_name": volume_name,
                "volume_path": volume_path,
                "volume_type": volume_data.get("volume_type", ""),
                "volume_capacity": volume_data.get("volume_capacity", 0),
                "status": volume_data.get("status", ""),
            })
        return items

    def _resolve_vm_disk_layout_for_service(self, runtime: dict, asset: Any, volume_items: list) -> list:
        current_layout = runtime.get("disk_layout") or []
        if current_layout:
            return self._normalize_vm_disk_layout_items(current_layout)
        if str(runtime.get("boot_source_format") or "").lower() == "iso":
            return self.build_initial_vm_disk_layout(
                boot_source_format="iso",
                asset=asset,
            )
        root_present = any(item.get("disk_key") == VM_DISK_ROOT_KEY for item in volume_items)
        if root_present:
            return self.build_initial_vm_disk_layout(
                boot_source_format=runtime.get("boot_source_format") or "",
                asset=asset,
            )
        return self._normalize_vm_disk_layout_items(current_layout)

    def _merge_vm_disk_layout_items(self, layout: list, volume_items: list, runtime: dict, asset: Any) -> list:
        normalized_layout = self._normalize_vm_disk_layout_items(layout)
        volume_map = {
            self._compound_vm_disk_key(item): dict(item)
            for item in volume_items
        }
        resolved = []
        seen = set()
        installer_item = self._build_vm_installer_disk_item(runtime, asset)
        for item in normalized_layout:
            compound_key = self._compound_vm_disk_key(item)
            if self._is_vm_installer_disk_item(item):
                if installer_item:
                    merged = dict(installer_item)
                    merged.update({
                        "order_index": item.get("order_index", 0),
                        "boot": False,
                    })
                    resolved.append(merged)
                    seen.add(compound_key)
                continue
            if item.get("source_kind") == VM_DISK_SOURCE_KIND_CONTAINER_DISK:
                resolved.append({
                    "disk_key": item.get("disk_key", ""),
                    "disk_name": item.get("disk_name") or item.get("disk_key", ""),
                    "disk_role": VM_DISK_ROLE_DATA,
                    "device_type": VM_DISK_DEVICE_CDROM,
                    "device_path": "/{}".format(VM_DISK_DEVICE_CDROM),
                    "source_kind": VM_DISK_SOURCE_KIND_CONTAINER_DISK,
                    "image": item.get("image", ""),
                    "order_index": item.get("order_index", len(resolved)),
                    "boot": False,
                    "deletable": True,
                    "status": "ready",
                })
                seen.add(compound_key)
                continue
            volume_item = volume_map.get(compound_key)
            if not volume_item:
                continue
            merged = dict(volume_item)
            merged.update({
                "disk_role": item.get("disk_role") or volume_item.get("disk_role") or VM_DISK_ROLE_DATA,
                "device_type": item.get("device_type") or volume_item.get("device_type") or VM_DISK_DEVICE_DISK,
                "source_kind": VM_DISK_SOURCE_KIND_VOLUME,
                "order_index": item.get("order_index", len(resolved)),
                "boot": False,
            })
            resolved.append(merged)
            seen.add(compound_key)

        next_index = len(resolved)
        for item in volume_items:
            compound_key = self._compound_vm_disk_key(item)
            if compound_key in seen:
                continue
            merged = dict(item)
            merged["order_index"] = next_index
            merged["boot"] = False
            resolved.append(merged)
            seen.add(compound_key)
            next_index += 1

        if not normalized_layout and installer_item:
            installer = dict(installer_item)
            installer["order_index"] = 0
            installer["boot"] = False
            resolved.insert(0, installer)
            for index, item in enumerate(resolved):
                item["order_index"] = index

        for index, item in enumerate(resolved):
            item["order_index"] = index
            item["boot"] = index == 0
            item["deletable"] = not self._is_vm_root_disk_item(item)
        return resolved

    def _build_vm_installer_disk_item(self, runtime: dict, asset: Any = None) -> Optional[dict]:
        source_format = str(runtime.get("boot_source_format") or "").strip().lower()
        layout = runtime.get("disk_layout") or []
        if source_format != "iso":
            return None
        if layout and not any(self._is_vm_installer_disk_item(item) for item in layout):
            return None
        asset_os_name = getattr(asset, "os_name", "") if asset else ""
        disk_name = runtime.get("os_name") or asset_os_name or "installer-media"
        return {
            "disk_key": VM_DISK_INSTALLER_KEY,
            "disk_name": disk_name or "installer-media",
            "disk_role": VM_DISK_ROLE_INSTALLER,
            "device_type": VM_DISK_DEVICE_CDROM,
            "source_kind": VM_DISK_SOURCE_KIND_INSTALLER,
            "order_index": 0,
            "boot": False,
            "deletable": True,
            "status": "ready",
        }

    def _normalize_vm_disk_layout_items(self, disk_layout: Any) -> list:
        normalized: list = []
        seen = set()
        items = [item for item in (disk_layout or []) if isinstance(item, dict)]
        items = sorted(
            items,
            key=lambda value: (
                self._to_int(value.get("order_index"), 0),
                str(value.get("disk_key") or ""),
            )
        )
        for item in items:
            source_kind = self._normalize_vm_disk_source_kind(item)
            disk_role = self._normalize_vm_disk_role(item, source_kind)
            disk_key = self._normalize_vm_layout_disk_key(item, disk_role, source_kind)
            if not disk_key:
                continue
            compound_key = "{}:{}".format(source_kind, disk_key)
            if compound_key in seen:
                continue
            normalized.append({
                "disk_key": disk_key,
                "disk_name": str(item.get("disk_name") or disk_key),
                "disk_role": disk_role,
                "device_type": self._normalize_vm_disk_device_type(item, source_kind),
                "source_kind": source_kind,
                "order_index": len(normalized),
                "boot": False,
            })
            if source_kind == VM_DISK_SOURCE_KIND_CONTAINER_DISK:
                normalized[-1]["image"] = str(item.get("image") or "").strip()
            seen.add(compound_key)
        for index, item in enumerate(normalized):
            item["boot"] = index == 0
        return normalized

    def _normalize_vm_disk_source_kind(self, item: dict) -> str:
        source_kind = str(item.get("source_kind") or "").strip().lower()
        if source_kind in (VM_DISK_SOURCE_KIND_VOLUME, VM_DISK_SOURCE_KIND_INSTALLER, VM_DISK_SOURCE_KIND_CONTAINER_DISK):
            return source_kind
        if self._is_vm_installer_disk_item(item):
            return VM_DISK_SOURCE_KIND_INSTALLER
        return VM_DISK_SOURCE_KIND_VOLUME

    def _normalize_vm_disk_role(self, item: dict, source_kind: str) -> str:
        if source_kind == VM_DISK_SOURCE_KIND_INSTALLER:
            return VM_DISK_ROLE_INSTALLER
        if source_kind == VM_DISK_SOURCE_KIND_CONTAINER_DISK:
            return VM_DISK_ROLE_DATA
        role = str(item.get("disk_role") or "").strip().lower()
        if role in (VM_DISK_ROLE_ROOT, VM_DISK_ROLE_DATA, VM_DISK_ROLE_INSTALLER):
            return role
        disk_key = str(item.get("disk_key") or "").strip().lower()
        if disk_key in (VM_DISK_ROOT_KEY, "rootdisk") or item.get("boot"):
            return VM_DISK_ROLE_ROOT
        return VM_DISK_ROLE_DATA

    def _normalize_vm_layout_disk_key(self, item: dict, disk_role: str, source_kind: str) -> str:
        if source_kind == VM_DISK_SOURCE_KIND_INSTALLER:
            return VM_DISK_INSTALLER_KEY
        disk_key = str(item.get("disk_key") or "").strip()
        if source_kind == VM_DISK_SOURCE_KIND_CONTAINER_DISK:
            return disk_key
        if disk_role == VM_DISK_ROLE_ROOT:
            return VM_DISK_ROOT_KEY
        return disk_key

    def _normalize_vm_disk_device_type(self, item: dict, source_kind: str) -> str:
        if source_kind in (VM_DISK_SOURCE_KIND_INSTALLER, VM_DISK_SOURCE_KIND_CONTAINER_DISK):
            return VM_DISK_DEVICE_CDROM
        device_type = str(item.get("device_type") or "").strip().lower()
        if device_type in (VM_DISK_DEVICE_DISK, VM_DISK_DEVICE_CDROM, VM_DISK_DEVICE_LUN):
            return device_type
        return VM_DISK_DEVICE_DISK

    def _resolve_vm_device_type(self, volume_path: Any) -> str:
        path = str(volume_path or "").strip()
        for base_path, device_type in VM_DISK_PATH_TO_DEVICE_TYPE.items():
            if path == base_path or path.startswith(base_path + "-"):
                return device_type
        return VM_DISK_DEVICE_DISK

    def _compound_vm_disk_key(self, item: dict) -> str:
        return "{}:{}".format(
            item.get("source_kind") or VM_DISK_SOURCE_KIND_VOLUME,
            item.get("disk_key") or ""
        )

    def _is_vm_root_disk_item(self, item: Any) -> bool:
        if not isinstance(item, dict):
            return False
        if item.get("source_kind") == VM_DISK_SOURCE_KIND_INSTALLER:
            return False
        return str(item.get("disk_role") or "").strip().lower() == VM_DISK_ROLE_ROOT or str(
            item.get("disk_key") or "").strip() == VM_DISK_ROOT_KEY

    def _is_vm_installer_disk_item(self, item: Any) -> bool:
        if not isinstance(item, dict):
            return False
        if str(item.get("source_kind") or "").strip().lower() == VM_DISK_SOURCE_KIND_INSTALLER:
            return True
        if str(item.get("disk_role") or "").strip().lower() == VM_DISK_ROLE_INSTALLER:
            return True
        return str(item.get("disk_key") or "").strip() == VM_DISK_INSTALLER_KEY

    def _persist_managed_k8s_attribute(self, tenant_id: str, service_id: str, name: str, save_type: str,
                                       value: Any, sync_context: Optional[dict] = None) -> None:
        current_attr = k8s_attribute_repo.get_by_component_id_name(service_id, name).first()
        existed = bool(current_attr)
        if value is None:
            if current_attr:
                k8s_attribute_repo.delete(service_id, name)
                self._sync_managed_k8s_attribute(sync_context, name, None, None, existed_before=True)
            return

        if current_attr:
            k8s_attribute_repo.update(service_id, name, save_type=save_type, attribute_value=value)
        else:
            k8s_attribute_repo.create(
                tenant_id=tenant_id,
                component_id=service_id,
                name=name,
                save_type=save_type,
                attribute_value=value
            )
        self._sync_managed_k8s_attribute(sync_context, name, save_type, value, existed_before=existed)

    def _get_vm_attr_sync_context(self, service_id: str) -> Optional[dict]:
        service = TenantServiceInfo.objects.filter(service_id=service_id).first()
        if not service or getattr(service, "create_status", "") != "complete":
            return None
        tenant = Tenants.objects.filter(tenant_id=service.tenant_id).first()
        tenant_name = getattr(tenant, "tenant_name", "") or service.tenant_id
        if not tenant_name or not getattr(service, "service_region", "") or not getattr(service, "service_alias", ""):
            return None
        return {
            "tenant_name": tenant_name,
            "region_name": service.service_region,
            "service_alias": service.service_alias,
        }

    def _sync_managed_k8s_attribute(self, sync_context: Optional[dict], name: str, save_type: Optional[str],
                                    value: Any, existed_before: bool) -> None:
        if not sync_context:
            return
        if value is None:
            region_api.delete_component_k8s_attribute(
                sync_context["tenant_name"],
                sync_context["region_name"],
                sync_context["service_alias"],
                {"name": name}
            )
            return

        payload = {
            "name": name,
            "save_type": save_type,
            "attribute_value": value,
        }
        if existed_before:
            region_api.update_component_k8s_attribute(
                sync_context["tenant_name"],
                sync_context["region_name"],
                sync_context["service_alias"],
                payload
            )
        else:
            try:
                region_api.create_component_k8s_attribute(
                    sync_context["tenant_name"],
                    sync_context["region_name"],
                    sync_context["service_alias"],
                    payload
                )
            except Exception:
                region_api.update_component_k8s_attribute(
                    sync_context["tenant_name"],
                    sync_context["region_name"],
                    sync_context["service_alias"],
                    payload
                )

    def _persist_vm_fixed_pod_ip_state(self, service: TenantServiceInfo, bean: dict,
                                       requested_enabled: bool) -> None:
        tenant_id = getattr(service, "tenant_id", "")
        service_id = getattr(service, "service_id", "")
        if not tenant_id or not service_id:
            return

        fixed_ip_enabled = bool(requested_enabled)
        fixed_ip = ""
        if isinstance(bean, dict):
            if "fixed_ip_enabled" in bean:
                fixed_ip_enabled = self._as_bool(bean.get("fixed_ip_enabled"))
            fixed_ip = str(bean.get("fixed_ip") or "").strip()

        self._persist_managed_k8s_attribute(
            tenant_id,
            service_id,
            "vm_fixed_ip_enabled",
            "string",
            "true" if fixed_ip_enabled else "false",
        )
        self._persist_managed_k8s_attribute(
            tenant_id,
            service_id,
            "vm_fixed_ip",
            "string",
            fixed_ip if fixed_ip_enabled and fixed_ip else None,
        )

    def _normalize_asset_payload(self, payload: dict) -> dict:
        normalized = dict(payload)
        labels = normalized.pop("labels", {})
        extra = normalized.pop("extra", {})
        normalized["source_type"] = normalized.get("source_type") or "existing"
        normalized["source_uri"] = normalized.get("source_uri") or normalized.get("image_url") or ""
        normalized["arch"] = normalized.get("arch") or "amd64"
        normalized["os_name"] = normalized.get("os_name") or ""
        normalized["format"] = normalized.get("format") or self._infer_asset_format(
            normalized.get("source_uri"), normalized.get("image_url"), normalized.get("name"))
        normalized["size_bytes"] = self._to_int(normalized.get("size_bytes"), 0)
        normalized["checksum"] = normalized.get("checksum") or ""
        normalized["status"] = normalized.get("status") or "ready"
        normalized["build_event_id"] = normalized.get("build_event_id") or ""
        normalized["source_asset_id"] = self._to_int(normalized.get("source_asset_id"))
        normalized["clone_mode"] = normalized.get("clone_mode") or ""
        normalized["is_public_template"] = bool(normalized.get("is_public_template", False))
        normalized["boot_mode"] = normalized.get("boot_mode") or ""
        normalized["storage_backend"] = normalized.get("storage_backend") or ""
        normalized["labels_json"] = self._dump_json(normalized.get("labels_json"), labels)
        normalized["extra_json"] = self._dump_json(normalized.get("extra_json"), extra)
        return normalized

    def _load_json(self, value: Any, default: Any) -> Any:
        if value in (None, ""):
            return default
        if isinstance(value, (dict, list)):
            return value
        try:
            return json.loads(value)
        except Exception:
            return default

    def _dump_json(self, raw_value: Any, default: Any) -> str:
        if raw_value in (None, ""):
            return json.dumps(default)
        if isinstance(raw_value, str):
            try:
                json.loads(raw_value)
                return raw_value
            except Exception:
                return json.dumps(default)
        return json.dumps(raw_value)

    def _infer_asset_format(self, *candidates: Any) -> str:
        known_suffixes = (".qcow2", ".img", ".iso", ".tar.gz", ".tar.xz", ".gz", ".xz", ".tar")
        for candidate in candidates:
            candidate = str(candidate or "").lower()
            for suffix in known_suffixes:
                if candidate.endswith(suffix):
                    return suffix.lstrip(".")
        return ""

    def _requires_vm_source_build(self, image_url: str) -> Any:
        return requires_vm_source_build(image_url)

    def _build_vm_runtime_image_name(self, tenant: Tenants, image_name: str) -> Any:
        return build_vm_runtime_image_name(tenant, image_name)

    def _format_datetime(self, value: Optional[datetime]) -> str:
        if not value:
            return ""
        return value.strftime("%Y-%m-%d %H:%M:%S")

    def _as_bool(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        return str(value).lower() in ("1", "true", "yes", "on", "enabled")

    def _as_list(self, value: Any) -> list:
        if isinstance(value, list):
            return [item for item in value if str(item).strip()]
        if not value:
            return []
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return [item for item in parsed if str(item).strip()]
            except Exception:
                pass
            return [item.strip() for item in value.split(",") if item.strip()]
        return []

    def _as_list_of_dicts(self, value: Any) -> list:
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if not value:
            return []
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return [item for item in parsed if isinstance(item, dict)]
            except Exception:
                return []
        return []

    def _to_int(self, value: Any, default: Optional[int] = None) -> Optional[int]:
        if value in (None, ""):
            return default
        try:
            return int(value)
        except (TypeError, ValueError):
            return default


vms = VirtualMachineService()
