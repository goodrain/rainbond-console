# -*- coding: utf-8 -*-
from math import isfinite
from numbers import Real
from typing import Any, Dict

from console.exception.main import ServiceHandleException
from www.apiclient.regionapi import RegionInvokeApi

region_api = RegionInvokeApi()


class AvailableResourcesService(object):
    RESOURCE_FIELDS = ("all_node", "node_ready", "cap_cpu", "req_cpu", "cap_mem", "req_mem")

    def get_available_resources(self, tenant: Any, region: Any) -> Dict[str, int]:
        try:
            response, body = region_api.get_region_resources(tenant.enterprise_id, region=region.region_name)
        except Exception:
            raise self._detection_failure()

        if not hasattr(response, "get") or response.get("status") != 200:
            raise self._detection_failure()
        bean = body.get("bean") if isinstance(body, dict) else None
        if not self._is_valid_resource_bean(bean):
            raise self._detection_failure()

        try:
            total_cpu = int(round(bean["cap_cpu"] * 1000))
            requested_cpu = int(round(bean["req_cpu"] * 1000))
            free_memory = int(max(bean["cap_mem"] - bean["req_mem"], 0))
        except (OverflowError, TypeError, ValueError):
            raise self._detection_failure()
        return {
            "free_cpu": max(total_cpu - requested_cpu, 0),
            "free_memory": free_memory,
        }

    @classmethod
    def _is_valid_resource_bean(cls, bean: Any) -> bool:
        if not isinstance(bean, dict):
            return False
        if any(not cls._is_nonnegative_number(bean.get(field)) for field in cls.RESOURCE_FIELDS):
            return False
        if not all(cls._is_integer_value(bean[field]) for field in ("all_node", "node_ready", "cap_mem", "req_mem")):
            return False
        return bean["node_ready"] > 0 and bean["node_ready"] <= bean["all_node"]

    @staticmethod
    def _is_nonnegative_number(value: Any) -> bool:
        if not isinstance(value, Real) or isinstance(value, bool):
            return False
        try:
            return isfinite(value) and value >= 0
        except (TypeError, ValueError, OverflowError):
            return False

    @staticmethod
    def _is_integer_value(value: Any) -> bool:
        try:
            return int(value) == value
        except (TypeError, ValueError, OverflowError):
            return False

    @staticmethod
    def _detection_failure() -> ServiceHandleException:
        return ServiceHandleException(
            msg="available resources detection failed",
            msg_show="资源检测失败，请稍后重试",
            status_code=502,
            error_code=502,
        )


available_resources_service = AvailableResourcesService()
