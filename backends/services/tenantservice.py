# -*- coding: utf8 -*-
import datetime
import logging

from django.conf import settings
from django.db.models import F, Q, Sum
from fuzzyfinder.main import fuzzyfinder

from backends.models.main import RegionConfig
from backends.services.exceptions import *
from www.models.main import Tenants, PermRelTenant, Users, TenantRegionInfo, TenantServiceInfo, TenantEnterprise
from www.utils import sn
from www.utils.license import LICENSE

logger = logging.getLogger("default")


class TenantService(object):
    def get_all_tenants(self):
        """
        获取云帮所有租户名
        :return: [{"tenant_name":"goodrain","tenant_id":"auer889283jadkj23aksufhaksjd","ID":1}]
        """
        tenants = Tenants.objects.values("tenant_name", "tenant_id", "ID", "tenant_alias").order_by("-ID")
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

    def get_fuzzy_tenants_by_tenant_name(self, tenant_name):
        tenant_name_map = list(Tenants.objects.values("tenant_name"))
        tenant_name_list = map(lambda x: x.get("tenant_name", "").lower(), tenant_name_map)
        find_tenant_name = list(fuzzyfinder(tenant_name.lower(), tenant_name_list))
        tenant_query = Q(tenant_name__in=find_tenant_name)
        tenant_list = Tenants.objects.filter(tenant_query)
        return tenant_list

    def get_fuzzy_tenants_by_tenant_alias(self, tenant_alias):
        tenant_alias_map = list(Tenants.objects.values("tenant_alias"))
        tenant_alias_list = map(lambda x: x.get("tenant_alias", "").lower(), tenant_alias_map)
        find_tenant_alias = list(fuzzyfinder(tenant_alias.lower(), tenant_alias_list))
        tenant_query = Q(tenant_alias__in=find_tenant_alias)
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
        enterprise_id = user.enterprise_id
        tenants_num = Tenants.objects.count()
        allow_num = LICENSE.get_authorization_tenant_number()
        if tenants_num >= allow_num:
            raise TenantOverFlowError("租户数已超最大配额")
        if Tenants.objects.filter(
                tenant_name=tenant_name).exists():
            raise TenantExistError("租户{}已存在".format(tenant_name))
        expired_day = 7
        if hasattr(settings, "TENANT_VALID_TIME"):
            expired_day = int(settings.TENANT_VALID_TIME)
        expire_time = datetime.datetime.now() + datetime.timedelta(
            days=expired_day)
        # 计算此团队需要初始化的数据中心
        prepare_init_regions = []
        if regions:
            region_configs = RegionConfig.objects.filter(region_name__in=regions, status="1")
            prepare_init_regions.extend(region_configs)
        else:
            region_configs = RegionConfig.objects.filter(status="1")
            prepare_init_regions.extend(region_configs)

        if not prepare_init_regions:
            raise Exception('please init one region at least.')
        enterprise = TenantEnterprise.objects.get(enterprise_id=enterprise_id)
        # 团队管理的默认数据中心
        default_region = prepare_init_regions[0]
        tenant_alias = u'{0}的团队'.format(enterprise.enterprise_alias)
        is_private = sn.instance.is_private()
        if is_private:
            pay_type = 'payed'
            pay_level = 'company'
        else:
            pay_type = 'free'
            pay_level = 'company'
        tenant = Tenants.objects.create(tenant_name=tenant_name, pay_type=pay_type, pay_level=pay_level,
                                        creater=creater, region=default_region.region_name,
                                        expired_time=expire_time, tenant_alias=tenant_alias,
                                        enterprise_id=enterprise.enterprise_id)
        logger.info('create tenant:{}'.format(tenant.to_dict()))
        PermRelTenant.objects.create(user_id=creater, tenant_id=tenant.pk, identity='admin',
                                     enterprise_id=enterprise.pk)
        if regions:
            for r in regions:
                TenantRegionInfo.objects.create(tenant_id=tenant.tenant_id,
                                                region_name=r,
                                                enterprise_id=enterprise.enterprise_id,
                                                is_active=True,
                                                is_init=False,
                                                region_tenant_id=tenant.tenant_id,
                                                region_tenant_name=tenant.tenant_name,
                                                region_scope='public')

        # tenant = enterprise_svc.create_and_init_tenant(creater, tenant_name, regions, user.enterprise_id)
        return tenant

    def add_user_to_tenant(self, tenant, user, identity, enterprise):
        perm_tenants = PermRelTenant.objects.filter(tenant_id=tenant.ID, user_id=user.user_id)
        if perm_tenants:
            raise PermTenantsExistError("用户{0}已存在于租户{1}下".format(user.nick_name, tenant.tenant_name))
        perm_tenant = PermRelTenant.objects.create(
            user_id=user.pk, tenant_id=tenant.pk, identity=identity, enterprise_id=enterprise.ID)
        return perm_tenant

    def get_team_by_name_or_alias_or_enter(self, tenant_name, tenant_alias, enterprise_id):
        query = Q()
        if tenant_name:
            query &= Q(tenant_name=tenant_name)
        if tenant_alias:
            query &= Q(tenant_alias=tenant_alias)
        if enterprise_id:
            query &= Q(enterprise_id=enterprise_id)
        return Tenants.objects.filter(query)

tenant_service = TenantService()
