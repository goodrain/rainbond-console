# -*- coding: utf-8 -*-
import logging
import os
import random
import re
import string
import yaml
import json

from django.core.paginator import Paginator
from console.exception.main import ServiceHandleException
from console.repositories.group import group_repo
from console.repositories.group import group_service_relation_repo
from console.repositories.enterprise_repo import enterprise_repo
from console.repositories.region_repo import region_repo
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import TenantEnterprise
from www.models.main import TenantEnterpriseToken
from www.models.main import Tenants
from www.utils.crypt import make_uuid

logger = logging.getLogger('default')

region_api = RegionInvokeApi()
notify_mail_list = ['21395930@qq.com', 'zhanghy@goodrain.com']


class EnterpriseServices(object):
    """
    企业组件接口，提供以企业为中心的操作集合，企业在云帮体系中为最大业务隔离单元，企业下有团队（也就是tenant）
    """

    def list_all(self, query="", page=None, page_size=None):
        ents = enterprise_repo.list_all(query)
        total = ents.count()
        if total == 0:
            return [], 0

        paginator = Paginator(ents, page_size)
        pp = paginator.page(page)
        data = []
        for ent in pp:
            data.append({
                "enterprise_id": ent.enterprise_id,
                "enterprise_name": ent.enterprise_name,
                "enterprise_alias": ent.enterprise_alias,
                "create_time": ent.create_time,
                "is_active": ent.is_active,
            })
        return data, total

    def update(self, eid, data):
        d = {}
        if data.get("alias", "") != "":
            d["enterprise_alias"] = data["alias"]
        if data.get("name", "") != "":
            d["enterprise_name"] = data["name"]
        enterprise_repo.update(eid, **data)

    def random_tenant_name(self, enterprise=None, length=8):
        """
        生成随机的云帮租户（云帮的团队名），副需要符合k8s的规范(小写字母,_)
        :param enterprise 企业信息
        :param length:
        :return:
        """

        # todo 可以根据enterprise的信息来生成租户名
        tenant_name = ''.join(random.sample(string.ascii_lowercase + string.digits, length))
        while Tenants.objects.filter(tenant_name=tenant_name).count() > 0:
            tenant_name = ''.join(random.sample(string.ascii_lowercase + string.digits, length))
        return tenant_name

    def random_enterprise_name(self, length=8):
        """
        生成随机的云帮企业名，副需要符合k8s的规范(小写字母,_)
        :param length:
        :return:
        """

        enter_name = ''.join(random.sample(string.ascii_lowercase + string.digits, length))
        while TenantEnterprise.objects.filter(enterprise_name=enter_name).count() > 0:
            enter_name = ''.join(random.sample(string.ascii_lowercase + string.digits, length))
        return enter_name

    def create_enterprise(self, enterprise_name='', enterprise_alias=''):
        """
        创建一个本地的企业信息, 并生成本地的企业ID

        :param enterprise_name: 企业的英文名, 如果没有则自动生成一个, 如果存在则需要保证传递的名字在数据库中唯一
        :param enterprise_alias: 企业的别名, 可以中文, 用于展示用, 如果为空则自动生成一个
        :return:
        """
        enterprise = TenantEnterprise()

        # 处理企业英文名
        if enterprise_name:
            enterprise_name_regx = re.compile(r'^[a-z0-9-]*$')
            if enterprise_name and not enterprise_name_regx.match(enterprise_name):
                logger.error('bad enterprise_name: {}'.format(enterprise_name))
                raise Exception('enterprise_name  must consist of lower case alphanumeric characters or -')

            if TenantEnterprise.objects.filter(enterprise_name=enterprise_name).count() > 0:
                raise Exception('enterprise_name [{}] already existed!'.format(enterprise_name))
            else:
                enter_name = enterprise_name
        else:
            enter_name = self.random_enterprise_name()
        enterprise.enterprise_name = enter_name

        # 根据企业英文名确认UUID
        enterprise.enterprise_id = os.environ.get('ENTERPRISE_ID', make_uuid(enter_name))

        # 处理企业别名
        if not enterprise_alias:
            enterprise.enterprise_alias = '企业{0}'.format(enter_name)
        else:
            enterprise.enterprise_alias = enterprise_alias

        enterprise.save()
        return enterprise

    def create_oauth_enterprise(self, enterprise_name, enterprise_alias, enterprise_id):
        """
        创建一个本地的企业信息, 并生成本地的企业ID

        :param enterprise_name: 企业的domain, 如果没有则自动生成一个, 如果存在则需要保证传递的名字在数据库中唯一
        :param enterprise_alias: 企业的名称, 可以中文, 用于展示用, 如果为空则自动生成一个
        :param enterprise_id: 企业的id
        :return:
        """
        enterprise = TenantEnterprise()
        enterprise.enterprise_name = enterprise_name
        enterprise.enterprise_id = enterprise_id
        enterprise.enterprise_alias = enterprise_alias
        enterprise.save()
        return enterprise

    def get_enterprise_by_id(self, enterprise_id):
        try:
            return TenantEnterprise.objects.get(enterprise_id=enterprise_id)
        except TenantEnterprise.DoesNotExist:
            return None

    def active(self, enterprise, enterprise_token):
        """
        绑定企业与云市的访问的api token
        :param enterprise:
        :param enterprise_token:
        :return:
        """
        enterprise.enterprise_token = enterprise_token
        enterprise.is_active = 1
        enterprise.save()
        return True

    def get_enterprise_by_enterprise_name(self, enterprise_name, exception=True):
        """
        通过企业名查找企业
        :param enterprise_name: 企业名
        :param exception: 控制如果企业不存在抛异常与否
        :return: 返回 None 或者企业
        """
        return enterprise_repo.get_enterprise_by_enterprise_name(enterprise_name=enterprise_name, exception=exception)

    def get_enterprise_first(self):
        return enterprise_repo.get_enterprise_first()

    def get_enterprise_by_enterprise_id(self, enterprise_id, exception=True):
        return enterprise_repo.get_enterprise_by_enterprise_id(enterprise_id=enterprise_id, exception=exception)

    def create_tenant_enterprise(self, enterprise_id, enterprise_name, enterprise_alias, is_active=True):
        params = {
            "enterprise_id": enterprise_id,
            "enterprise_name": enterprise_name,
            "enterprise_alias": enterprise_alias,
            "is_active": is_active,
        }
        return enterprise_repo.create_enterprise(**params)

    def get_enterprise_by_eids(self, eid_list):
        return enterprise_repo.get_enterprises_by_enterprise_ids(eid_list)

    def get_enterprise_by_enterprise_alias(self, enterprise_alias):
        return enterprise_repo.get_by_enterprise_alias(enterprise_alias)

    def list_appstore_infos(self, query="", page=None, page_size=None):
        infos = enterprise_repo.list_appstore_infos(query, page, page_size)
        for info in infos:
            appstore_name = ""
            if "api.goodrain.com" in info["access_url"]:
                appstore_name = "好雨科技公有应用市场(默认)"
            info["appstore_name"] = appstore_name
        total = enterprise_repo.count_appstore_infos(query)
        return infos, total

    def update_appstore_info(self, eid, data):
        ent = enterprise_repo.get_enterprise_by_enterprise_id(eid)
        # raise TenantEnterpriseToken.DoesNotExist
        tet = TenantEnterpriseToken.objects.get(enterprise_id=ent.ID)
        access_url = data["access_url"]
        tet.access_url = access_url
        tet.access_id = ""
        tet.access_token = ""
        tet.save()
        setattr(ent, "access_url", access_url)
        appstore_name = ""
        if "api.goodrain.com" in tet.access_url:
            appstore_name = "好雨科技公有应用市场(默认)"
        setattr(ent, "appstore_name", appstore_name)
        return ent

    # def get_services_status_by_service_ids(self, region_name, enterprise_id, service_ids):
    def get_enterprise_runing_service(self, enterprise_id, regions):
        app_total_num = 0
        app_running_num = 0
        component_total_num = 0
        component_running_num = 0

        # 1. get all teams
        teams = enterprise_repo.get_enterprise_teams(enterprise_id)
        if not teams:
            return {
                "service_groups": {"total": 0, "running": 0, "closed": 0},
                "components": {"total": 0, "running": 0, "closed": 0}
            }
        # 2. get all apps in all teams
        team_ids = [team.tenant_id for team in teams]
        apps = group_repo.get_apps_in_multi_team(team_ids)
        app_total_num = len(apps)

        app_ids = [app.ID for app in apps]
        app_relations = group_service_relation_repo.get_service_group_relation_by_groups(app_ids)
        component_total_num = len(app_relations)

        # 3. get all running component
        # attention, component maybe belong to any other enterprise
        running_component_ids = []
        for region in regions:
            data = None
            try:
                data = region_api.get_enterprise_running_services(enterprise_id, region.region_name)
            except (region_api.CallApiError, ServiceHandleException) as e:
                logger.exception("get region:'{0}' running failed: {1}".format(region.region_name, e))
            if data and data.get("service_ids"):
                running_component_ids.extend(data.get("service_ids"))

        # 4 get all running app
        component_and_app = dict()
        for relation in app_relations:
            component_and_app[relation.service_id] = relation.group_id

        running_apps = []
        for running_component in running_component_ids:
            # if this running component belong to this enterprise
            app = component_and_app.get(running_component)
            if app:
                component_running_num += 1
                if app not in running_apps:
                    running_apps.append(app)
        app_running_num = len(running_apps)
        data = {
            "service_groups": {
                "total": app_total_num,
                "running": app_running_num,
                "closed": app_total_num - app_running_num
            },
            "components": {
                "total": component_total_num,
                "running": component_running_num,
                "closed": component_total_num - component_running_num
            }
        }
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
        return region_resource

    def get_enterprise_regions(self, enterprise_id, level="open", status="", check_status="yes"):
        regions = region_repo.get_regions_by_enterprise_id(enterprise_id, status)
        region_info_list = []
        if not regions:
            return []
        for region in regions:
            region_resource = self.__init_region_resource_data(region, level)
            if check_status == "yes":
                try:
                    res, rbd_version = region_api.get_enterprise_api_version_v2(enterprise_id, region=region.region_name)
                    res, body = region_api.get_region_resources(enterprise_id, region=region.region_name)
                    rbd_version = rbd_version["raw"].decode("utf-8")
                    if res.get("status") == 200:
                        logger.debug(body["bean"]["cap_mem"])
                        region_resource["total_memory"] = body["bean"]["cap_mem"]
                        region_resource["used_memory"] = body["bean"]["req_mem"]
                        region_resource["total_cpu"] = body["bean"]["cap_cpu"]
                        region_resource["used_cpu"] = body["bean"]["req_cpu"]
                        region_resource["total_disk"] = body["bean"]["cap_disk"]
                        region_resource["used_disk"] = body["bean"]["req_disk"]
                        region_resource["rbd_version"] = rbd_version
                except (region_api.CallApiError, ServiceHandleException) as e:
                    logger.exception(e)
                    region_resource["rbd_version"] = ""
                    region_resource["health_status"] = "failure"
            region_info_list.append(region_resource)
        return region_info_list

    def get_enterprise_region(self, enterprise_id, region_id, link_api=True):
        region = region_repo.get_region_by_id(enterprise_id, region_id)
        if not region:
            return None
        region_resource = self.__init_region_resource_data(region)
        if link_api:
            try:
                res, body = region_api.get_region_resources(enterprise_id, region=region.region_name)
                res, rbd_version = region_api.get_enterprise_api_version_v2(enterprise_id, region=region.region_name)
                rbd_version = rbd_version["raw"].decode("utf-8")
                if res.get("status") == 200:
                    region_resource["total_memory"] = body["bean"]["cap_mem"],
                    region_resource["used_memory"] = body["bean"]["req_mem"],
                    region_resource["total_cpu"] = body["bean"]["cap_cpu"],
                    region_resource["used_cpu"] = body["bean"]["req_cpu"],
                    region_resource["total_disk"] = body["bean"]["cap_disk"],
                    region_resource["used_disk"] = body["bean"]["req_disk"],
                    region_resource["rbd_version"] = rbd_version,
            except (region_api.CallApiError, ServiceHandleException) as e:
                logger.exception(e)
                region_resource["rbd_version"] = ""
                region_resource["health_status"] = "failure"
        return region_resource

    def update_enterprise_region(self, enterprise_id, region_id, data):
        return self.__init_region_resource_data(region_repo.update_enterprise_region(enterprise_id, region_id, data))


enterprise_services = EnterpriseServices()
