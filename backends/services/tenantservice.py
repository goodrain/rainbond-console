# -*- coding: utf8 -*-
import logging

from django.db.models import F, Q, Sum
from fuzzyfinder.main import fuzzyfinder

from backends.services.exceptions import *
from www.models.main import Tenants, PermRelTenant, Users, TenantRegionInfo, TenantServiceInfo
from www.services import enterprise_svc

logger = logging.getLogger("default")


class TenantService(object):
    def get_all_tenants(self):
        """
        获取云帮所有租户名
        :return: [{"tenant_name":"goodrain","tenant_id":"auer889283jadkj23aksufhaksjd","ID":1}]
        """
        tenants = Tenants.objects.values("tenant_name", "tenant_id", "ID").order_by("tenant_name")
        return tenants

    def get_tenant_users(self, tenant_name):
        tenant = self.get_tenant(tenant_name)
        user_id_list = PermRelTenant.objects.filter(tenant_id=tenant.ID).values_list("user_id", flat=True)
        user_list = Users.objects.filter(user_id__in=user_id_list)
        return user_list

    def get_users_by_tenantID(self, tenant_ID):
        user_id_list = PermRelTenant.objects.filter(tenant_id=tenant_ID).values_list("user_id", flat=True)
        user_list = Users.objects.filter(user_id__in=user_id_list)
        return user_list

    def get_tenant(self, tenant_name):
        if not Tenants.objects.filter(tenant_name=tenant_name).exists():
            raise Tenants.DoesNotExist
        return Tenants.objects.get(tenant_name=tenant_name)

    def get_fuzzy_tenants(self, tenant_name):
        tenant_name_map = list(Tenants.objects.values("tenant_name"))
        tenant_name_list = map(lambda x: x.get("tenant_name", "").lower(), tenant_name_map)
        find_tenant_name = list(fuzzyfinder(tenant_name.lower(), tenant_name_list))
        tenant_query = Q(tenant_name__in=find_tenant_name)
        tenant_list = Tenants.objects.filter(tenant_query)
        return tenant_list

    def get_tenant_region(self, tenant_id, region):
        tenant_region_list = TenantRegionInfo.objects.filter(tenant_id=tenant_id, region_name=region)
        result = {}
        if not tenant_region_list:
            result["is_exist"] = False
            result["is_active"] = False
            result["is_init"] = False
        else:
            tenant_region = tenant_region_list[0]
            result["is_exist"] = True
            result["is_active"] = tenant_region.is_active
            result["is_init"] = tenant_region.is_init
        return result

    def get_all_tenant_region(self, regions):
        tenant_region_list = TenantRegionInfo.objects.filter(region_name__in=regions)
        return tenant_region_list

    def get_tenant_service(self, enable_regions, start, end):
        """
        返回数据
        [
            {
                'tenant_id': u'ff13b88209e64ed194e9941684c1d075',
                'service_region': u'ali-sh',
                'memory': Decimal('1462703')
            }

        ]
        """
        tenant_services = TenantServiceInfo.objects.all().values("tenant_id", "service_region").annotate(
            cpu=Sum("min_cpu"), memory=Sum(F('min_node') * F('min_memory'))).filter(
            service_region__in=enable_regions).order_by(
            "-memory")

        total = len(tenant_services)
        rt_services = tenant_services[start:end]
        return total, rt_services

    def add_tenant(self, tenant_name, user, regions):
        if not user:
            user = Users.objects.get(user_id=1)
        creater = user.pk
        tenant = enterprise_svc.create_and_init_tenant(creater, tenant_name, regions)
        return tenant

    def add_user_to_tenant(self, tenant, user):
        perm_tenants = PermRelTenant.objects.filter(tenant_id=tenant.ID, user_id=user.user_id)
        if perm_tenants:
            raise PermTenantsExistError("用户{0}已存在于租户{1}下".format(user.nick_name,tenant.tenant_name))
        perm_tenant = PermRelTenant.objects.create(
            user_id=user.pk, tenant_id=tenant.pk, identity='admin')
        return perm_tenant

tenant_service = TenantService()
