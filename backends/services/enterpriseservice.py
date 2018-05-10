# -*- coding: utf8 -*-
import logging

from www.models import TenantEnterprise
from django.db.models import F, Q, Sum
from fuzzyfinder.main import fuzzyfinder

logger = logging.getLogger("default")


class EnterpriseService(object):

    def is_enterprise_exist(self, enterprise_name):
        try:
            enterprise = TenantEnterprise.objects.get(enterprise_alias=enterprise_name)
            return True
        except TenantEnterprise.DoesNotExist as e:
            return False

    def create_enterprise(self, eid, enterprise_name, enterprise_alias, token, is_active=False):
        enterprise = TenantEnterprise.objects.create(enterprise_id=eid,
                                                     enterprise_name=enterprise_name,
                                                     enterprise_alias=enterprise_alias,
                                                     enterprise_token=token,
                                                     is_active=is_active)
        return enterprise

    def fuzzy_query_enterprise_by_enterprise_alias(self, enterprise_alias):
        enter_alias_map = list(TenantEnterprise.objects.values("enterprise_alias"))
        enter_alias_list = map(lambda x: x.get("enterprise_alias", "").lower(), enter_alias_map)
        find_enter_alias = list(fuzzyfinder(enterprise_alias.lower(), enter_alias_list))
        tenant_query = Q(enterprise_alias__in=find_enter_alias)
        tenant_list = TenantEnterprise.objects.filter(tenant_query)
        return tenant_list

    def fuzzy_query_enterprise_by_enterprise_name(self, enterprise_name):
        enter_name_map = list(TenantEnterprise.objects.values("enterprise_name"))
        enter_name_list = map(lambda x: x.get("enterprise_name", "").lower(), enter_name_map)
        find_enter_name = list(fuzzyfinder(enterprise_name.lower(), enter_name_list))
        tenant_query = Q(enterprise_name__in=find_enter_name)
        tenant_list = TenantEnterprise.objects.filter(tenant_query)
        return tenant_list

enterprise_service = EnterpriseService()
