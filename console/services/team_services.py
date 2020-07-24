# -*- coding: utf-8 -*-
import datetime
import logging
import random
import string

from django.conf import settings
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q

from console.exception.exceptions import UserNotExistError
from console.exception.main import ServiceHandleException
from console.models.main import TenantUserRole
from console.repositories.enterprise_repo import enterprise_repo
from console.repositories.perm_repo import role_repo
from console.repositories.region_repo import region_repo
from console.repositories.team_repo import team_repo
from console.repositories.tenant_region_repo import tenant_region_repo
from console.repositories.user_repo import user_repo
from console.services.common_services import common_services
from console.services.enterprise_services import enterprise_services
from console.services.exception import (ErrAllTenantDeletionFailed, ErrStillHasServices, ErrTenantRegionNotFound)
from console.services.perm_services import user_kind_role_service
from console.services.region_services import region_services
from www.apiclient.regionapi import RegionInvokeApi
from www.apiclient.regionapibaseclient import RegionApiBaseHttpClient
from www.models.main import PermRelTenant, Tenants, TenantServiceInfo

logger = logging.getLogger("default")
region_api = RegionInvokeApi()


class TeamService(object):
    def get_tenant_by_tenant_name(self, tenant_name, exception=True):
        return team_repo.get_tenant_by_tenant_name(tenant_name=tenant_name, exception=exception)

    def get_tenant(self, tenant_name):
        if not Tenants.objects.filter(tenant_name=tenant_name).exists():
            raise Tenants.DoesNotExist
        return Tenants.objects.get(tenant_name=tenant_name)

    def get_enterprise_tenant_by_tenant_name(self, enterprise_id, tenant_name):
        return Tenants.objects.filter(tenant_name=tenant_name, enterprise_id=enterprise_id).first()

    def get_team_by_team_alias_and_eid(self, team_alias, enterprise_id):
        return Tenants.objects.filter(tenant_alias=team_alias, enterprise_id=enterprise_id).first()

    def get_team_by_team_id_and_eid(self, team_id, enterprise_id):
        return Tenants.objects.filter(tenant_id=team_id, enterprise_id=enterprise_id).first()

    def random_tenant_name(self, enterprise=None, length=8):
        """
        生成随机的云帮租户（云帮的团队名），副需要符合k8s的规范(小写字母,_)
        :param enterprise 企业信息
        :param length:
        :return:
        """
        tenant_name = ''.join(random.sample(string.ascii_lowercase + string.digits, length))
        while Tenants.objects.filter(tenant_name=tenant_name).count() > 0:
            tenant_name = ''.join(random.sample(string.ascii_lowercase + string.digits, length))
        return tenant_name

    def add_user_to_team(self, tenant, user_id, role_ids=None):
        user = user_repo.get_by_user_id(user_id)
        if not user:
            raise ServiceHandleException(msg="user not found", msg_show=u"用户不存在", status_code=404)
        exist_team_user = PermRelTenant.objects.filter(tenant_id=tenant.ID, user_id=user.user_id)
        enterprise = enterprise_services.get_enterprise_by_enterprise_id(enterprise_id=tenant.enterprise_id)
        if exist_team_user:
            raise ServiceHandleException(msg="user exist", msg_show=u"用户已经加入此团队")
        PermRelTenant.objects.create(tenant_id=tenant.ID, user_id=user.user_id, identity="", enterprise_id=enterprise.ID)
        if role_ids:
            user_kind_role_service.update_user_roles(kind="team", kind_id=tenant.tenant_id, user=user, role_ids=role_ids)

    def get_team_users(self, team):
        users = team_repo.get_tenant_users_by_tenant_ID(team.ID)
        return users

    def get_tenant_users_by_tenant_name(self, tenant_name):
        tenant = team_repo.get_tenant_by_tenant_name(tenant_name=tenant_name)
        user_list = team_repo.get_tenant_users_by_tenant_ID(tenant_ID=tenant.ID)
        return user_list

    def update_tenant_alias(self, tenant_name, new_team_alias):
        tenant = team_repo.get_tenant_by_tenant_name(tenant_name=tenant_name, exception=True)
        tenant.tenant_alias = new_team_alias
        tenant.save()
        return tenant

    def get_user_perms_in_permtenant(self, user_id, tenant_name):
        tenant = self.get_tenant_by_tenant_name(tenant_name=tenant_name)
        user_perms = team_repo.get_user_perms_in_permtenant(user_id=user_id, tenant_id=tenant.ID)
        return user_perms

    def get_not_join_users(
            self,
            enterprise,
            tenant,
            query,
    ):
        return team_repo.get_not_join_users(enterprise, tenant, query)

    def get_user_perms_in_permtenant_list(self, user_id, tenant_name):
        """
        一个用户在一个团队中的身份列表
        :return: 一个用户在一个团队中的身份列表
        """
        tenant = self.get_tenant_by_tenant_name(tenant_name=tenant_name)
        user_perms_list = team_repo.get_user_perms_in_permtenant_list(user_id=user_id, tenant_id=tenant.ID)
        return user_perms_list

    def get_user_perm_identitys_in_permtenant(self, user_id, tenant_name):
        """获取用户在一个团队的身份列表"""
        user = user_repo.get_by_user_id(user_id)
        try:
            tenant = self.get_tenant(tenant_name=tenant_name)
        except Tenants.DoesNotExist:
            tenant = self.get_team_by_team_id(tenant_name)
            if tenant is None:
                raise Tenants.DoesNotExist()
        user_roles = user_kind_role_service.get_user_roles(kind_id=tenant.ID, kind="team", user=user)
        if tenant.creater == user_id:
            user_roles["roles"].append("owner")
        return user_roles

    def get_user_perm_role_id_in_permtenant(self, user_id, tenant_name):
        """获取一个用户在一个团队的角色ID列表"""
        try:
            tenant = self.get_tenant(tenant_name=tenant_name)
        except Tenants.DoesNotExist:
            tenant = self.get_team_by_team_id(tenant_name)
            if tenant is None:
                raise Tenants.DoesNotExist()
        user_perms = team_repo.get_user_perms_in_permtenant(user_id=user_id, tenant_id=tenant.ID)
        if not user_perms:
            return []
        role_id_list = []
        for role_id in [perm.role_id for perm in user_perms]:
            if not role_id:
                continue
            role_id_list.append(role_id)
        return role_id_list

    def get_all_team_role_id(self, tenant_name, allow_owner=False):
        """获取一个团队中的所有可选角色ID列表"""
        try:
            team_obj = self.get_tenant(tenant_name=tenant_name)
        except Tenants.DoesNotExist:
            team_obj = self.get_team_by_team_id(tenant_name)
            if team_obj is None:
                raise Tenants.DoesNotExist()

        filter = Q(is_default=True)
        if not allow_owner:
            filter &= ~Q(role_name="owner")
        default_role_id_list = TenantUserRole.objects.filter(filter).values_list("pk", flat=True)
        team_role_id_list = TenantUserRole.objects.filter(tenant_id=team_obj.pk, is_default=False).values_list("pk", flat=True)
        return list(default_role_id_list) + list(team_role_id_list)

    # todo 废弃
    def change_tenant_role(self, user_id, tenant_name, role_id_list):
        """修改用户在团队中的角色"""
        try:
            tenant = self.get_tenant(tenant_name=tenant_name)
        except Tenants.DoesNotExist:
            tenant = self.get_team_by_team_id(tenant_name)
            if tenant is None:
                raise Tenants.DoesNotExist()
        enterprise = enterprise_services.get_enterprise_by_enterprise_id(enterprise_id=tenant.enterprise_id)
        user_role = role_repo.update_user_role_in_tenant_by_user_id_tenant_id_role_id(
            user_id=user_id, tenant_id=tenant.pk, enterprise_id=enterprise.pk, role_id_list=role_id_list)
        return user_role

    def add_user_role_to_team(self, tenant, user_ids, role_ids):
        """在团队中添加一个用户并给用户分配一个角色"""
        enterprise = enterprise_services.get_enterprise_by_enterprise_id(enterprise_id=tenant.enterprise_id)
        if enterprise:
            for user_id in user_ids:
                # for role_id in role_ids:
                PermRelTenant.objects.update_or_create(user_id=user_id, tenant_id=tenant.pk, enterprise_id=enterprise.pk)
                user = user_repo.get_by_user_id(user_id)
                user_kind_role_service.update_user_roles(kind="team", kind_id=tenant.tenant_id, user=user, role_ids=role_ids)

    def user_is_exist_in_team(self, user_list, tenant_name):
        """判断一个用户是否存在于一个团队中"""
        try:
            tenant = self.get_tenant(tenant_name=tenant_name)
        except Tenants.DoesNotExist:
            tenant = self.get_team_by_team_id(tenant_name)
            if tenant is None:
                raise Tenants.DoesNotExist()
        enterprise = enterprise_services.get_enterprise_by_enterprise_id(enterprise_id=tenant.enterprise_id)
        for user_id in user_list:
            obj = PermRelTenant.objects.filter(user_id=user_id, tenant_id=tenant.pk, enterprise_id=enterprise.pk)
            if obj:
                return obj[0].user_id
        return False

    def get_team_service_count_by_team_name(self, team_name):
        tenant = self.get_tenant_by_tenant_name(tenant_name=team_name)
        if tenant is None:
            raise Tenants.DoesNotExist()
        return TenantServiceInfo.objects.filter(tenant_id=tenant.tenant_id).count()

    def count_by_tenant_id(self, tenant_id):
        return TenantServiceInfo.objects.filter(tenant_id=tenant_id).count()

    def get_service_source(self, service_alias):
        service_source = TenantServiceInfo.objects.filter(service_alias=service_alias)
        if service_source:
            return service_source[0]
        else:
            return []

    def delete_tenant(self, tenant_name):
        team_repo.delete_tenant(tenant_name=tenant_name)

    @transaction.atomic()
    def delete_by_tenant_id(self, user, tenant, force=False):
        from openapi.services.app_service import app_service
        from console.services.plugin import plugin_service
        from console.services.group_service import group_service
        from console.services.service_services import base_service
        from console.services.app_actions import app_manage_service
        from console.repositories.app import service_repo
        msg_list = []
        tenant_regions = region_repo.list_by_tenant_id(tenant.tenant_id)
        if not force:
            service_count = self.count_by_tenant_id(tenant_id=tenant.tenant_id)
            if service_count >= 1:
                raise ErrStillHasServices
        success_count = 0
        for region in tenant_regions:
            if force:
                apps = group_service.get_apps_list(team_id=tenant.tenant_id, region_name=region["region_name"])
                plugins = plugin_service.get_tenant_plugins(region["region_name"], tenant)
                for app in apps:
                    service_ids = app_service.get_group_services_by_id(app.ID)
                    services = service_repo.get_services_by_service_ids(service_ids)
                    if services:
                        status_list = base_service.status_multi_service(
                            region=app.region_name,
                            tenant_name=tenant.tenant_name,
                            service_ids=service_ids,
                            enterprise_id=tenant.enterprise_id)
                        status_list = filter(lambda x: x not in ["closed", "undeploy"], map(lambda x: x["status"], status_list))
                        if len(status_list) > 0:
                            raise ServiceHandleException(
                                msg="There are running components under the current application", msg_show=u"当前团队下有运行态的组件，不可删除")
                        code_status = 200
                        for service in services:
                            code, msg = app_manage_service.batch_delete(user, tenant, service, is_force=True)
                            msg_dict = dict()
                            msg_dict['status'] = code
                            msg_dict['msg'] = msg
                            msg_dict['service_id'] = service.service_id
                            msg_dict['service_cname'] = service.service_cname
                            msg_list.append(msg_dict)
                            if code != 200:
                                code, msg = app_manage_service.delete_again(user, tenant, service, is_force=True)
                                if code != 200:
                                    code_status = code
                        if code_status != 200:
                            raise ServiceHandleException(msg=msg_list, msg_show=u"请求错误")
                        code, msg, data = group_service.delete_group_no_service(app.ID)
                        if code != 200:
                            raise ServiceHandleException(msg=msg, msg_show=u"请求错误")
                for plugin in plugins:
                    plugin_service.delete_plugin(region["region_name"], tenant, plugin.plugin_id)
            try:
                # There is no guarantee that the deletion of each tenant can be successful.
                region_api.delete_tenant(region["region_name"], region["tenant_name"])
                success_count += 1
            except Exception as e:
                logger.error("tenant id: {}; region name: {}; delete tenant: {}".format(tenant.tenant_id, region["tenant_name"],
                                                                                        e))
        if success_count == 0:
            raise ErrAllTenantDeletionFailed
        team_repo.delete_by_tenant_id(tenant_id=tenant.tenant_id)

    def get_current_user_tenants(self, user_id):
        tenants = team_repo.get_tenants_by_user_id(user_id=user_id)
        return tenants

    def get_active_user_tenants(self, user_id):
        return team_repo.get_active_tenants_by_user_id(user_id=user_id)

    @transaction.atomic
    def exit_current_team(self, team_name, user_id):
        s_id = transaction.savepoint()
        try:
            tenant = self.get_tenant_by_tenant_name(tenant_name=team_name)
            team_repo.get_user_perms_in_permtenant(user_id=user_id, tenant_id=tenant.ID).delete()
            user = user_repo.get_by_user_id(user_id)
            user_kind_role_service.delete_user_roles(kind="team", kind_id=tenant.tenant_id, user=user)
            transaction.savepoint_commit(s_id)
            return 200, u"退出团队成功"
        except Exception as e:
            logger.exception(e)
            transaction.savepoint_rollback(s_id)
            return 400, u"退出团队失败"

    def get_team_by_team_id(self, team_id):
        team = team_repo.get_team_by_team_id(team_id=team_id)
        if team:
            user = user_repo.get_by_user_id(team.creater)
            team.creater_name = user.get_name()
        return team

    def create_team(self, user, enterprise, region_list=None, team_alias=None):
        team_name = self.random_tenant_name(enterprise=user.enterprise_id, length=8)
        is_public = settings.MODULES.get('SSO_LOGIN')
        if not is_public:
            pay_type = 'payed'
            pay_level = 'company'
        else:
            pay_type = 'free'
            pay_level = 'company'
        expired_day = 7
        if hasattr(settings, "TENANT_VALID_TIME"):
            expired_day = int(settings.TENANT_VALID_TIME)
        expire_time = datetime.datetime.now() + datetime.timedelta(days=expired_day)
        if not region_list:
            region_list = [r.region_name for r in region_repo.get_usable_regions(enterprise.enterprise_id)]
            if not region_list:
                return 404, "无可用数据中心", None
        default_region = region_list[0]
        if not team_alias:
            team_alias = "{0}的团队".format(user.nick_name)
        params = {
            "tenant_name": team_name,
            "pay_type": pay_type,
            "pay_level": pay_level,
            "creater": user.user_id,
            "region": default_region,
            "expired_time": expire_time,
            "tenant_alias": team_alias,
            "enterprise_id": enterprise.enterprise_id,
            "limit_memory": 0,
        }
        team = team_repo.create_tenant(**params)
        create_perm_param = {
            "user_id": user.user_id,
            "tenant_id": team.ID,
            "identity": "owner",
            "enterprise_id": enterprise.ID,
        }
        team_repo.create_team_perms(**create_perm_param)
        return 200, "success", team

    def delete_team_region(self, team_id, region_name):
        # check team
        tenant = team_repo.get_team_by_team_id(team_id)
        # check region
        region_services.get_by_region_name(region_name)

        tenant_region = region_repo.get_team_region_by_tenant_and_region(team_id, region_name)
        if not tenant_region:
            raise ErrTenantRegionNotFound()

        region_api.delete_tenant(region_name, tenant.tenant_name)

        tenant_region.delete()

    def get_enterprise_teams(self, enterprise_id, query=None, page=None, page_size=None, user=None):
        tall = team_repo.get_teams_by_enterprise_id(enterprise_id, query=query)
        total = tall.count()
        if page is not None and page_size is not None:
            paginator = Paginator(tall, page_size)
            raw_tenants = paginator.page(page)
        else:
            raw_tenants = tall
        tenants = []
        for tenant in raw_tenants:
            tenants.append(self.__team_with_region_info(tenant, user))
        return tenants, total

    def list_teams_v2(self, eid, query=None, page=None, page_size=None):
        if query:
            total = Tenants.objects.filter(tenant_alias__contains=query).count()
        else:
            total = Tenants.objects.count()
        tenants = team_repo.list_teams_v2(query, page, page_size)
        for tenant in tenants:
            region_num = tenant_region_repo.count_by_tenant_id(tenant["tenant_id"])
            tenant["region_num"] = region_num
        return tenants, total

    def list_by_tenant_names(self, tenant_names):
        query_set = Tenants.objects.filter(tenant_name__in=tenant_names)
        return [qs.to_dict() for qs in query_set]

    def list_teams_by_user_id(self, eid, user_id, query=None, page=None, page_size=None):
        tenants = team_repo.list_by_user_id(eid, user_id, query, page, page_size)
        total = team_repo.count_by_user_id(eid, user_id, query)
        user = user_repo.get_by_user_id(user_id)
        for tenant in tenants:
            roles = user_kind_role_service.get_user_roles(kind="team", kind_id=tenant["tenant_id"], user=user)
            tenant["role_infos"] = roles["roles"]
        return tenants, total

    def __team_with_region_info(self, tenant, request_user=None):
        try:
            user = user_repo.get_user_by_user_id(tenant.creater)
            owner_name = user.get_name()
        except UserNotExistError:
            owner_name = None
        if request_user:
            user_role_list = user_kind_role_service.get_user_roles(kind="team", kind_id=tenant.tenant_id, user=request_user)
            roles = map(lambda x: x["role_name"], user_role_list["roles"])
            if tenant.creater == request_user.user_id:
                roles.append("owner")
        region_info_map = []
        region_list = team_repo.get_team_regions(tenant.tenant_id)
        if region_list:
            region_name_list = region_list.values_list("region_name", flat=True)
            region_infos = region_repo.get_region_by_region_names(region_name_list)
            if region_infos:
                for region in region_infos:
                    region_info_map.append({"region_name": region.region_name, "region_alias": region.region_alias})
        info = {
            "team_name": tenant.tenant_name,
            "team_alias": tenant.tenant_alias,
            "team_id": tenant.tenant_id,
            "create_time": tenant.create_time,
            "region": tenant.region,
            "region_list": region_info_map,
            "enterprise_id": tenant.enterprise_id,
            "owner": tenant.creater,
            "owner_name": owner_name,
        }
        if request_user:
            info["roles"] = roles
        return info

    def get_teams_region_by_user_id(self, enterprise_id, user, name=None):
        teams_list = list()
        tenants = enterprise_repo.get_enterprise_user_teams(enterprise_id, user.user_id, name)
        if tenants:
            for tenant in tenants:
                teams_list.append(self.__team_with_region_info(tenant, user))
        return teams_list

    def check_and_get_user_team_by_name_and_region(self, user_id, tenant_name, region_name):
        tenant = team_repo.get_user_tenant_by_name(user_id, tenant_name)
        if not tenant:
            return tenant
        if not team_repo.get_team_region_by_name(tenant.tenant_id, region_name):
            return None
        else:
            return tenant

    def get_team_by_team_alias(self, team_alias):
        return team_repo.get_team_by_team_alias(team_alias)

    def get_fuzzy_tenants_by_tenant_alias_and_enterprise_id(self, enterprise_id, tenant_alias):
        return team_repo.get_fuzzy_tenants_by_tenant_alias_and_enterprise_id(enterprise_id, tenant_alias)

    def update_by_tenant_id(self, tenant_id, data):
        d = {}
        if data.get("enterprise", ""):
            d["enterprise_id"] = data.get("enterprise_id")
        if data.get("region", ""):
            d["region"] = data.get("region")
        if data.get("is_active", None):
            d["is_active"] = data.get("is_active")
        if data.get("creater", 0):
            d["creater"] = data.get("creater")
        if data.get("tenant_alias", ""):
            d["tenant_alias"] = data.get("tenant_alias")
        team_repo.update_by_tenant_id(tenant_id).update(**d)

    def get_tenant_resource(self, team, region_name):
        if team:
            data = {
                "team_id": team.tenant_id,
                "team_name": team.tenant_name,
                "team_alias": team.tenant_alias,
            }
            source = common_services.get_current_region_used_resource(team, region_name)
            if source:
                cpu_usage = 0
                memory_usage = 0
                if int(source["limit_cpu"]) != 0:
                    cpu_usage = float(int(source["cpu"])) / float(int(source["limit_cpu"])) * 100
                if int(source["limit_memory"]) != 0:
                    memory_usage = float(int(source["memory"])) / float(int(source["limit_memory"])) * 100
                data.update({
                    "used_cpu": int(source["cpu"]),
                    "used_memory": int(source["memory"]),
                    "total_cpu": int(source["limit_cpu"]),
                    "total_memory": int(source["limit_memory"]),
                    "used_cpu_percentage": round(cpu_usage, 2),
                    "used_memory_percentage": round(memory_usage, 2),
                })
            return data
        return None

    def get_tenant_list_by_region(self, eid, region_id, page=1, page_size=10):
        teams = team_repo.get_team_by_enterprise_id(eid)
        team_maps = {}
        if teams:
            for team in teams:
                team_maps[team.tenant_id] = team
        res, body = region_api.list_tenants(eid, region_id, page, page_size)
        tenant_list = []
        total = 0
        if body.get("bean"):
            tenants = body.get("bean").get("list")
            total = body.get("bean").get("total")
            if tenants:
                for tenant in tenants:
                    tenant_alias = team_maps.get(tenant["UUID"]).tenant_alias if team_maps.get(tenant["UUID"]) else ''
                    tenant_list.append({
                        "tenant_id": tenant["UUID"],
                        "team_name": tenant_alias,
                        "tenant_name": tenant["Name"],
                        "memory_request": tenant["memory_request"],
                        "cpu_request": tenant["cpu_request"],
                        "memory_limit": tenant["memory_limit"],
                        "cpu_limit": tenant["cpu_limit"],
                        "running_app_num": tenant["running_app_num"],
                        "running_app_internal_num": tenant["running_app_internal_num"],
                        "running_app_third_num": tenant["running_app_third_num"],
                        "set_limit_memory": tenant["LimitMemory"],
                    })
        else:
            logger.error(body)
        return tenant_list, total

    def set_tenant_memory_limit(self, eid, region_id, tenant_name, limit):
        try:
            region_api.set_tenant_limit_memory(eid, tenant_name, region_id, body=limit)
        except RegionApiBaseHttpClient.CallApiError as e:
            logger.exception(e)
            raise ServiceHandleException(status_code=500, msg="", msg_show=u"设置租户限额失败")


team_services = TeamService()
