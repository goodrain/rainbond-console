# -*- coding: utf-8 -*-
import base64
import json
import logging
import os
import random
import re
import string
from typing import Any, Dict, List, NoReturn, Optional, Tuple
from urllib.parse import urlparse, quote

import requests  # type: ignore[import-untyped]
from django.db.models import QuerySet

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
from www.models.main import (PermRelTenant, Tenants, TenantServiceInfo, TenantRegionInfo, ServiceGroup, RegionApp,
                              ServiceGroupRelation, Users)
from www.utils.crypt import make_uuid

logger = logging.getLogger("default")
region_api = RegionInvokeApi()


class TeamService(object):
    USER_REGISTRY_SCOPE = "user"
    ENTERPRISE_REGISTRY_SCOPE = "enterprise"
    SUPPORTED_REGISTRY_HUB_TYPES = (
        "Docker", "Harbor", "AliyunACR", "TencentTCR", "HuaweiSWR", "VolcanoCR")
    LEGACY_REGISTRY_HUB_TYPE_ALIASES = {
        "Aliyun": "AliyunACR",
        "Tencent": "TencentTCR",
        "Huawei": "HuaweiSWR",
        "Volcano": "VolcanoCR",
    }
    CLOUD_REGISTRY_HUB_TYPES = ("AliyunACR", "TencentTCR", "HuaweiSWR", "VolcanoCR")
    ALIYUN_ACR_DOMAIN_RE = re.compile(r"^registry\.(?P<region>[^.]+)\.aliyuncs\.com$")
    TENCENT_TCR_DOMAIN_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9-]*(?:\.[a-zA-Z0-9-]+)*\.tencentcloudcr\.com$")
    TENCENT_TCR_PERSONAL_REGIONS = {
        "ccr.ccs.tencentyun.com": "ap-guangzhou",
        "hkccr.ccs.tencentyun.com": "ap-hongkong",
    }
    HUAWEI_SWR_DOMAIN_RE = re.compile(r"^swr\.(?P<region>[^.]+)\.myhuaweicloud\.com$")
    VOLCANO_CR_DOMAIN_RE = re.compile(r"^(?P<registry>[a-zA-Z0-9][a-zA-Z0-9-]{1,28}[a-zA-Z0-9])-(?P<region>cn-[^.]+)\.cr\.volces\.com$")
    TENCENT_TCR_DISCOVERY_REGION = "ap-guangzhou"
    REGISTRY_MANIFEST_ACCEPT_TYPES = (
        "application/vnd.oci.image.index.v1+json",
        "application/vnd.oci.image.manifest.v1+json",
        "application/vnd.docker.distribution.manifest.list.v2+json",
        "application/vnd.docker.distribution.manifest.v2+json",
    )
    CLOUD_REGISTRY_AUTH_ERROR_MARKERS = (
        "signaturedoesnotmatch",
        "authfailure",
        "invalidaccesskey",
        "invalid access key",
        "secretidnotfound",
        "unauthorized",
        "accessdenied",
        "access denied",
        "forbidden",
        "permission",
    )

    def get_tenant_by_tenant_name(self, tenant_name: str, exception: bool = True) -> Optional[Tenants]:
        return team_repo.get_tenant_by_tenant_name(tenant_name=tenant_name, exception=exception)

    def get_tenant(self, tenant_name: str) -> Tenants:
        if not Tenants.objects.filter(tenant_name=tenant_name).exists():
            raise Tenants.DoesNotExist
        return Tenants.objects.get(tenant_name=tenant_name)

    def get_enterprise_tenant_by_tenant_name(self, enterprise_id: str, tenant_name: str) -> Optional[Tenants]:
        return Tenants.objects.filter(tenant_name=tenant_name, enterprise_id=enterprise_id).first()

    def get_team_by_team_alias_and_eid(self, team_alias: str, enterprise_id: str) -> Optional[Tenants]:
        return Tenants.objects.filter(tenant_alias=team_alias, enterprise_id=enterprise_id).first()

    def get_team_by_team_id_and_eid(self, team_id: str, enterprise_id: str) -> Optional[Tenants]:
        if enterprise_id:
            return Tenants.objects.filter(tenant_id=team_id, enterprise_id=enterprise_id).first()
        return Tenants.objects.filter(tenant_id=team_id).first()

    def random_tenant_name(self, enterprise: Any = None, length: int = 8) -> str:
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

    def add_user_to_team(self, tenant: Tenants, user_id: str, role_ids: Any = None) -> None:
        user = user_repo.get_by_user_id(user_id)
        if not user:
            raise ServiceHandleException(msg="user not found", msg_show="用户不存在", status_code=404)
        exist_team_user = PermRelTenant.objects.filter(tenant_id=tenant.ID, user_id=user.user_id)
        enterprise = enterprise_services.get_enterprise_by_enterprise_id(enterprise_id=tenant.enterprise_id)
        if exist_team_user:
            raise ServiceHandleException(msg="user exist", msg_show="用户已经加入此团队")
        # enterprise is non-None: get_enterprise_by_enterprise_id defaults exception=True (raises if missing)
        PermRelTenant.objects.create(
            tenant_id=tenant.ID, user_id=user.user_id, identity="",
            enterprise_id=enterprise.ID)  # type: ignore[union-attr]
        if role_ids:
            user_kind_role_service.update_user_roles(kind="team", kind_id=tenant.tenant_id, user=user, role_ids=role_ids)

    def get_team_users(self, team: Tenants, name: Optional[str] = None) -> Any:
        # NOTE: Tenants.ID is the int PK; repo annotates tenant_ID as str (signature mismatch).
        users = team_repo.get_tenant_users_by_tenant_ID(team.ID)  # type: ignore[arg-type]
        if users and name:
            users = users.filter(Q(nick_name__contains=name) | Q(real_name__contains=name))
        return users

    def get_tenant_users_by_tenant_name(self, tenant_name: str) -> Any:
        tenant = team_repo.get_tenant_by_tenant_name(tenant_name=tenant_name)
        # NOTE: get_tenant_by_tenant_name defaults exception=True -> raises, never None.
        # NOTE: Tenants.ID is the int PK; repo annotates tenant_ID as str (signature mismatch).
        user_list = team_repo.get_tenant_users_by_tenant_ID(tenant_ID=tenant.ID)  # type: ignore[union-attr, arg-type]
        return user_list

    def update_tenant_info(self, tenant_name: str, new_team_alias: str, new_logo: str) -> Optional[Tenants]:
        tenant = team_repo.get_tenant_by_tenant_name(tenant_name=tenant_name, exception=True)
        # NOTE: exception=True -> repo raises instead of returning None; tenant is non-None here.
        tenant.tenant_alias = new_team_alias  # type: ignore[union-attr]
        if new_logo:
            tenant.logo = new_logo  # type: ignore[union-attr]
        tenant.save()  # type: ignore[union-attr]
        return tenant

    def get_user_perms_in_permtenant(self, user_id: str, tenant_name: str) -> Any:
        tenant = self.get_tenant_by_tenant_name(tenant_name=tenant_name)
        # NOTE: get_tenant_by_tenant_name defaults exception=True -> non-None; ID is int PK vs str sig.
        user_perms = team_repo.get_user_perms_in_permtenant(
            user_id=user_id, tenant_id=tenant.ID)  # type: ignore[union-attr, arg-type]
        return user_perms

    def get_not_join_users(
            self,
            enterprise: Any,
            tenant: Tenants,
            query: str,
    ) -> Any:
        return team_repo.get_not_join_users(enterprise, tenant, query)

    def get_user_perms_in_permtenant_list(self, user_id: str, tenant_name: str) -> Any:
        """
        一个用户在一个团队中的身份列表
        :return: 一个用户在一个团队中的身份列表
        """
        tenant = self.get_tenant_by_tenant_name(tenant_name=tenant_name)
        # NOTE: get_tenant_by_tenant_name defaults exception=True -> non-None; ID is int PK vs str sig.
        user_perms_list = team_repo.get_user_perms_in_permtenant_list(
            user_id=user_id, tenant_id=tenant.ID)  # type: ignore[union-attr, arg-type]
        return user_perms_list

    def get_user_perm_identitys_in_permtenant(self, user_id: str, tenant_name: str) -> dict:
        """获取用户在一个团队的身份列表"""
        user = user_repo.get_by_user_id(user_id)
        try:
            tenant = self.get_tenant(tenant_name=tenant_name)
        except Tenants.DoesNotExist:
            tenant = self.get_team_by_team_id(tenant_name)
            if tenant is None:
                raise Tenants.DoesNotExist()
        user_roles = user_kind_role_service.get_user_roles(kind_id=tenant.ID, kind="team", user=user)  # type: ignore[arg-type]  # NOTE: tenant.ID int vs str kind_id (systemic)
        if tenant.creater == user_id:
            user_roles["roles"].append("owner")
        return user_roles

    def get_user_perm_role_id_in_permtenant(self, user_id: str, tenant_name: str) -> list:
        """获取一个用户在一个团队的角色ID列表"""
        try:
            tenant = self.get_tenant(tenant_name=tenant_name)
        except Tenants.DoesNotExist:
            tenant = self.get_team_by_team_id(tenant_name)
            if tenant is None:
                raise Tenants.DoesNotExist()
        # NOTE: Tenants.ID is the int PK; repo annotates tenant_id as str (signature mismatch).
        user_perms = team_repo.get_user_perms_in_permtenant(
            user_id=user_id, tenant_id=tenant.ID)  # type: ignore[arg-type]
        if not user_perms:
            return []
        role_id_list = []
        for role_id in [perm.role_id for perm in user_perms]:
            if not role_id:
                continue
            role_id_list.append(role_id)
        return role_id_list

    def get_all_team_role_id(self, tenant_name: str, allow_owner: bool = False) -> list:
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
    def change_tenant_role(self, user_id: str, tenant_name: str, role_id_list: Any) -> Any:
        """修改用户在团队中的角色"""
        try:
            tenant = self.get_tenant(tenant_name=tenant_name)
        except Tenants.DoesNotExist:
            tenant = self.get_team_by_team_id(tenant_name)
            if tenant is None:
                raise Tenants.DoesNotExist()
        enterprise = enterprise_services.get_enterprise_by_enterprise_id(enterprise_id=tenant.enterprise_id)
        # NOTE: role_repo has no update_user_role_in_tenant_by_user_id_tenant_id_role_id; deprecated
        # method (# todo 废弃) that would AttributeError at runtime -- latent bug, left as-is.
        user_role = role_repo.update_user_role_in_tenant_by_user_id_tenant_id_role_id(  # type: ignore[attr-defined]
            user_id=user_id, tenant_id=tenant.pk,
            enterprise_id=enterprise.pk,  # type: ignore[union-attr]  # exception=True -> non-None
            role_id_list=role_id_list)
        return user_role

    def add_user_role_to_team(self, tenant: Tenants, user_ids: Any, role_ids: Any) -> None:
        """在团队中添加一个用户并给用户分配一个角色"""
        enterprise = enterprise_services.get_enterprise_by_enterprise_id(enterprise_id=tenant.enterprise_id)
        if enterprise:
            for user_id in user_ids:
                # for role_id in role_ids:
                PermRelTenant.objects.update_or_create(user_id=user_id, tenant_id=tenant.pk, enterprise_id=enterprise.pk)
                user = user_repo.get_by_user_id(user_id)
                user_kind_role_service.update_user_roles(kind="team", kind_id=tenant.tenant_id, user=user, role_ids=role_ids)

    def user_is_exist_in_team(self, user_list: Any, tenant_name: str) -> Any:
        """判断一个用户是否存在于一个团队中"""
        try:
            tenant = self.get_tenant(tenant_name=tenant_name)
        except Tenants.DoesNotExist:
            tenant = self.get_team_by_team_id(tenant_name)
            if tenant is None:
                raise Tenants.DoesNotExist()
        enterprise = enterprise_services.get_enterprise_by_enterprise_id(enterprise_id=tenant.enterprise_id)
        for user_id in user_list:
            obj = PermRelTenant.objects.filter(
                user_id=user_id, tenant_id=tenant.pk,
                enterprise_id=enterprise.pk)  # type: ignore[union-attr]  # exception=True -> non-None
            if obj:
                return obj[0].user_id
        return False

    def get_team_service_count_by_team_name(self, team_name: str) -> int:
        tenant = self.get_tenant_by_tenant_name(tenant_name=team_name)
        if tenant is None:
            raise Tenants.DoesNotExist()
        return TenantServiceInfo.objects.filter(tenant_id=tenant.tenant_id).count()

    def count_by_tenant_id(self, tenant_id: str) -> int:
        return TenantServiceInfo.objects.filter(tenant_id=tenant_id).count()

    def get_service_source(self, service_alias: str) -> Any:
        service_source = TenantServiceInfo.objects.filter(service_alias=service_alias)
        if service_source:
            return service_source[0]
        else:
            return []

    def delete_tenant(self, tenant_name: str) -> None:
        team_repo.delete_tenant(tenant_name=tenant_name)

    @transaction.atomic()
    def delete_by_tenant_id(self, user: Users, tenant: Tenants) -> list:
        tenant_regions = region_repo.get_tenant_regions_by_teamid(tenant.tenant_id)
        region_list = list()
        for region in tenant_regions:
            try:
                # NOTE: tenant.enterprise_id is Optional[str]; delete_tenant_on_region declares enterprise_id: str
                region_config = region_services.delete_tenant_on_region(
                    tenant.enterprise_id, tenant.tenant_name, region.region_name, user)  # type: ignore[arg-type]
                # region_config is non-None: delete_tenant_on_region raises ServiceHandleException instead of returning None
                region_list.append(region_config.region_alias)  # type: ignore[union-attr]
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


    def get_current_user_tenants(self, user_id: str, team_name: str = "") -> Any:
        tenants = team_repo.get_tenants_by_user_id(user_id=user_id, team_name=team_name)
        return tenants

    @transaction.atomic
    def exit_current_team(self, team_name: str, user_id: str) -> Tuple[int, str]:
        s_id = transaction.savepoint()
        try:
            tenant = self.get_tenant_by_tenant_name(tenant_name=team_name)
            # NOTE: exception=True default -> non-None; ID is int PK vs str sig; perms QuerySet non-None.
            team_repo.get_user_perms_in_permtenant(
                user_id=user_id, tenant_id=tenant.ID).delete()  # type: ignore[union-attr, arg-type]
            user = user_repo.get_by_user_id(user_id)
            user_kind_role_service.delete_user_roles(
                kind="team", kind_id=tenant.tenant_id, user=user)  # type: ignore[union-attr]
            transaction.savepoint_commit(s_id)
            return 200, "退出团队成功"
        except Exception as e:
            logger.exception(e)
            transaction.savepoint_rollback(s_id)
            return 400, "退出团队失败"

    def get_team_by_team_id(self, team_id: str) -> Tenants:
        team = team_repo.get_team_by_team_id(team_id=team_id)
        if team:
            # NOTE: team.creater is int PK; get_by_user_id annotates user_id as str (signature mismatch).
            user = user_repo.get_by_user_id(team.creater)  # type: ignore[arg-type]
            # NOTE: creater_name is a dynamic attr attached for serialization, not a model field.
            team.creater_name = "admin"  # type: ignore[attr-defined]
            if user:
                team.creater_name = user.get_name()  # type: ignore[attr-defined]
        return team

    @transaction.atomic
    def create_team(self, user: Users, enterprise: Any, region_list: Any = None, team_alias: Optional[str] = None,
                    namespace: str = "", logo: str = "") -> Tenants:
        if not team_alias and namespace == "default":
            team_name = "default"
        else:
            team_name = self.random_tenant_name(enterprise=user.enterprise_id, length=8)
        if not team_alias:
            team_alias = "{0} 工作空间".format(user.nick_name)
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
        user_kind_role_service.update_user_roles(kind="team", kind_id=team.tenant_id, user=user, role_ids=[admin_role.ID])  # type: ignore[union-attr]  # NOTE: admin_role Optional (latent)
        return team

    def delete_team_region(self, team_id: str, region_name: str) -> None:
        # check team
        tenant = team_repo.get_team_by_team_id(team_id)
        # check region
        region_services.get_by_region_name(region_name)

        tenant_region = region_repo.get_team_region_by_tenant_and_region(team_id, region_name)
        if not tenant_region:
            raise ErrTenantRegionNotFound()

        region_api.delete_tenant(region_name, tenant.tenant_name)

        tenant_region.delete()

    def get_enterprise_teams_fenye(self, enterprise_id: str, query: Optional[str] = None, page: Optional[int] = None,
                                   page_size: Optional[int] = None) -> Tuple[Any, int]:
        tall = team_repo.get_teams_by_enterprise_id(enterprise_id, query=query)
        total = tall.count()
        raw_tenants: Any
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

    def jg_teams(self, eid: str, teams: Any) -> Any:
        tenants: Dict[Any, Any] = dict()
        creaters = [team.creater for team in teams]
        users = user_repo.get_by_user_ids(creaters)
        user_list = {user.user_id: user.get_name() for user in users}
        tenant_ids = [team.tenant_id for team in teams]
        region_dict = dict()
        tenant_IDs = {ten.ID: ten.tenant_id for ten in teams}
        user_id_list = PermRelTenant.objects.filter().values("tenant_id", "user_id")
        user_id_dict: Dict[Any, int] = dict()
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
            team_components: Dict[Any, List[Any]] = {}
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
            region_tenants: List[Any] = list()
            for region_id in region_dict.keys():
                region_tenants += self.get_region_tenant(eid, region_id, tenant_ids)
            for region_tenant in region_tenants:
                tenant_id = region_tenant.get("UUID")
                # NOTE: tenants.get(tenant_id) returns None if region reports a tenant_id absent
                # from the local map; downstream .get()/[...] would fail -> latent None-bug.
                running_apps = tenants.get(tenant_id).get("running_apps")  # type: ignore[union-attr]
                tenants.get(tenant_id)["set_limit_memory"] = region_tenant.get("LimitMemory", 0)  # type: ignore[index]
                tenants.get(tenant_id)["set_limit_cpu"] = region_tenant.get("LimitCPU", 0)  # type: ignore[index]
                tenants.get(tenant_id)["set_limit_storage"] = region_tenant.get("LimitStorage", 0)  # type: ignore[index]
                tenants.get(tenant_id)["running_apps"] = running_apps + region_tenant.get(  # type: ignore[index]
                    "running_applications", 0)
                tenants.get(tenant_id)["memory_request"] = region_tenant.get("memory_limit", 0)  # type: ignore[index]
                tenants.get(tenant_id)["cpu_request"] = region_tenant.get("cpu_limit", 0)  # type: ignore[index]
        return tenants.values()

    def get_region_tenant(self, eid: str, region_id: str, tenant_ids: Any) -> Any:
        res, body = region_api.list_tenants(eid, region_id, json.dumps(tenant_ids))
        # NOTE: list_tenants returns Optional[dict]; body assumed non-None on success.
        if body.get("list"):  # type: ignore[union-attr]
            tenants = body.get("list")  # type: ignore[union-attr]
            if tenants:
                return tenants
        return []

    def get_enterprise_teams(self, enterprise_id: str, query: Optional[str] = None, page: Optional[int] = None,
                             page_size: Optional[int] = None, user: Optional[Users] = None) -> Tuple[list, int]:
        tall = team_repo.get_teams_by_enterprise_id(enterprise_id, query=query)
        total = tall.count()
        raw_tenants: Any
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

    def list_teams_v2(self, eid: str, query: Optional[str] = None, page: Optional[int] = None,
                      page_size: Optional[int] = None) -> Tuple[Any, int]:
        if query:
            total = Tenants.objects.filter(tenant_alias__contains=query).count()
        else:
            total = Tenants.objects.count()
        # NOTE: query may be None; repo annotates query as str (handles falsy at runtime).
        tenants = team_repo.list_teams_v2(query, page, page_size)  # type: ignore[arg-type]
        for tenant in tenants:
            region_num = tenant_region_repo.count_by_tenant_id(tenant["tenant_id"])
            tenant["region_num"] = region_num
        return tenants, total

    def list_by_team_names(self, team_names: Any) -> QuerySet:
        return Tenants.objects.filter(tenant_name__in=team_names)

    def list_teams_by_user_id(self, eid: str, user_id: str, query: Optional[str] = None, page: Optional[int] = None,
                              page_size: Optional[int] = None) -> Tuple[Any, int]:
        # NOTE: query may be None; repos annotate query as str (handle falsy at runtime).
        tenants = team_repo.list_by_user_id(eid, user_id, query, page, page_size)  # type: ignore[arg-type]
        total = team_repo.count_by_user_id(eid, user_id, query)  # type: ignore[arg-type]
        user = user_repo.get_by_user_id(user_id)
        for tenant in tenants:
            if isinstance(tenant["is_active"], int):
                tenant["is_active"] = True if tenant["is_active"] == 1 else False
            roles = user_kind_role_service.get_user_roles(kind="team", kind_id=tenant["tenant_id"], user=user)
            tenant["role_infos"] = roles["roles"]
        return tenants, total

    def team_with_region_info(self, tenant: Tenants, request_user: Optional[Users] = None,
                              get_region: bool = True) -> dict:
        try:
            # NOTE: tenant.creater is int; get_user_by_user_id annotates user_id as str (sig mismatch).
            user = user_repo.get_user_by_user_id(tenant.creater)  # type: ignore[arg-type]
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

    def get_teams_region_by_user_id(self, enterprise_id: str, user: Users, name: Optional[str] = None,
                                    get_region: bool = True, use_region: bool = False) -> list:
        teams_list_no_region = list()
        teams_list_use_region = list()
        # NOTE: user.user_id is int; get_enterprise_user_teams annotates user_id as str (sig mismatch).
        tenants = enterprise_repo.get_enterprise_user_teams(
            enterprise_id, user.user_id, name)  # type: ignore[arg-type]
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

    def list_user_teams(self, enterprise_id: str, user: Optional[Users], name: Optional[str]) -> list:
        # User joined team
        # NOTE: get_teams_region_by_user_id deref's user.user_id; passing None would fail there.
        teams = self.get_teams_region_by_user_id(
            enterprise_id, user, name, get_region=True)  # type: ignore[arg-type]
        # The team that the user did not join
        user_id = user.user_id if user else ""
        # NOTE: user_id is int|str; get_user_notjoin_teams annotates user_id as str (sig mismatch).
        nojoin_teams = team_repo.get_user_notjoin_teams(enterprise_id, user_id, name)  # type: ignore[arg-type]
        for nojoin_team in nojoin_teams:
            team = self.team_with_region_info(nojoin_team, get_region=False)
            teams.append(team)
        return teams

    def check_and_get_user_team_by_name_and_region(self, user_id: str, tenant_name: str,
                                                   region_name: str) -> Optional[Tenants]:
        tenant = team_repo.get_user_tenant_by_name(user_id, tenant_name)
        if not tenant:
            return tenant
        if not team_repo.get_team_region_by_name(tenant.tenant_id, region_name):
            return None
        else:
            return tenant

    def get_team_by_team_alias(self, team_alias: str) -> Optional[Tenants]:
        return team_repo.get_team_by_team_alias(team_alias)

    def get_fuzzy_tenants_by_tenant_alias_and_enterprise_id(self, enterprise_id: str, tenant_alias: str) -> Any:
        return team_repo.get_fuzzy_tenants_by_tenant_alias_and_enterprise_id(enterprise_id, tenant_alias)

    def update_by_tenant_id(self, tenant_id: str, data: dict) -> None:
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
        # NOTE: repo update_by_tenant_id returns int (rows updated); calling .update(**d) on an int
        # raises AttributeError at runtime -- latent bug (likely meant update_by_tenant_id(tenant_id, **d)).
        team_repo.update_by_tenant_id(tenant_id).update(**d)  # type: ignore[attr-defined]

    def overview(self, team: Tenants, region_name: str) -> dict:
        resource = self.get_tenant_resource(team, region_name)
        component_nums = service_repo.get_team_service_num_by_team_id(team.tenant_id, region_name)
        app_nums = group_repo.get_tenant_region_groups_count(team.tenant_id, region_name)
        # NOTE: get_tenant_resource returns None only when team is falsy; team is non-None here.
        return {
            "total_memory": resource.get("total_memory", 0),  # type: ignore[union-attr]
            "used_memory": resource.get("used_memory", 0),  # type: ignore[union-attr]
            "total_cpu": resource.get("total_cpu", 0),  # type: ignore[union-attr]
            "used_cpu": resource.get("used_cpu", 0),  # type: ignore[union-attr]
            "app_nums": app_nums,
            "component_nums": component_nums,
        }

    def get_tenant_resource(self, team: Tenants, region_name: str) -> Optional[dict]:
        if team:
            data: Dict[str, Any] = {
                "team_id": team.tenant_id,
                "team_name": team.tenant_name,
                "team_alias": team.tenant_alias,
            }
            source = common_services.get_current_region_used_resource(team, region_name)
            if source:
                cpu_usage: float = 0
                memory_usage: float = 0
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

    def get_tenant_list_by_region(self, eid: str, region_id: str, page: int = 1,
                                  page_size: int = 10) -> Tuple[list, int]:
        teams = team_repo.get_team_by_enterprise_id(eid)
        team_maps = {}
        tenant_ids = []
        if teams:
            for team in teams:
                team_maps[team.tenant_id] = team
                tenant_ids.append(team.tenant_id)
        # NOTE: tenant_ids is a list; list_tenants annotates it as str (elsewhere json.dumps is used) -- latent mismatch.
        res, body = region_api.list_tenants(eid, region_id, tenant_ids)  # type: ignore[arg-type]
        tenant_list = []
        total = 0
        # NOTE: list_tenants returns Optional[dict]; body assumed non-None when "bean" present.
        if body.get("bean"):  # type: ignore[union-attr]
            tenants = body.get("bean").get("list")  # type: ignore[union-attr]
            total = body.get("bean").get("total")  # type: ignore[union-attr]
            if tenants:
                for tenant in tenants:
                    # NOTE: team_maps.get(...) is None if UUID absent; guarded by trailing else ''.
                    tenant_alias = team_maps.get(
                        tenant["UUID"]).tenant_alias if team_maps.get(tenant["UUID"]) else ''  # type: ignore[union-attr]
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

    def set_tenant_resource_limit(self, eid: str, region_id: str, tenant_name: str, limit: Any) -> None:
        try:
            region_api.set_tenant_resource_limit(eid, tenant_name, region_id, body=limit)
        except RegionApiBaseHttpClient.CallApiError as e:
            logger.exception(e)
            raise ServiceHandleException(status_code=500, msg="", msg_show="设置租户限额失败")

    def update(self, tenant_id: str, data: dict) -> None:
        team_repo.update_by_tenant_id(tenant_id, **data)

    @staticmethod
    def check_resource_name(tenant_name: str, region_name: str, rtype: str, name: str) -> Any:
        return region_api.check_resource_name(tenant_name, region_name, rtype, name)

    def list_registry_auths(self, tenant_id: str, region_name: str, user_id: str) -> Any:
        return team_registry_auth_repo.list_by_team_id(tenant_id, region_name, user_id)

    def serialize_registry_auth(self, auth: Any, include_password: bool = False) -> Dict[str, Any]:
        data = auth.to_dict() if hasattr(auth, "to_dict") else dict(auth.__dict__)
        scope = data.get("scope") or self.USER_REGISTRY_SCOPE
        data["scope"] = scope
        data["hub_type"] = self.normalize_registry_hub_type(data.get("hub_type", "Docker"))
        data.pop("access_secret", None)
        if scope == self.ENTERPRISE_REGISTRY_SCOPE and not include_password:
            data.pop("password", None)
        return data

    def list_accessible_registry_auths(self, user: Any) -> List[Any]:
        auths = list(team_registry_auth_repo.list_user_registry_auths(user.user_id))
        enterprise_id = getattr(user, "enterprise_id", "")
        if enterprise_id and self.is_enterprise_registry_enabled(enterprise_id):
            auths.extend(list(team_registry_auth_repo.list_enterprise_registry_auths(enterprise_id)))
        return auths

    def resolve_registry_auth(self, user: Any, secret_id: str) -> Any:
        if not secret_id:
            raise ServiceHandleException(msg="registry auth id is required", msg_show="缺少镜像仓库认证ID", status_code=400)
        auth = team_registry_auth_repo.get_user_registry_auth(secret_id, user.user_id)
        if auth:
            return auth
        enterprise_id = getattr(user, "enterprise_id", "")
        if enterprise_id and self.is_enterprise_registry_enabled(enterprise_id):
            auth = team_registry_auth_repo.get_enterprise_registry_auth(secret_id, enterprise_id)
            if auth:
                return auth
        raise ServiceHandleException(msg="registry auth not found", msg_show="镜像仓库不存在", status_code=404)

    def is_enterprise_registry_enabled(self, enterprise_id: str) -> bool:
        if not enterprise_id:
            return False
        from console.services.config_service import EnterpriseConfigService
        config_service = EnterpriseConfigService(enterprise_id, None)
        config = config_service.get_config_by_key("GLOBAL_IMAGE_REGISTRY")
        if not config:
            config = config_service.add_config(
                key="GLOBAL_IMAGE_REGISTRY",
                default_value=None,
                type="string",
                enable=False,
                desc="全局容器镜像仓库开关")
        return bool(config.enable)

    def normalize_registry_hub_type(self, hub_type: str) -> str:
        return self.LEGACY_REGISTRY_HUB_TYPE_ALIASES.get(hub_type, hub_type)

    def validate_registry_hub_type(self, hub_type: str) -> None:
        if self.normalize_registry_hub_type(hub_type) not in self.SUPPORTED_REGISTRY_HUB_TYPES:
            raise ServiceHandleException(msg="unsupported registry hub type", msg_show="不支持的镜像仓库类型", status_code=400)

    def _registry_v2_headers(self, username: str, password: str) -> Dict[str, str]:
        auth = base64.b64encode("{}:{}".format(username, password).encode()).decode()
        return {"Authorization": "Basic {}".format(auth)}

    def _registry_error_detail(self, response: Any) -> str:
        body = getattr(response, "text", "") or ""
        body = body.replace("\n", " ").replace("\r", " ").strip()
        if len(body) > 300:
            body = body[:300] + "..."
        return "status:{}, body:{}".format(response.status_code, body) if body else "status:{}".format(response.status_code)

    def _parse_registry_bearer_challenge(self, header: Optional[str]) -> Optional[Dict[str, str]]:
        if not header or not header.startswith("Bearer "):
            return None
        challenge = header[len("Bearer "):]
        return dict((key, value) for key, value in re.findall(r'(\w+)="([^"]*)"', challenge))

    def _get_registry_bearer_token(self, challenge: Dict[str, str], username: str, password: str) -> Optional[str]:
        realm = challenge.get("realm")
        if not realm:
            return None
        params = {}
        if challenge.get("service"):
            params["service"] = challenge["service"]
        if challenge.get("scope"):
            params["scope"] = challenge["scope"]
        response = requests.get(
            realm,
            params=params,
            auth=(username, password),
            verify=False,
            timeout=10,
        )
        if response.status_code != 200:
            detail = self._registry_error_detail(response)
            logger.warning("failed to get registry bearer token: %s", detail)
            raise ServiceHandleException(
                msg="failed to get registry bearer token, {}".format(detail),
                msg_show="镜像仓库认证失败({})".format(detail),
                status_code=response.status_code)
        data = response.json()
        return data.get("token") or data.get("access_token")

    def _registry_v2_get(self, url: str, username: str, password: str, headers: Optional[Dict[str, str]] = None) -> Any:
        request_headers = self._registry_v2_headers(username, password)
        if headers:
            request_headers.update(headers)
        response = requests.get(
            url,
            headers=request_headers,
            verify=False,
            timeout=10,
        )
        if response.status_code != 401:
            return response
        challenge = self._parse_registry_bearer_challenge(response.headers.get("WWW-Authenticate"))
        if not challenge:
            return response
        token = self._get_registry_bearer_token(challenge, username, password)
        if not token:
            return response
        bearer_headers = dict(request_headers)
        bearer_headers["Authorization"] = "Bearer {}".format(token)
        return requests.get(
            url,
            headers=bearer_headers,
            verify=False,
            timeout=10,
        )

    def _registry_base_url(self, domain: str) -> str:
        parsed_url = urlparse(domain)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise ServiceHandleException(msg="invalid registry domain", msg_show="镜像仓库地址格式错误", status_code=400)
        return parsed_url.scheme + "://" + parsed_url.netloc

    def _region_registry_auth_payload(self, auth: Any) -> Dict[str, Any]:
        data = auth.to_dict() if hasattr(auth, "to_dict") else dict(auth)
        return {
            "tenant_id": data.get("tenant_id", ""),
            "secret_id": data.get("secret_id", ""),
            "domain": data.get("domain", ""),
            "username": data.get("username", ""),
            "password": data.get("password", ""),
            "region_name": data.get("region_name", ""),
            "hub_type": self.normalize_registry_hub_type(data.get("hub_type", "Docker")),
        }

    def _registry_domain_host(self, domain: str) -> str:
        parsed_url = urlparse(domain)
        host = parsed_url.hostname
        if not host:
            raise ServiceHandleException(msg="invalid registry domain", msg_show="镜像仓库地址格式错误", status_code=400)
        return host.lower()

    def _parse_aliyun_acr_domain(self, domain: str) -> str:
        host = self._registry_domain_host(domain)
        match = self.ALIYUN_ACR_DOMAIN_RE.match(host)
        if not match:
            raise ServiceHandleException(
                msg="invalid aliyun acr domain",
                msg_show="阿里云ACR地址格式错误",
                status_code=400)
        return match.group("region")

    def _parse_tencent_tcr_domain(self, domain: str) -> str:
        host = self._registry_domain_host(domain)
        if not self.TENCENT_TCR_DOMAIN_RE.match(host) and host not in self.TENCENT_TCR_PERSONAL_REGIONS:
            raise ServiceHandleException(
                msg="invalid tencent tcr domain",
                msg_show="腾讯云TCR地址格式错误",
                status_code=400)
        return host

    def _is_tencent_tcr_personal_domain(self, domain: str) -> bool:
        host = self._parse_tencent_tcr_domain(domain)
        return host in self.TENCENT_TCR_PERSONAL_REGIONS

    def _tencent_tcr_personal_region(self, domain: str) -> str:
        host = self._parse_tencent_tcr_domain(domain)
        return self.TENCENT_TCR_PERSONAL_REGIONS[host]

    def _parse_huawei_swr_domain(self, domain: str) -> str:
        host = self._registry_domain_host(domain)
        match = self.HUAWEI_SWR_DOMAIN_RE.match(host)
        if not match:
            raise ServiceHandleException(
                msg="invalid huawei swr domain",
                msg_show="华为云SWR地址格式错误",
                status_code=400)
        return match.group("region")

    def _parse_volcano_cr_domain(self, domain: str) -> Tuple[str, str]:
        host = self._registry_domain_host(domain)
        match = self.VOLCANO_CR_DOMAIN_RE.match(host)
        if not match:
            raise ServiceHandleException(
                msg="invalid volcano cr domain",
                msg_show="火山云CR地址格式错误",
                status_code=400)
        return match.group("registry"), match.group("region")

    def _volcano_cr_api(self, access_key: str, access_secret: str, region: str) -> Any:
        import volcenginesdkcore
        import volcenginesdkcr

        configuration = volcenginesdkcore.Configuration()
        configuration.schema = "https"
        configuration.host = "cr.{}.volcengineapi.com".format(region)
        configuration.ak = (access_key or "").strip()
        configuration.sk = (access_secret or "").strip()
        configuration.region = region.strip()
        return volcenginesdkcr.CRApi(volcenginesdkcore.ApiClient(configuration))

    def _aliyun_acr_client(self, access_key: str, access_secret: str, region: str) -> Any:
        from alibabacloud_cr20160607.client import Client as AcrClient
        from alibabacloud_tea_openapi import models as open_api_models

        config = open_api_models.Config(
            access_key_id=access_key,
            access_key_secret=access_secret,
            endpoint="cr.{}.aliyuncs.com".format(region))
        return AcrClient(config)

    def _tencent_tcr_client(self, access_key: str, access_secret: str, region: str) -> Any:
        from tencentcloud.common import credential
        from tencentcloud.common.profile.client_profile import ClientProfile
        from tencentcloud.common.profile.http_profile import HttpProfile
        from tencentcloud.tcr.v20190924 import tcr_client

        cred = credential.Credential(access_key, access_secret)
        http_profile = HttpProfile(endpoint="tcr.tencentcloudapi.com")
        client_profile = ClientProfile(httpProfile=http_profile)
        return tcr_client.TcrClient(cred, region, client_profile)

    def _huawei_swr_client(self, access_key: str, access_secret: str, region: str) -> Any:
        from huaweicloudsdkcore.auth.credentials import BasicCredentials
        from huaweicloudsdkswr.v2 import SwrClient
        from huaweicloudsdkswr.v2.region.swr_region import SwrRegion

        credentials = BasicCredentials(access_key, access_secret)
        return SwrClient.new_builder() \
            .with_credentials(credentials) \
            .with_region(SwrRegion.value_of(region)) \
            .build()

    def _handle_cloud_registry_exception(self, action: str, provider: str, e: Exception) -> NoReturn:
        logger.warning("failed to %s %s registry: %s", action, provider, e)
        if self._is_cloud_registry_auth_error(e):
            raise ServiceHandleException(
                msg="cloud registry credential unauthorized",
                msg_show="云厂商镜像仓库认证失败，请检查 Access Key、Access Secret 是否正确并确认已授予镜像仓库访问权限",
                status_code=401)
        detail = self._cloud_registry_exception_detail(e)
        raise ServiceHandleException(
            msg="failed to {} {} registry: {}".format(action, provider, detail),
            msg_show="获取镜像仓库信息失败({})".format(detail),
            status_code=500)

    def _is_cloud_registry_auth_error(self, e: Exception) -> bool:
        status = getattr(e, "status", None)
        if status not in (401, 403):
            return False
        content = "{} {} {}".format(
            status,
            getattr(e, "reason", "") or "",
            getattr(e, "body", "") or "",
        ).lower()
        return any(marker in content for marker in self.CLOUD_REGISTRY_AUTH_ERROR_MARKERS)

    def _cloud_registry_exception_detail(self, e: Exception) -> str:
        status = getattr(e, "status", None)
        reason = getattr(e, "reason", "") or ""
        body = getattr(e, "body", "") or ""
        if body:
            match = re.search(r'"Code"\s*:\s*"([^"]+)"', body)
            if match:
                code = match.group(1)
                message_match = re.search(r'"Message"\s*:\s*"([^"]+)"', body)
                message = message_match.group(1) if message_match else ""
                return "{}{}".format(code, ": {}".format(message) if message else "")
        if status:
            return "{}{}".format(status, ": {}".format(reason) if reason else "")
        return str(e)

    def _cloud_attr(self, value: Any, *names: str) -> Any:
        if value is None:
            return None
        if isinstance(value, dict):
            lower_value = {str(k).lower(): v for k, v in value.items()}
            for name in names:
                if name in value:
                    return value.get(name)
                lower_name = name.lower()
                if lower_name in lower_value:
                    return lower_value.get(lower_name)
            return None
        for name in names:
            if hasattr(value, name):
                return getattr(value, name)
            private_name = "_{}".format(name)
            if hasattr(value, private_name):
                return getattr(value, private_name)
        return None

    def _cloud_item_value(self, value: Any, *names: str) -> Any:
        if isinstance(value, str):
            return value
        return self._cloud_attr(value, *names)

    def _cloud_response_body(self, response: Any) -> Any:
        if isinstance(response, dict):
            return response.get("body") or response.get("Body") or response
        return self._cloud_attr(response, "body", "Body") or response

    def _cloud_response_data(self, response: Any) -> Any:
        body = self._cloud_response_body(response)
        return self._cloud_attr(body, "data", "Data") or body

    def _cloud_list(self, data: Any, *keys: str) -> List[Any]:
        if data is None:
            return []
        if isinstance(data, (list, tuple)):
            return list(data)
        for key in keys:
            value = self._cloud_attr(data, key)
            if isinstance(value, (list, tuple)):
                return list(value)
        nested = self._cloud_attr(data, "data", "Data", "body", "Body")
        if nested is not data:
            return self._cloud_list(nested, *keys)
        return []

    def _cloud_total(self, data: Any, default: int = 0) -> int:
        for key in ("total", "Total", "totalCount", "TotalCount", "count", "Count"):
            value = self._cloud_attr(data, key)
            if value is not None:
                try:
                    return int(value)
                except (TypeError, ValueError):
                    return default
        return default

    def _cloud_total_from_content_range(self, content_range: Any, default: int = 0) -> int:
        if not content_range:
            return default
        try:
            return int(str(content_range).rsplit("/", 1)[1])
        except (IndexError, TypeError, ValueError):
            return default

    def _cloud_registry_image(self, name: str, namespace: str, hub_type: str, description: Any = "",
                              is_public: Any = False, pull_count: Any = 0, created_at: Any = "",
                              updated_at: Any = "", status: Any = "active") -> Dict[str, Any]:
        if name and namespace and name.startswith(namespace + "/"):
            name = name.split("/", 1)[1]
        if isinstance(status, bool):
            status = "active" if status else "inactive"
        elif not status:
            status = "active"
        return {
            "name": name,
            "namespace": namespace,
            "description": description or "",
            "is_public": bool(is_public),
            "pull_count": pull_count or 0,
            "star_count": 0,
            "created_at": created_at or "",
            "updated_at": updated_at or "",
            "status": status,
            "registry_type": hub_type,
        }

    def _aliyun_acr_call_api(self, client: Any, action: str, pathname: str,
                             query: Optional[Dict[str, Any]] = None) -> Any:
        from alibabacloud_tea_openapi import models as open_api_models
        from alibabacloud_openapi_util.client import Client as OpenApiUtilClient
        from alibabacloud_tea_util import models as util_models

        request = open_api_models.OpenApiRequest(
            query=OpenApiUtilClient.query(query or {}))
        params = open_api_models.Params(
            action=action,
            version="2016-06-07",
            protocol="HTTPS",
            pathname=pathname,
            method="GET",
            auth_type="AK",
            style="ROA",
            req_body_type="json",
            body_type="json")
        return client.call_api(params, request, util_models.RuntimeOptions())

    def _get_aliyun_acr_namespaces(self, domain: str, access_key: str, access_secret: str) -> List[str]:
        region = self._parse_aliyun_acr_domain(domain)
        client = self._aliyun_acr_client(access_key, access_secret, region)
        response = self._aliyun_acr_call_api(client, "GetNamespaceList", "/namespace")
        data = self._cloud_response_data(response)
        items = self._cloud_list(data, "namespaces", "Namespaces", "namespaceList", "NamespaceList")
        return [
            self._cloud_item_value(item, "namespace", "Namespace", "namespaceName", "NamespaceName", "name", "Name")
            for item in items
            if self._cloud_item_value(item, "namespace", "Namespace", "namespaceName", "NamespaceName", "name", "Name")
        ]

    def _get_aliyun_acr_images(self, domain: str, access_key: str, access_secret: str, namespace: str,
                               page: int = 1, page_size: int = 10,
                               search_key: Optional[str] = None) -> Dict[str, Any]:
        region = self._parse_aliyun_acr_domain(domain)
        client = self._aliyun_acr_client(access_key, access_secret, region)

        def list_repositories(request_page: int, request_page_size: int) -> Tuple[List[Any], int]:
            response = self._aliyun_acr_call_api(
                client,
                "GetRepoListByNamespace",
                "/repos/{}".format(quote(namespace, safe="")),
                {"Page": request_page, "PageSize": request_page_size})
            data = self._cloud_response_data(response)
            repositories = self._cloud_list(data, "repos", "Repos", "repositories", "Repositories", "repoList", "RepoList")
            return repositories, self._cloud_total(data, len(repositories))

        if search_key:
            repositories = []
            request_page = 1
            request_page_size = 100
            while True:
                page_repositories, total_count = list_repositories(request_page, request_page_size)
                repositories.extend(page_repositories)
                if not page_repositories or len(repositories) >= total_count:
                    break
                request_page += 1
        else:
            repositories, total = list_repositories(page, page_size)

        images = []
        search_lower = search_key.lower() if search_key else ""
        for repo in repositories:
            repo_name = self._cloud_item_value(repo, "repoName", "RepoName", "name", "Name")
            if search_lower and search_lower not in repo_name.lower():
                continue
            repo_type = self._cloud_attr(repo, "repoType", "RepoType")
            is_public = self._cloud_attr(repo, "isPublic", "IsPublic")
            if is_public is None:
                is_public = str(repo_type).lower() == "public"
            images.append(self._cloud_registry_image(
                repo_name,
                self._cloud_attr(repo, "repoNamespace", "RepoNamespace", "namespace", "Namespace") or namespace,
                "AliyunACR",
                description=self._cloud_attr(repo, "summary", "Summary", "description", "Description"),
                is_public=is_public,
                created_at=self._cloud_attr(repo, "gmtCreate", "GmtCreate", "creationTime", "CreationTime"),
                updated_at=self._cloud_attr(repo, "gmtModified", "GmtModified", "updateTime", "UpdateTime")))
        if search_key:
            total = len(images)
            start = (page - 1) * page_size
            end = start + page_size
            images = images[start:end]
        return {"images": images, "total": total, "page": page, "page_size": page_size}

    def _tencent_domain_host(self, value: str) -> str:
        parsed = urlparse(value if "://" in value else "//{}".format(value))
        return (parsed.hostname or value or "").lower()

    def _tencent_registry_matches_domain(self, registry: Any, host: str) -> bool:
        registry_name = self._cloud_attr(registry, "RegistryName")
        registry_id = self._cloud_attr(registry, "RegistryId")
        prefix = host.split(".", 1)[0]
        domains = [
            self._cloud_attr(registry, "PublicDomain"),
            self._cloud_attr(registry, "InternalEndpoint"),
        ]
        normalized_domains = [self._tencent_domain_host(domain) for domain in domains if domain]
        return host in normalized_domains or prefix in (registry_name, registry_id)

    def _resolve_tencent_tcr_registry(self, domain: str, access_key: str, access_secret: str) -> Tuple[str, str]:
        from tencentcloud.tcr.v20190924 import models as tcr_models

        host = self._parse_tencent_tcr_domain(domain)
        discovery_client = self._tencent_tcr_client(access_key, access_secret, self.TENCENT_TCR_DISCOVERY_REGION)
        offset = 0
        limit = 100
        while True:
            request = tcr_models.DescribeInstancesRequest()
            request.AllRegion = True
            request.Offset = offset
            request.Limit = limit
            response = discovery_client.DescribeInstances(request)
            registries = self._cloud_list(response, "Registries")
            for registry in registries:
                if self._tencent_registry_matches_domain(registry, host):
                    registry_id = self._cloud_attr(registry, "RegistryId")
                    region = self._cloud_attr(registry, "RegionName") or self.TENCENT_TCR_DISCOVERY_REGION
                    return registry_id, region
            total = self._cloud_total(response, len(registries))
            if not registries or offset + limit >= total:
                break
            offset += limit
        raise ServiceHandleException(
            msg="tencent tcr registry not found for domain {}".format(host),
            msg_show="腾讯云TCR实例未找到，请确认仓库地址与Access Key权限",
            status_code=404)

    def _get_tencent_tcr_namespaces(self, domain: str, access_key: str, access_secret: str) -> List[str]:
        from tencentcloud.tcr.v20190924 import models as tcr_models

        if self._is_tencent_tcr_personal_domain(domain):
            return self._get_tencent_tcr_personal_namespaces(domain, access_key, access_secret)
        registry_id, region = self._resolve_tencent_tcr_registry(domain, access_key, access_secret)
        client = self._tencent_tcr_client(access_key, access_secret, region)
        request = tcr_models.DescribeNamespacesRequest()
        request.RegistryId = registry_id
        request.Offset = 0
        request.Limit = 100
        request.All = True
        response = client.DescribeNamespaces(request)
        items = self._cloud_list(response, "NamespaceList")
        return [
            self._cloud_item_value(item, "Name", "Namespace", "name", "namespace")
            for item in items
            if self._cloud_item_value(item, "Name", "Namespace", "name", "namespace")
        ]

    def _get_tencent_tcr_personal_namespaces(self, domain: str, access_key: str, access_secret: str) -> List[str]:
        from tencentcloud.tcr.v20190924 import models as tcr_models

        client = self._tencent_tcr_client(access_key, access_secret, self._tencent_tcr_personal_region(domain))
        request = tcr_models.DescribeNamespacePersonalRequest()
        request.Namespace = ""
        request.Offset = 0
        request.Limit = 100
        response = client.DescribeNamespacePersonal(request)
        items = self._cloud_list(response, "NamespaceInfo")
        return [
            self._cloud_item_value(item, "Namespace", "Name", "namespace", "name")
            for item in items
            if self._cloud_item_value(item, "Namespace", "Name", "namespace", "name")
        ]

    def _get_tencent_tcr_images(self, domain: str, access_key: str, access_secret: str, namespace: str,
                                page: int = 1, page_size: int = 10,
                                search_key: Optional[str] = None) -> Dict[str, Any]:
        from tencentcloud.tcr.v20190924 import models as tcr_models

        if self._is_tencent_tcr_personal_domain(domain):
            return self._get_tencent_tcr_personal_images(
                domain, access_key, access_secret, namespace, page, page_size, search_key)
        registry_id, region = self._resolve_tencent_tcr_registry(domain, access_key, access_secret)
        client = self._tencent_tcr_client(access_key, access_secret, region)
        request = tcr_models.DescribeRepositoriesRequest()
        request.RegistryId = registry_id
        request.NamespaceName = namespace
        request.Offset = (page - 1) * page_size
        request.Limit = page_size
        if search_key:
            request.RepositoryName = search_key
        response = client.DescribeRepositories(request)
        repositories = self._cloud_list(response, "RepositoryList")
        images = []
        for repo in repositories:
            repo_name = self._cloud_item_value(repo, "Name", "name")
            if search_key and search_key.lower() not in repo_name.lower():
                continue
            images.append(self._cloud_registry_image(
                repo_name,
                self._cloud_attr(repo, "Namespace", "namespace") or namespace,
                "TencentTCR",
                description=self._cloud_attr(repo, "Description", "BriefDescription", "description", "briefDescription"),
                is_public=self._cloud_attr(repo, "Public", "public"),
                created_at=self._cloud_attr(repo, "CreationTime", "creationTime"),
                updated_at=self._cloud_attr(repo, "UpdateTime", "updateTime")))
        total = self._cloud_total(response, len(images))
        if search_key:
            total = len(images)
        return {"images": images, "total": total, "page": page, "page_size": page_size}

    def _get_tencent_tcr_personal_images(self, domain: str, access_key: str, access_secret: str, namespace: str,
                                         page: int = 1, page_size: int = 10,
                                         search_key: Optional[str] = None) -> Dict[str, Any]:
        from tencentcloud.tcr.v20190924 import models as tcr_models

        client = self._tencent_tcr_client(access_key, access_secret, self._tencent_tcr_personal_region(domain))
        request = tcr_models.DescribeRepositoryFilterPersonalRequest()
        request.Namespace = namespace
        request.Offset = (page - 1) * page_size
        request.Limit = page_size
        if search_key:
            request.RepoName = search_key
        response = client.DescribeRepositoryFilterPersonal(request)
        repositories = self._cloud_list(response, "RepoInfo")
        images = []
        for repo in repositories:
            repo_name = self._cloud_item_value(repo, "RepoName", "Name", "name")
            if search_key and search_key.lower() not in repo_name.lower():
                continue
            is_public = self._cloud_attr(repo, "Public", "public")
            if isinstance(is_public, int):
                is_public = bool(is_public)
            images.append(self._cloud_registry_image(
                repo_name,
                namespace,
                "TencentTCR",
                description=self._cloud_attr(repo, "Description", "BriefDescription", "description", "briefDescription"),
                is_public=is_public,
                pull_count=self._cloud_attr(repo, "PullCount", "pullCount") or 0,
                created_at=self._cloud_attr(repo, "CreationTime", "creationTime"),
                updated_at=self._cloud_attr(repo, "UpdateTime", "updateTime")))
        total = self._cloud_total(response, len(images))
        return {"images": images, "total": total, "page": page, "page_size": page_size}

    def _get_huawei_swr_namespaces(self, domain: str, access_key: str, access_secret: str) -> List[str]:
        from huaweicloudsdkswr.v2 import model as swr_models

        region = self._parse_huawei_swr_domain(domain)
        client = self._huawei_swr_client(access_key, access_secret, region)
        response = client.list_namespaces(swr_models.ListNamespacesRequest())
        items = self._cloud_list(response, "namespaces", "Namespaces")
        return [
            self._cloud_item_value(item, "name", "Name", "namespace", "Namespace")
            for item in items
            if self._cloud_item_value(item, "name", "Name", "namespace", "Namespace")
        ]

    def _get_huawei_swr_images(self, domain: str, access_key: str, access_secret: str, namespace: str,
                               page: int = 1, page_size: int = 10,
                               search_key: Optional[str] = None) -> Dict[str, Any]:
        from huaweicloudsdkswr.v2 import model as swr_models

        region = self._parse_huawei_swr_domain(domain)
        client = self._huawei_swr_client(access_key, access_secret, region)
        request = swr_models.ListReposDetailsRequest(
            namespace=namespace,
            name=search_key,
        )
        request.limit = page_size
        request.offset = (page - 1) * page_size
        response = client.list_repos_details(request)
        repositories = self._cloud_list(response, "body", "Body")
        images = []
        for repo in repositories:
            repo_name = self._cloud_item_value(repo, "name", "Name")
            if search_key and search_key.lower() not in repo_name.lower():
                continue
            images.append(self._cloud_registry_image(
                repo_name,
                self._cloud_attr(repo, "namespace", "Namespace") or namespace,
                "HuaweiSWR",
                description=self._cloud_attr(repo, "description", "Description"),
                is_public=self._cloud_attr(repo, "is_public", "isPublic", "IsPublic"),
                pull_count=self._cloud_attr(repo, "num_download", "numDownload", "NumDownload"),
                created_at=self._cloud_attr(repo, "created_at", "createdAt", "CreatedAt"),
                updated_at=self._cloud_attr(repo, "updated_at", "updatedAt", "UpdatedAt"),
                status=self._cloud_attr(repo, "status", "Status")))
        total = self._cloud_total_from_content_range(
            self._cloud_attr(response, "content_range", "ContentRange"),
            len(images))
        if search_key:
            total = len(images)
        return {"images": images, "total": total, "page": page, "page_size": page_size}

    def _get_volcano_cr_namespaces(self, domain: str, access_key: str, access_secret: str) -> List[str]:
        import volcenginesdkcr

        registry, region = self._parse_volcano_cr_domain(domain)
        api = self._volcano_cr_api(access_key, access_secret, region)
        namespaces = []
        page = 1
        page_size = 100
        while True:
            request = volcenginesdkcr.ListNamespacesRequest(
                registry=registry,
                page_number=page,
                page_size=page_size)
            response = api.list_namespaces(request)
            items = getattr(response, "items", None) or []
            namespaces.extend([item.name for item in items if getattr(item, "name", None)])
            total = getattr(response, "total_count", 0) or 0
            if not items or page * page_size >= total:
                break
            page += 1
        return namespaces

    def _get_volcano_cr_images(self, domain: str, access_key: str, access_secret: str, namespace: str,
                               page: int = 1, page_size: int = 10,
                               search_key: Optional[str] = None) -> Dict[str, Any]:
        import volcenginesdkcr

        registry, region = self._parse_volcano_cr_domain(domain)
        api = self._volcano_cr_api(access_key, access_secret, region)
        request = volcenginesdkcr.ListRepositoriesRequest(
            filter=volcenginesdkcr.FilterForListRepositoriesInput(namespaces=[namespace]),
            registry=registry,
            page_number=page,
            page_size=page_size)
        response = api.list_repositories(request)
        repositories = getattr(response, "items", None) or []
        images = []
        for repo in repositories:
            repo_name = getattr(repo, "name", "")
            if search_key and search_key.lower() not in repo_name.lower():
                continue
            images.append(self._cloud_registry_image(
                repo_name,
                getattr(repo, "namespace", namespace),
                "VolcanoCR",
                description=getattr(repo, "description", "") or "",
                is_public=getattr(repo, "access_level", "") == "Public",
                created_at=getattr(repo, "create_time", "") or "",
                updated_at=getattr(repo, "update_time", "") or ""))
        total = getattr(response, "total_count", len(images)) or len(images)
        if search_key:
            total = len(images)
        return {"images": images, "total": total, "page": page, "page_size": page_size}

    def _get_volcano_cr_tags(self, domain: str, access_key: str, access_secret: str, namespace: str, name: str,
                             page: int = 1, page_size: int = 10,
                             search_key: Optional[str] = None) -> Dict[str, Any]:
        import volcenginesdkcr

        registry, region = self._parse_volcano_cr_domain(domain)
        api = self._volcano_cr_api(access_key, access_secret, region)

        def unique_join(values: List[Any]) -> str:
            result = []
            for value in values:
                if value and value not in result:
                    result.append(value)
            return ",".join(result)

        def list_tags(request_page: int, request_page_size: int) -> Tuple[List[Dict[str, Any]], int]:
            request = volcenginesdkcr.ListTagsRequest(
                namespace=namespace,
                page_number=request_page,
                page_size=request_page_size,
                registry=registry,
                repository=name)
            response = api.list_tags(request)
            items = getattr(response, "items", None) or []
            tags = []
            for item in items:
                tag_name = getattr(item, "name", "") or ""
                image_attributes = getattr(item, "image_attributes", None) or []
                item_size = getattr(item, "size", 0) or 0
                item_digest = getattr(item, "digest", "") or ""
                if image_attributes:
                    item_size = item_size or sum([getattr(attr, "size", 0) or 0 for attr in image_attributes])
                    item_digest = item_digest or getattr(image_attributes[0], "digest", "") or ""
                tags.append({
                    "name": tag_name,
                    "size": item_size,
                    "digest": item_digest,
                    "created_at": getattr(item, "push_time", "") or "",
                    "updated_at": getattr(item, "push_time", "") or "",
                    "os": unique_join([getattr(attr, "os", "") for attr in image_attributes]),
                    "architecture": unique_join([getattr(attr, "architecture", "") for attr in image_attributes]),
                    "status": "active",
                })
            return tags, getattr(response, "total_count", len(tags)) or len(tags)

        if not search_key:
            tags, total = list_tags(page, page_size)
            return {"tags": tags, "total": total, "page": page, "page_size": page_size}

        all_tags = []
        current_page = 1
        fetch_page_size = 100
        while True:
            tags, total_count = list_tags(current_page, fetch_page_size)
            all_tags.extend(tags)
            if not tags or current_page * fetch_page_size >= total_count:
                break
            current_page += 1
        search_lower = search_key.lower()
        filtered_tags = [tag for tag in all_tags if search_lower in tag["name"].lower()]
        total = len(filtered_tags)
        start = (page - 1) * page_size
        end = start + page_size
        tags = filtered_tags[start:end]
        return {"tags": tags, "total": total, "page": page, "page_size": page_size}

    def get_cloud_registry_namespaces(self, domain: str, access_key: str, access_secret: str, hub_type: str) -> List[str]:
        hub_type = self.normalize_registry_hub_type(hub_type)
        handlers = {
            "AliyunACR": self._get_aliyun_acr_namespaces,
            "TencentTCR": self._get_tencent_tcr_namespaces,
            "HuaweiSWR": self._get_huawei_swr_namespaces,
            "VolcanoCR": self._get_volcano_cr_namespaces,
        }
        handler = handlers.get(hub_type)
        if not handler:
            raise ServiceHandleException(
                msg="cloud registry api not supported for {}".format(hub_type),
                msg_show="当前云厂商镜像仓库暂未支持自动获取命名空间",
                status_code=400)
        try:
            return handler(domain, access_key, access_secret)
        except ServiceHandleException:
            raise
        except Exception as e:
            self._handle_cloud_registry_exception("list namespaces from", hub_type, e)

    def get_cloud_registry_images(self, domain: str, access_key: str, access_secret: str, hub_type: str,
                                  namespace: str, page: int = 1, page_size: int = 10,
                                  search_key: Optional[str] = None) -> Dict[str, Any]:
        hub_type = self.normalize_registry_hub_type(hub_type)
        handlers = {
            "AliyunACR": self._get_aliyun_acr_images,
            "TencentTCR": self._get_tencent_tcr_images,
            "HuaweiSWR": self._get_huawei_swr_images,
            "VolcanoCR": self._get_volcano_cr_images,
        }
        handler = handlers.get(hub_type)
        if not handler:
            raise ServiceHandleException(
                msg="cloud registry api not supported for {}".format(hub_type),
                msg_show="当前云厂商镜像仓库暂未支持自动获取镜像列表",
                status_code=400)
        try:
            return handler(domain, access_key, access_secret, namespace, page, page_size, search_key)
        except ServiceHandleException:
            raise
        except Exception as e:
            self._handle_cloud_registry_exception("list images from", hub_type, e)

    def get_cloud_registry_tags(self, domain: str, username: str, password: str, access_key: str, access_secret: str,
                                hub_type: str, namespace: str, name: str, page: int = 1, page_size: int = 10,
                                search_key: Optional[str] = None) -> Dict[str, Any]:
        hub_type = self.normalize_registry_hub_type(hub_type)
        handlers = {
            "VolcanoCR": self._get_volcano_cr_tags,
        }
        handler = handlers.get(hub_type)
        if handler:
            try:
                return handler(domain, access_key, access_secret, namespace, name, page, page_size, search_key)
            except ServiceHandleException:
                raise
            except Exception as e:
                self._handle_cloud_registry_exception("list tags from", hub_type, e)
        return self.get_registry_tags(domain, username, password, hub_type, namespace, name, page, page_size, search_key)

    def check_registry_connection(self, domain: str, username: str, password: str, hub_type: str,
                                  access_key: str = "", access_secret: str = "") -> bool:
        self.validate_registry_hub_type(hub_type)
        hub_type = self.normalize_registry_hub_type(hub_type)
        if hub_type in self.CLOUD_REGISTRY_HUB_TYPES:
            self.get_cloud_registry_namespaces(domain, access_key, access_secret, hub_type)
            return True
        base_url = self._registry_base_url(domain)
        try:
            response = self._registry_v2_get("{}/v2/".format(base_url), username, password)
        except requests.exceptions.RequestException as e:
            logger.exception(e)
            raise ServiceHandleException(
                msg="failed to connect registry: {}".format(e), msg_show="连接镜像仓库失败", status_code=500)
        if response.status_code != 200:
            detail = self._registry_error_detail(response)
            logger.warning("failed to connect registry %s, hub_type=%s, %s", base_url, hub_type, detail)
            raise ServiceHandleException(
                msg="failed to connect registry, {}".format(detail),
                msg_show="镜像仓库连接测试失败({})".format(detail),
                status_code=response.status_code)
        return True

    def _get_registry_v2_namespaces(self, base_url: str, username: str, password: str) -> List[str]:
        response = self._registry_v2_get("{}/v2/_catalog".format(base_url), username, password)
        if response.status_code != 200:
            detail = self._registry_error_detail(response)
            logger.warning("failed to get registry namespaces %s, %s", base_url, detail)
            raise ServiceHandleException(
                msg="failed to get registry namespaces, {}".format(detail),
                msg_show="获取镜像仓库命名空间失败({})".format(detail),
                status_code=response.status_code)
        repositories = response.json().get("repositories", [])
        namespaces = set()
        for repo in repositories:
            if "/" in repo:
                namespaces.add(repo.split("/", 1)[0])
            else:
                namespaces.add("library")
        return list(namespaces) or ["library"]

    def _get_registry_v2_images(self, base_url: str, username: str, password: str, hub_type: str, namespace: str,
                                page: int = 1, page_size: int = 10, search_key: Optional[str] = None) -> Dict[str, Any]:
        response = self._registry_v2_get("{}/v2/_catalog".format(base_url), username, password)
        if response.status_code != 200:
            detail = self._registry_error_detail(response)
            logger.warning("failed to get registry images %s, hub_type=%s, %s", base_url, hub_type, detail)
            raise ServiceHandleException(
                msg="failed to get registry images, {}".format(detail),
                msg_show="获取镜像列表失败({})".format(detail),
                status_code=response.status_code)
        repositories = response.json().get("repositories", [])
        if namespace == "library":
            filtered_repos = [repo for repo in repositories if "/" not in repo]
        else:
            filtered_repos = [repo.split("/", 1)[1] for repo in repositories if repo.startswith(namespace + "/")]
        if search_key:
            filtered_repos = [repo for repo in filtered_repos if search_key.lower() in repo.lower()]
        total = len(filtered_repos)
        start = (page - 1) * page_size
        end = start + page_size
        images = [{
            "name": repo,
            "namespace": namespace,
            "description": "",
            "is_public": True,
            "pull_count": 0,
            "star_count": 0,
            "created_at": "",
            "updated_at": "",
            "status": "active",
            "registry_type": hub_type,
        } for repo in filtered_repos[start:end]]
        return {"images": images, "total": total, "page": page, "page_size": page_size}

    def _registry_tag_info_to_payload(self, tag: str, tag_info: Dict[str, Any]) -> Dict[str, Any]:
        created_at = tag_info.get("created_at") or tag_info.get("updated_at") or ""
        updated_at = tag_info.get("updated_at") or created_at
        return {
            "name": tag,
            "size": tag_info.get("size") or 0,
            "digest": tag_info.get("digest") or "",
            "created_at": created_at,
            "updated_at": updated_at,
            "os": tag_info.get("os") or "",
            "architecture": tag_info.get("architecture") or "",
            "status": tag_info.get("status") or "active",
        }

    def _get_registry_v2_tags(self, base_url: str, username: str, password: str, namespace: str, name: str,
                              page: int = 1, page_size: int = 10, search_key: Optional[str] = None) -> Dict[str, Any]:
        repo_name = name if namespace == "library" else "{}/{}".format(namespace, name)
        response = self._registry_v2_get("{}/v2/{}/tags/list".format(base_url, repo_name), username, password)
        if response.status_code != 200:
            detail = self._registry_error_detail(response)
            logger.warning("failed to get registry tags %s/%s, %s", base_url, repo_name, detail)
            raise ServiceHandleException(
                msg="failed to get registry tags, {}".format(detail),
                msg_show="获取镜像标签失败({})".format(detail),
                status_code=response.status_code)
        all_tags = response.json().get("tags", []) or []
        if search_key:
            all_tags = [tag for tag in all_tags if search_key.lower() in tag.lower()]
        total = len(all_tags)
        start = (page - 1) * page_size
        end = start + page_size
        tags = []
        for tag in all_tags[start:end]:
            tag_info = self._get_registry_tag_info(base_url, repo_name, tag, username, password)
            tags.append(self._registry_tag_info_to_payload(tag, tag_info))
        return {"tags": tags, "total": total, "page": page, "page_size": page_size}

    @transaction.atomic()
    def create_registry_auth(self, tenant: Tenants, region_name: str, domain: str, username: str, password: str,
                             hub_type: str = "Docker", user_id: int = 0) -> None:
        hub_type = self.normalize_registry_hub_type(hub_type)
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
            "hub_type": hub_type,
            "user_id": user_id,
            "scope": self.USER_REGISTRY_SCOPE,
            "enterprise_id": "",
        }
        team_registry_auth_repo.create_team_registry_auth(**params)
        region_api.create_registry_auth(tenant.tenant_name, region_name, self._region_registry_auth_payload(params))

    @transaction.atomic()
    def update_registry_auth(self, tenant: Tenants, region_name: str, secret_id: str, data: dict) -> None:
        auth = team_registry_auth_repo.get_by_secret_id(secret_id)
        if not auth:
            return
        if "hub_type" in data:
            data["hub_type"] = self.normalize_registry_hub_type(data["hub_type"])
        team_registry_auth_repo.update_team_registry_auth(tenant.tenant_id, region_name, secret_id, **data)
        region_api.update_registry_auth(tenant.tenant_name, region_name, self._region_registry_auth_payload(auth[0]))

    @transaction.atomic()
    def delete_registry_auth(self, tenant: Tenants, region_name: str, secret_id: str, user_id: str) -> None:
        team_registry_auth_repo.delete_team_registry_auth(tenant.tenant_id, region_name, secret_id, user_id)
        region_api.delete_registry_auth(tenant.tenant_name, region_name, {
            "secret_id": secret_id,
            "tenant_id": tenant.tenant_id
        })

    def get_registry_namespaces(self, domain: str, username: str, password: str, hub_type: str) -> Any:
        self.validate_registry_hub_type(hub_type)
        hub_type = self.normalize_registry_hub_type(hub_type)
        try:
            base_url = self._registry_base_url(domain)
            parsed_url = urlparse(domain)
            
            if hub_type == "Harbor":
                # Harbor API
                current_page = 1
                fetch_page_size = 100
                namespaces = []

                while True:
                    api_url = "{}/api/v2.0/projects?page={}&page_size={}".format(
                        base_url, current_page, fetch_page_size)
                    response = requests.get(
                        api_url,
                        auth=(username, password),
                        verify=False,
                        timeout=10
                    )
                    if response.status_code != 200:
                        break

                    projects = response.json()
                    namespaces.extend([project["name"] for project in projects])
                    total_count = response.headers.get('X-Total-Count')

                    if not projects:
                        return namespaces
                    if total_count and current_page * fetch_page_size >= int(total_count):
                        return namespaces
                    if not total_count and len(projects) < fetch_page_size:
                        return namespaces
                    current_page += 1
                    
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
                    response = self._registry_v2_get("{}/v2/_catalog".format(base_url), username, password)
                    if response.status_code == 200:
                        repositories = response.json().get("repositories", [])
                        # 提取命名空间（取第一个/之前的部分作为命名空间）
                        namespace_set = set()
                        for repo in repositories:
                            if "/" in repo:
                                namespace = repo.split("/")[0]
                                namespace_set.add(namespace)
                            else:
                                namespace_set.add("library")
                        return list(namespace_set) or ["library"]
                    
            elif hub_type in self.CLOUD_REGISTRY_HUB_TYPES:
                return self._get_registry_v2_namespaces(base_url, username, password)

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

    def _get_dockerhub_token(self, username: str, password: str) -> Any:
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

    def get_registry_images(self, domain: str, username: str, password: str, hub_type: str, namespace: str, page: int = 1,
                            page_size: int = 10, search_key: Optional[str] = None) -> dict:
        """获取指定命名空间下的镜像列表,支持分页和搜索
        
        Args:
            search_key (str): 搜索关键字,用于过滤镜像名称
            
        Returns:
            dict: 包含镜像详细信息的字典
        """
        self.validate_registry_hub_type(hub_type)
        hub_type = self.normalize_registry_hub_type(hub_type)
        try:
            base_url = self._registry_base_url(domain)
            if hub_type in self.CLOUD_REGISTRY_HUB_TYPES:
                return self._get_registry_v2_images(base_url, username, password, hub_type, namespace, page, page_size, search_key)
            parsed_url = urlparse(domain)
            
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
                        # 使用 split("/", 1)[1] 保留完整的相对路径（如 zq/zq-ng）
                        repo_name = repo["name"].split("/", 1)[1] if "/" in repo["name"] else repo["name"]
                        images.append({
                            "name": repo_name,
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
                    response = self._registry_v2_get("{}/v2/_catalog".format(base_url), username, password)
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
                            tags_response = self._registry_v2_get(tags_url, username, password)
                            updated_at = ""
                            
                            if tags_response.status_code == 200:
                                tags = tags_response.json().get("tags", [])
                                if tags:
                                    # 获取最新标签的信息
                                    repo_name = repo if namespace == "library" else f"{namespace}/{repo}"
                                    tag_info = self._get_registry_tag_info(base_url, repo_name, tags[0], username, password)
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

    def get_registry_tags(self, domain: str, username: str, password: str, hub_type: str, namespace: str, name: str,
                           page: int = 1, page_size: int = 10, search_key: Optional[str] = None) -> dict:
        """获取指定镜像的标签列表,支持分页和搜索
        
        Args:
            search_key (str): 标签名称搜索关键字
            
        Returns:
            dict: 包含标签详细信息的字典
        """
        self.validate_registry_hub_type(hub_type)
        hub_type = self.normalize_registry_hub_type(hub_type)
        try:
            base_url = self._registry_base_url(domain)
            if hub_type in self.CLOUD_REGISTRY_HUB_TYPES:
                return self._get_registry_v2_tags(base_url, username, password, namespace, name, page, page_size, search_key)
            parsed_url = urlparse(domain)
            
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
                    response = self._registry_v2_get("{}/v2/{}/tags/list".format(base_url, repo_name), username, password)
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
                            tag_info = self._get_registry_tag_info(base_url, repo_name, tag_name, username, password)
                            
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
                # 先获取所有 artifacts，然后在客户端进行 tag 过滤和分页
                auth = base64.b64encode(f"{username}:{password}".encode()).decode()
                headers = {"Authorization": f"Basic {auth}"}

                all_tags = []
                current_page = 1
                fetch_page_size = 100  # 每次获取较多数据以减少请求次数

                # 对 name 进行双重 URL 编码，处理包含 / 的嵌套路径（如 zq/zq-ng）
                # Harbor API 需要双重编码：zq/zq-ng -> zq%2Fzq-ng -> zq%252Fzq-ng
                encoded_name = quote(quote(name, safe=''), safe='')

                first_request = True
                while True:
                    api_url = "{}/api/v2.0/projects/{}/repositories/{}/artifacts?page={}&page_size={}&with_tag=true&with_label=false".format(
                        base_url, namespace, encoded_name, current_page, fetch_page_size)

                    logger.debug("Harbor API request: {}".format(api_url))
                    response = requests.get(
                        api_url,
                        headers=headers,
                        verify=False,
                        timeout=10
                    )

                    if response.status_code != 200:
                        # 第一次请求就失败，说明仓库或镜像不存在
                        if first_request:
                            logger.warning("Harbor API failed: status={}, url={}, response={}".format(
                                response.status_code, api_url, response.text[:500] if response.text else ""))
                            raise ServiceHandleException(
                                msg="failed to get registry tags, status:{}".format(response.status_code),
                                msg_show="获取镜像标签失败，请检查镜像是否存在",
                                status_code=response.status_code)
                        break
                    first_request = False

                    artifacts = response.json()
                    if not artifacts:
                        break

                    for artifact in artifacts:
                        artifact_tags = artifact.get('tags') or []
                        extra_attrs = artifact.get('extra_attrs', {})
                        size = artifact.get('size', 0)
                        architecture = extra_attrs.get('architecture', '')
                        os_name = extra_attrs.get('os', '')

                        for tag in artifact_tags:
                            tag_name = tag.get('name', '')
                            all_tags.append({
                                "name": tag_name,
                                "size": size,
                                "digest": artifact.get('digest', ''),
                                "created_at": artifact.get('push_time', ''),
                                "updated_at": artifact.get('push_time', ''),
                                "os": os_name,
                                "architecture": architecture,
                                "status": "active"
                            })

                    # 检查是否还有更多数据
                    total_artifacts = int(response.headers.get('X-Total-Count', 0))
                    if current_page * fetch_page_size >= total_artifacts:
                        break
                    current_page += 1

                # 搜索过滤
                if search_key:
                    search_lower = search_key.lower()
                    all_tags = [t for t in all_tags if search_lower in t['name'].lower()]

                # 计算分页
                total = len(all_tags)
                start = (page - 1) * page_size
                end = start + page_size
                paginated_tags = all_tags[start:end]

                return {
                    "tags": paginated_tags,
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

    def _get_registry_tag_info(self, base_url: str, repo_name: str, tag_name: str,
                               username: str, password: str) -> dict:
        """获取 Docker Registry 标签的详细信息
        
        Args:
            base_url: 仓库基础URL
            repo_name: 仓库名称
            tag_name: 标签名称
            username: 仓库用户名
            password: 仓库密码
            
        Returns:
            dict: 包含标签详细信息的字典
        """
        try:
            manifest_url = "{}/v2/{}/manifests/{}".format(base_url, repo_name, tag_name)
            manifest_response = self._registry_v2_get(
                manifest_url,
                username,
                password,
                {"Accept": ", ".join(self.REGISTRY_MANIFEST_ACCEPT_TYPES)}
            )
            
            if manifest_response.status_code == 200:
                manifest = manifest_response.json()
                manifest_digest = manifest_response.headers.get("Docker-Content-Digest", "")
                config_digest = manifest.get("config", {}).get("digest")
                manifests = manifest.get("manifests", []) or []
                if not config_digest and manifests:
                    platform = manifests[0].get("platform", {}) or {}
                    return {
                        "updated_at": "",
                        "created_at": "",
                        "digest": manifest_digest or manifests[0].get("digest", ""),
                        "os": platform.get("os", ""),
                        "architecture": platform.get("architecture", ""),
                        "size": sum(item.get("size", 0) or 0 for item in manifests),
                    }

                compressed_size = sum(layer.get("size", 0) or 0 for layer in manifest.get("layers", []))

                if config_digest:
                    config_url = "{}/v2/{}/blobs/{}".format(base_url, repo_name, config_digest)
                    config_response = self._registry_v2_get(config_url, username, password)
                    if config_response.status_code == 200:
                        config = config_response.json()
                        return {
                            "updated_at": config.get("created", ""),
                            "created_at": config.get("created", ""),
                            "digest": manifest_digest or config_digest,
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

    def get_full_image_name(self, domain: str, hub_type: str, namespace: str, name: str, tag: str) -> str:
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
                    # NOTE: format string has 3 placeholders but only 2 args -> IndexError at runtime; latent bug.
                    return "{}/{}:{}".format(name, tag)  # type: ignore[str-format]
                return "{}/{}:{}".format(namespace, name, tag)
            
            # 其他类型仓库
            return "{}/{}/{}:{}".format(registry, namespace, name, tag)
            
        except Exception as e:
            logger.exception(e)
            raise ServiceHandleException(
                msg="failed to generate full image name: {}".format(e),
                msg_show="生成完整镜像地址失败",
                status_code=500)

    def get_user_team_details(self, user: Users) -> list:
        """
        获取用户创建的团队详情
        """
        # 获取所有启用状态的集群
        regions = RegionConfig.objects.filter(status='1')
        
        # 获取用户创建的团队
        teams = Tenants.objects.filter(creater=user.user_id)
        
        # 获取团队与集群的关联关系
        team_region_map: Dict[Any, List[Any]] = {}
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
        group_service_map: Dict[Any, List[Any]] = {}
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
        team_apps_map: Dict[Any, List[Any]] = {}
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

    @staticmethod
    def count_teams(enterprise_id: str) -> int:
        return Tenants.objects.filter(enterprise_id=enterprise_id).count()


team_services = TeamService()
