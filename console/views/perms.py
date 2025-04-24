# -*- coding: utf8 -*-
import logging

from rest_framework.response import Response

from console.models.main import EnterpriseUserPerm
from console.repositories.enterprise_repo import enterprise_repo
from console.repositories.region_repo import region_repo
from console.services.operation_log import operation_log_service, Operation
from console.services.perm_services import perm_services
from console.services.perm_services import role_kind_services
from console.services.perm_services import role_perm_service
from console.services.perm_services import user_kind_perm_service
from console.services.perm_services import user_kind_role_service
from console.services.team_services import team_services
from console.views.base import RegionTenantHeaderView, AlowAnyApiView, TenantHeaderView
from www.utils.return_message import general_message

logger = logging.getLogger("default")


class PermsInfoLView(AlowAnyApiView):
    def get(self, request, *args, **kwargs):
        tenant_id = request.GET.get("tenant_id", None)
        perms = perm_services.get_all_perms(tenant_id)
        result = general_message(200, None, None, bean=perms)
        return Response(result, status=200)


class TeamRolesLCView(TenantHeaderView):
    def get(self, request, team_name, *args, **kwargs):
        roles = role_kind_services.get_roles("team", self.tenant.tenant_id, with_default=True)
        result = general_message(200, "success", None, list=roles.values("name", "ID"))
        return Response(result, status=200)

    def post(self, request, team_name, *args, **kwargs):
        name = request.data.get("name")
        tenant = team_services.get_tenant(team_name)
        regions = region_repo.get_region_by_tenant_name(team_name)
        role = role_kind_services.create_role("team", self.tenant.tenant_id, name)
        result = general_message(200, "success", "创建角色成功", bean=role.to_dict())
        comment = operation_log_service.generate_team_comment(
            operation=Operation.IN,
            module_name=tenant.tenant_alias,
            region=regions[0].region_name if regions else "",
            team_name=tenant.tenant_name,
            suffix=" 中创建了角色 {}".format(name))
        operation_log_service.create_team_log(
            user=self.user, comment=comment, enterprise_id=self.user.enterprise_id, team_name=tenant.tenant_name)
        return Response(result, status=200)


class TeamRolesRUDView(RegionTenantHeaderView):
    def get(self, request, team_name, role_id, *args, **kwargs):
        role = role_kind_services.get_role_by_id("team", self.tenant.tenant_id, role_id, with_default=True)
        data = role.to_dict()
        del data["kind"]
        del data["kind_id"]
        result = general_message(200, "success", None, bean=data)
        return Response(result, status=200)

    def put(self, request, team_name, role_id, *args, **kwargs):
        name = request.data.get("name")
        role = role_kind_services.update_role("team", self.tenant.tenant_id, role_id, name)
        data = role.to_dict()
        del data["kind"]
        del data["kind_id"]
        result = general_message(200, "success", "更新角色成功", bean=data)
        comment = operation_log_service.generate_team_comment(
            operation=Operation.IN,
            module_name=self.tenant.tenant_alias,
            region=self.response_region,
            team_name=self.tenant.tenant_name,
            suffix=" 中编辑了角色 {}".format(role.name))
        operation_log_service.create_team_log(
            user=self.user, comment=comment, enterprise_id=self.user.enterprise_id, team_name=self.tenant.tenant_name)
        return Response(result, status=200)

    def delete(self, request, team_name, role_id, *args, **kwargs):
        role = role_kind_services.get_role_by_id("team", self.tenant.tenant_id, role_id)
        role_kind_services.delete_role("team", self.tenant.tenant_id, role_id)
        result = general_message(200, "success", "删除角色成功")
        comment = operation_log_service.generate_team_comment(
            operation=Operation.IN,
            module_name=self.tenant.tenant_alias,
            region=self.response_region,
            team_name=self.tenant.tenant_name,
            suffix=" 中删除了角色 {}".format(role.name))
        operation_log_service.create_team_log(
            user=self.user, comment=comment, enterprise_id=self.user.enterprise_id, team_name=self.tenant.tenant_name)
        return Response(result, status=200)


class TeamRolesPermsLView(RegionTenantHeaderView):
    def get(self, request, team_name, *args, **kwargs):
        roles = role_kind_services.get_roles("team", self.tenant.tenant_id, with_default=True)
        data = role_perm_service.get_roles_perms(roles, kind="team")
        result = general_message(200, "success", None, list=data)
        return Response(result, status=200)


