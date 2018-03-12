# -*- coding: utf8 -*-
"""
  Created on 18/2/8.
"""
from console.models.main import ComposeGroup, ComposeServiceRelation


class GroupComposeRepository(object):
    def create_group_compose(self, **params):
        return ComposeGroup.objects.create(**params)

    def get_group_compose_by_id(self, compose_group_id):
        try:
            return ComposeGroup.objects.get(ID=compose_group_id)
        except ComposeGroup.DoesNotExist:
            return None

    def get_group_compose_by_group_id(self, group_id):
        cgs = ComposeGroup.objects.filter(group_id=group_id)
        if cgs:
            return cgs[0]
        return None

    def get_group_compose_by_compose_id(self, compose_id):
        cgs = ComposeGroup.objects.filter(compose_id=compose_id)
        if cgs:
            return cgs[0]
        return None

    def delete_group_compose_by_compose_id(self, compose_id):
        ComposeGroup.objects.filter(compose_id=compose_id).delete()

    def delete_group_compose_by_group_id(self, group_id):
        ComposeGroup.objects.filter(group_id=group_id).delete()


class ComposeServiceRepository(object):
    def create_compose_service_relation(self, team_id, service_id, compose_id):
        return ComposeServiceRelation.objects.create(team_id=team_id, service_id=service_id, compose_id=compose_id)

    def get_compose_service_relation_by_compose_id(self, compose_id):
        return ComposeServiceRelation.objects.filter(compose_id=compose_id)

    def bulk_create_compose_service_relation(self, service_ids, team_id, compose_id):
        csr_list = []
        for service_id in service_ids:
            csr = ComposeServiceRelation()
            csr.compose_id = compose_id
            csr.team_id = team_id
            csr.service_id = service_id
            csr_list.append(csr)
        ComposeServiceRelation.objects.bulk_create(csr_list)

    def delete_compose_service_relation_by_compose_id(self, compose_id):
        ComposeServiceRelation.objects.filter(compose_id=compose_id).delete()

    def delete_relation_by_service_id(self, service_id):
        ComposeServiceRelation.objects.filter(service_id=service_id).delete()

    def get_compose_id_by_service_id(self, service_id):
        csrs = ComposeServiceRelation.objects.filter(service_id=service_id)
        if csrs:
            return csrs[0]
        return None

compose_repo = GroupComposeRepository()
compose_relation_repo = ComposeServiceRepository()
