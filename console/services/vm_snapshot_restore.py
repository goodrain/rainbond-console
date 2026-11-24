# -*- coding: utf-8 -*-
"""Scoped offline native VM snapshot restore projection."""
import re

from console.exception.main import ServiceHandleException
from console.services.vm_snapshot_read import (_object, _upstream_error, snapshot_error, vm_snapshot_read_service)
from www.apiclient.regionapi import RegionInvokeApi
from www.apiclient.regionapibaseclient import RegionApiBaseHttpClient


def _restore(value):
    value = _object(value)
    result = {}
    specification = {
        "restore_name": str,
        "snapshot_name": str,
        "request_id": str,
        "phase": str,
        "complete": bool,
    }
    for key, kind in specification.items():
        if type(value.get(key)) is not kind:
            raise snapshot_error("vm_snapshot_read_failed")
        result[key] = value[key]
    try:
        RegionInvokeApi._validated_vm_snapshot_name(result["snapshot_name"])
        RegionInvokeApi._validated_vm_snapshot_request_id(result["request_id"])
    except ServiceHandleException:
        raise snapshot_error("vm_snapshot_read_failed") from None
    if not re.fullmatch(r"vmr-[a-f0-9]{24}", result["restore_name"]):
        raise snapshot_error("vm_snapshot_read_failed")
    if result["phase"] not in {"pending", "succeeded", "failed"} or result["complete"] != (result["phase"] == "succeeded"):
        raise snapshot_error("vm_snapshot_read_failed")
    if "requires_advance" in value:
        advance = value["requires_advance"]
        if type(advance) is not bool or (advance and (result["phase"] != "pending" or result["complete"])):
            raise snapshot_error("vm_snapshot_read_failed")
        result["requires_advance"] = advance
    error_code = value.get("error_code")
    if error_code is not None:
        if error_code != "vm_restore_native_failed":
            raise snapshot_error("vm_snapshot_read_failed")
        result["error_code"] = error_code
    volumes = value.get("volumes")
    if not isinstance(volumes, list) or len(volumes) > 128:
        raise snapshot_error("vm_snapshot_read_failed")
    result["volumes"] = []
    for volume in volumes:
        volume = _object(volume)
        projected = {}
        for key in ("volume_name", "pvc_name", "volume_snapshot_name"):
            if type(volume.get(key)) is not str or not volume[key] or len(volume[key]) > 253:
                raise snapshot_error("vm_snapshot_read_failed")
            projected[key] = volume[key]
        result["volumes"].append(projected)
    return result


class VMSnapshotRestoreService:
    def __init__(self):
        self.client = RegionInvokeApi()

    @staticmethod
    def selection(tenant, service, region, snapshot_name, payload):
        vm_snapshot_read_service.validate_scope(tenant, service, region)
        allowed = {"request_id", "team_name", "region_name"}
        if not isinstance(payload, dict) or set(payload) - allowed:
            raise snapshot_error("vm_snapshot_invalid_request")
        if payload.get("team_name", tenant.tenant_name) != tenant.tenant_name or payload.get("region_name", region) != region:
            raise snapshot_error("vm_snapshot_invalid_request")
        try:
            snapshot_name = RegionInvokeApi._validated_vm_snapshot_name(snapshot_name)
            request_id = RegionInvokeApi._validated_vm_snapshot_request_id(payload.get("request_id"))
        except ServiceHandleException:
            raise snapshot_error("vm_snapshot_invalid_request") from None
        return snapshot_name, request_id

    @staticmethod
    def _call(reader, expected_status, *args):
        try:
            response, body = reader(*args)
        except ServiceHandleException as error:
            _upstream_error(error.status_code, {"bean": error.bean}, error.msg)
        except (RegionApiBaseHttpClient.CallApiError, RegionApiBaseHttpClient.CallApiFrequentError) as error:
            _upstream_error(error.status, error.body, error.body.get("msg") if isinstance(error.body, dict) else None)
        except Exception:
            raise snapshot_error("vm_snapshot_read_failed") from None
        response, body = _object(response), _object(body)
        status = response.get("status")
        if status != expected_status or body.get("code", status) != expected_status:
            _upstream_error(status, body, body.get("msg"))
        return _restore(_object(body.get("bean")))

    def start(self, tenant, service, region, snapshot_name, payload):
        snapshot_name, request_id = self.selection(tenant, service, region, snapshot_name, payload)
        return self._call(self.client.start_native_vm_restore, 202, region, tenant.tenant_name, service.service_alias,
                          snapshot_name, request_id)

    def status(self, tenant, service, region, snapshot_name, request_id):
        snapshot_name, request_id = self.selection(tenant, service, region, snapshot_name, {
            "request_id": request_id,
            "region_name": region
        })
        return self._call(self.client.get_native_vm_restore, 200, region, tenant.tenant_name, service.service_alias,
                          snapshot_name, request_id)


vm_snapshot_restore_service = VMSnapshotRestoreService()
