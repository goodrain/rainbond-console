# -*- coding: utf-8 -*-
"""Read-only Console projection of the Region VM snapshot contract."""
import re

from django.utils.translation import get_language

from console.exception.main import ServiceHandleException
from www.apiclient.regionapi import RegionInvokeApi
from www.apiclient.regionapibaseclient import RegionApiBaseHttpClient

# Keep Region machine codes and HTTP distinctions, without returning upstream text.
ERRORS = {
    "vm_snapshot_invalid_request": (400, "快照查询参数无效", "Invalid snapshot query.", False),
    "vm_snapshot_forbidden": (403, "无权查看此虚拟机的快照", "You cannot view this VM's snapshots.", False),
    "vm_snapshot_not_found": (404, "虚拟机快照不存在", "VM snapshot not found.", False),
    "vm_restore_busy": (409, "虚拟机正在执行其他操作，请稍后重试", "The VM is busy. Try again later.", False),
    "vm_restore_conflict": (409, "快照状态冲突，请刷新后重试", "Snapshot state conflicts. Refresh and try again.", False),
    "vm_snapshot_pending": (409, "快照状态尚未确认，请稍后重试", "Snapshot state is pending. Try again later.", True),
    "vm_snapshot_config_unsupported": (422, "当前虚拟机配置不支持快照", "This VM configuration does not support snapshots.", False),
    "vm_snapshot_storage_unsupported": (422, "当前存储不支持虚拟机快照", "This storage does not support VM snapshots.", False),
    "vm_snapshot_incomplete": (422, "快照未包含全部可写磁盘", "The snapshot does not cover all writable disks.", False),
    "vm_snapshot_unsupported": (422, "此组件不支持虚拟机快照", "This component does not support VM snapshots.", False),
    "vm_snapshot_dependency_unavailable":
    (503, "快照依赖服务暂不可用，请稍后重试", "Snapshot services are unavailable. Try again later.", True),
    "vm_snapshot_read_failed": (502, "读取虚拟机快照失败，请稍后重试", "Failed to read VM snapshots. Try again later.", True),
}
PUBLIC_SNAPSHOT_ERRORS = {
    "vm_snapshot_native_failed", "vm_snapshot_cleanup_outcome_pending", "vm_snapshot_create_outcome_pending",
    "vm_snapshot_delete_outcome_pending", "vm_snapshot_halt_outcome_pending", "vm_snapshot_resume_outcome_pending",
    "vm_snapshot_identity_pending", "vm_snapshot_identity_outcome_unknown"
}


def snapshot_error(code):
    status, chinese, english, retryable = ERRORS[code]
    language = get_language() or "zh-hans"
    return ServiceHandleException(code,
                                  english if language.startswith("en") else chinese,
                                  status,
                                  status,
                                  bean={"error": {
                                      "code": code,
                                      "retryable": retryable
                                  }},
                                  details={"retryable": retryable})


def _upstream_error(status, body=None, message=None):
    try:
        status = int(status)
    except (TypeError, ValueError):
        status = 502
    bean = body.get("bean", {}) if isinstance(body, dict) else {}
    error = bean.get("error", {}) if isinstance(bean, dict) else {}
    code = error.get("code") if isinstance(error, dict) else None
    if not isinstance(code, str) or code not in ERRORS or ERRORS[code][0] != status:
        code = message if isinstance(message, str) else None
    if code not in ERRORS or ERRORS[code][0] != status:
        code = {
            400: "vm_snapshot_invalid_request",
            401: "vm_snapshot_forbidden",
            403: "vm_snapshot_forbidden",
            404: "vm_snapshot_not_found",
            409: "vm_restore_conflict",
            422: "vm_snapshot_unsupported",
            503: "vm_snapshot_dependency_unavailable"
        }.get(status, "vm_snapshot_read_failed")
    raise snapshot_error(code)


def _object(value):
    if not isinstance(value, dict):
        raise snapshot_error("vm_snapshot_read_failed")
    return value


def _fields(value, specification):
    value = _object(value)
    projected = {}
    for key, kind in specification.items():
        item = value.get(key)
        if type(item) is not kind or (kind is int and not 0 <= item <= 2**63 - 1) or (kind is str and len(item) > 2048):
            raise snapshot_error("vm_snapshot_read_failed")
        projected[key] = item
    return projected


def _string_list(value):
    if not isinstance(value, list) or any(type(item) is not str or len(item) > 253 for item in value):
        raise snapshot_error("vm_snapshot_read_failed")
    return list(value)


