import logging
import json
import re

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

VM_RUNTIME_ATTR_SPECS = {
    "vm_network_mode": "string",
    "vm_network_name": "string",
    "vm_fixed_ip": "string",
    "vm_gateway": "string",
    "vm_dns_servers": "string",
    "vm_os_family": "string",
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
VM_MACHINE_ASSET_KIND = "machine"
VM_DISK_ASSET_KIND = "disk"
VM_EXPORT_ALLOWED_STATUSES = ("closed",)


class VirtualMachineService(object):
    def resolve_vm_boot_source(self, tenant, image_name, image_url, source_uri=""):
        return resolve_vm_boot_source_binding(tenant, image_name, image_url, source_uri=source_uri)

    def has_vm_export_machine_manifest(self, asset):
        if not asset or getattr(asset, "source_type", "") != "vm_export":
            return False
        extra = self._load_json(getattr(asset, "extra_json", ""), {})
        manifest = extra.get("machine_manifest") or {}
        return isinstance(manifest.get("disks"), list) and len(manifest.get("disks")) > 0

    def resolve_vm_export_restore_plan(self, asset, region_name, tenant_name):
        if not asset:
            return {}
        extra = self._load_json(getattr(asset, "extra_json", ""), {})
        manifest = extra.get("machine_manifest") or {}
        if not manifest:
            return {}
        _, body = region_api.get_vm_asset_restore_plan(
            region_name,
            tenant_name,
            {"manifest": manifest},
        )
        return body.get("bean", {}) if isinstance(body, dict) else {}

    def _create_vm_export_snapshot(self, region_name, tenant_name, service_alias, export_name, description):
        body = {
            "name": self._build_vm_export_snapshot_name(export_name),
            "description": description or ""
        }
        _, snapshot_body = region_api.create_vm_snapshot(region_name, tenant_name, service_alias, body)
        bean = snapshot_body.get("bean", {}) if isinstance(snapshot_body, dict) else {}
        return bean.get("snapshot_name") or body["name"]

    def _build_vm_export_snapshot_name(self, export_name):
        snapshot_name = "{}-snapshot".format(export_name or "vm-export").lower()
        snapshot_name = re.sub(r"[^a-z0-9-]+", "-", snapshot_name)
        snapshot_name = re.sub(r"-+", "-", snapshot_name).strip("-")
        if not snapshot_name:
            return "vm-export-snapshot"
        snapshot_name = snapshot_name[:63].rstrip("-")
        return snapshot_name or "vm-export-snapshot"

    def list_vm_image(self, tenant_id, region_name=None, tenant_name=None):
        vm_images = list(vm_repo.get_vm_images_by_tenant_id(tenant_id))
        vm_images = [
            self.sync_vm_export_asset_record(vm_image, region_name, tenant_name, allow_persist=False)
            for vm_image in vm_images
        ]
        source_ids = [vm_image.source_asset_id for vm_image in vm_images if vm_image.source_asset_id]
        source_map = {}
        if source_ids:
            source_map = {
                image.ID: image
                for image in VirtualMachineImage.objects.filter(tenant_id=tenant_id, ID__in=source_ids)
            }
        return [self.serialize_vm_image(vm_image, source_map.get(vm_image.source_asset_id)) for vm_image in vm_images]

    def get_vm_asset(self, tenant_id, asset_id, region_name=None, tenant_name=None):
        vm_image = vm_repo.get_vm_image_instance_by_id(tenant_id, asset_id)
        if not vm_image:
            return None
        vm_image = self.sync_vm_export_asset_record(vm_image, region_name, tenant_name)
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

    def get_vm_capabilities(self, region_name, tenant_name):
        _, body = region_api.get_vm_capabilities(region_name, tenant_name)
        return body.get("bean", {})

    def delete_vm_image(self, tenant_id, asset_id, region_name=None, tenant_name=None):
        vm_image = vm_repo.get_vm_image_instance_by_id(tenant_id, asset_id)
        if not vm_image:
            return 0, {}
        if self.get_vm_asset_reference_count(tenant_id, vm_image) > 0:
            raise ValueError("vm asset is still referenced")
        if getattr(vm_image, "source_type", "") == "vm_export":
            self.delete_vm_export_asset_resource(vm_image, region_name, tenant_name)
        return vm_repo.delete_vm_image_by_id(tenant_id, asset_id)

    def get_vm_current_pod_ip(self, tenant, service):
        if getattr(service, "extend_method", "") != "vm" or not tenant:
            return ""
        try:
            body = region_api.get_service_pods(
                service.service_region,
                tenant.tenant_name,
                service.service_alias,
                tenant.enterprise_id
            )
        except Exception as err:
            logger.exception(err)
            return ""

        bean = body.get("bean", {}) if isinstance(body, dict) else {}
        if not isinstance(bean, dict):
            return ""

        def pick_pod_ip(pods, running_only=False):
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

    def get_vm_profile(self, service, connections=None, current_pod_ip=""):
        if getattr(service, "extend_method", "") != "vm":
            return {}
        runtime = self.get_vm_runtime_config(service.service_id)
        asset = self.get_vm_asset_for_service(service, runtime.get("asset_id"))
        latest_export = self.get_latest_vm_export_asset(service.tenant_id, service.service_id)
        return {
            "asset": self.serialize_vm_image(asset) if asset else {},
            "runtime": runtime,
            "latest_export": self.serialize_vm_image(latest_export) if latest_export else {},
            "current_pod_ip": current_pod_ip or "",
            "connections": connections or {
                "vnc_url": "",
                "console_url": ""
            }
        }

    def get_live_vm_export_name(self, service):
        return str(getattr(service, "service_id", "") or "").strip()

    def get_live_vm_export_display_name(self, service):
        return str(
            getattr(service, "service_cname", "") or
            getattr(service, "service_alias", "") or
            getattr(service, "service_id", "") or
            ""
        ).strip()

    def list_vm_export_assets_for_service(self, tenant_id, service_id):
        return list(VirtualMachineImage.objects.filter(
            tenant_id=tenant_id,
            source_type="vm_export",
            source_uri="service://{}".format(service_id)
        ).order_by("-ID"))

    def build_vm_export_confirmation_payload(self, asset):
        if not asset:
            return {}
        serialized = self.serialize_vm_image(asset)
        return {
            "id": serialized.get("id"),
            "display_name": serialized.get("display_name") or serialized.get("name"),
            "status": serialized.get("status"),
        }

    def delete_vm_export_resource(self, region_name, tenant_name, service_alias, export_id):
        if not region_name or not tenant_name or not service_alias or not export_id:
            return
        try:
            region_api.delete_vm_export(region_name, tenant_name, service_alias, export_id)
        except Exception as err:
            if self._is_missing_vm_export_error(err, export_id) or self._is_region_resource_missing_error(err):
                logger.warning(
                    "vm export delete ignored missing resource: service_alias=%s export_id=%s err=%s",
                    service_alias,
                    export_id,
                    err,
                )
                return
            raise

    def delete_vm_export_asset_resource(self, asset, region_name=None, tenant_name=None):
        if not asset or getattr(asset, "source_type", "") != "vm_export":
            return
        extra = self._load_json(getattr(asset, "extra_json", ""), {})
        service_alias = extra.get("source_service_alias", "")
        export_id = getattr(asset, "build_event_id", "") or extra.get("source_service_id", "")
        self.delete_vm_export_resource(region_name, tenant_name, service_alias, export_id)

    def replace_vm_export_assets_for_service(self, service, region_name, tenant_name):
        assets = self.list_vm_export_assets_for_service(service.tenant_id, service.service_id)
        export_ids = set()
        for asset in assets:
            extra = self._load_json(getattr(asset, "extra_json", ""), {})
            export_id = getattr(asset, "build_event_id", "") or extra.get("source_service_id", "")
            if export_id:
                export_ids.add(export_id)
        export_ids.add(self.get_live_vm_export_name(service))
        for export_id in export_ids:
            self.delete_vm_export_resource(region_name, tenant_name, service.service_alias, export_id)
        if assets:
            VirtualMachineImage.objects.filter(
                tenant_id=service.tenant_id,
                source_type="vm_export",
                source_uri="service://{}".format(service.service_id)
            ).delete()

    def start_vm_export(self, service, region_name, tenant_name, vm_status, description=""):
        if getattr(service, "extend_method", "") != "vm":
            raise ValueError("only vm service supports export")
        vm_status = str(vm_status or "").lower()
        if vm_status not in VM_EXPORT_ALLOWED_STATUSES:
            raise ValueError("vm export requires closed status")

        export_name = self.get_live_vm_export_name(service)
        display_name = self.get_live_vm_export_display_name(service)
        runtime_snapshot = self.get_vm_runtime_config(service.service_id)
        source_asset = self.get_vm_asset_for_service(service, runtime_snapshot.get("asset_id"))
        request_body = {
            "name": export_name,
            "description": description,
            "export_all_disks": True,
            "source_kind": "vm",
        }
        # Keep the single-slot export clean even if a stale region export survived without a DB row.
        self.delete_vm_export_resource(region_name, tenant_name, service.service_alias, export_name)
        _, body = region_api.start_vm_export(region_name, tenant_name, service.service_alias, request_body)
        bean = body.get("bean", {}) if isinstance(body, dict) else {}
        disks = bean.get("disks", [])
        asset = self.create_vm_image_asset(
            tenant_id=service.tenant_id,
            name=export_name,
            image_url="",
            source_type="vm_export",
            source_uri="service://{}".format(service.service_id),
            status=bean.get("status") or "exporting",
            build_event_id=bean.get("export_id", ""),
            source_asset_id=source_asset.get("id") if isinstance(source_asset, dict) else getattr(source_asset, "ID", None),
            boot_mode=runtime_snapshot.get("boot_mode", ""),
            extra={
                "asset_kind": VM_MACHINE_ASSET_KIND,
                "disk_count": len(disks),
                "source_service_id": service.service_id,
                "source_service_alias": service.service_alias,
                "source_service_cname": getattr(service, "service_cname", "") or "",
                "display_name": display_name,
                "export_request": {
                    "description": description,
                    "vm_status": vm_status,
                    "export_all_disks": True,
                    "source_kind": "vm",
                    "snapshot_name": "",
                },
                "runtime_snapshot": runtime_snapshot,
                "storage_status": "exporting",
                "disks": disks,
            }
        )
        return self.serialize_vm_image(asset)

    def sync_vm_export_status(self, asset, region_name, tenant_name, allow_persist=True):
        if not asset:
            return None
        extra = self._load_json(asset.extra_json, {})
        _, body = region_api.get_vm_export_status(
            region_name,
            tenant_name,
            extra.get("source_service_alias", ""),
            asset.build_event_id)
        bean = body.get("bean", {}) if isinstance(body, dict) else {}
        disks = bean.get("disks", extra.get("disks", []))
        extra["disks"] = disks
        extra["disk_count"] = len(disks)
        extra["latest_export_status"] = bean.get("status") or asset.status
        extra["storage_status"] = bean.get("status") or extra.get("storage_status") or asset.status

        root_disk = next((disk for disk in disks if disk.get("disk_role") == "root"), None)
        asset.status = bean.get("status") or asset.status
        if root_disk and root_disk.get("download_url"):
            asset.image_url = root_disk.get("download_url")
        logger.info(
            "vm export asset sync: asset_id=%s export_id=%s status=%s root_url=%s disk_count=%s",
            getattr(asset, "ID", ""),
            getattr(asset, "build_event_id", ""),
            asset.status,
            root_disk.get("download_url", "") if root_disk else "",
            len(disks),
        )
        asset.extra_json = json.dumps(extra)
        asset.save()
        return self.serialize_vm_image(asset)

    def sync_vm_export_asset_record(self, asset, region_name=None, tenant_name=None, allow_persist=True):
        if not asset or getattr(asset, "source_type", "") != "vm_export":
            return asset
        if not region_name or not tenant_name:
            return asset
        try:
            self.sync_vm_export_status(asset, region_name, tenant_name, allow_persist=allow_persist)
        except Exception as err:
            if self._is_missing_vm_export_error(err, getattr(asset, "build_event_id", "")):
                logger.warning(
                    "vm export asset sync fallback: asset=%s export_id=%s err=%s",
                    getattr(asset, "ID", ""),
                    getattr(asset, "build_event_id", ""),
                    err,
                )
                self._mark_vm_export_asset_missing(asset)
            elif self._is_region_resource_missing_error(err):
                logger.warning(
                    "vm export asset sync skipped missing region resource: asset=%s export_id=%s err=%s",
                    getattr(asset, "ID", ""),
                    getattr(asset, "build_event_id", ""),
                    err,
                )
            else:
                raise
        asset.refresh_from_db()
        return asset

    def get_latest_vm_export_asset(self, tenant_id, service_id):
        return VirtualMachineImage.objects.filter(
            tenant_id=tenant_id,
            source_type="vm_export",
            source_uri="service://{}".format(service_id)
        ).order_by("-ID").first()

    def is_vm_asset_ready(self, asset):
        if not asset:
            return False
        if getattr(asset, "source_type", "") == "vm_export":
            extra = self._load_json(getattr(asset, "extra_json", ""), {})
            disks = extra.get("disks") or []
            root_ready = any(
                str(disk.get("disk_role", "")).lower() == "root" and disk.get("download_url")
                for disk in disks
            )
            all_ready = bool(disks) and all(disk.get("download_url") for disk in disks)
            return bool(getattr(asset, "status", "") == "ready" and root_ready and all_ready)
        return bool(getattr(asset, "status", "") == "ready" and getattr(asset, "image_url", ""))

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
            "disk_layout": self._as_list_of_dicts(attrs.get("vm_disk_layout")),
            "network_mode": attrs.get("vm_network_mode") or "random",
            "network_name": attrs.get("vm_network_name", ""),
            "fixed_ip": attrs.get("vm_fixed_ip", ""),
            "gateway": attrs.get("vm_gateway", ""),
            "dns_servers": attrs.get("vm_dns_servers", ""),
            "os_family": attrs.get("vm_os_family", ""),
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

    def save_vm_runtime_config(self, tenant_id, service_id, runtime_config, sync_context=None):
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

    def save_vm_disk_imports(self, tenant_id, service_id, disk_imports):
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

    def validate_vm_runtime_config(self, runtime_config):
        network_mode = runtime_config.get("network_mode") or "random"
        if network_mode == "fixed" and not runtime_config.get("fixed_ip"):
            raise ValueError("fixed vm network mode requires fixed_ip")

        gpu_enabled = self._as_bool(runtime_config.get("gpu_enabled"))
        gpu_resources = self._as_list(runtime_config.get("gpu_resources"))
        if gpu_enabled and not gpu_resources:
            raise ValueError("gpu_enabled requires gpu_resources")
        gpu_count = self._to_int(runtime_config.get("gpu_count"), 1 if gpu_enabled else 0)
        if gpu_enabled and (gpu_count is None or gpu_count < 1):
            raise ValueError("gpu_enabled requires gpu_count")
        if gpu_enabled and gpu_count > 1 and len(gpu_resources) != 1:
            raise ValueError("gpu_count greater than 1 requires exactly one gpu resource")

        usb_enabled = self._as_bool(runtime_config.get("usb_enabled"))
        usb_resources = self._as_list(runtime_config.get("usb_resources"))
        if usb_enabled and not usb_resources:
            raise ValueError("usb_enabled requires usb_resources")

    def serialize_vm_image(self, vm_image, source_asset=None):
        if not vm_image:
            return {}
        if vm_image.source_asset_id and not source_asset:
            source_asset = vm_repo.get_vm_image_instance_by_id(vm_image.tenant_id, vm_image.source_asset_id)
        extra = self._load_json(vm_image.extra_json, {})
        disks = extra.get("disks", [])
        display_name = (
            extra.get("display_name") or
            extra.get("source_service_cname") or
            extra.get("source_service_alias") or
            vm_image.name
        )
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
            "reference_count": self.get_vm_asset_reference_count(vm_image.tenant_id, vm_image),
            "source_asset": {
                "id": source_asset.ID,
                "name": source_asset.name
            } if source_asset else None,
            "create_time": self._format_datetime(getattr(vm_image, "create_time", None)),
            "update_time": self._format_datetime(getattr(vm_image, "update_time", None)),
        }

    def get_vm_asset_reference_count(self, tenant_id, vm_image):
        # Incomplete VM rows are transient and should not block asset deletion or inflate catalog references.
        active_vm_services = TenantServiceInfo.objects.filter(
            tenant_id=tenant_id,
            extend_method="vm",
            create_status="complete")
        active_vm_service_ids = active_vm_services.values_list("service_id", flat=True)
        attr_refs = ComponentK8sAttributes.objects.filter(
            tenant_id=tenant_id,
            component_id__in=active_vm_service_ids,
            name="vm_asset_id",
            attribute_value=str(vm_image.ID)).count()
        if attr_refs > 0:
            return attr_refs
        bound_service_ids = ComponentK8sAttributes.objects.filter(
            tenant_id=tenant_id,
            component_id__in=active_vm_service_ids,
            name="vm_asset_id").values_list("component_id", flat=True)
        return active_vm_services.exclude(service_id__in=bound_service_ids).filter(image=vm_image.image_url).count()

    def _build_vm_runtime_attrs(self, runtime_config):
        attrs = {
            "vm_network_mode": runtime_config.get("network_mode") or "random"
        }

        if attrs["vm_network_mode"] == "fixed":
            attrs["vm_network_name"] = runtime_config.get("network_name") or ""
            attrs["vm_fixed_ip"] = runtime_config.get("fixed_ip") or ""
            attrs["vm_gateway"] = runtime_config.get("gateway") or ""
            attrs["vm_dns_servers"] = runtime_config.get("dns_servers") or ""

        os_family = runtime_config.get("os_family")
        if os_family not in (None, ""):
            attrs["vm_os_family"] = str(os_family)

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

    def infer_vm_boot_source_format(self, asset=None, template_payload=None, image_name="", image_url="", source_uri=""):
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
            if getattr(asset, "source_type", "") == "vm_export":
                return "disk"
        inferred = self._infer_asset_format(source_uri, image_url, image_name)
        if inferred:
            return inferred
        return ""

    def build_vm_create_disk_imports(self, asset=None, template_payload=None, image_name="", image_url="", source_uri=""):
        imports = []
        root_import = self._build_vm_root_disk_import(
            asset=asset,
            template_payload=template_payload,
            image_name=image_name,
            image_url=image_url,
            source_uri=source_uri,
        )
        if root_import:
            imports.append(root_import)
        if asset and getattr(asset, "source_type", "") == "vm_export":
            imports.extend(self._build_vm_export_data_disk_imports(asset))
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
            self.infer_vm_boot_source_format(
                asset=asset,
                template_payload=template_payload,
                image_name=image_name,
                image_url=image_url,
                source_uri=source_uri,
            ),
        )
        return imports

    def resolve_vm_boot_mode(self,
                             requested_boot_mode="",
                             asset=None,
                             template_payload=None,
                             runtime_config=None,
                             image_name="",
                             image_url="",
                             source_uri="",
                             boot_source_format=""):
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

    def _build_vm_root_disk_import(self, asset=None, template_payload=None, image_name="", image_url="", source_uri=""):
        boot_source_format = self.infer_vm_boot_source_format(
            asset=asset,
            template_payload=template_payload,
            image_name=image_name,
            image_url=image_url,
            source_uri=source_uri,
        )
        if boot_source_format == "iso":
            return None

        root_disk = self._extract_root_disk_payload(asset=asset, template_payload=template_payload)
        if root_disk:
            restore_url = root_disk.get("image_url") or ""
            if not self._is_http_source(restore_url):
                return None
            return {
                "volume_name": "disk",
                "disk_key": root_disk.get("disk_key") or "rootdisk",
                "disk_name": root_disk.get("disk_name") or root_disk.get("disk_key") or "rootdisk",
                "image_url": restore_url,
                "source_uri": root_disk.get("source_uri") or "",
                "format": root_disk.get("format") or "",
                "checksum": root_disk.get("checksum") or "",
            }

        restore_url = self._resolve_root_restore_url(asset=asset, image_url=image_url, source_uri=source_uri)
        if not self._is_http_source(restore_url):
            return None
        return {
            "volume_name": "disk",
            "disk_key": "rootdisk",
            "disk_name": "rootdisk",
            "image_url": restore_url,
            "source_uri": "",
            "format": boot_source_format or "",
            "checksum": "",
        }

    def _build_vm_export_data_disk_imports(self, asset):
        if not asset or getattr(asset, "source_type", "") != "vm_export":
            return []
        extra = self._load_json(getattr(asset, "extra_json", ""), {})
        imports = []
        for disk in extra.get("disks", []) or []:
            if str(disk.get("disk_role", "")).lower() == "root":
                continue
            image_url = disk.get("download_url") or disk.get("image_url") or ""
            if not self._is_http_source(image_url):
                continue
            imports.append({
                "volume_name": disk.get("disk_key") or "disk",
                "disk_key": disk.get("disk_key") or "disk",
                "disk_name": disk.get("disk_name") or disk.get("disk_key") or "disk",
                "image_url": image_url,
                "source_uri": disk.get("source_uri") or disk.get("export_name") or "",
                "format": disk.get("format") or "",
                "checksum": disk.get("checksum") or "",
            })
        return imports

    def build_vm_export_disk_layout(self, asset):
        if not asset or getattr(asset, "source_type", "") != "vm_export":
            return []
        extra = self._load_json(getattr(asset, "extra_json", ""), {})
        layout = []
        for index, disk in enumerate(extra.get("disks", []) or []):
            disk_role = str(disk.get("disk_role", "") or "data").lower()
            boot_order = self._to_int(disk.get("boot_order"), index + 1)
            layout.append({
                "disk_key": disk.get("disk_key") or "disk-{}".format(index + 1),
                "disk_name": disk.get("disk_name") or disk.get("disk_key") or "disk-{}".format(index + 1),
                "disk_role": disk_role,
                "boot_order": boot_order,
                "order_index": index,
                "boot": disk_role == "root",
            })
        return layout

    def resolve_vm_export_data_disks(self, asset):
        if not asset or getattr(asset, "source_type", "") != "vm_export":
            return []
        extra = self._load_json(getattr(asset, "extra_json", ""), {})
        resolved = []
        for disk in extra.get("disks", []) or []:
            if str(disk.get("disk_role", "")).lower() == "root":
                continue
            resolved.append({
                "disk_key": disk.get("disk_key"),
                "size_bytes": self._to_int(disk.get("size_bytes"), 0),
            })
        return resolved

    def _extract_root_disk_payload(self, asset=None, template_payload=None):
        if template_payload:
            for disk in template_payload.get("disk_layout") or []:
                if str(disk.get("disk_role", "")).lower() == "root":
                    return {
                        "disk_key": disk.get("disk_key") or "rootdisk",
                        "disk_name": disk.get("disk_name") or disk.get("disk_key") or "rootdisk",
                        "image_url": disk.get("image_url") or "",
                        "source_uri": disk.get("source_uri") or "",
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
                        "format": disk.get("format") or "",
                        "checksum": disk.get("checksum") or "",
                    }
        return None

    def _resolve_root_restore_url(self, asset=None, image_url="", source_uri=""):
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

    def _normalize_vm_boot_mode(self, value):
        return str(value or "").strip().lower()

    def _infer_vm_guest_os_family(self, runtime_config=None, asset=None, image_name=""):
        runtime_config = runtime_config or {}
        explicit = str(runtime_config.get("os_family") or "").strip().lower()
        if explicit in ("windows", "linux"):
            return explicit

        hints = [
            getattr(asset, "os_name", "") if asset else "",
            getattr(asset, "name", "") if asset else "",
            image_name,
        ]
        merged_hint = " ".join([str(item or "") for item in hints]).strip().lower()
        if "windows" in merged_hint:
            return "windows"
        return ""

    def _is_http_source(self, value):
        value = str(value or "").strip().lower()
        return value.startswith("http://") or value.startswith("https://")

    def _should_persist_vm_export_asset(self, asset, bean, extra):
        if not asset or getattr(asset, "source_type", "") != "vm_export":
            return False
        if extra.get("storage_status") == "ready":
            return False
        if (bean or {}).get("status") != "ready":
            return False
        disks = (bean or {}).get("disks") or []
        if not disks:
            return False
        return all(disk.get("download_url") for disk in disks)

    def _apply_vm_export_persist_result(self, asset, extra, persist_bean):
        if not persist_bean:
            return
        extra["storage_status"] = persist_bean.get("status") or extra.get("storage_status") or "exporting"
        if persist_bean.get("storage_backend"):
            extra["storage_backend"] = persist_bean.get("storage_backend")
            asset.storage_backend = persist_bean.get("storage_backend")
        if persist_bean.get("storage_bucket"):
            extra["storage_bucket"] = persist_bean.get("storage_bucket")
        if persist_bean.get("storage_prefix"):
            extra["storage_prefix"] = persist_bean.get("storage_prefix")
        if persist_bean.get("machine_manifest"):
            extra["machine_manifest"] = persist_bean.get("machine_manifest")
        root_object_uri = persist_bean.get("root_object_uri") or ""
        if root_object_uri:
            asset.image_url = root_object_uri
        if extra.get("storage_status") == "ready":
            asset.status = "ready"
        else:
            asset.status = persist_bean.get("status") or "exporting"

    def _is_missing_vm_export_error(self, err, export_id=""):
        message = self._flatten_vm_export_error_message(err)
        if "vm export" not in message or "not found" not in message:
            return False
        if export_id and export_id.lower() not in message:
            return False
        return True

    def _flatten_vm_export_error_message(self, err):
        parts = []

        def collect(value):
            if value in (None, ""):
                return
            if isinstance(value, dict):
                for item in value.values():
                    collect(item)
                return
            if isinstance(value, (list, tuple, set)):
                for item in value:
                    collect(item)
                return
            parts.append(str(value))

        if isinstance(err, ServiceHandleException):
            collect(err.msg)
            collect(err.msg_show)
            collect(err.details)
        collect(getattr(err, "message", None))
        collect(str(err))
        return " ".join(parts).lower()

    def _mark_vm_export_asset_missing(self, asset):
        if not asset:
            return
        extra = self._load_json(asset.extra_json, {})
        extra["export_record_missing"] = True
        extra["latest_export_error"] = "vm export not found"
        extra["latest_export_status"] = extra.get("latest_export_status") or asset.status
        if not getattr(asset, "image_url", "") and getattr(asset, "status", "") not in ("ready", "failed"):
            asset.status = "failed"
        asset.extra_json = json.dumps(extra)
        asset.save()

    def _is_region_resource_missing_error(self, err):
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

    def _normalize_vm_disk_imports(self, disk_imports):
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
            }
        return normalized

    def _persist_managed_k8s_attribute(self, tenant_id, service_id, name, save_type, value, sync_context=None):
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

    def _get_vm_attr_sync_context(self, service_id):
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

    def _sync_managed_k8s_attribute(self, sync_context, name, save_type, value, existed_before):
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

    def _normalize_asset_payload(self, payload):
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

    def _requires_vm_source_build(self, image_url):
        return requires_vm_source_build(image_url)

    def _build_vm_runtime_image_name(self, tenant, image_name):
        return build_vm_runtime_image_name(tenant, image_name)

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

    def _as_list_of_dicts(self, value):
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

    def _to_int(self, value, default=None):
        if value in (None, ""):
            return default
        try:
            return int(value)
        except (TypeError, ValueError):
            return default


vms = VirtualMachineService()
