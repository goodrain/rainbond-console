# -*- coding: utf-8 -*-
import base64
import pickle
import random
import string

from console.models.main import DeployRelation


class DeployRepo(object):
    def get_deploy_relation_by_service_id(self, service_id):
        secret_obj = DeployRelation.objects.filter(service_id=service_id)
        if not secret_obj:
            secretkey = ''.join(random.sample(string.ascii_letters + string.digits, 8))
            pwd = base64.b64encode(pickle.dumps({"secret_key": secretkey}))
            deploy = DeployRelation.objects.create(service_id=service_id, secret_key=pwd)
            secret_key = deploy.secret_key
            return secret_key
        else:
            return secret_obj[0].secret_key

    def create_deploy_relation_by_service_id(self, service_id):
        deploy_relation = DeployRelation.objects.filter(service_id=service_id)
        if not deploy_relation:
            secretkey = ''.join(random.sample(string.ascii_letters + string.digits, 8))
            secret_key = base64.b64encode(pickle.dumps({"secret_key": secretkey}))
            DeployRelation.objects.create(service_id=service_id, secret_key=secret_key)

    def get_secret_key_by_service_id(self, service_id):
        deploy_obj = DeployRelation.objects.filter(service_id=service_id)
        if not deploy_obj:
            return None
        else:
            return deploy_obj[0].secret_key

    def get_service_key_by_service_id(self, service_id):
        secret_obj = DeployRelation.objects.filter(service_id=service_id).first()
        if not secret_obj:
            return None
        else:
            return secret_obj


deploy_repo = DeployRepo()