def _project_snapshot(value):
    value = _object(value)
    result = _fields(
        value, {
            "snapshot_name": str,
            "description": str,
            "phase": str,
            "ready_to_use": bool,
            "consistency": str,
            "manifest_acked": bool,
            "finalized": bool,
            "cancelled": bool,
            "deleted": bool
        })
    try:
        RegionInvokeApi._validated_vm_snapshot_name(result["snapshot_name"])
    except ServiceHandleException:
        raise snapshot_error("vm_snapshot_read_failed") from None
    if not re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", result["phase"]) or result["consistency"] != "offline":
        raise snapshot_error("vm_snapshot_read_failed")
    coverage = _object(value.get("coverage"))
    result["coverage"] = _fields(coverage, {"complete": bool, "expected_writable_disks": int, "included_disks": int})
    for key in ("missing_disk_keys", "excluded_read_only"):
        result["coverage"][key] = _string_list(coverage.get(key))
    if "creation_time" in value:
        result.update(_fields(value, {"creation_time": str}))
    if "error_code" in value:
        if not isinstance(value["error_code"], str) or (value["error_code"]
                                                        and value["error_code"] not in PUBLIC_SNAPSHOT_ERRORS):
            raise snapshot_error("vm_snapshot_read_failed")
        if value["error_code"]:
            result["error_code"] = value["error_code"]
        if value["error_code"] in ("vm_snapshot_identity_pending",
                                   "vm_snapshot_identity_outcome_unknown") and result["ready_to_use"]:
            raise snapshot_error("vm_snapshot_read_failed")
    disks = value.get("disks")
    if not isinstance(disks, list):
        raise snapshot_error("vm_snapshot_read_failed")
    result["disks"] = [
        _fields(disk, {
            "volume_id": int,
            "disk_key": str,
            "role": str,
            "read_only": bool,
            "storage_class": str,
            "requested_bytes": int
        }) for disk in disks
    ]
    if "config" in value:
        config = _object(value["config"])
        result["config"] = _fields(config, {"cpu_milli": int, "memory_mib": int, "boot_mode": str})
        if not isinstance(config.get("disk_layout"), list):
            raise snapshot_error("vm_snapshot_read_failed")
        result["config"]["disk_layout"] = [
            _fields(disk, {
                "volume_id": int,
                "role": str,
                "device": str,
                "bus": str,
                "boot_order": int,
                "read_only": bool
            }) for disk in config["disk_layout"]
        ]
    return result


class VMSnapshotReadService:
    def __init__(self):
        self.client = RegionInvokeApi()

    def capability(self, tenant, service, region):
        from console.services.vm_existing_snapshot_capability import project_existing_snapshot_capability
        self.validate_scope(tenant, service, region)
        data = self._read(self.client.get_vm_snapshot_capability, region, tenant.tenant_name, service.service_alias)
        return project_existing_snapshot_capability(data)

    @staticmethod
    def validate_scope(tenant, service, region):
        if service.tenant_id != tenant.tenant_id or service.service_region != region:
            raise snapshot_error("vm_snapshot_not_found")
        if service.extend_method != "vm":
            raise snapshot_error("vm_snapshot_unsupported")

    @staticmethod
    def _pagination(value, maximum):
        if type(value) is str and re.fullmatch(r"[0-9]{1,19}", value):
            value = int(value)
        if type(value) is not int or not 1 <= value <= maximum:
            raise snapshot_error("vm_snapshot_invalid_request")
        return value

    @staticmethod
    def _read(reader, *args, **kwargs):
        try:
            response, body = reader(*args, **kwargs)
        except ServiceHandleException as error:
            _upstream_error(error.status_code, {"bean": error.bean}, error.msg)
        except (RegionApiBaseHttpClient.CallApiError, RegionApiBaseHttpClient.CallApiFrequentError) as error:
            _upstream_error(error.status, error.body, error.body.get("msg") if isinstance(error.body, dict) else None)
        except Exception:
            raise snapshot_error("vm_snapshot_read_failed") from None
        response = _object(response)
        if response.get("status") != 200:
            _upstream_error(response.get("status"), body, body.get("msg") if isinstance(body, dict) else None)
        body = _object(body)
        if body.get("code", 200) != 200:
            _upstream_error(body.get("code"), body, body.get("msg"))
        bean = _object(body.get("bean"))
        if "error" in bean:
            error = _object(bean["error"])
            code = error.get("code")
            if not isinstance(code, str) or code not in ERRORS:
                raise snapshot_error("vm_snapshot_read_failed")
            _upstream_error(ERRORS[code][0], {"bean": bean}, code)
        return bean

    def list(self, tenant, service, region, page=1, page_size=20):
        self.validate_scope(tenant, service, region)
        page = self._pagination(page, 2**63 - 1)
        page_size = self._pagination(page_size, 100)
        data = self._read(self.client.list_vm_snapshots,
                          region,
                          tenant.tenant_name,
                          service.service_alias,
                          page=page,
                          page_size=page_size)
        result = _fields(data, {"page": int, "page_size": int, "total": int})
        if result["page"] != page or result["page_size"] != page_size or not isinstance(data.get("items"), list):
            raise snapshot_error("vm_snapshot_read_failed")
        if len(data["items"]) > page_size or result["total"] < len(data["items"]):
            raise snapshot_error("vm_snapshot_read_failed")
        result["items"] = [_project_snapshot(item) for item in data["items"]]
        return result

    def detail(self, tenant, service, region, snapshot_name):
        self.validate_scope(tenant, service, region)
        try:
            self.client._validated_vm_snapshot_name(snapshot_name)
        except ServiceHandleException:
            raise snapshot_error("vm_snapshot_invalid_request") from None
        data = self._read(self.client.get_vm_snapshot, region, tenant.tenant_name, service.service_alias, snapshot_name)
        result = _project_snapshot(data)
        if result["snapshot_name"] != snapshot_name:
            raise snapshot_error("vm_snapshot_read_failed")
        return result


vm_snapshot_read_service = VMSnapshotReadService()
