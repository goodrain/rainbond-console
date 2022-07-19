# -*- coding: utf8 -*-

from console.models.main import ComponentK8sAttributes


class ComponentK8sAttributeRepo(object):
<<<<<<< HEAD
    def bulk_create(self, data):
        ComponentK8sAttributes.objects.bulk_create(data)

    def delete_by_component_ids(self, component_ids):
        return ComponentK8sAttributes.objects.filter(component_id__in=component_ids).delete()
=======
    def create(self, **params):
        return ComponentK8sAttributes.objects.create(**params)

    def update(self, component_id, name, **data):
        return ComponentK8sAttributes.objects.filter(component_id=component_id, name=name).update(**data)

    def delete(self, component_id, name):
        return ComponentK8sAttributes.objects.filter(component_id=component_id, name=name).delete()
>>>>>>> 5a2d228cf1d7cb5d08c91e445d88c202fdea2011

    def list_by_component_ids(self, component_ids):
        return ComponentK8sAttributes.objects.filter(component_id__in=component_ids)


k8s_attribute_repo = ComponentK8sAttributeRepo()
