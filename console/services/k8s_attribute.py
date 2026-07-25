# -*- coding: utf8 -*-
import json
from typing import Any, Dict, List

import yaml
from django.db import transaction
from django.db.models import QuerySet

from console.exception.main import ServiceHandleException
from console.repositories.k8s_attribute import k8s_attribute_repo
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import TenantServiceInfo, Tenants

region_api = RegionInvokeApi()

SEQUENCE_ATTRIBUTE_NAMES = {"cmd", "args"}


class ComponentK8sAttributeService(object):
    @staticmethod
    def _is_record_already_exists_error(error: Exception) -> bool:
        return "already exist" in str(error).lower()

    @staticmethod
    def _serialize_json_attribute_value(attribute_value: Any) -> str:
        if isinstance(attribute_value, str):
            try:
                json.loads(attribute_value)
                return attribute_value
            except (json.JSONDecodeError, ValueError):
                return json.dumps(attribute_value)
        if isinstance(attribute_value, dict):
            return json.dumps(attribute_value)
        if isinstance(attribute_value, list):
            if all(isinstance(value, dict) and "key" in value and "value" in value for value in attribute_value):
                return json.dumps({value["key"]: value["value"] for value in attribute_value})
            return json.dumps(attribute_value)
        return json.dumps(attribute_value)

    @staticmethod
    def _serialize_sequence_attribute_value(name: str, attribute_value: Any, save_type: str = "") -> str:
        if isinstance(attribute_value, str):
            try:
                values = yaml.safe_load(attribute_value)
            except yaml.YAMLError as exc:
                if save_type != "yaml":
                    values = [attribute_value]
                else:
                    raise ServiceHandleException(
                        msg="{0} must be a YAML string array".format(name),
                        msg_show="{0} 必须是 YAML 字符串数组".format(name)
                    ) from exc
            if not isinstance(values, list) and save_type != "yaml":
                values = [attribute_value]
            elif not isinstance(values, list):
                raise ServiceHandleException(
                    msg="{0} must be a YAML string array".format(name),
                    msg_show="{0} 必须是 YAML 字符串数组".format(name)
                )
        else:
            values = attribute_value

        if not isinstance(values, list):
            raise ServiceHandleException(
                msg="{0} must be a YAML string array".format(name),
                msg_show="{0} 必须是 YAML 字符串数组".format(name)
            )
        for index, item in enumerate(values):
            if not isinstance(item, str):
                raise ServiceHandleException(
                    msg="{0}[{1}] must be string".format(name, index),
                    msg_show="{0} 的第 {1} 项必须是字符串".format(name, index + 1)
                )
        return yaml.safe_dump(values, default_flow_style=False, allow_unicode=True)

    def _normalize_attribute_payload(self, attribute: Dict[str, Any]) -> Dict[str, Any]:
        if attribute.get("name") in SEQUENCE_ATTRIBUTE_NAMES:
            save_type = attribute.get("save_type", "")
            attribute["save_type"] = "yaml"
            attribute["attribute_value"] = self._serialize_sequence_attribute_value(
                attribute["name"], attribute.get("attribute_value", []), save_type)
        return attribute

    def get_by_component_ids_and_name(self, component_id: str, name: str) -> QuerySet:
        attributes = k8s_attribute_repo.get_by_component_id_name(component_id, name)
        if attributes and attributes[0].save_type == "json" and attributes[0].attribute_value:
            try:
                attributes[0].attribute_value = json.loads(attributes[0].attribute_value)
            except (json.JSONDecodeError, ValueError):
                pass
        return attributes

    def list_by_component_ids(self, component_ids: List[str]) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        attributes = k8s_attribute_repo.list_by_component_ids(component_ids)
        for attribute in attributes:
            if attribute.save_type == "json" and attribute.attribute_value:
                try:
                    parsed = json.loads(attribute.attribute_value)
                except (json.JSONDecodeError, ValueError):
                    result.append(attribute.to_dict())
                    continue
                if isinstance(parsed, dict):
                    attribute.attribute_value = [{
                        "key": key,
                        "value": value
                    } for key, value in parsed.items()]
                else:
                    # arrays (args, cmd) and plain strings (workingDir) pass through as-is
                    attribute.attribute_value = parsed
            result.append(attribute.to_dict())
        return result

    @transaction.atomic
    def create_k8s_attribute(self, tenant: Tenants, component: TenantServiceInfo, region_name: str,
                             attribute: Dict[str, Any], user_name: str) -> None:
        attribute = self._normalize_attribute_payload(attribute)
        if attribute["save_type"] == "json":
            attribute["attribute_value"] = self._serialize_json_attribute_value(attribute.get("attribute_value", []))
        k8s_attribute_repo.create(tenant_id=tenant.tenant_id, component_id=component.service_id, **attribute)
        attribute['operator'] = user_name
        try:
            region_api.create_component_k8s_attribute(tenant.tenant_name, region_name, component.service_alias, attribute)
        except Exception as error:
            if not self._is_record_already_exists_error(error):
                raise
            region_api.update_component_k8s_attribute(tenant.tenant_name, region_name, component.service_alias, attribute)

    @transaction.atomic
    def update_k8s_attribute(self, tenant: Tenants, component: TenantServiceInfo, region_name: str,
                             attribute: Dict[str, Any]) -> None:
        data: Dict[str, Any] = {"attribute_value": attribute.get("attribute_value", "")}
        attribute = self._normalize_attribute_payload(attribute)
        if attribute.get("name") in SEQUENCE_ATTRIBUTE_NAMES:
            data = {"save_type": "yaml", "attribute_value": attribute["attribute_value"]}
        elif attribute.get("save_type", "") == "json":
            attribute_value_json = self._serialize_json_attribute_value(attribute.get("attribute_value", []))
            attribute["attribute_value"] = attribute_value_json
            data = {"attribute_value": attribute_value_json}
        updated = k8s_attribute_repo.update(component.service_id, attribute["name"], **data)
        if updated == 0:
            k8s_attribute_repo.create(
                tenant_id=tenant.tenant_id,
                component_id=component.service_id,
                name=attribute["name"],
                save_type=attribute.get("save_type", ""),
                attribute_value=data["attribute_value"]
            )
        region_api.update_component_k8s_attribute(tenant.tenant_name, region_name, component.service_alias, attribute)

    @transaction.atomic
    def delete_k8s_attribute(self, tenant: Tenants, component: TenantServiceInfo, region_name: str, name: str,
                             operator: str) -> None:
        k8s_attribute_repo.delete(component.service_id, name)
        region_api.delete_component_k8s_attribute(tenant.tenant_name, region_name, component.service_alias, {
            "name": name,
            "operator": operator
        })


k8s_attribute_service = ComponentK8sAttributeService()
