# -*- coding: utf-8 -*-
import logging

from www.models import TenantEnterprise, Tenants

logger = logging.getLogger("default")


class TenantEnterpriseRepo(object):

    def get_enterprise_by_enterprise_name(self, enterprise_name):
        enterprise = TenantEnterprise.objects.filter(enterprise_name=enterprise_name)
        if not enterprise:
            return None
        else:
            return enterprise[0]

    def get_enterprise_first(self):
        """
        获取第一条企业名
        :return:
        """
        enterprise = TenantEnterprise.objects.first()
        if not enterprise:
            return None
        else:
            return enterprise

    def get_enterprise_by_enterprise_id(self, enterprise_id, exception=True):
        enterprise = TenantEnterprise.objects.filter(enterprise_id=enterprise_id)
        if not enterprise:
            return None
        else:
            return enterprise[0]


enterprise_repo = TenantEnterpriseRepo()
