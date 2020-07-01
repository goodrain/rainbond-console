# -*- coding: utf-8 -*-
import json
import logging
import yaml
from django.core.paginator import Paginator
from django.db import transaction
from www.utils.crypt import make_uuid
from console.exception.main import ServiceHandleException
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
from console.services.enterprise_services import enterprise_services

logger = logging.getLogger("default")
region_api = RegionInvokeApi()
market_api = MarketOpenAPI()


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


class RegionService(object):
    def get_region_by_tenant_name(self, tenant_name):
        return region_repo.get_region_by_tenant_name(tenant_name=tenant_name)

    def get_region_by_region_id(self, region_id):
        return region_repo.get_region_by_region_id(region_id=region_id)

    def get_region_by_region_name(self, region_name):
        return region_repo.get_region_by_region_name(region_name=region_name)

    def get_enterprise_region_by_region_name(self, enterprise_id, region_name):
        return region_repo.get_enterprise_region_by_region_name(enterprise_id, region_name)

    def get_by_region_name(self, region_name):
        return region_repo.get_by_region_name(region_name)

    def get_region_all_list_by_team_name(self, team_name):
        regions = region_repo.get_region_by_tenant_name(tenant_name=team_name)
        region_name_list = list()
        if regions:
            for region in regions:
                region_desc = region_repo.get_region_desc_by_region_name(region_name=region.region_name)
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

    def get_team_unopen_region(self, team_name, enterprise_id):
        usable_regions = region_repo.get_usable_regions(enterprise_id)
        team_opened_regions = region_repo.get_team_opened_region(team_name).filter(is_init=True)
        opened_regions_name = [team_region.region_name for team_region in team_opened_regions]
        unopen_regions = usable_regions.exclude(region_name__in=opened_regions_name)
        return [unopen_region.to_dict() for unopen_region in unopen_regions]

    def get_open_regions(self, enterprise_id):
        usable_regions = region_repo.get_usable_regions(enterprise_id)
        return usable_regions

    def get_public_key(self, tenant, region):
        try:
            res, body = region_api.get_region_publickey(tenant.tenant_name, region, tenant.enterprise_id, tenant.tenant_id)
            if body and body["bean"]:
                return body["bean"]
            return {}
        except Exception as e:
            logger.exception(e)
            return {}

    def get_all_regions(self, query="", page=None, page_size=None):
        # 即将移除，仅用于OpenAPI V1
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

    def get_regions_with_resource(self, query="", page=None, page_size=None):
        # get all region list
        regions = region_repo.get_all_regions(query)
        total = regions.count()
        if page and page_size:
            paginator = Paginator(regions, page_size)
            regions = paginator.page(page)
        return self.conver_regions_info(regions, "yes"), total

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
            res, body = region_api.create_tenant(region_name, tenant.tenant_name, tenant.tenant_id, tenant.enterprise_id)
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
            logger.error("get_new_user_free_res_pkg error with params: {}".format((tenant_id, enterprise_id, region_name,
                                                                                   user_name)))
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

    def get_team_usable_regions(self, team_name, enterprise_id):
        usable_regions = region_repo.get_usable_regions(enterprise_id)
        region_names = [r.region_name for r in usable_regions]
        team_opened_regions = region_repo.get_team_opened_region(team_name).filter(is_init=True, region_name__in=region_names)
        return team_opened_regions

    def get_regions_by_enterprise_id(self, enterprise_id):
        return RegionConfig.objects.filter(enterprise_id=enterprise_id)

    def add_region(self, region_data):
        region = region_repo.get_region_by_region_name(region_data["region_name"])
        if region:
            raise ServiceHandleException(status_code=400, msg="", msg_show="集群ID{0}已存在".format(region_data["region_name"]))
        try:
            region_api.test_region_api(region_data)
        except ServiceHandleException:
            raise ServiceHandleException(status_code=400, msg="test link region field", msg_show="连接集群测试失败，请确认网络和集群状态")
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
        # TODO 修改 REGION_SERVICE_API 配置方式
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

    def parse_token(self, token, region_name, region_alias, region_type):
        try:
            info = yaml.load(token, Loader=yaml.BaseLoader)
        except Exception as e:
            logger.exception(e)
            raise ServiceHandleException("parse yaml error", "Region Config 内容不是有效YAML格式", 400, 400)
        if not isinstance(info, dict):
            raise ServiceHandleException("parse yaml error", "Region Config 内容不是有效YAML格式", 400, 400)
        if not info.get("ca.pem"):
            raise ServiceHandleException("ca.pem not found", "CA证书不存在", 400, 400)
        if not info.get("client.key.pem"):
            raise ServiceHandleException("client.key.pem not found", "客户端密钥不存在", 400, 400)
        if not info.get("client.pem"):
            raise ServiceHandleException("client.pem not found", "客户端证书不存在", 400, 400)
        if not info.get("apiAddress"):
            raise ServiceHandleException("apiAddress not found", "API地址不存在", 400, 400)
        if not info.get("websocketAddress"):
            raise ServiceHandleException("websocketAddress not found", "Websocket地址不存在", 400, 400)
        if not info.get("defaultDomainSuffix"):
            raise ServiceHandleException("defaultDomainSuffix not found", "HTTP默认域名后缀不存在", 400, 400)
        if not info.get("defaultTCPHost"):
            raise ServiceHandleException("defaultTCPHost not found", "TCP默认IP地址不存在", 400, 400)
        region_info = {
            "region_alias": region_alias,
            "region_name": region_name,
            "region_type": region_type,
            "ssl_ca_cert": info.get("ca.pem"),
            "key_file": info.get("client.key.pem"),
            "cert_file": info.get("client.pem"),
            "url": info.get("apiAddress"),
            "wsurl": info.get("websocketAddress"),
            "httpdomain": info.get("defaultDomainSuffix"),
            "tcpdomain": info.get("defaultTCPHost"),
            "region_id": make_uuid()
        }
        return region_info

    def __init_region_resource_data(self, region, level="open"):
        region_resource = {}
        region_resource["region_id"] = region.region_id
        region_resource["region_alias"] = region.region_alias
        region_resource["region_name"] = region.region_name
        region_resource["status"] = region.status
        region_resource["region_type"] = (json.loads(region.region_type) if region.region_type else [])
        region_resource["enterprise_id"] = region.enterprise_id
        region_resource["url"] = region.url
        region_resource["scope"] = region.scope
        if level == "open":
            region_resource["wsurl"] = region.wsurl
            region_resource["httpdomain"] = region.httpdomain
            region_resource["tcpdomain"] = region.tcpdomain
            region_resource["ssl_ca_cert"] = region.ssl_ca_cert
            region_resource["cert_file"] = region.cert_file
            region_resource["key_file"] = region.key_file
        region_resource["desc"] = region.desc
        region_resource["total_memory"] = 0
        region_resource["used_memory"] = 0
        region_resource["total_cpu"] = 0
        region_resource["used_cpu"] = 0
        region_resource["total_disk"] = 0
        region_resource["used_disk"] = 0
        region_resource["rbd_version"] = "unknown"
        region_resource["health_status"] = "ok"
        region_resource["enterprise_id"] = region.enterprise_id
        enterprise_info = enterprise_services.get_enterprise_by_enterprise_id(region.enterprise_id)
        if enterprise_info:
            region_resource["enterprise_alias"] = enterprise_info.enterprise_alias
        return region_resource

    def conver_regions_info(self, regions, check_status, level="open"):
        # 转换集群数据，若需要附加状态则从集群API获取
        region_info_list = []
        for region in regions:
            region_info_list.append(self.conver_region_info(region, check_status, level))
        return region_info_list

    def conver_region_info(self, region, check_status, level="open"):
        # 转换集群数据，若需要附加状态则从集群API获取
        region_resource = self.__init_region_resource_data(region, level)
        if check_status == "yes":
            try:
                _, rbd_version = region_api.get_enterprise_api_version_v2(
                    enterprise_id=region.enterprise_id, region=region.region_name)
                res, body = region_api.get_region_resources(region.enterprise_id, region=region.region_name)
                rbd_version = rbd_version["raw"].decode("utf-8")
                if res.get("status") == 200:
                    region_resource["total_memory"] = body["bean"]["cap_mem"]
                    region_resource["used_memory"] = body["bean"]["req_mem"]
                    region_resource["total_cpu"] = body["bean"]["cap_cpu"]
                    region_resource["used_cpu"] = body["bean"]["req_cpu"]
                    region_resource["total_disk"] = body["bean"]["cap_disk"] / 1024 / 1024 / 1024
                    region_resource["used_disk"] = body["bean"]["req_disk"] / 1024 / 1024 / 1024
                    region_resource["rbd_version"] = rbd_version
            except (region_api.CallApiError, ServiceHandleException) as e:
                logger.exception(e)
                region_resource["rbd_version"] = ""
                region_resource["health_status"] = "failure"
        return region_resource

    def get_enterprise_regions(self, enterprise_id, level="open", status="", check_status="yes"):
        regions = region_repo.get_regions_by_enterprise_id(enterprise_id, status)
        if not regions:
            return []
        return self.conver_regions_info(regions, check_status, level)

    def get_enterprise_region(self, enterprise_id, region_id, check_status=True):
        region = region_repo.get_region_by_id(enterprise_id, region_id)
        if not region:
            return None
        return self.conver_region_info(region, check_status)

    def update_enterprise_region(self, enterprise_id, region_id, data):
        return self.__init_region_resource_data(region_repo.update_enterprise_region(enterprise_id, region_id, data))

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


region_services = RegionService()
