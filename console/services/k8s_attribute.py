# -*- coding: utf8 -*-
import json

from django.db import transaction

from console.repositories.k8s_attribute import k8s_attribute_repo
from www.apiclient.regionapi import RegionInvokeApi

region_api = RegionInvokeApi()


class ComponentK8sAttributeService(object):
    def get_by_component_ids_and_name(self, component_id, name):
        attributes = k8s_attribute_repo.get_by_component_id_name(component_id, name)
        if attributes and attributes[0].save_type == "json":
            attributes[0].attribute_value = json.loads(attributes[0].attribute_value)
        return attributes

    def list_by_component_ids(self, component_ids):
        result = []
        attributes = k8s_attribute_repo.list_by_component_ids(component_ids)
        for attribute in attributes:
            if attribute.save_type == "json":
                attribute.attribute_value = [{
                    "key": key,
                    "value": value
                } for key, value in json.loads(attribute.attribute_value).items()]
            result.append(attribute.to_dict())
        return result

    @transaction.atomic
    def create_k8s_attribute(self, tenant, component, region_name, attribute):
        k8s_attribute_repo.create(tenant_id=tenant.tenant_id, component_id=component.service_id, **attribute)
        region_api.create_component_k8s_attribute(tenant.tenant_name, region_name, component.service_alias, attribute)

    @transaction.atomic
    def update_k8s_attribute(self, tenant, component, region_name, attribute):
        data = {"attribute_value": attribute.get("attribute_value", "")}
        k8s_attribute_repo.update(component.service_id, attribute["name"], **data)
        region_api.update_component_k8s_attribute(tenant.tenant_name, region_name, component.service_alias, attribute)

    @transaction.atomic
    def delete_k8s_attribute(self, tenant, component, region_name, name):
        k8s_attribute_repo.delete(component.service_id, name)
        region_api.delete_component_k8s_attribute(tenant.tenant_name, region_name, component.service_alias, {"name": name})


k8s_attribute_service = ComponentK8sAttributeService()
