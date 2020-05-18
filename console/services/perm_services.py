# -*- coding: utf-8 -*-
from django.db import transaction

from console.exception.main import ServiceHandleException
from console.repositories.user_repo import user_repo
from console.repositories.perm_repo import service_perm_repo
from console.repositories.perm_repo import perms_repo
from console.repositories.perm_repo import role_perm_repo
from console.repositories.perm_repo import role_repo
from console.repositories.perm_repo import role_perm_relation_repo
from console.repositories.perm_repo import role_kind_repo
from console.repositories.perm_repo import user_kind_role_repo
from console.repositories.enterprise_repo import enterprise_repo
from console.utils.perms import get_perms_structure, get_perms_model, get_team_perms_model, get_enterprise_perms_model, get_perms_name_code_kv, DEFAULT_TEAM_ROLE_PERMS, DEFAULT_ENTERPRISE_ROLE_PERMS
from console.models.main import RolePerms
import logging

logger = logging.getLogger("default")


class PermService(object):
    def get_all_perms(self):
        perms_structure = get_perms_structure()
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
            raise ServiceHandleException(msg="role no found", msg_show=u"角色不存在", status_code=404)
        return role

    def get_role_by_name(self, kind, kind_id, name, with_default=False):
        return role_kind_repo.get_role_by_name(kind, kind_id, name, with_default)

    def create_role(self, kind, kind_id, name):
        if not name:
            raise ServiceHandleException(msg="role name exit", msg_show=u"角色名称不能为空")
        if self.get_role_by_name(kind, kind_id, name, with_default=True):
            raise ServiceHandleException(msg="role name exit", msg_show=u"角色名称已存在")
        return role_kind_repo.create_role(kind, kind_id, name)

    def update_role(self, kind, kind_id, id, name):
        if not name:
            raise ServiceHandleException(msg="role name exit", msg_show=u"角色名称不能为空")
        if self.get_role_by_name(kind, kind_id, name, with_default=True):
            raise ServiceHandleException(msg="role name exit", msg_show=u"角色名称已存在")
        role = self.get_role_by_id(kind, kind_id, id)
        if not role:
            raise ServiceHandleException(msg="role no found", msg_show=u"角色不存在或为默认角色", status_code=404)
        role.name = name
        role.save()
        return role

    @transaction.atomic()
    def delete_role(self, kind, kind_id, id):
        role = self.get_role_by_id(kind, kind_id, id)
        if not role:
            raise ServiceHandleException(msg="role no found or is default", msg_show=u"角色不存在或为默认角色")
        role_perm_relation_repo.delete_role_perm_relation(role.ID)
        user_kind_role_repo.delete_users_role(kind, kind_id, role.ID)
        role.delete()

    def init_default_role_perms(self, role):
        if role.name in DEFAULT_TEAM_ROLE_PERMS.keys():
            role_perm_relation_repo.delete_role_perm_relation(role.ID)
            role_perm_relation_repo.create_role_perm_relation(role.ID, DEFAULT_TEAM_ROLE_PERMS[role.name])

    def init_default_roles(self, kind, kind_id):
        if kind == "team":
            DEFAULT_ROLES = DEFAULT_TEAM_ROLE_PERMS.keys()
        elif kind == "enterprise":
            DEFAULT_ROLES = DEFAULT_ENTERPRISE_ROLE_PERMS.keys()
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
        for role_id, rule_perms in roles_perms.items():
            role_perms_info = {"role_id": int(role_id)}
            if kind == "team":
                permissions = self.pack_role_perms_tree(get_team_perms_model(), rule_perms)
            elif kind == "enterprise":
                permissions = self.pack_role_perms_tree(get_enterprise_perms_model(), rule_perms)
            else:
                permissions = self.pack_role_perms_tree(get_perms_model(), rule_perms)
            role_perms_info.update({"permissions": permissions})
            data.append(role_perms_info)
        return data

    def get_roles_union_perms(self, roles, kind=None, is_owner=False):
        union_role_perms = []
        if roles:
            role_ids = roles.values_list("role_id", flat=True)
            roles_perm_relation_mode = role_perm_relation_repo.get_roles_perm_relation(role_ids)
            if roles_perm_relation_mode:
                roles_perm_relations = roles_perm_relation_mode.values("role_id", "perm_code")
                for roles_perm_relation in roles_perm_relations:
                    union_role_perms.append(roles_perm_relation["perm_code"])
        if kind == "team":
            permissions = self.pack_role_perms_tree(get_team_perms_model(), union_role_perms, is_owner)
        elif kind == "enterprise":
            permissions = self.pack_role_perms_tree(get_enterprise_perms_model(), union_role_perms, is_owner)
        else:
            permissions = self.pack_role_perms_tree(get_perms_model(), union_role_perms, is_owner)
        return {"permissions": permissions}

    def get_role_perms(self, role, kind=None):
        if not role:
            return None
        roles_perms = {str(role): []}
        role_perm_relation_mode = role_perm_relation_repo.get_role_perm_relation(role.ID)
        if role_perm_relation_mode:
            roles_perm_relations = role_perm_relation_mode.values("role_id", "perm_code")
            for roles_perm_relation in roles_perm_relations:
                if str(roles_perm_relation["role_id"]) not in roles_perms:
                    roles_perms[str(roles_perm_relation["role_id"])] = []
                roles_perms[str(roles_perm_relation["role_id"])].append(roles_perm_relation["perm_code"])
        data = []
        for role_id, rule_perms in roles_perms.items():
            role_perms_info = {"role_id": role_id}
            if kind == "team":
                permissions = self.pack_role_perms_tree(get_team_perms_model(), rule_perms)
            elif kind == "enterprise":
                permissions = self.pack_role_perms_tree(get_enterprise_perms_model(), rule_perms)
            else:
                permissions = self.pack_role_perms_tree(get_perms_model(), rule_perms)
            role_perms_info.update({"permissions": permissions})
            data.append(role_perms_info)
        return data[0]

    ### 已有一维角色权限列表变更权限模型权限的默认值
    def __build_perms_list(self, model_perms, role_codes, is_owner):
        perms_list = []
        for model_perm in model_perms:
            model_perm_key = model_perm.keys()
            model_perm_key.remove("code")
            if is_owner:
                perms_list.append({model_perm_key[0]: True})
            else:
                if model_perm["code"] in role_codes:
                    perms_list.append({model_perm_key[0]: True})
                else:
                    perms_list.append({model_perm_key[0]: False})
        return perms_list

    ### 角色权限树打包
    def pack_role_perms_tree(self, models, role_codes, is_owner=False):
        items_list = models.items()
        sub_models = []
        for items in items_list:
            kind_name, body = items
            if body["sub_models"]:
                for sub in body["sub_models"]:
                    sub_models.append(self.pack_role_perms_tree(sub, role_codes, is_owner))
                models[kind_name]["sub_models"] = sub_models
            models[kind_name]["perms"] = self.__build_perms_list(body["perms"], role_codes, is_owner)
        return models

    def __unpack_to_build_perms_list(self, perms_model, role_id, perms_name_code_kv):
        role_perms_list = []
        items_list = perms_model.items()
        for items in items_list:
            kind_name, body = items
            if body["sub_models"]:
                for sub in body["sub_models"]:
                    role_perms_list.extend(self.__unpack_to_build_perms_list(sub, role_id, perms_name_code_kv))
            for perm in body["perms"]:
                perm_items = perm.items()[0]
                perm_key, perms_value = perm_items
                if perms_value:
                    role_perms_list.append(
                        RolePerms(role_id=role_id, perm_code=perms_name_code_kv["_".join([kind_name, perm_key])]))
        return role_perms_list

    ### 角色的权限树降维
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
    def get_users_roles(self, kind, kind_id, users):
        return user_kind_role_repo.get_users_roles(kind, kind_id, users)

    def get_user_roles(self, kind, kind_id, user):
        return user_kind_role_repo.get_user_roles(kind, kind_id, user)

    def update_user_roles(self, kind, kind_id, user, role_ids):
        self.delete_user_roles(kind, kind_id, user)
        user_kind_role_repo.update_user_roles(kind, kind_id, user, role_ids)

    def delete_user_roles(self, kind, kind_id, user):
        user_kind_role_repo.delete_user_roles(kind, kind_id, user)