class TeamRolePermsRUDView(RegionTenantHeaderView):
    def get(self, request, team_name, role_id, *args, **kwargs):
        role = role_kind_services.get_role_by_id("team", self.tenant.tenant_id, role_id, with_default=True)
        data = role_perm_service.get_role_perms(role, kind="team", tenant_id=self.tenant.tenant_id)
        result = general_message(200, "success", None, bean=data)
        return Response(result, status=200)

    def put(self, request, team_name, role_id, *args, **kwargs):
        perms_model = request.data.get("permissions")
        role = role_kind_services.get_role_by_id("team", self.tenant.tenant_id, role_id, with_default=True)
        role_perm_service.update_role_perms(role.ID, perms_model, kind="team")
        data = role_perm_service.get_role_perms(role, kind="team", tenant_id=self.tenant.tenant_id)
        result = general_message(200, "success", None, bean=data)
        return Response(result, status=200)


class TeamUsersRolesLView(RegionTenantHeaderView):
    def get(self, request, team_name, *args, **kwargs):
        # 获取团队所有用户
        team_users = team_services.get_team_users(self.tenant)
        
        # 获取企业管理员列表（除了团队创建者）
        admin_users = EnterpriseUserPerm.objects.filter()
        admin_user_ids = set(admin_users.values_list('user_id', flat=True))
        
        # 过滤用户列表，排除企业管理员（除非是团队创建者）
        filtered_users = [user for user in team_users if user.user_id not in admin_user_ids or user.user_id == self.tenant.creater]
        
        # 获取用户角色信息
        data = user_kind_role_service.get_users_roles(
            kind="team", 
            kind_id=self.tenant.tenant_id, 
            users=filtered_users, 
            creater_id=self.tenant.creater
        )
        
        result = general_message(200, "success", None, list=data)
        return Response(result, status=200)


class TeamUserRolesRUDView(TenantHeaderView):
    def get(self, request, team_name, user_id, *args, **kwargs):
        team_users = team_services.get_team_users(self.tenant)
        user = team_users.filter(user_id=user_id).first()
        data = user_kind_role_service.get_user_roles(kind="team", kind_id=self.tenant.tenant_id, user=user)
        result = general_message(200, "success", None, bean=data)
        return Response(result, status=200)

    def put(self, request, team_name, user_id, *args, **kwargs):
        roles = request.data.get("roles")
        team_users = team_services.get_team_users(self.tenant)
        user = team_users.filter(user_id=user_id).first()
        user_kind_role_service.update_user_roles(kind="team", kind_id=self.tenant.tenant_id, user=user, role_ids=roles)
        data = user_kind_role_service.get_user_roles(kind="team", kind_id=self.tenant.tenant_id, user=user)
        result = general_message(200, "success", None, bean=data)
        comment = operation_log_service.generate_team_comment(
            operation=Operation.IN,
            module_name=self.tenant.tenant_alias,
            team_name=self.tenant.tenant_name,
            suffix=" 中修改了用户 {} 的角色".format(user.get_name()))
        operation_log_service.create_team_log(
            user=self.user, comment=comment, enterprise_id=self.user.enterprise_id, team_name=self.tenant.tenant_name)
        return Response(result, status=200)

    def delete(self, request, team_name, user_id, *args, **kwargs):
        team_users = team_services.get_team_users(self.tenant)
        user = team_users.filter(user_id=user_id).first()
        user_kind_role_service.delete_user_roles(kind="team", kind_id=self.tenant.tenant_id, user=user)
        data = user_kind_role_service.get_user_roles(kind="team", kind_id=self.tenant.tenant_id, user=user)
        result = general_message(200, "success", None, bean=data)
        return Response(result, status=200)


class TeamUserPermsLView(RegionTenantHeaderView):
    def get(self, request, team_name, user_id, *args, **kwargs):
        team_users = team_services.get_team_users(self.tenant)
        user = team_users.filter(user_id=user_id).first()
        data = user_kind_perm_service.get_user_perms(
            kind="team",
            kind_id=self.tenant.tenant_id,
            user=user,
            is_owner=self.is_team_owner,
            is_ent_admin=self.is_enterprise_admin)
        result = general_message(200, "success", None, bean=data)
        return Response(result, status=200)
