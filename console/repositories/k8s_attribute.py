# -*- coding: utf8 -*-

from console.models.main import ComponentK8sAttributes


class ComponentK8sAttributeRepo(object):
    def bulk_create(self, data):
        ComponentK8sAttributes.objects.bulk_create(data)

    def delete_by_component_ids(self, component_ids):
        return ComponentK8sAttributes.objects.filter(component_id__in=component_ids).delete()

    def list_by_component_ids(self, component_ids):
        return ComponentK8sAttributes.objects.filter(component_id__in=component_ids)


k8s_attribute_repo = ComponentK8sAttributeRepo()