class UserKindPermService(object):
    def get_user_perms(self, kind, kind_id, user, is_owner=False):
        user_roles = user_kind_role_repo.get_user_roles_model(kind, kind_id, user)
        perms = role_perm_service.get_roles_union_perms(user_roles, kind, is_owner)
        data = {"user_id": user.user_id}
        data.update(perms)
        return data

class ServicePermService(object):
    def add_service_perm(self, current_user, user_id, tenant, service, identity):
        if current_user.user_id == user_id:
            return 409, u"不能给自己添加组件权限", None
        user = user_repo.get_user_by_user_id(user_id)
        if not user:
            return 404, "用户{0}不存在".format(user_id), None
        service_perm = service_perm_repo.get_service_perm_by_user_pk(service.ID, user_id)
        if service_perm:
            return 409, "用户{0}已有权限，无需添加".format(user.nick_name), None
        service_perm = service_perm_repo.add_service_perm(user_id, service.ID, identity)
        perm_tenant = perms_repo.get_user_tenant_perm(tenant.ID, user_id)
        enterprise = None
        try:
            enterprise = enterprise_repo.get_enterprise_by_enterprise_id(tenant.enterprise_id)
        except Exception as e:
            logger.exception(e)
        if not perm_tenant:
            perm_info = {
                "user_id": user.user_id,
                "tenant_id": tenant.ID,
                "identity": "access",
                "enterprise_id": enterprise.ID if enterprise else 0
            }
            perm_tenant = perms_repo.add_user_tenant_perm(perm_info)
        logger.debug("service_perm {0} , perm_tenant {1}".format(service_perm, perm_tenant))
        return 200, "已向用户{0}授权".format(user.nick_name), service_perm

    def get_service_perm(self, service):
        service_perms = service_perm_repo.get_service_perms(service.ID)
        perm_list = []
        for service_perm in service_perms:
            perm = {}
            u = user_repo.get_by_user_id(service_perm.user_id)
            perm["user_id"] = service_perm.user_id
            perm["identity"] = service_perm.identity
            perm["nick_name"] = u.nick_name
            perm["email"] = u.email
            perm_list.append(perm)
        return perm_list

    def update_service_perm(self, current_user, user_id, service, identity):
        if current_user.user_id == user_id:
            return 409, u"您不能修改自己的权限", None
        service_perm = service_perm_repo.get_service_perm_by_user_pk(service.ID, user_id)
        if not service_perm:
            return 404, u"需要修改的权限不存在", None
        service_perm.identity = identity
        service_perm.save()
        return 200, u"success", service_perm

    def delete_service_perm(self, current_user, user_id, service):
        if current_user.user_id == user_id:
            return 409, u"您不能删除自己的权限"
        service_perm = service_perm_repo.get_service_perm_by_user_pk(service.ID, user_id)
        if not service_perm:
            return 404, u"需要删除的权限不存在"
        service_perm.delete()
        return 200, u"success"

    def get_user_service_perm(self, user_id, service_pk):
        service_perm_repo.get_service_perm_by_user_pk(service_pk, user_id)

    def add_user_service_perm(self, current_user, user_list, tenant, service, perm_list):
        """添加用户在一个组件中的权限"""
        if current_user.user_id in user_list:
            return 409, u"不能给自己添加组件权限", None
        for user_id in user_list:
            user = user_repo.get_user_by_user_id(user_id)
            if not user:
                return 404, "用户{0}不存在".format(user_id), None

            service_perm = service_perm_repo.get_service_perm_by_user_pk_service_pk(service_pk=service.ID, user_pk=user_id)
            if service_perm:
                return 409, "用户{0}已有权限，无需添加".format(user.nick_name), None

        service_perm_repo.add_user_service_perm(user_ids=user_list, service_pk=service.ID, perm_ids=perm_list)

        enterprise = None
        try:
            enterprise = enterprise_repo.get_enterprise_by_enterprise_id(tenant.enterprise_id)
        except Exception as e:
            logger.exception(e)
            pass

        for user_id in user_list:
            perm_tenant = perms_repo.get_user_tenant_perm(tenant.ID, user_id)

            if not perm_tenant:
                perm_info = {
                    "user_id": user_id,
                    "tenant_id": tenant.ID,
                    "role_id": role_repo.get_role_id_by_role_name("viewer"),
                    "enterprise_id": enterprise.ID if enterprise else 0
                }
                perm_tenant = perms_repo.add_user_tenant_perm(perm_info)

        return 200, "添加用户组件权限成功", None

    def delete_user_service_perm(self, current_user, user_id, service):
        if current_user.user_id == user_id:
            return 409, u"您不能删除自己的权限"
        service_perm = service_perm_repo.get_service_perm_by_service_pk_user_pk(service.ID, user_id)
        if not service_perm:
            return 404, u"需要删除的权限不存在"
        service_perm.delete()
        return 200, u"success"

    def update_user_service_perm(self, current_user, user_id, service, perm_list):
        if current_user.user_id == user_id:
            return 409, u"您不能修改自己的权限", None
        service_perm = service_perm_repo.get_service_perm_by_service_pk_user_pk(service.ID, user_id)
        if not service_perm:
            return 404, u"需要修改的权限不存在", None
        service_perm_repo.update_service_perm_by_service_id_user_id_perm_list(
            user_id=user_id, service_id=service.ID, perm_list=perm_list)
        return 200, u"success", service_perm

    def get_user_service_perm_info(self, service):
        """获取组件下的成员及对应的权限"""
        user_id_list = service_perm_repo.get_user_id_in_service(service.ID)
        user_id_list = list(set(user_id_list))
        perm_list = []

        for user_id in user_id_list:
            user_obj = user_repo.get_by_user_id(user_id)
            if not user_obj:
                continue
            user_info = {}
            user_perm_list = []

            perm_id_list = service_perm_repo.get_perms_by_user_id_service_id(user_id=user_id, service_id=service.ID)

            for perm_id in perm_id_list:
                perm_obj = role_perm_repo.get_perm_obj_by_perm_id(perm_id=perm_id)
                if not perm_obj:
                    continue
                perm_info = dict()
                perm_info["id"] = perm_obj.ID
                perm_info["codename"] = perm_obj.codename
                perm_info["perm_info"] = perm_obj.per_info

                user_perm_list.append(perm_info)

            user_info["user_id"] = user_obj.user_id
            user_info["nick_name"] = user_obj.nick_name
            user_info["email"] = user_obj.email
            user_info["service_perms"] = user_perm_list
            perm_list.append(user_info)
        return perm_list


# perm_services = PermService()
# app_perm_service = ServicePermService()

perm_services = PermService()
app_perm_service = ServicePermService()

role_services = RoleService()
role_kind_services = RoleKindService()
role_perm_service = RolePermService()
user_kind_role_service = UserKindRoleService()
user_kind_perm_service = UserKindPermService()