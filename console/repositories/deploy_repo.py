# -*- coding: utf-8 -*-
import base64
import pickle
import random
import string

from console.models import DeployRelation


class DeployRepo(object):
    def get_deploy_relation_by_service_id(self, service_id):
        deploy = DeployRelation.objects.filter(service_id=service_id)
        if not deploy:
            secretkey = ''.join(random.sample(string.ascii_letters + string.digits, 8))
            secret_key = base64.b64encode(pickle.dumps({"secret_key": secretkey}))
            deploy = DeployRelation.objects.create(service_id=service_id, secret_key=secret_key)
            return deploy


    def create_deploy_relation_by_service_id(self, service_id):
        deploy_relation = DeployRelation.objects.filter(service_id=service_id)
        if not deploy_relation:
            secretkey = ''.join(random.sample(string.ascii_letters + string.digits, 8))
            secret_key = base64.b64encode(pickle.dumps({"secret_key": secretkey}))
            DeployRelation.objects.create(service_id=service_id, secret_key=secret_key)
        # return deploy_relation[0]



deploy_repo = DeployRepo()