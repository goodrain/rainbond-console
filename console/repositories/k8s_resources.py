# -*- coding: utf8 -*-

from console.models.main import K8sResource


class AppK8sResourceRepo(object):
    def create(self, **params):
        return K8sResource.objects.create(**params)

    def bulk_create(self, app_k8s_resource):
        return K8sResource.objects.bulk_create(app_k8s_resource)

    def update(self, app_id, name, **data):
        return K8sResource.objects.filter(app_id=app_id, name=name).update(**data)

    def delete_by_name(self, app_id, name):
        return K8sResource.objects.filter(app_id=app_id, name=name).delete()

    def delete_by_id(self, id):
        return K8sResource.objects.filter(ID=id).delete()

    def list_by_app_id(self, app_id):
        return K8sResource.objects.filter(app_id=app_id)

    def get_by_app_id_name(self, app_id, name):
        return K8sResource.objects.get(app_id=app_id, name=name)

    def get_by_id(self, id):
        return K8sResource.objects.get(ID=id)

    def list_available_resources(self, app_id):
        # CreateSuccess = 1, UpdateSuccess = 2
        return K8sResource.objects.filter(app_id=app_id, success__in=[1, 2])


k8s_resources_repo = AppK8sResourceRepo()
