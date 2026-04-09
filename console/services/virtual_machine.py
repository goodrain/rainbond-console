import json

from console.models.main import ComponentK8sAttributes
from console.repositories.k8s_attribute import k8s_attribute_repo
from console.repositories.virtual_machine import vm_repo
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import TenantServiceInfo, VirtualMachineImage

region_api = RegionInvokeApi()

VM_RUNTIME_ATTR_SPECS = {
    "vm_network_mode": "string",
    "vm_network_name": "string",
    "vm_fixed_ip": "string",
    "vm_gpu_enabled": "string",
    "vm_gpu_resources": "json",
    "vm_usb_enabled": "string",
    "vm_usb_resources": "json",
    "vm_asset_id": "string",
    "vm_asset_clone_source": "string",
    "vm_boot_mode": "string",
}
VM_RUNTIME_MANAGED_KEYS = set(VM_RUNTIME_ATTR_SPECS.keys())
VM_RUNTIME_LIST_KEYS = ("vm_gpu_resources", "vm_usb_resources")


class VirtualMachineService(object):
    def list_vm_image(self, tenant_id):
        vm_images = list(vm_repo.get_vm_images_by_tenant_id(tenant_id))
        source_ids = [vm_image.source_asset_id for vm_image in vm_images if vm_image.source_asset_id]
        source_map = {}
        if source_ids:
            source_map = {
                image.ID: image
                for image in VirtualMachineImage.objects.filter(tenant_id=tenant_id, ID__in=source_ids)
            }
        return [self.serialize_vm_image(vm_image, source_map.get(vm_image.source_asset_id)) for vm_image in vm_images]

    def get_vm_asset(self, tenant_id, asset_id):
        vm_image = vm_repo.get_vm_image_instance_by_id(tenant_id, asset_id)
        if not vm_image:
            return None
        source_asset = None
        if vm_image.source_asset_id:
            source_asset = vm_repo.get_vm_image_instance_by_id(tenant_id, vm_image.source_asset_id)
        return self.serialize_vm_image(vm_image, source_asset)

    def create_vm_image_asset(self, tenant_id, name, image_url, **params):
        payload = self._normalize_asset_payload({
            "tenant_id": tenant_id,
            "name": name,
            "image_url": image_url,
            **params
        })
        return vm_repo.create_vm_image(**payload)

    def get_vm_capabilities(self, region_name, tenant_name):
        _, body = region_api.get_vm_capabilities(region_name, tenant_name)
        return body.get("bean", {})

    def clone_vm_image(self, tenant_id, source_name, target_name):
        source = vm_repo.get_vm_image_instance_by_tenant_id_and_name(tenant_id, source_name)
        if not source:
            return None
        extra = self._load_json(source.extra_json, {})
        extra.update({
            "clone_source_id": source.ID,
            "clone_source_name": source.name
        })
        return self.create_vm_image_asset(
            tenant_id=tenant_id,
            name=target_name,
            image_url=source.image_url,
            source_type="clone",
            source_uri=source.image_url,
            arch=source.arch,
            os_name=source.os_name,
            format=source.format,
            size_bytes=source.size_bytes,
            checksum=source.checksum,
            status="ready",
            build_event_id=source.build_event_id,
            source_asset_id=source.ID,
            clone_mode="reuse",
            is_public_template=False,
            boot_mode=source.boot_mode,
            storage_backend=source.storage_backend,
            labels_json=source.labels_json,
            extra_json=json.dumps(extra)
        )

    def delete_vm_image(self, tenant_id, asset_id):
        vm_image = vm_repo.get_vm_image_instance_by_id(tenant_id, asset_id)
        if not vm_image:
            return 0, {}
        if self.get_vm_asset_reference_count(tenant_id, vm_image) > 0:
            raise ValueError("vm asset is still referenced")
        return vm_repo.delete_vm_image_by_id(tenant_id, asset_id)

    def get_vm_profile(self, service, connections=None):
        if getattr(service, "extend_method", "") != "vm":
            return {}
        runtime = self.get_vm_runtime_config(service.service_id)
        asset = self.get_vm_asset_for_service(service, runtime.get("asset_id"))
        return {
            "asset": self.serialize_vm_image(asset) if asset else {},
            "runtime": runtime,
            "connections": connections or {
                "vnc_url": "",
                "console_url": ""
            }
        }

    def get_vm_asset_for_service(self, service, asset_id=None):
        tenant_id = getattr(service, "tenant_id", "")
        if asset_id:
            asset = vm_repo.get_vm_image_instance_by_id(tenant_id, asset_id)
            if asset:
                return asset
        return vm_repo.get_vm_image_instance_by_tenant_id_and_image_url(tenant_id, getattr(service, "image", ""))

    def get_vm_runtime_config(self, service_id):
        attrs = {attr.name: attr.attribute_value for attr in k8s_attribute_repo.get_by_component_id(service_id)}
        return {
            "asset_id": self._to_int(attrs.get("vm_asset_id")),
            "asset_clone_source": attrs.get("vm_asset_clone_source", ""),
            "boot_mode": attrs.get("vm_boot_mode", ""),
            "network_mode": attrs.get("vm_network_mode") or "random",
            "network_name": attrs.get("vm_network_name", ""),
            "fixed_ip": attrs.get("vm_fixed_ip", ""),
            "gpu_enabled": self._as_bool(attrs.get("vm_gpu_enabled")),
            "gpu_resources": self._as_list(attrs.get("vm_gpu_resources")),
            "usb_enabled": self._as_bool(attrs.get("vm_usb_enabled")),
            "usb_resources": self._as_list(attrs.get("vm_usb_resources")),
        }

    def save_vm_runtime_config(self, tenant_id, service_id, runtime_config):
        self.validate_vm_runtime_config(runtime_config)
        attrs = self._build_vm_runtime_attrs(runtime_config)
        current_attrs = {
            attr.name: attr
            for attr in k8s_attribute_repo.get_by_component_id(service_id)
            if attr.name in VM_RUNTIME_MANAGED_KEYS
        }
        for name in VM_RUNTIME_MANAGED_KEYS:
            value = attrs.get(name)
            if value is None:
                if name in current_attrs:
                    k8s_attribute_repo.delete(service_id, name)
                continue
            save_type = VM_RUNTIME_ATTR_SPECS[name]
            if name in current_attrs:
                k8s_attribute_repo.update(service_id, name, save_type=save_type, attribute_value=value)
            else:
                k8s_attribute_repo.create(
                    tenant_id=tenant_id,
                    component_id=service_id,
                    name=name,
                    save_type=save_type,
                    attribute_value=value)

    def validate_vm_runtime_config(self, runtime_config):
        network_mode = runtime_config.get("network_mode") or "random"
        if network_mode == "fixed" and not runtime_config.get("network_name"):
            raise ValueError("fixed vm network mode requires network_name")
        if network_mode == "fixed" and not runtime_config.get("fixed_ip"):
            raise ValueError("fixed vm network mode requires fixed_ip")

        gpu_enabled = self._as_bool(runtime_config.get("gpu_enabled"))
        gpu_resources = self._as_list(runtime_config.get("gpu_resources"))
        if gpu_enabled and not gpu_resources:
            raise ValueError("gpu_enabled requires gpu_resources")

        usb_enabled = self._as_bool(runtime_config.get("usb_enabled"))
        usb_resources = self._as_list(runtime_config.get("usb_resources"))
        if usb_enabled and not usb_resources:
            raise ValueError("usb_enabled requires usb_resources")

    def serialize_vm_image(self, vm_image, source_asset=None):
        if not vm_image:
            return {}
        if vm_image.source_asset_id and not source_asset:
            source_asset = vm_repo.get_vm_image_instance_by_id(vm_image.tenant_id, vm_image.source_asset_id)
        return {
            "id": vm_image.ID,
            "name": vm_image.name,
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
            "extra": self._load_json(vm_image.extra_json, {}),
            "reference_count": self.get_vm_asset_reference_count(vm_image.tenant_id, vm_image),
            "source_asset": {
                "id": source_asset.ID,
                "name": source_asset.name
            } if source_asset else None,
            "create_time": self._format_datetime(getattr(vm_image, "create_time", None)),
            "update_time": self._format_datetime(getattr(vm_image, "update_time", None)),
        }

    def get_vm_asset_reference_count(self, tenant_id, vm_image):
        attr_refs = ComponentK8sAttributes.objects.filter(
            tenant_id=tenant_id, name="vm_asset_id", attribute_value=str(vm_image.ID)).count()
        if attr_refs > 0:
            return attr_refs
        return TenantServiceInfo.objects.filter(
            tenant_id=tenant_id, extend_method="vm", image=vm_image.image_url).count()

    def _build_vm_runtime_attrs(self, runtime_config):
        attrs = {
            "vm_network_mode": runtime_config.get("network_mode") or "random"
        }

        if attrs["vm_network_mode"] == "fixed":
            attrs["vm_network_name"] = runtime_config.get("network_name") or ""
            attrs["vm_fixed_ip"] = runtime_config.get("fixed_ip") or ""

        gpu_enabled = self._as_bool(runtime_config.get("gpu_enabled"))
        gpu_resources = self._as_list(runtime_config.get("gpu_resources"))
        if gpu_enabled and gpu_resources:
            attrs["vm_gpu_enabled"] = "true"
            attrs["vm_gpu_resources"] = json.dumps(gpu_resources)

        usb_enabled = self._as_bool(runtime_config.get("usb_enabled"))
        usb_resources = self._as_list(runtime_config.get("usb_resources"))
        if usb_enabled and usb_resources:
            attrs["vm_usb_enabled"] = "true"
            attrs["vm_usb_resources"] = json.dumps(usb_resources)

        asset_id = runtime_config.get("asset_id")
        if asset_id not in (None, ""):
            attrs["vm_asset_id"] = str(asset_id)

        clone_source = runtime_config.get("clone_source_id") or runtime_config.get("clone_source_name")
        if clone_source not in (None, ""):
            attrs["vm_asset_clone_source"] = str(clone_source)

        boot_mode = runtime_config.get("boot_mode")
        if boot_mode:
            attrs["vm_boot_mode"] = str(boot_mode)

        return attrs

    def _normalize_asset_payload(self, payload):
        normalized = dict(payload)
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
        normalized["labels_json"] = self._dump_json(normalized.get("labels_json"), normalized.get("labels", {}))
        normalized["extra_json"] = self._dump_json(normalized.get("extra_json"), normalized.get("extra", {}))
        return normalized

    def _load_json(self, value, default):
        if value in (None, ""):
            return default
        if isinstance(value, (dict, list)):
            return value
        try:
            return json.loads(value)
        except Exception:
            return default

    def _dump_json(self, raw_value, default):
        if raw_value in (None, ""):
            return json.dumps(default)
        if isinstance(raw_value, str):
            try:
                json.loads(raw_value)
                return raw_value
            except Exception:
                return json.dumps(default)
        return json.dumps(raw_value)

    def _infer_asset_format(self, *candidates):
        known_suffixes = (".qcow2", ".img", ".iso", ".tar.gz", ".tar.xz", ".gz", ".xz", ".tar")
        for candidate in candidates:
            candidate = str(candidate or "").lower()
            for suffix in known_suffixes:
                if candidate.endswith(suffix):
                    return suffix.lstrip(".")
        return ""

    def _format_datetime(self, value):
        if not value:
            return ""
        return value.strftime("%Y-%m-%d %H:%M:%S")

    def _as_bool(self, value):
        if isinstance(value, bool):
            return value
        return str(value).lower() in ("1", "true", "yes", "on", "enabled")

    def _as_list(self, value):
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

    def _to_int(self, value, default=None):
        if value in (None, ""):
            return default
        try:
            return int(value)
        except (TypeError, ValueError):
            return default


vms = VirtualMachineService()
