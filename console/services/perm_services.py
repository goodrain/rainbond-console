# -*- coding: utf-8 -*-
import logging

from django.db import transaction

from console.exception.main import ServiceHandleException
from console.models.main import RolePerms
from console.repositories.perm_repo import perms_repo
from console.repositories.perm_repo import role_kind_repo
from console.repositories.perm_repo import role_perm_relation_repo
from console.repositories.perm_repo import user_kind_role_repo
from console.utils.perms import get_perms_structure, get_perms_model, get_team_perms_model, \
    get_perms_name_code_kv, DEFAULT_TEAM_ROLE_PERMS, get_app_perms_model
from www.models.main import ServiceGroup

logger = logging.getLogger("default")


class PermService(object):
    def get_all_perms(self, tenant_id):
        perms_structure = get_perms_structure(tenant_id)
        return perms_structure

    def add_user_tenant_perm(self, perm_info):
        return perms_repo.add_user_tenant_perm(perm_info=perm_info)

    def get_user_tenant_perm(self, tenant_pk, user_id):
        return perms_repo.get_user_tenant_perm(tenant_pk, user_id)


class RoleService(object):
    pass


class RoleKindService(object):
    def get_roles(self, kind, kind_id, with_default=False):
        return role_kind_repo.get_roles(kind, kind_id, with_default)

    def get_role_by_id(self, kind, kind_id, id, with_default=False):
        role = role_kind_repo.get_role_by_id(kind, kind_id, id, with_default)
        if not role:
            raise ServiceHandleException(msg="role no found", msg_show="角色不存在", status_code=404)
        return role

    def get_role_by_name(self, kind, kind_id, name, with_default=False):
        return role_kind_repo.get_role_by_name(kind, kind_id, name, with_default)

    def create_role(self, kind, kind_id, name):
        if not name:
            raise ServiceHandleException(msg="role name exit", msg_show="角色名称不能为空")
        if self.get_role_by_name(kind, kind_id, name, with_default=True):
            raise ServiceHandleException(msg="role name exit", msg_show="角色名称已存在")
        return role_kind_repo.create_role(kind, kind_id, name)

    def update_role(self, kind, kind_id, id, name):
        if not name:
            raise ServiceHandleException(msg="role name exit", msg_show="角色名称不能为空")
        exit_role = self.get_role_by_name(kind, kind_id, name, with_default=True)
        if exit_role:
            if int(exit_role.ID) != int(id):
                raise ServiceHandleException(msg="role name exit", msg_show="角色名称已存在")
            else:
                return exit_role
        role = self.get_role_by_id(kind, kind_id, id)
        if not role:
            raise ServiceHandleException(msg="role no found", msg_show="角色不存在或为默认角色", status_code=404)
        role.name = name
        role.save()
        return role

    @transaction.atomic()
    def delete_role(self, kind, kind_id, id):
        role = self.get_role_by_id(kind, kind_id, id)
        if not role:
            raise ServiceHandleException(msg="role no found or is default", msg_show="角色不存在或为默认角色")
        role_perm_relation_repo.delete_role_perm_relation(role.ID)
        user_kind_role_repo.delete_users_role(kind, kind_id, role.ID)
        role.delete()

    def init_default_role_perms(self, role):
        if role.name in list(DEFAULT_TEAM_ROLE_PERMS.keys()):
            role_perm_relation_repo.delete_role_perm_relation(role.ID)
            role_perm_relation_repo.create_role_perm_relation(role.ID, DEFAULT_TEAM_ROLE_PERMS[role.name])

    def init_default_roles(self, kind, kind_id):
        if kind == "team":
            DEFAULT_ROLES = list(DEFAULT_TEAM_ROLE_PERMS.keys())
        else:
            DEFAULT_ROLES = []
        if DEFAULT_ROLES == []:
            pass
        for default_role in DEFAULT_ROLES:
            role = role_kind_repo.get_role_by_name(kind, kind_id, default_role)
            if not role:
                role = self.create_role(kind, kind_id, default_role)
            self.init_default_role_perms(role)


