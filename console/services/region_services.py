# -*- coding: utf-8 -*-
import logging

from django.conf import settings

from console.repositories.region_repo import region_repo
from console.repositories.team_repo import team_repo
from www.apiclient.regionapi import RegionInvokeApi

logger = logging.getLogger("default")
region_api = RegionInvokeApi()


class RegionService(object):
    def get_region_by_tenant_name(self, tenant_name):
        return region_repo.get_region_by_tenant_name(tenant_name=tenant_name)

    def get_region_name_list_by_team_name(self, team_name):
        regions = region_repo.get_region_by_tenant_name(tenant_name=team_name)
        region_name_list = list()
        if regions:
            for region in regions:
                region_desc = region_repo.get_region_desc_by_region_name(
                    region_name=region.region_name)
                if region_desc:
                    region_name_list.append({
                        "region_id":
                        region.ID,
                        "region_name":
                        region.region_name,
                        "service_status":
                        region.service_status,
                        "is_active":
                        region.is_active,
                        "is_init":
                        region.is_init,
                        "region_scope":
                        region.region_scope,
                        "region_alisa":
                        team_repo.get_region_alias(region.region_name),
                        "region.region_tenant_id":
                        region.region_tenant_id,
                        "create_time":
                        region.create_time,
                        "desc":
                        region_desc
                    })
            return region_name_list
        else:
            return []

    def get_region_list_by_team_name(self, request, team_name):
        regions = region_repo.get_active_region_by_tenant_name(tenant_name=team_name)
        if regions:
            region_name_list = []
            for region in regions:
                regionconfig = region_repo.get_region_by_region_name(region.region_name)
                if regionconfig:
                    region_info = {
                        "service_status": region.service_status,
                        "is_active": region.is_active,
                        "region_status": regionconfig.status,
                        "team_region_alias": regionconfig.region_alias,
                        "region.region_tenant_id": region.region_tenant_id,
                        "team_region_name": region.region_name,
                        "region_scope": region.region_scope,
                        "region_create_time": region.create_time,
                        "websocket_uri": regionconfig.wsurl
                    }
                    region_name_list.append(region_info)
            return region_name_list
        else:
            return []

    def get_team_unopen_region(self, team_name):
        usable_regions = region_repo.get_usable_regions()
        team_opened_regions = region_repo.get_team_opened_region(team_name)
        opened_regions_name = [
            team_region.region_name for team_region in team_opened_regions
        ]
        unopen_regions = usable_regions.exclude(
            region_name__in=opened_regions_name)
        return [unopen_region.to_dict() for unopen_region in unopen_regions]

    def get_open_regions(self):
        usable_regions = region_repo.get_usable_regions()
        return usable_regions

    def get_public_key(self, tenant, region):
        try:
            res, body = region_api.get_region_publickey(tenant.tenant_name, region, tenant.enterprise_id)
            if body and body["bean"]:
                return body["bean"]
            return {}
        except Exception as e:
            logger.exception(e)
            return {}

    # 调用数据中心API开通一个租户
    def open_team_region(self, team_name, region_name):
        tenant = team_repo.get_team_by_team_name(team_name)
        if not tenant:
            return 404, u"需要开通的团队{0}不存在".format(team_name), None
        region_config = region_repo.get_region_by_region_name_and_region_id(
            region_name)
        if not region_config:
            return 404, u"需要开通的数据中心{0}不存在".format(region_name), None
        tenant_region = region_repo.get_team_region_by_teannt_and_region(
            tenant.tenant_id, region_name)
        if not tenant_region:
            tenant_region = self.create_new_tenant_region(tenant, region_name)
        else:
            if not tenant_region.is_init:
                
                res, body = region_api.create_tenant(
                    region_name, tenant.tenant_name, tenant.tenant_id,
                    tenant.enterprise_id)
                logger.debug("create region tenant : res, {0}, body {1}".
                             format(res, body))
                tenant_region.is_active = True
                tenant_region.is_init = True
                # TODO 将从数据中心获取的租户信息记录到tenant_region, 当前只是用tenant的数据填充
                tenant_region.region_tenant_id = tenant.tenant_id
                tenant_region.region_tenant_name = tenant.tenant_name
                tenant_region.region_scope = 'public'
                tenant_region.enterprise_id = tenant.enterprise_id
                tenant_region.save()
            else:
                if (not tenant_region.region_tenant_id) or \
                        (not tenant_region.region_tenant_name) or \
                        (not tenant_region.enterprise_id):
                    tenant_region.region_tenant_id = tenant.tenant_id
                    tenant_region.region_tenant_name = tenant.tenant_name
                    tenant_region.region_scope = 'public'
                    tenant_region.enterprise_id = tenant.enterprise_id
                    tenant_region.save()
        return 200, u"success", tenant_region

    # 新建团队开通数据中心关系并调用数据中心API开通一个租户
    def create_new_tenant_region(self, tenant, region_name):
        tenant_region_info = {
            "tenant_id": tenant.tenant_id,
            "region_name": region_name
        }
        tenant_region = region_repo.create_tenant_region(**tenant_region_info)
        res, body = region_api.create_tenant(region_name, tenant.tenant_name,
                                             tenant.tenant_id,
                                             tenant.enterprise_id)
        logger.debug(
            "create region tenant : res, {0}, body {1}".format(res, body))
        tenant_region.is_active = True
        tenant_region.is_init = True
        # TODO 将从数据中心获取的租户信息记录到tenant_region, 当前只是用tenant的数据填充
        tenant_region.region_tenant_id = tenant.tenant_id
        tenant_region.region_tenant_name = tenant.tenant_name
        tenant_region.region_scope = 'public'
        tenant_region.enterprise_id = tenant.enterprise_id
        tenant_region.save()
        return tenant_region

    def get_region_httpdomain(self, region_name):
        region = region_repo.get_region_by_region_name(region_name)
        if region:
            return region.httpdomain
        return ""

    def get_region_tcpdomain(self, region_name):
        region = region_repo.get_region_by_region_name(region_name)
        if region:
            return region.tcpdomain
        return ""

    def get_region_wsurl(self, region_name):
        region = region_repo.get_region_by_region_name(region_name)
        if region:
            return region.wsurl
        return ""

    def get_region_url(self, region_name):
        region = region_repo.get_region_by_region_name(region_name)
        if region:
            return region.url
        return ""


region_services = RegionService()
