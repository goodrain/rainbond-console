# -*- coding: utf-8 -*-
import base64
import json
import logging
import os
import random
import string
from urllib.parse import urlparse

import requests

from console.exception.exceptions import UserNotExistError
from console.exception.main import ServiceHandleException
from console.models.main import TenantUserRole, RegionConfig
from console.repositories.app import TenantServiceInfoRepository
from console.repositories.app_config import volume_repo
from console.repositories.enterprise_repo import enterprise_repo
from console.repositories.perm_repo import role_repo
from console.repositories.region_repo import region_repo
from console.repositories.team_repo import team_repo, team_registry_auth_repo
from console.repositories.tenant_region_repo import tenant_region_repo
from console.repositories.user_repo import user_repo
from console.repositories.service_repo import service_repo
from console.repositories.group import group_repo
from console.services.common_services import common_services
from console.services.enterprise_services import enterprise_services
from console.services.exception import ErrTenantRegionNotFound
from console.services.perm_services import (role_kind_services, user_kind_role_service)
from console.services.region_services import region_services
from django.core.paginator import Paginator, EmptyPage
from django.db import transaction
from django.db.models import Q

from console.services.storage_service import storage_service
from www.apiclient.regionapi import RegionInvokeApi
from www.apiclient.regionapibaseclient import RegionApiBaseHttpClient
from www.models.main import PermRelTenant, Tenants, TenantServiceInfo, TenantRegionInfo, ServiceGroup, RegionApp, ServiceGroupRelation
from www.utils.crypt import make_uuid

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
        if enterprise_id:
            return Tenants.objects.filter(tenant_id=team_id, enterprise_id=enterprise_id).first()
        return Tenants.objects.filter(tenant_id=team_id).first()

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
            raise ServiceHandleException(msg="user not found", msg_show="用户不存在", status_code=404)
        exist_team_user = PermRelTenant.objects.filter(tenant_id=tenant.ID, user_id=user.user_id)
        enterprise = enterprise_services.get_enterprise_by_enterprise_id(enterprise_id=tenant.enterprise_id)
        if exist_team_user:
            raise ServiceHandleException(msg="user exist", msg_show="用户已经加入此团队")
        PermRelTenant.objects.create(tenant_id=tenant.ID, user_id=user.user_id, identity="", enterprise_id=enterprise.ID)
        if role_ids:
            user_kind_role_service.update_user_roles(kind="team", kind_id=tenant.tenant_id, user=user, role_ids=role_ids)

    def get_team_users(self, team, name=None):
        users = team_repo.get_tenant_users_by_tenant_ID(team.ID)
        if users and name:
            users = users.filter(Q(nick_name__contains=name) | Q(real_name__contains=name))
        return users

    def get_tenant_users_by_tenant_name(self, tenant_name):
        tenant = team_repo.get_tenant_by_tenant_name(tenant_name=tenant_name)
        user_list = team_repo.get_tenant_users_by_tenant_ID(tenant_ID=tenant.ID)
        return user_list

    def update_tenant_info(self, tenant_name, new_team_alias, new_logo):
        tenant = team_repo.get_tenant_by_tenant_name(tenant_name=tenant_name, exception=True)
        tenant.tenant_alias = new_team_alias
        if new_logo:
            tenant.logo = new_logo
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
    def delete_by_tenant_id(self, user, tenant):
        tenant_regions = region_repo.get_tenant_regions_by_teamid(tenant.tenant_id)
        region_list = list()
        for region in tenant_regions:
            try:
                region_config = region_services.delete_tenant_on_region(tenant.enterprise_id, tenant.tenant_name, region.region_name, user)
                region_list.append(region_config.region_alias)
            except ServiceHandleException as e:
                raise e
            except Exception as e:
                logger.exception(e)
                raise ServiceHandleException(
                    msg_show="{}集群自动卸载失败，请手动卸载后重新删除团队".format(region.region_name), msg="delete tenant failure")
        sid = None
        try:
            sid = transaction.savepoint()
            team_repo.delete_by_tenant_id(tenant_id=tenant.tenant_id)
            transaction.savepoint_commit(sid)
        except Exception as e:
            if sid:
                transaction.savepoint_rollback(sid)
            logger.exception(e)
        return region_list


    def get_current_user_tenants(self, user_id, team_name=""):
        tenants = team_repo.get_tenants_by_user_id(user_id=user_id, team_name=team_name)
        return tenants

    @transaction.atomic
    def exit_current_team(self, team_name, user_id):
        s_id = transaction.savepoint()
        try:
            tenant = self.get_tenant_by_tenant_name(tenant_name=team_name)
            team_repo.get_user_perms_in_permtenant(user_id=user_id, tenant_id=tenant.ID).delete()
            user = user_repo.get_by_user_id(user_id)
            user_kind_role_service.delete_user_roles(kind="team", kind_id=tenant.tenant_id, user=user)
            transaction.savepoint_commit(s_id)
            return 200, "退出团队成功"
        except Exception as e:
            logger.exception(e)
            transaction.savepoint_rollback(s_id)
            return 400, "退出团队失败"

    def get_team_by_team_id(self, team_id):
        team = team_repo.get_team_by_team_id(team_id=team_id)
        if team:
            user = user_repo.get_by_user_id(team.creater)
            team.creater_name = "admin"
            if user:
                team.creater_name = user.get_name()
        return team

    @transaction.atomic
    def create_team(self, user, enterprise, region_list=None, team_alias=None, namespace="", logo=""):
        if not team_alias and namespace == "default":
            team_name = "default"
        else:
            team_name = self.random_tenant_name(enterprise=user.enterprise_id, length=8)
        if not team_alias:
            team_alias = "{0} workspace".format(user.nick_name)
        params = {
            "tenant_name": team_name,
            "creater": user.user_id,
            "tenant_alias": team_alias,
            "enterprise_id": enterprise.enterprise_id,
            "limit_memory": 0,
            "namespace": namespace,
            "logo": logo,
        }
        team = team_repo.create_tenant(**params)
        create_perm_param = {
            "user_id": user.user_id,
            "tenant_id": team.ID,
            "identity": "owner",
            "enterprise_id": enterprise.ID,
        }
        team_repo.create_team_perms(**create_perm_param)
        # init default roles
        role_kind_services.init_default_roles(kind="team", kind_id=team.tenant_id)
        admin_role = role_kind_services.get_role_by_name(kind="team", kind_id=team.tenant_id, name="管理员")
        user_kind_role_service.update_user_roles(kind="team", kind_id=team.tenant_id, user=user, role_ids=[admin_role.ID])
        return team

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

    def get_enterprise_teams_fenye(self, enterprise_id, query=None, page=None, page_size=None):
        tall = team_repo.get_teams_by_enterprise_id(enterprise_id, query=query)
        total = tall.count()
        if page is not None and page_size is not None:
            try:
                start = (page - 1) * page_size
                end = page * page_size
                raw_tenants = tall[start:end]
            except EmptyPage:
                raw_tenants = []
        else:
            raw_tenants = tall
        return raw_tenants, total

    def jg_teams(self, eid, teams):
        tenants = dict()
        creaters = [team.creater for team in teams]
        users = user_repo.get_by_user_ids(creaters)
        user_list = {user.user_id: user.get_name() for user in users}
        tenant_ids = [team.tenant_id for team in teams]
        region_dict = dict()
        tenant_IDs = {ten.ID: ten.tenant_id for ten in teams}
        user_id_list = PermRelTenant.objects.filter().values("tenant_id", "user_id")
        user_id_dict = dict()
        for user_id in user_id_list:
            user_id_dict[tenant_IDs.get(user_id["tenant_id"])] = user_id_dict.get(tenant_IDs.get(user_id["tenant_id"]), 0) + 1
        
        # Pre-calculate storage usage for all teams
        storage_dict = {}
        if not os.getenv("USE_SAAS"):
            # Get all components for all teams
            all_components = TenantServiceInfo.objects.filter()
            service_ids = [comp.service_id for comp in all_components]
            
            # Get all volumes for these components
            all_volumes = volume_repo.get_services_volumes(service_ids)
            
            # Calculate storage for each team
            team_components = {}
            for comp in all_components:
                if comp.tenant_id not in team_components:
                    team_components[comp.tenant_id] = []
                team_components[comp.tenant_id].append(comp.service_id)
            
            for team_id in team_components:
                use_disk = 0
                team_service_ids = team_components[team_id]
                for volume in all_volumes:
                    if volume.service_id in team_service_ids and volume.volume_type != "config-file":
                        volume.volume_capacity = 10 if volume.volume_capacity == 0 else volume.volume_capacity
                        use_disk += volume.volume_capacity
                storage_dict[team_id] = use_disk

        for team in teams:
            region_info_map = []
            region_name_list = team_repo.get_team_region_names(team.tenant_id)
            if region_name_list:
                region_infos = region_repo.get_region_by_region_names(region_name_list)
                if region_infos:
                    for region in region_infos:
                        region_dict[region.region_name] = 1
                        region_info_map.append({"region_name": region.region_name, "region_alias": region.region_alias, "region_id": region.region_id})
            tenant = team.to_dict()
            # 获取团队的集群信息
            tenant["region"] = region_info_map[0]["region_name"] if len(region_info_map) > 0 else ""
            tenant["region_list"] = region_info_map
            tenant["team_alias"] = team.tenant_alias
            tenant["team_name"] = team.tenant_name
            tenant["user_number"] = user_id_dict.get(team.tenant_id, 0)
            tenant["namespace"] = team.namespace
            tenant["owner_name"] = user_list.get(team.creater)
            tenant["set_limit_memory"] = 0
            tenant["set_limit_cpu"] = 0
            tenant["set_limit_storage"] = 0
            tenant["running_apps"] = 0
            tenant["memory_request"] = 0
            tenant["cpu_request"] = 0
            if os.getenv("USE_SAAS"):
                storage_request = storage_service.get_tenant_storage_usage(team.tenant_id)
                tenant["storage_request"] = "{}{}".format(storage_request.get("value", 0), storage_request.get("unit", "B"))
            else:
                tenant["storage_request"] = storage_dict.get(team.tenant_id, 0)
            tenants[team.tenant_id] = tenant
        if region_dict:
            region_tenants = list()
            for region_id in region_dict.keys():
                region_tenants += self.get_region_tenant(eid, region_id, tenant_ids)
            for region_tenant in region_tenants:
                tenant_id = region_tenant.get("UUID")
                running_apps = tenants.get(tenant_id).get("running_apps")
                tenants.get(tenant_id)["set_limit_memory"] = region_tenant.get("LimitMemory", 0)
                tenants.get(tenant_id)["set_limit_cpu"] = region_tenant.get("LimitCPU", 0)
                tenants.get(tenant_id)["set_limit_storage"] = region_tenant.get("LimitStorage", 0)
                tenants.get(tenant_id)["running_apps"] = running_apps + region_tenant.get("running_applications", 0)
                tenants.get(tenant_id)["memory_request"] = region_tenant.get("memory_limit", 0)
                tenants.get(tenant_id)["cpu_request"] = region_tenant.get("cpu_limit", 0)
        return tenants.values()

    def get_region_tenant(self, eid, region_id, tenant_ids):
        res, body = region_api.list_tenants(eid, region_id, json.dumps(tenant_ids))
        if body.get("list"):
            tenants = body.get("list")
            if tenants:
                return tenants
        return []

    def get_enterprise_teams(self, enterprise_id, query=None, page=None, page_size=None, user=None):
        tall = team_repo.get_teams_by_enterprise_id(enterprise_id, query=query)
        total = tall.count()
        if page is not None and page_size is not None:
            try:
                paginator = Paginator(tall, page_size)
                raw_tenants = paginator.page(page)
            except EmptyPage:
                raw_tenants = []
        else:
            raw_tenants = tall
        tenants = []
        for tenant in raw_tenants:
            tenants.append(self.team_with_region_info(tenant, user))
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

    def list_by_team_names(self, team_names):
        return Tenants.objects.filter(tenant_name__in=team_names)

    def list_teams_by_user_id(self, eid, user_id, query=None, page=None, page_size=None):
        tenants = team_repo.list_by_user_id(eid, user_id, query, page, page_size)
        total = team_repo.count_by_user_id(eid, user_id, query)
        user = user_repo.get_by_user_id(user_id)
        for tenant in tenants:
            if isinstance(tenant["is_active"], int):
                tenant["is_active"] = True if tenant["is_active"] == 1 else False
            roles = user_kind_role_service.get_user_roles(kind="team", kind_id=tenant["tenant_id"], user=user)
            tenant["role_infos"] = roles["roles"]
        return tenants, total

    def team_with_region_info(self, tenant, request_user=None, get_region=True):
        try:
            user = user_repo.get_user_by_user_id(tenant.creater)
            owner_name = user.get_name()
        except UserNotExistError:
            owner_name = None

        info = {
            "team_name": tenant.tenant_name,
            "team_alias": tenant.tenant_alias,
            "team_id": tenant.tenant_id,
            "create_time": tenant.create_time,
            "enterprise_id": tenant.enterprise_id,
            "owner": tenant.creater,
            "owner_name": owner_name,
            "logo": tenant.logo
        }

        if request_user:
            user_role_list = user_kind_role_service.get_user_roles(kind="team", kind_id=tenant.tenant_id, user=request_user)
            roles = [x["role_name"] for x in user_role_list["roles"]]
            if tenant.creater == request_user.user_id:
                roles.append("owner")
            info["roles"] = roles

        if get_region:
            region_info_map = []
            region_name_list = team_repo.get_team_region_names(tenant.tenant_id)
            if region_name_list:
                region_infos = region_repo.get_region_by_region_names(region_name_list)
                if region_infos:
                    for region in region_infos:
                        region_info_map.append({"region_name": region.region_name, "region_alias": region.region_alias})
            info["region"] = region_info_map[0]["region_name"] if len(region_info_map) > 0 else ""
            info["region_list"] = region_info_map
        service_reps = TenantServiceInfoRepository()
        service_count = service_reps.get_tenant_services_count(tenant.tenant_id)
        app_count = group_repo.get_tenant_groups_count(tenant.tenant_id)
        info["app_count"] = app_count
        info["service_count"] = service_count
        return info

    def get_teams_region_by_user_id(self, enterprise_id, user, name=None, get_region=True, use_region=False):
        teams_list_no_region = list()
        teams_list_use_region = list()
        tenants = enterprise_repo.get_enterprise_user_teams(enterprise_id, user.user_id, name)
        if tenants:
            for tenant in tenants:
                team = self.team_with_region_info(tenant, user, get_region=get_region)
                if not team.get("region_list"):
                    teams_list_no_region.append(team)
                else:
                    teams_list_use_region.append(team)
        if use_region:
            return teams_list_use_region
        return teams_list_no_region + teams_list_use_region

    def list_user_teams(self, enterprise_id, user, name):
        # User joined team
        teams = self.get_teams_region_by_user_id(enterprise_id, user, name, get_region=True)
        # The team that the user did not join
        user_id = user.user_id if user else ""
        nojoin_teams = team_repo.get_user_notjoin_teams(enterprise_id, user_id, name)
        for nojoin_team in nojoin_teams:
            team = self.team_with_region_info(nojoin_team, get_region=False)
            teams.append(team)
        return teams

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

    def overview(self, team, region_name):
        resource = self.get_tenant_resource(team, region_name)
        component_nums = service_repo.get_team_service_num_by_team_id(team.tenant_id, region_name)
        app_nums = group_repo.get_tenant_region_groups_count(team.tenant_id, region_name)
        return {
            "total_memory": resource.get("total_memory", 0),
            "used_memory": resource.get("used_memory", 0),
            "total_cpu": resource.get("total_cpu", 0),
            "used_cpu": resource.get("used_cpu", 0),
            "app_nums": app_nums,
            "component_nums": component_nums,
        }

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
        tenant_ids = []
        if teams:
            for team in teams:
                team_maps[team.tenant_id] = team
                tenant_ids.append(team.tenant_id)
        res, body = region_api.list_tenants(eid, region_id, tenant_ids)
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
                        "running_applications": tenant["running_applications"]
                    })
        else:
            logger.error(body)
        return tenant_list, total

    def set_tenant_resource_limit(self, eid, region_id, tenant_name, limit):
        try:
            region_api.set_tenant_resource_limit(eid, tenant_name, region_id, body=limit)
        except RegionApiBaseHttpClient.CallApiError as e:
            logger.exception(e)
            raise ServiceHandleException(status_code=500, msg="", msg_show="设置租户限额失败")

    def update(self, tenant_id, data):
        team_repo.update_by_tenant_id(tenant_id, **data)

    @staticmethod
    def check_resource_name(tenant_name: str, region_name: str, rtype: string, name: str):
        return region_api.check_resource_name(tenant_name, region_name, rtype, name)

    def list_registry_auths(self, tenant_id, region_name, user_id):
        return team_registry_auth_repo.list_by_team_id(tenant_id, region_name, user_id)

    @transaction.atomic()
    def create_registry_auth(self, tenant, region_name, domain, username, password, hub_type, user_id):
        auth = team_registry_auth_repo.get_by_team_id_domain(tenant.tenant_id, region_name, domain)
        if auth:
            raise ServiceHandleException(
                status_code=409, msg="The image warehouse address already exists", msg_show="该镜像仓库地址已存在")
        params = {
            "tenant_id": tenant.tenant_id,
            "secret_id": make_uuid(),
            "domain": domain,
            "username": username,
            "password": password,
            "region_name": region_name,
        }
        team_registry_auth_repo.create_team_registry_auth(**params)
        region_api.create_registry_auth(tenant.tenant_name, region_name, params)

    @transaction.atomic()
    def update_registry_auth(self, tenant, region_name, secret_id, data):
        auth = team_registry_auth_repo.get_by_secret_id(secret_id)
        if not auth:
            return
        team_registry_auth_repo.update_team_registry_auth(tenant.tenant_id, region_name, secret_id, **data)
        region_api.update_registry_auth(tenant.tenant_name, region_name, auth[0].to_dict())

    @transaction.atomic()
    def delete_registry_auth(self, tenant, region_name, secret_id, user_id):
        team_registry_auth_repo.delete_team_registry_auth(tenant.tenant_id, region_name, secret_id, user_id)
        region_api.delete_registry_auth(tenant.tenant_name, region_name, {
            "secret_id": secret_id,
            "tenant_id": tenant.tenant_id
        })

    def get_registry_namespaces(self, domain, username, password, hub_type):
        try:
            parsed_url = urlparse(domain)
            base_url = parsed_url.scheme + "://" + parsed_url.netloc
            
            if hub_type == "Harbor":
                # Harbor API
                api_url = "{}/api/v2.0/projects".format(base_url)
                response = requests.get(
                    api_url,
                    auth=(username, password),
                    verify=False,
                    timeout=10
                )
                if response.status_code == 200:
                    projects = response.json()
                    return [project["name"] for project in projects]
                    
            elif hub_type == "Docker":
                if "docker.io" in domain:
                    # Docker Hub API
                    api_url = "https://hub.docker.com/v2/repositories/{}/".format(username)
                    response = requests.get(
                        api_url,
                        headers={"Authorization": "JWT " + self._get_dockerhub_token(username, password)},
                        timeout=10
                    )
                    if response.status_code == 200:
                        namespaces = response.json().get("namespaces", [])
                        if username not in namespaces:
                            namespaces.append(username)
                        return namespaces
                else:
                    # 自建 Docker Registry API v2
                    api_url = "{}/v2/_catalog".format(base_url)
                    auth = base64.b64encode(f"{username}:{password}".encode()).decode()
                    headers = {"Authorization": f"Basic {auth}"}
                    response = requests.get(
                        api_url,
                        headers=headers,
                        verify=False,
                        timeout=10
                    )
                    if response.status_code == 200:
                        repositories = response.json().get("repositories", [])
                        # 提取命名空间（取第一个/之前的部分作为命名空间）
                        namespaces = set()
                        for repo in repositories:
                            if "/" in repo:
                                namespace = repo.split("/")[0]
                                namespaces.add(namespace)
                            else:
                                namespaces.add("library")
                        return list(namespaces) or ["library"]
                    
            elif hub_type == "Volcano":
                # 火山引擎容器镜像服务 API
                api_url = "{}/v2/manage/namespaces".format(base_url)
                response = requests.get(
                    api_url,
                    auth=(username, password),
                    verify=False,
                    timeout=10
                )
                if response.status_code == 200:
                    namespaces = response.json().get("namespaces", [])
                    return [ns["name"] for ns in namespaces]
                    
            elif hub_type == "Aliyun":
                # 阿里云容器镜像服务 API
                api_url = "https://cr.{}.aliyuncs.com/v2/repos/namespaces".format(
                    parsed_url.netloc.split('.')[1]  # 获取地域信息
                )
                response = requests.get(
                    api_url,
                    headers={"Authorization": "Basic " + base64.b64encode(f"{username}:{password}".encode()).decode()},
                    timeout=10
                )
                if response.status_code == 200:
                    namespaces = response.json().get("data", {}).get("namespaces", [])
                    return [ns["namespace"] for ns in namespaces]

            raise ServiceHandleException(
                msg="failed to get registry namespaces, status:{}".format(response.status_code),
                msg_show="获取镜像仓库命名空间失败",
                status_code=response.status_code)
            
        except requests.exceptions.RequestException as e:
            logger.exception(e)
            raise ServiceHandleException(
                msg="failed to connect registry: {}".format(e),
                msg_show="连接镜像仓库失败",
                status_code=500)

    def _get_dockerhub_token(self, username, password):
        """获取Docker Hub的JWT token"""
        try:
            response = requests.post(
                "https://hub.docker.com/v2/users/login/",
                json={
                    "username": username,
                    "password": password
                },
                timeout=10
            )
            if response.status_code == 200:
                return response.json().get("token")
            raise ServiceHandleException(
                msg="failed to get docker hub token",
                msg_show="Docker Hub认证失败",
                status_code=response.status_code)
        except requests.exceptions.RequestException as e:
            logger.exception(e)
            raise ServiceHandleException(
                msg="failed to connect docker hub: {}".format(e),
                msg_show="连接Docker Hub失败", 
                status_code=500)

    def get_registry_images(self, domain, username, password, hub_type, namespace, page=1, page_size=10, search_key=None):
        """获取指定命名空间下的镜像列表,支持分页和搜索
        
        Args:
            search_key (str): 搜索关键字,用于过滤镜像名称
            
        Returns:
            dict: 包含镜像详细信息的字典
        """
        try:
            parsed_url = urlparse(domain)
            base_url = parsed_url.scheme + "://" + parsed_url.netloc
            
            if hub_type == "Harbor":
                # Harbor API 支持搜索
                api_url = "{}/api/v2.0/projects/{}/repositories?page={}&page_size={}".format(
                    base_url, namespace, page, page_size)
                if search_key:
                    api_url += "&q=name=~{}".format(search_key)
                    
                response = requests.get(
                    api_url,
                    auth=(username, password),
                    verify=False,
                    timeout=10
                )
                if response.status_code == 200:
                    repositories = response.json()
                    total = int(response.headers.get('X-Total-Count', 0))
                    
                    images = []
                    for repo in repositories:
                        images.append({
                            "name": repo["name"].split("/")[-1],
                            "namespace": namespace,
                            "description": repo.get("description", ""),
                            "is_public": not repo.get("private", True),
                            "pull_count": repo.get("pull_count", 0), 
                            "star_count": 0,
                            "created_at": repo.get("creation_time", ""),
                            "updated_at": repo.get("update_time", ""),
                            "status": "active" if repo.get("status", "") == "active" else "inactive",
                            "registry_type": "Harbor"
                        })
                    
                    return {
                        "images": images,
                        "total": total,
                        "page": page,
                        "page_size": page_size
                    }
                    
            elif hub_type == "Docker":
                if "docker.io" in domain:
                    # Docker Hub API 支持搜索
                    api_url = "https://hub.docker.com/v2/repositories/{}/?page={}&page_size={}".format(
                        namespace, page, page_size)
                    if search_key:
                        api_url += "&name={}".format(search_key)
                    
                    response = requests.get(
                        api_url,
                        headers={"Authorization": "JWT " + self._get_dockerhub_token(username, password)},
                        timeout=10
                    )
                    if response.status_code == 200:
                        data = response.json()
                        repositories = data.get("results", [])
                        images = []
                        for repo in repositories:
                            images.append({
                                "name": repo["name"],
                                "namespace": namespace,
                                "description": repo.get("description", ""),
                                "is_public": not repo.get("is_private", False),
                                "pull_count": repo.get("pull_count", 0),
                                "star_count": repo.get("star_count", 0),
                                "created_at": repo.get("date_registered", ""),
                                "updated_at": repo.get("last_updated", ""),
                                "status": repo.get("status", "active"),
                                "registry_type": "Docker"
                            })
                        
                        return {
                            "images": images,
                            "total": data.get("count", 0),
                            "page": page,
                            "page_size": page_size
                        }
                else:
                    # 自建 Docker Registry API v2
                    api_url = "{}/v2/_catalog".format(base_url)
                    auth = base64.b64encode(f"{username}:{password}".encode()).decode()
                    headers = {"Authorization": f"Basic {auth}"}
                    response = requests.get(
                        api_url,
                        headers=headers,
                        verify=False,
                        timeout=10
                    )
                    if response.status_code == 200:
                        repositories = response.json().get("repositories", [])
                        # 过滤指定命名空间的镜像
                        if namespace == "library":
                            filtered_repos = [r for r in repositories if "/" not in r]
                        else:
                            filtered_repos = [r.split("/", 1)[1] for r in repositories if r.startswith(namespace + "/")]
                        
                        # 搜索过滤
                        if search_key:
                            filtered_repos = [r for r in filtered_repos if search_key.lower() in r.lower()]
                        
                        total = len(filtered_repos)
                        start = (page - 1) * page_size
                        end = start + page_size
                        paginated_repos = filtered_repos[start:end]
                        
                        images = []
                        for repo in paginated_repos:
                            # 获取仓库的标签列表
                            tags_url = "{}/v2/{}/tags/list".format(base_url, repo if namespace == "library" else f"{namespace}/{repo}")
                            tags_response = requests.get(
                                tags_url,
                                headers=headers,
                                verify=False,
                                timeout=10
                            )
                            
                            if tags_response.status_code == 200:
                                tags = tags_response.json().get("tags", [])
                                if tags:
                                    # 获取最新标签的信息
                                    repo_name = repo if namespace == "library" else f"{namespace}/{repo}"
                                    tag_info = self._get_registry_tag_info(base_url, repo_name, tags[0], f"Basic {auth}")
                                    updated_at = tag_info["updated_at"]
                            
                            images.append({
                                "name": repo,
                                "namespace": namespace,
                                "description": "",
                                "is_public": True,
                                "pull_count": 0,
                                "star_count": 0,
                                "created_at": updated_at,
                                "updated_at": updated_at,
                                "status": "active",
                                "registry_type": "Docker"
                            })
                        
                        return {
                            "images": images,
                            "total": total,
                            "page": page,
                            "page_size": page_size
                        }
            elif hub_type == "Harbor":
                # Harbor API v2.0
                api_url = "{}/api/v2.0/projects/{}/repositories/{}/artifacts?page={}&page_size={}&with_tag=true&with_label=false".format(
                    base_url, namespace, name, page, page_size)
                if search_key:
                    api_url += "&q=tags=~{}".format(search_key)

                auth = base64.b64encode(f"{username}:{password}".encode()).decode()
                headers = {"Authorization": f"Basic {auth}"}
                response = requests.get(
                    api_url,
                    headers=headers,
                    verify=False,
                    timeout=10
                )
                
                if response.status_code == 200:
                    total = int(response.headers.get('X-Total-Count', 0))
                    artifacts = response.json()
                    tags = []
                    
                    for artifact in artifacts:
                        # Harbor可能返回多个tag，我们需要处理所有的tag
                        artifact_tags = artifact.get('tags', [])
                        # 获取镜像大小和架构信息
                        extra_attrs = artifact.get('extra_attrs', {})
                        size = artifact.get('size', 0)
                        architecture = extra_attrs.get('architecture', '')
                        os = extra_attrs.get('os', '')
                        
                        for tag in artifact_tags:
                            tags.append({
                                "name": tag.get('name'),
                                "size": size,
                                "digest": artifact.get('digest', ''),
                                "created_at": artifact.get('push_time', ''),
                                "updated_at": artifact.get('push_time', ''),
                                "os": os,
                                "architecture": architecture,
                                "status": "active"
                            })
                    
                    return {
                        "tags": tags,
                        "total": total,
                        "page": page,
                        "page_size": page_size
                    }
        
            raise ServiceHandleException(
                msg="failed to get registry images, status:{}".format(response.status_code),
                msg_show="获取镜像列表失败",
                status_code=response.status_code)
            
        except requests.exceptions.RequestException as e:
            logger.exception(e)
            raise ServiceHandleException(
                msg="failed to connect registry: {}".format(e),
                msg_show="连接镜像仓库失败",
                status_code=500)

    def get_registry_tags(self, domain, username, password, hub_type, namespace, name, page=1, page_size=10, search_key=None):
        """获取指定镜像的标签列表,支持分页和搜索
        
        Args:
            search_key (str): 标签名称搜索关键字
            
        Returns:
            dict: 包含标签详细信息的字典
        """
        try:
            parsed_url = urlparse(domain)
            base_url = parsed_url.scheme + "://" + parsed_url.netloc
            
            if hub_type == "Docker":
                if "docker.io" in domain:
                    # Docker Hub API
                    api_url = "https://hub.docker.com/v2/repositories/{}/{}/tags?page={}&page_size={}".format(
                        namespace, name, page, page_size)
                    if search_key:
                        api_url += "&name={}".format(search_key)
                    
                    response = requests.get(
                        api_url,
                        headers={"Authorization": "JWT " + self._get_dockerhub_token(username, password)},
                        timeout=10
                    )
                    if response.status_code == 200:
                        data = response.json()
                        tags = []
                        
                        for tag in data.get("results", []):
                            image_detail = tag.get("images", [{}])[0] if tag.get("images") else {}
                            tags.append({
                                "name": tag.get("name"),
                                "size": image_detail.get("size", 0),
                                "digest": image_detail.get("digest", ""),
                                "created_at": tag.get("last_updated", ""),
                                "updated_at": tag.get("last_updated", ""),
                                "os": image_detail.get("os", ""),
                                "architecture": image_detail.get("architecture", ""),
                                "status": tag.get("status", "active")
                            })
                        
                        return {
                            "tags": tags,
                            "total": data.get("count", 0),
                            "page": page,
                            "page_size": page_size
                        }
                else:
                    # 自建 Docker Registry API v2
                    repo_name = name if namespace == "library" else f"{namespace}/{name}"
                    api_url = "{}/v2/{}/tags/list".format(base_url, repo_name)
                    auth = base64.b64encode(f"{username}:{password}".encode()).decode()
                    headers = {"Authorization": f"Basic {auth}"}
                    response = requests.get(
                        api_url,
                        headers=headers,
                        verify=False,
                        timeout=10
                    )
                    if response.status_code == 200:
                        all_tags = response.json().get("tags", [])
                        if search_key:
                            all_tags = [t for t in all_tags if search_key.lower() in t.lower()]
                        
                        total = len(all_tags)
                        start = (page - 1) * page_size
                        end = start + page_size
                        paginated_tags = all_tags[start:end]
                        
                        tags = []
                        for tag_name in paginated_tags:
                            # 获取标签详细信息
                            tag_info = self._get_registry_tag_info(base_url, repo_name, tag_name, f"Basic {auth}")
                            
                            tags.append({
                                "name": tag_name,
                                "size": tag_info["size"],
                                "digest": tag_info["digest"],
                                "created_at": tag_info["updated_at"],
                                "updated_at": tag_info["updated_at"],
                                "os": tag_info["os"],
                                "architecture": tag_info["architecture"],
                                "status": "active"
                            })
                        
                        return {
                            "tags": tags,
                            "total": total,
                            "page": page,
                            "page_size": page_size
                        }
            elif hub_type == "Harbor":
                # Harbor API v2.0
                api_url = "{}/api/v2.0/projects/{}/repositories/{}/artifacts?page={}&page_size={}&with_tag=true&with_label=false".format(
                    base_url, namespace, name, page, page_size)
                if search_key:
                    api_url += "&q=tags=~{}".format(search_key)

                auth = base64.b64encode(f"{username}:{password}".encode()).decode()
                headers = {"Authorization": f"Basic {auth}"}
                response = requests.get(
                    api_url,
                    headers=headers,
                    verify=False,
                    timeout=10
                )
                
                if response.status_code == 200:
                    total = int(response.headers.get('X-Total-Count', 0))
                    artifacts = response.json()
                    tags = []
                    
                    for artifact in artifacts:
                        # Harbor可能返回多个tag，我们需要处理所有的tag
                        artifact_tags = artifact.get('tags', [])
                        # 获取镜像大小和架构信息
                        extra_attrs = artifact.get('extra_attrs', {})
                        size = artifact.get('size', 0)
                        architecture = extra_attrs.get('architecture', '')
                        os = extra_attrs.get('os', '')
                        
                        for tag in artifact_tags:
                            tags.append({
                                "name": tag.get('name'),
                                "size": size,
                                "digest": artifact.get('digest', ''),
                                "created_at": artifact.get('push_time', ''),
                                "updated_at": artifact.get('push_time', ''),
                                "os": os,
                                "architecture": architecture,
                                "status": "active"
                            })
                    
                    return {
                        "tags": tags,
                        "total": total,
                        "page": page,
                        "page_size": page_size
                    }
        
            raise ServiceHandleException(
                msg="failed to get registry tags, status:{}".format(response.status_code),
                msg_show="获取镜像标签失败",
                status_code=response.status_code)
            
        except requests.exceptions.RequestException as e:
            logger.exception(e)
            raise ServiceHandleException(
                msg="failed to connect registry: {}".format(e),
                msg_show="连接镜像仓库失败",
                status_code=500)

    def _get_registry_tag_info(self, base_url, repo_name, tag_name, auth_header):
        """获取 Docker Registry 标签的详细信息
        
        Args:
            base_url: 仓库基础URL
            repo_name: 仓库名称
            tag_name: 标签名称
            auth_header: 认证头信息
            
        Returns:
            dict: 包含标签详细信息的字典
        """
        try:
            manifest_url = "{}/v2/{}/manifests/{}".format(base_url, repo_name, tag_name)
            manifest_response = requests.get(
                manifest_url,
                headers={
                    "Authorization": auth_header,
                    "Accept": "application/vnd.docker.distribution.manifest.v2+json"
                },
                verify=False,
                timeout=10
            )
            
            if manifest_response.status_code == 200:
                manifest = manifest_response.json()
                config_digest = manifest.get("config", {}).get("digest")
                
                # 只计算压缩后的大小
                compressed_size = sum(layer.get("size", 0) for layer in manifest.get("layers", []))
                
                if config_digest:
                    config_url = "{}/v2/{}/blobs/{}".format(base_url, repo_name, config_digest)
                    config_response = requests.get(
                        config_url,
                        headers={
                            "Authorization": auth_header,
                        },
                        verify=False,
                        timeout=10
                    )
                    if config_response.status_code == 200:
                        config = config_response.json()
                        return {
                            "updated_at": config.get("created", ""),
                            "created_at": config.get("created", ""),
                            "digest": manifest.get("config", {}).get("digest", ""),
                            "os": config.get("os", ""),
                            "architecture": config.get("architecture", ""),
                            "size": compressed_size
                        }
        except requests.exceptions.RequestException as e:
            logger.exception(e)
        
        return {
            "updated_at": "",
            "created_at": "",
            "digest": "",
            "os": "",
            "architecture": "",
            "size": 0
        }

    def get_full_image_name(self, domain, hub_type, namespace, name, tag):
        """获取完整的镜像地址
        
        Args:
            domain: 镜像仓库域名
            hub_type: 仓库类型
            namespace: 命名空间
            name: 镜像名称
            tag: 标签
            
        Returns:
            str: 完整的镜像地址
        """
        try:
            parsed_url = urlparse(domain)
            registry = parsed_url.netloc
            
            if hub_type == "Docker" and registry == "hub.docker.com":
                # Docker Hub的特殊处理
                if namespace == "library":
                    return "{}/{}:{}".format(name, tag)
                return "{}/{}:{}".format(namespace, name, tag)
            
            # 其他类型仓库
            return "{}/{}/{}:{}".format(registry, namespace, name, tag)
            
        except Exception as e:
            logger.exception(e)
            raise ServiceHandleException(
                msg="failed to generate full image name: {}".format(e),
                msg_show="生成完整镜像地址失败",
                status_code=500)

    def get_user_team_details(self, user):
        """
        获取用户创建的团队详情
        """
        # 获取所有启用状态的集群
        regions = RegionConfig.objects.filter(status='1')
        
        # 获取用户创建的团队
        teams = Tenants.objects.filter(creater=user.user_id)
        
        # 获取团队与集群的关联关系
        team_region_map = {}
        team_ids = [t.tenant_id for t in teams]
        team_regions = TenantRegionInfo.objects.filter(
            tenant_id__in=team_ids,
            is_active=True
        )
        
        # 构建团队和集群的映射关系
        for tr in team_regions:
            if tr.region_name not in team_region_map:
                team_region_map[tr.region_name] = []
            team_region_map[tr.region_name].append(tr.tenant_id)

        # 获取所有相关的应用信息
        service_groups = ServiceGroup.objects.filter(tenant_id__in=team_ids)
        
        # 获取应用与region_app的映射关系
        app_ids = [sg.ID for sg in service_groups]
        region_apps = RegionApp.objects.filter(app_id__in=app_ids)
        region_app_map = {ra.app_id: ra.region_app_id for ra in region_apps}

        # 获取应用与组件的关联关系
        group_service_map = {}
        group_relations = ServiceGroupRelation.objects.filter(group_id__in=app_ids)
        service_ids = [gr.service_id for gr in group_relations]
        
        # 获取组件信息
        services = TenantServiceInfo.objects.filter(service_id__in=service_ids)
        service_map = {s.service_id: s for s in services}
        
        # 构建应用与组件的映射关系
        for relation in group_relations:
            if relation.group_id not in group_service_map:
                group_service_map[relation.group_id] = []
            service = service_map.get(relation.service_id)
            if service:
                group_service_map[relation.group_id].append({
                    "service_id": service.service_id,
                    "service_name": service.service_cname
                })

        # 构建团队ID到应用的映射
        team_apps_map = {}
        for sg in service_groups:
            if sg.tenant_id not in team_apps_map:
                team_apps_map[sg.tenant_id] = []
            # 使用region_app_id，如果没有则使用group_id的字符串形式
            app_id = region_app_map.get(sg.ID, str(sg.ID))
            team_apps_map[sg.tenant_id].append({
                "app_id": app_id,
                "app_name": sg.group_name,
                "components": group_service_map.get(sg.ID, [])
            })

        # 构建返回数据结构
        region_list = []
        for region in regions:
            team_ids = team_region_map.get(region.region_name, [])
            region_teams = [t for t in teams if t.tenant_id in team_ids]
            
            namespaces = []
            for team in region_teams:
                namespaces.append({
                    "namespace": team.namespace,
                    "user_id": user.user_id,
                    "username": user.nick_name,
                    "apps": team_apps_map.get(team.tenant_id, [])
                })

            region_list.append({
                "region_name": region.region_name,
                "region_alias": region.region_alias,
                "namespaces": namespaces
            })
            
        return region_list


team_services = TeamService()
