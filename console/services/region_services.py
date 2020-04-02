# -*- coding: utf-8 -*-
import json
import logging

from django.core.paginator import Paginator
from django.db import transaction

from console.enum.region_enum import RegionStatusEnum
from console.exception.exceptions import RegionUnreachableError
from console.models.main import ConsoleSysConfig
from console.models.main import RegionConfig
from console.repositories.group import group_repo
from console.repositories.region_repo import region_repo
from console.repositories.team_repo import team_repo
from console.services.config_service import platform_config_service
from console.services.service_services import base_service
from www.apiclient.baseclient import client_auth_service
from www.apiclient.marketclient import MarketOpenAPI
from www.apiclient.regionapi import RegionInvokeApi

logger = logging.getLogger("default")
region_api = RegionInvokeApi()
market_api = MarketOpenAPI()


class RegionService(object):
    def get_region_by_tenant_name(self, tenant_name):
        return region_repo.get_region_by_tenant_name(tenant_name=tenant_name)

    def get_region_by_region_id(self, region_id):
        return region_repo.get_region_by_region_id(region_id=region_id)

    def get_region_by_region_name(self, region_name):
        return region_repo.get_region_by_region_name(region_name=region_name)

    def get_by_region_name(self, region_name):
        return region_repo.get_by_region_name(region_name)

    def get_region_all_list_by_team_name(self, team_name):
        regions = region_repo.get_region_by_tenant_name(tenant_name=team_name)
        region_name_list = list()
        if regions:
            for region in regions:
                region_desc = region_repo.get_region_desc_by_region_name(region_name=region.region_name)
                if region_desc:
                    region_name_list.append({
                        "region_id": region.ID,
                        "region_name": region.region_name,
                        "service_status": region.service_status,
                        "is_active": region.is_active,
                        "is_init": region.is_init,
                        "region_scope": region.region_scope,
                        "region_alisa": team_repo.get_region_alias(region.region_name),
                        "region.region_tenant_id": region.region_tenant_id,
                        "create_time": region.create_time,
                        "desc": region_desc
                    })
            return region_name_list
        else:
            return []

    # get_region_list_by_team_name get region list that status is used
    def get_region_list_by_team_name(self, team_name):
        regions = region_repo.get_active_region_by_tenant_name(tenant_name=team_name)
        if regions:
            region_name_list = []
            for region in regions:
                regionconfig = region_repo.get_region_by_region_name(region.region_name)
                if regionconfig and regionconfig.status in ("1", "3"):
                    region_info = {
                        "service_status": region.service_status,
                        "is_active": region.is_active,
                        "region_status": regionconfig.status,
                        "team_region_alias": regionconfig.region_alias,
                        "region_tenant_id": region.region_tenant_id,
                        "team_region_name": region.region_name,
                        "region_scope": regionconfig.scope,
                        "region_create_time": regionconfig.create_time,
                        "websocket_uri": regionconfig.wsurl,
                        "tcpdomain": regionconfig.tcpdomain
                    }
                    region_name_list.append(region_info)
            return region_name_list
        else:
            return []

    # verify_team_region Verify that the team tenant is open
    def verify_team_region(self, team_name, region_name):
        regions = region_repo.get_active_region_by_tenant_name(tenant_name=team_name)
        if regions:
            for region in regions:
                if region_name == region.region_name:
                    return True
        return False

    def list_by_tenant_ids(self, tenant_ids):
        regions = region_repo.list_active_region_by_tenant_ids(tenant_ids)
        if regions:
            result = []
            for region in regions:
                regionconfig = region_repo.get_region_by_region_name(region.region_name)
                if regionconfig and regionconfig.status in ("1", "3"):
                    region_info = {
                        "service_status": region.service_status,
                        "is_active": region.is_active,
                        "region_status": regionconfig.status,
                        "team_region_alias": regionconfig.region_alias,
                        "region_tenant_id": region.region_tenant_id,
                        "team_region_name": region.region_name,
                        "region_scope": regionconfig.scope,
                        "region_create_time": regionconfig.create_time,
                        "websocket_uri": regionconfig.wsurl,
                        "tcpdomain": regionconfig.tcpdomain
                    }
                    result.append(region_info)
            return result
        else:
            return []

    def list_by_tenant_id(self, tenant_id, query="", page=None, page_size=None):
        regions = region_repo.list_by_tenant_id(tenant_id, query, page, page_size)
        total = region_repo.count_by_tenant_id(tenant_id, query)
        return regions, total

    def list_services_by_tenant_name(self, region_name, team_id):
        return base_service.get_services_list(team_id, region_name)

    def get_team_unopen_region(self, team_name):
        usable_regions = region_repo.get_usable_regions()
        team_opened_regions = region_repo.get_team_opened_region(team_name).filter(is_init=True)
        opened_regions_name = [team_region.region_name for team_region in team_opened_regions]
        unopen_regions = usable_regions.exclude(region_name__in=opened_regions_name)
        return [unopen_region.to_dict() for unopen_region in unopen_regions]

    def get_open_regions(self):
        usable_regions = region_repo.get_usable_regions()
        return usable_regions

    def get_public_key(self, tenant, region):
        try:
            res, body = region_api.get_region_publickey(
                tenant.tenant_name, region, tenant.enterprise_id, tenant.tenant_id)
            if body and body["bean"]:
                return body["bean"]
            return {}
        except Exception as e:
            logger.exception(e)
            return {}

    def get_all_regions(self, query="", page=None, page_size=None):
        regions = region_repo.get_all_regions(query)
        total = regions.count()
        paginator = Paginator(regions, page_size)
        rp = paginator.page(page)

        result = []
        for region in rp:
            result.append({
                "region_alias": region.region_alias,
                "url": region.url,
                "token": region.token,
                "wsurl": region.wsurl,
                "httpdomain": region.httpdomain,
                "tcpdomain": region.tcpdomain,
                "scope": region.scope,
                "ssl_ca_cert": region.ssl_ca_cert,
                "cert_file": region.cert_file,
                "key_file": region.key_file,
                "status": region.status,
                "desc": region.desc,
                "region_name": region.region_name,
                "region_id": region.region_id
            })

        return result, total

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

    def create_tenant_on_region(self, team_name, region_name):
        tenant = team_repo.get_team_by_team_name(team_name)
        if not tenant:
            return 404, u"需要开通的团队{0}不存在".format(team_name), None
        region_config = region_repo.get_region_by_region_name(region_name)
        if not region_config:
            return 404, u"需要开通的数据中心{0}不存在".format(region_name), None
        tenant_region = region_repo.get_team_region_by_tenant_and_region(tenant.tenant_id, region_name)
        if not tenant_region:
            tenant_region_info = {"tenant_id": tenant.tenant_id, "region_name": region_name, "is_active": False}
            tenant_region = region_repo.create_tenant_region(**tenant_region_info)
        if not tenant_region.is_init:
            res, body = region_api.create_tenant(region_name, tenant.tenant_name,
                                                 tenant.tenant_id, tenant.enterprise_id)
            if res["status"] != 200 and body['msg'] != 'tenant name {} is exist'.format(tenant.tenant_name):
                return res["status"], u"数据中心创建租户失败", None
            tenant_region.is_active = True
            tenant_region.is_init = True
            # TODO 将从数据中心获取的租户信息记录到tenant_region, 当前只是用tenant的数据填充
            tenant_region.region_tenant_id = tenant.tenant_id
            tenant_region.region_tenant_name = tenant.tenant_name
            tenant_region.region_scope = region_config.scope
            tenant_region.enterprise_id = tenant.enterprise_id
            tenant_region.save()
        else:
            if (not tenant_region.region_tenant_id) or \
                    (not tenant_region.region_tenant_name) or \
                    (not tenant_region.enterprise_id):
                tenant_region.region_tenant_id = tenant.tenant_id
                tenant_region.region_tenant_name = tenant.tenant_name
                tenant_region.region_scope = region_config.scope
                tenant_region.enterprise_id = tenant.enterprise_id
                tenant_region.save()
        group_repo.get_or_create_default_group(tenant.tenant_id, region_name)
        return 200, u"success", tenant_region

    def get_enterprise_free_resource(self, tenant_id, enterprise_id, region_name, user_name):
        try:
            res, data = market_api.get_enterprise_free_resource(tenant_id, enterprise_id, region_name, user_name)
            return True
        except Exception as e:
            logger.error("get_new_user_free_res_pkg error with params: {}".format(
                (tenant_id, enterprise_id, region_name, user_name)))
            logger.exception(e)
            return False

    def get_region_access_info(self, team_name, region_name):
        """获取一个团队在指定数据中心的身份认证信息"""
        url, token = client_auth_service.get_region_access_token_by_tenant(team_name, region_name)
        # 如果团队所在企业所属数据中心信息不存在则使用通用的配置(兼容未申请数据中心token的企业)
        region_info = region_repo.get_region_by_region_name(region_name)
        url = region_info.url
        if not token:
            token = region_info.token
        else:
            token = "Token {}".format(token)
        return url, token

    def get_region_access_info_by_enterprise_id(self, enterprise_id, region_name):
        """获取一个团队在指定数据中心的身份认证信息"""
        url, token = client_auth_service.get_region_access_token_by_enterprise_id(enterprise_id, region_name)
        # 如果团队所在企业所属数据中心信息不存在则使用通用的配置(兼容未申请数据中心token的企业)
        region_info = region_repo.get_region_by_region_name(region_name)
        url = region_info.url
        if not token:
            token = region_info.token
        else:
            token = "Token {}".format(token)
        return url, token

    def get_team_usable_regions(self, team_name):
        usable_regions = region_repo.get_usable_regions()
        region_names = [r.region_name for r in usable_regions]
        team_opened_regions = region_repo.get_team_opened_region(
            team_name).filter(is_init=True, region_name__in=region_names)
        return team_opened_regions

    def get_regions_by_enterprise_id(self, enterprise_id):
        teams = team_repo.get_team_by_enterprise_id(enterprise_id)
        team_ids = [t.tenant_id for t in teams]
        region_names = region_repo.get_regions_by_tenant_ids(team_ids)
        return region_repo.get_region_by_region_names(region_names)

    def add_region(self, region_data):
        region = region_repo.get_region_by_region_name(region_data["region_name"])
        if region:
            raise RegionExistException("数据中心{0}已存在".format(region_data["region_name"]))
        region = region_repo.create_region(region_data)
        return region

    def update_region(self, region_data):
        region_id = region_data.get("region_id")
        region = self.get_region_by_region_id(region_id)
        if not region:
            raise RegionNotExistException("数据中心{0}不存在".format(region_id))
        # Update fields that can be updated
        if "region_alias" in region_data:
            region.region_alias = region_data["region_alias"]
        if "url" in region_data:
            region.url = region_data["url"]
        if "wsurl" in region_data:
            region.wsurl = region_data["wsurl"]
        if "httpdomain" in region_data:
            region.httpdomain = region_data["httpdomain"]
        if "tcpdomain" in region_data:
            region.tcpdomain = region_data["tcpdomain"]
        if "status" in region_data:
            region.status = region_data["status"]
        if "desc" in region_data:
            region.desc = region_data["desc"]
        if "scope" in region_data:
            region.scope = region_data["scope"]
        if "ssl_ca_cert" in region_data:
            region.ssl_ca_cert = region_data["ssl_ca_cert"]
        if "cert_file" in region_data:
            region.cert_file = region_data["cert_file"]
        if "key_file" in region_data:
            region.key_file = region_data["key_file"]
        return region_repo.update_region(region)

    @transaction.atomic
    def update_region_status(self, region_id, status):
        region = region_repo.get_region_by_region_id(region_id)

        stauts_tbl = RegionStatusEnum.to_dict()
        status = status.upper()
        region.status = stauts_tbl[status]

        if status == RegionStatusEnum.ONLINE.name:
            try:
                region_api.get_api_version(region.url, region.token, region.region_name)
            except region_api.CallApiError as e:
                logger.warning("数据中心{0}不可达,无法上线: {1}".format(region.region_name, e.message))
                raise RegionUnreachableError("数据中心{0}不可达,无法上线".format(region.region_name))

        region.save()
        self.update_region_config()
        return region

    def update_region_config(self):
        region_data = self.generate_region_config()
        try:
            platform_config_service.get_config_by_key("REGION_SERVICE_API")
            platform_config_service.update_config("REGION_SERVICE_API", region_data)
        except ConsoleSysConfig.DoesNotExist:
            platform_config_service.add_config("REGION_SERVICE_API", region_data, 'json', "数据中心配置")

    def generate_region_config(self):
        # 查询已上线的数据中心配置
        region_config_list = []
        regions = RegionConfig.objects.filter(status='1')
        for region in regions:
            config_map = dict()
            config_map["region_name"] = region.region_name
            config_map["region_alias"] = region.region_alias
            config_map["url"] = region.url
            config_map["token"] = region.token
            config_map["enable"] = True
            region_config_list.append(config_map)
        data = json.dumps(region_config_list)
        return data

    @transaction.atomic
    def del_by_region_id(self, region_id):
        """
        Without deleting tenant_region, the relationship between region and tenant can be restored.

        raise RegionConfig.DoesNotExist
        """
        region = region_repo.del_by_region_id(region_id)
        self.update_region_config()
        return region.to_dict()

    def check_region_in_config(self, region_name):
        return None


class RegionExistException(Exception):
    def __init__(self, message, *args, **kwargs):
        self.message = message
        self.http_code = 400
        self.service_code = 10400


class RegionNotExistException(Exception):
    def __init__(self, message, *args, **kwargs):
        self.message = message
        self.http_code = 404
        self.service_code = 10404


region_services = RegionService()