class RolePermService(object):
    def get_roles_perms(self, roles, kind=None):
        roles_perms = {}
        if not roles:
            return []
        role_ids = roles.values_list("ID", flat=True)
        for role_id in role_ids:
            roles_perms.update({str(role_id): []})
        roles_perm_relation_mode = role_perm_relation_repo.get_roles_perm_relation(role_ids)
        if roles_perm_relation_mode:
            roles_perm_relations = roles_perm_relation_mode.values("role_id", "perm_code")
            for roles_perm_relation in roles_perm_relations:
                roles_perms[str(roles_perm_relation["role_id"])].append(roles_perm_relation["perm_code"])
        data = []
        for role_id, rule_perms in list(roles_perms.items()):
            role_perms_info = {"role_id": int(role_id)}
            if kind == "team":
                permissions = self.pack_role_perms_tree(get_team_perms_model(), rule_perms)
            else:
                permissions = self.pack_role_perms_tree(get_perms_model(), rule_perms)
            role_perms_info.update({"permissions": permissions})
            data.append(role_perms_info)
        return data

    def get_roles_union_perms(self, roles, kind=None, is_owner=False, tenant_id=""):
        union_role_perms = []
        app_perms = dict()
        if roles:
            role_ids = roles.values_list("role_id", flat=True)
            roles_perm_relation_mode = role_perm_relation_repo.get_roles_perm_relation(role_ids)
            if roles_perm_relation_mode:
                roles_perm_relations = roles_perm_relation_mode.values("role_id", "perm_code", "app_id")
                for roles_perm_relation in roles_perm_relations:
                    if roles_perm_relation.get("app_id") != -1:
                        if str(roles_perm_relation["app_id"]) not in app_perms:
                            app_perms[str(roles_perm_relation["app_id"])] = []
                        app_perms[str(roles_perm_relation["app_id"])].append(roles_perm_relation["perm_code"])
                    else:
                        union_role_perms.append(roles_perm_relation["perm_code"])
        if kind == "team":
            permissions = self.pack_role_perms_tree(get_team_perms_model(), union_role_perms, is_owner)
        else:
            permissions = self.pack_role_perms_tree(get_perms_model(), union_role_perms, is_owner)
        app_ids = ServiceGroup.objects.filter(tenant_id=tenant_id).values_list("ID", flat=True)
        app = {"sub_models": [], "perms": {}}
        for app_id in app_ids:
            if str(app_id) not in app_perms:
                app_permissions = permissions.get("team").get("sub_models")[2].get("team_app_manage")
            else:
                models = self.pack_role_perms_tree(get_app_perms_model(), app_perms.get(str(app_id)))
                app_permissions = models.get("app")
            app["sub_models"].append({"app_" + str(app_id): app_permissions})
        permissions.get("team").get("sub_models")[2]["team_app_manage"] = app
        return {"permissions": permissions}

    def get_role_perms(self, role, kind=None, tenant_id=""):
        if not role:
            return None
        roles_perms = {str(role.ID): []}
        app_perms = dict()
        role_perm_relation_mode = role_perm_relation_repo.get_role_perm_relation(role.ID)
        if role_perm_relation_mode:
            roles_perm_relations = role_perm_relation_mode.values("role_id", "perm_code", "app_id")
            for roles_perm_relation in roles_perm_relations:
                if roles_perm_relation.get("app_id") != -1:
                    if str(roles_perm_relation["app_id"]) not in app_perms:
                        app_perms[str(roles_perm_relation["app_id"])] = []
                    app_perms[str(roles_perm_relation["app_id"])].append(roles_perm_relation["perm_code"])
                else:
                    roles_perms[str(roles_perm_relation["role_id"])].append(roles_perm_relation["perm_code"])
        data = []
        app_ids = ServiceGroup.objects.filter(tenant_id=tenant_id).values_list("ID", flat=True)
        for role_id, rule_perms in list(roles_perms.items()):
            role_perms_info = {"role_id": role_id}
            if kind == "team":
                permissions = self.pack_role_perms_tree(get_team_perms_model(), rule_perms)
            else:
                permissions = self.pack_role_perms_tree(get_perms_model(), rule_perms)
            app = {"sub_models": [], "perms": {}}
            for app_id in app_ids:
                if str(app_id) not in app_perms:
                    app_permissions = permissions.get("team").get("sub_models")[2].get("team_app_manage")
                else:
                    models = self.pack_role_perms_tree(get_app_perms_model(), app_perms.get(str(app_id)))
                    app_permissions = models.get("app")
                app["sub_models"].append({"app_" + str(app_id): app_permissions})
            permissions.get("team").get("sub_models")[2]["team_app_manage"] = app
            role_perms_info.update({"permissions": permissions})
            data.append(role_perms_info)
        return data[0]

    # 已有一维角色权限列表变更权限模型权限的默认值
    def __build_perms_list(self, model_perms, role_codes, is_owner):
        perms_list = []
        for model_perm in model_perms:
            model_perm_key = list(model_perm.keys())
            model_perm_key.remove("code")
            if is_owner:
                perms_list.append({model_perm_key[0]: True})
            else:
                if model_perm["code"] in role_codes:
                    perms_list.append({model_perm_key[0]: True})
                else:
                    perms_list.append({model_perm_key[0]: False})
        return perms_list

    # 角色权限树打包
    def pack_role_perms_tree(self, models, role_codes, is_owner=False):
        items_list = list(models.items())
        sub_models = []
        for items in items_list:
            kind_name, body = items
            if body["sub_models"]:
                for sub in body["sub_models"]:
                    sub_models.append(self.pack_role_perms_tree(sub, role_codes, is_owner))
                models[kind_name]["sub_models"] = sub_models
            models[kind_name]["perms"] = self.__build_perms_list(body["perms"], role_codes, is_owner)
        return models

    def __unpack_to_build_perms_list(self, perms_model, role_id, perms_name_code_kv, app_id=-1):
        role_perms_list = []
        items_list = list(perms_model.items())
        for items in items_list:
            kind_name, body = items
            if kind_name.startswith("app_"):
                kind_name_app = kind_name.split('_')
                if kind_name_app[1].isdigit():
                    app_id = int(kind_name_app[1])
            if body["sub_models"]:
                for sub in body["sub_models"]:
                    role_perms_list.extend(self.__unpack_to_build_perms_list(sub, role_id, perms_name_code_kv, app_id=app_id))
            for perm in body["perms"]:
                perm_items = list(perm.items())[0]
                perm_key, perms_value = perm_items
                if perms_value:
                    role_perms_list.append(
                        RolePerms(
                            role_id=role_id, perm_code=perms_name_code_kv["_".join([kind_name, perm_key])], app_id=app_id))
        return role_perms_list

    # 角色的权限树降维
    def unpack_role_perms_tree(self, perms_model, role_id, perms_name_code_kv):
        role_perms_list = self.__unpack_to_build_perms_list(perms_model, role_id, perms_name_code_kv)
        RolePerms.objects.bulk_create(role_perms_list)

    @transaction.atomic()
    def update_role_perms(self, role_id, perms_model, kind=None):
        self.delete_role_perms(role_id)
        self.unpack_role_perms_tree(perms_model, role_id, get_perms_name_code_kv())

    def delete_role_perms(self, role_id):
        return role_perm_relation_repo.delete_role_perm_relation(role_id)


