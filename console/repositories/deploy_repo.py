# -*- coding: utf-8 -*-
from console.models import DeployRelation


class DeployRepo(object):

    def get_deploy_relation_by_service_id(self, service_id):
        deploy_relation = DeployRelation.objects.filter(service_id=service_id)
        if not deploy_relation:
            return None
        return deploy_relation



    def create_deploy_relation(self, service_id, secret_key, key_type=None):
        DeployRelation.objects.create(service_id=service_id, secret_key=secret_key, key_type=key_type)



deploy_repo = DeployRepo()