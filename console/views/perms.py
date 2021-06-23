# -*- coding: utf8 -*-
import logging

from rest_framework.response import Response

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
        perms = perm_services.get_all_perms()
        result = general_message(200, None, None, bean=perms)
        return Response(result, status=200)


class TeamRolesLCView(TenantHeaderView):
    def get(self, request, team_name, *args, **kwargs):
        roles = role_kind_services.get_roles("team", self.tenant.tenant_id, with_default=True)
        result = general_message(200, "success", None, list=roles.values("name", "ID"))
        return Response(result, status=200)

    def post(self, request, team_name, *args, **kwargs):
        name = request.data.get("name")
        role = role_kind_services.create_role("team", self.tenant.tenant_id, name)
        result = general_message(200, "success", "创建角色成功", bean=role.to_dict())
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
        return Response(result, status=200)

    def delete(self, request, team_name, role_id, *args, **kwargs):
        role_kind_services.delete_role("team", self.tenant.tenant_id, role_id)
        result = general_message(200, "success", "删除角色成功")
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
        data = role_perm_service.get_role_perms(role, kind="team")
        result = general_message(200, "success", None, bean=data)
        return Response(result, status=200)

    def put(self, request, team_name, role_id, *args, **kwargs):
        perms_model = request.data.get("permissions")
        role = role_kind_services.get_role_by_id("team", self.tenant.tenant_id, role_id, with_default=True)
        role_perm_service.update_role_perms(role.ID, perms_model, kind="team")
        data = role_perm_service.get_role_perms(role, kind="team")
        result = general_message(200, "success", None, bean=data)
        return Response(result, status=200)


class TeamUsersRolesLView(RegionTenantHeaderView):
    def get(self, request, team_name, *args, **kwargs):
        team_users = team_services.get_team_users(self.tenant)
        data = user_kind_role_service.get_users_roles(
            kind="team", kind_id=self.tenant.tenant_id, users=team_users, creater_id=self.tenant.creater)
        result = general_message(200, "success", None, list=data)
        return Response(result, status=200)


class TeamUserRolesRUDView(RegionTenantHeaderView):
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
