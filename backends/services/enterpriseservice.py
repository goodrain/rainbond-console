# -*- coding: utf8 -*-
import logging

from www.models import TenantEnterprise

logger = logging.getLogger("default")


class EnterpriseService(object):

    def is_enterprise_exist(self, enterprise_name):
        try:
            enterprise = TenantEnterprise.objects.get(enterprise_alias=enterprise_name)
            return True
        except TenantEnterprise.DoesNotExist as e:
            return False

    def create_enterprise(self, eid, enterprise_name, enterprise_alias, token):
        enterprise = TenantEnterprise.objects.create(enterprise_id=eid,
                                                     enterprise_name=enterprise_name,
                                                     enterprise_alias=enterprise_alias,
                                                     enterprise_token=token)
        return enterprise

enterprise_service = EnterpriseService()
