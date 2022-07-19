# -*- coding: utf8 -*-
import json

from django.db import transaction

from console.repositories.k8s_attribute import k8s_attribute_repo
from console.models.main import ComponentK8sAttributes
from www.apiclient.regionapi import RegionInvokeApi

region_api = RegionInvokeApi()


class ComponentK8sAttributeService(object):
    def list_by_component_ids(self, component_ids):
        result = []
        attributes = k8s_attribute_repo.list_by_component_ids(component_ids)
        for attribute in attributes:
            if attribute.save_type == "json":
                attribute.attribute_value = json.loads(attribute.attribute_value)
            result.append(attribute.to_dict())
        return result

    @transaction.atomic
<<<<<<< HEAD
    def create_or_update_attributes(self, tenant, component, region_name, attributes):
        k8s_attributes = []
        component_k8s_attributes = []
        for attribute in attributes:
            attr_value = attribute.get("attribute_value")
            if attribute.get("save_type") == "json":
                attr_value = json.dumps(attr_value)
            k8s_attributes.append(
                ComponentK8sAttributes(
                    name=attribute.get("name"),
                    tenant_id=tenant.tenant_id,
                    component_id=component.component_id,
                    save_type=attribute.get("save_type"),
                    attribute_fields=attribute.get("attribute_fields"),
                    attribute_value=attr_value))
            component_k8s_attributes.append({
                "name": attribute.get("name"),
                "save_type": attribute.get("save_type"),
                "attribute_fields": attribute.get("attribute_fields"),
                "attribute_value": attr_value
            })
        body = {"component_k8s_attributes": component_k8s_attributes}
        k8s_attribute_repo.delete_by_component_ids([component.component_id])
        k8s_attribute_repo.bulk_create(k8s_attributes)
        region_api.create_or_update_component_k8s_attributes(tenant.tenant_name, region_name, component.service_alias, body)
=======
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
>>>>>>> 5a2d228cf1d7cb5d08c91e445d88c202fdea2011


k8s_attribute_service = ComponentK8sAttributeService()