class UserKindRoleService(object):
    def get_users_roles(self, kind, kind_id, users, creater_id=0):
        return user_kind_role_repo.get_users_roles(kind, kind_id, users, creater_id=creater_id)

    def get_user_roles(self, kind, kind_id, user):
        return user_kind_role_repo.get_user_roles(kind, kind_id, user)

    def update_user_roles(self, kind, kind_id, user, role_ids):
        self.delete_user_roles(kind, kind_id, user)
        user_kind_role_repo.update_user_roles(kind, kind_id, user, role_ids)

    def delete_user_roles(self, kind, kind_id, user):
        user_kind_role_repo.delete_user_roles(kind, kind_id, user)


class UserKindPermService(object):
    def get_user_perms(self, kind, kind_id, user, is_owner=False, is_ent_admin=False):
        if is_owner or is_ent_admin:
            is_owner = True
        user_roles = user_kind_role_repo.get_user_roles_model(kind, kind_id, user)
        perms = role_perm_service.get_roles_union_perms(user_roles, kind, is_owner, tenant_id=kind_id)
        data = {"user_id": user.user_id}
        data.update(perms)
        return data


perm_services = PermService()
role_services = RoleService()
role_kind_services = RoleKindService()
role_perm_service = RolePermService()
user_kind_role_service = UserKindRoleService()
user_kind_perm_service = UserKindPermService()
