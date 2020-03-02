# -*- coding: utf-8 -*-
import logging
import os
import random
import re
import string

from django.core.paginator import Paginator

from console.repositories.enterprise_repo import enterprise_repo
from console.services.service_services import base_service
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
        service_groups_nums = 0
        service_groups_running_nums = 0
        service_nums = 0
        service_running_nums = 0
        group_services = base_service.get_enterprise_group_services(enterprise_id)
        if group_services:
            service_groups_nums = len(group_services)
            running_service_ids = []
            for region in regions:
                data = region_api.get_enterprise_running_services(enterprise_id, region.region_name)
                if data:
                    region_service_ids = data.get("service_ids")
                    if region_service_ids:
                        running_service_ids.extend(region_service_ids)
            running_service_ids = set(running_service_ids)
            for group_service in group_services:
                service_ids = eval(group_service.service_ids)
                service_nums += len(service_ids)
                is_running = set(service_ids) & running_service_ids
                if is_running:
                    service_groups_running_nums += 1
                    service_running_nums += len(is_running)
        data = {
            "service_groups": {
                "total": service_groups_nums,
                "running": service_groups_running_nums,
                "closed": service_groups_nums - service_groups_running_nums
            },
            "components": {
                "total": service_nums,
                "running": service_running_nums,
                "closed": service_nums - service_running_nums
            }
        }
        return data


enterprise_services = EnterpriseServices()
