# -*- coding: utf-8 -*-

from www.models.main import ServiceGroupRelation


class ServiceGroupRelationRepositry(object):
    def get_group_id_by_service(self, svc):
        group = ServiceGroupRelation.objects.filter(
            service_id=svc.service_id, tenant_id=svc.tenant_id, region_name=svc.service_region)
        if group:
            return group[0].group_id
        return None

    @staticmethod
    def bulk_create(service_group_rels):
        ServiceGroupRelation.objects.bulk_create(service_group_rels)

    @staticmethod
    def get_components_by_app_id(app_id):
        return ServiceGroupRelation.objects.filter(group_id=app_id)


service_group_relation_repo = ServiceGroupRelationRepositry()
