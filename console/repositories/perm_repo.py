# -*- coding: utf-8 -*-
import logging

from django.db import transaction
from django.db.models import Q

from console.exception.main import ServiceHandleException
from console.models.main import PermsInfo
from console.models.main import RoleInfo
from console.models.main import RolePerms
from console.models.main import UserRole
from console.utils.perms import get_perms_metadata
from www.models.main import PermRelTenant

logger = logging.getLogger('default')


class PermsRepo(object):
    @transaction.atomic
    def initialize_permission_settings(self):
        """判断有没有初始化权限数据，没有则初始化"""
        all_perms_list = get_perms_metadata()
        has_perms = PermsInfo.objects.all()
        has_perms_list = list(has_perms.values_list("name", "desc", "code", "group", "kind"))
        if all_perms_list != has_perms_list:
            has_perms.delete()
            perms_list = []
            for perm in all_perms_list:
                perms_list.append(PermsInfo(name=perm[0], desc=perm[1], code=perm[2], group=perm[3], kind=perm[4]))
            PermsInfo.objects.bulk_create(perms_list)

    def get_all_perms(self):
        perms = PermsInfo.objects.all()
        return perms

    def add_user_tenant_perm(self, perm_info):
        perm_re_tenant = PermRelTenant(**perm_info)
        perm_re_tenant.save()
        return perm_re_tenant

    def get_user_tenant_perm(self, tenant_pk, user_pk):
        """
        获取用户在某个团队下的权限
        """
        prts = PermRelTenant.objects.filter(tenant_id=tenant_pk, user_id=user_pk)
        if prts:
            return prts[0]
        return None


class RoleKindRepo(object):
    def get_roles(self, kind, kind_id, with_default=False):
        if with_default:
            return RoleInfo.objects.filter(Q(kind_id=kind_id) | Q(kind_id="default")).filter(kind=kind)
        return RoleInfo.objects.filter(kind=kind, kind_id=kind_id)

    def get_role_by_id(self, kind, kind_id, id, with_default=False):
        if with_default:
            return RoleInfo.objects.filter(Q(kind_id=kind_id) | Q(kind_id="default")).filter(kind=kind, ID=id).first()
        return RoleInfo.objects.filter(kind=kind, kind_id=kind_id, ID=id).first()

    def get_role_by_name(self, kind, kind_id, name, with_default=False):
        if with_default:
            return RoleInfo.objects.filter(Q(kind_id=kind_id) | Q(kind_id="default")).filter(kind=kind, name=name).first()
        return RoleInfo.objects.filter(kind=kind, kind_id=kind_id, name=name).first()

    def get_roles_by_names(self, kind, kind_id, names):
        return RoleInfo.objects.filter(kind=kind, kind_id=kind_id, name__in=names)

    def create_role(self, kind, kind_id, name):
        return RoleInfo.objects.create(kind=kind, kind_id=kind_id, name=name)


class RoleRepo(object):
    def update_role_name(self, role, name):
        role.name = name
        role.save()
        return role

    def delete_role(self, role):
        role.delete()


class RolePermRelationRepo(object):
    def get_role_perm_relation(self, role_id):
        return RolePerms.objects.filter(role_id=role_id)

    def get_roles_perm_relation(self, role_ids):
        return RolePerms.objects.filter(role_id__in=role_ids)

    def create_role_perm_relation(self, role_id, perm_codes):
        if perm_codes:
            role_perm_list = []
            for perm_code in perm_codes:
                role_perm_list.append(RolePerms(role_id=role_id, perm_code=perm_code))
            return RolePerms.objects.bulk_create(role_perm_list)
        return []

    def delete_role_perm_relation(self, role_id):
        role_perms = self.get_role_perm_relation(role_id)
        role_perms.delete()

    def get_role_perms(self, role_id):
        role_perms = self.get_role_perm_relation(role_id)
        if not role_perms:
            return role_perms
        perm_codes = role_perms.values_list("perm_code", flat=True)
        return PermsInfo.objects.filter(code__in=perm_codes)


class UserKindRoleRepo(object):
    def get_user_roles_model(self, kind, kind_id, user):
        user_roles = []
        if not user:
            raise ServiceHandleException(msg="no found user", msg_show="用户不存在", status_code=404)
        roles = RoleInfo.objects.filter(kind=kind, kind_id=kind_id)
        if roles:
            role_ids = roles.values_list("ID", flat=True)
            user_roles = UserRole.objects.filter(role_id__in=role_ids, user_id=user.user_id)
        return user_roles

    def get_users_roles(self, kind, kind_id, users):
        data = []
        user_roles_kv = {}
        roles = RoleInfo.objects.filter(kind=kind, kind_id=kind_id)
        if roles:
            for user in users:
                user_roles_kv.update({str(user.user_id): []})
            role_id_name_kv = {}
            for role in roles:
                role_id_name_kv.update({str(role.ID): role.name})

            role_ids = roles.values_list("ID", flat=True)
            users_roles = UserRole.objects.filter(role_id__in=role_ids)
            for user_role in users_roles:
                user_roles_kv[str(user_role.user_id)].append({
                    "role_id": user_role.role_id,
                    "role_name": role_id_name_kv[str(user_role.role_id)]
                })
        for user in users:
            data.append({
                "nick_name": user.nick_name,
                "email": user.email,
                "user_id": user.user_id,
                "roles": user_roles_kv.get(str(user.user_id), [])
            })
        return data

    def get_user_roles(self, kind, kind_id, user):
        if not user:
            raise ServiceHandleException(msg="no found user", msg_show="用户不存在", status_code=404)
        user_roles_list = []
        roles = RoleInfo.objects.filter(kind=kind, kind_id=kind_id)
        if roles:
            role_id_name_kv = {}
            for role in roles:
                role_id_name_kv.update({str(role.ID): role.name})
            role_ids = roles.values_list("ID", flat=True)
            user_roles = UserRole.objects.filter(role_id__in=role_ids, user_id=user.user_id)
            if user_roles:
                for user_role in user_roles:
                    user_roles_list.append({"role_id": user_role.role_id, "role_name": role_id_name_kv[str(user_role.role_id)]})
        data = {"nick_name": user.nick_name, "user_id": user.user_id, "roles": user_roles_list}
        return data

    def update_user_roles(self, kind, kind_id, user, role_ids):
        update_role_list = []
        if not user:
            raise ServiceHandleException(msg="no found user", msg_show="用户不存在", status_code=404)
        roles = RoleInfo.objects.filter(kind=kind, kind_id=kind_id)
        has_role_ids = roles.values_list("ID", flat=True)
        update_role_ids = list(set(has_role_ids) & set(role_ids))
        if not update_role_ids and len(role_ids):
            raise ServiceHandleException(msg="no found can update params", msg_show="传入角色不可被分配，请检查参数", status_code=404)
        for role_id in update_role_ids:
            update_role_list.append(UserRole(user_id=user.user_id, role_id=role_id))
        UserRole.objects.bulk_create(update_role_list)

    def delete_user_roles(self, kind, kind_id, user, role_ids=None):
        if not user:
            raise ServiceHandleException(msg="no found user", msg_show="用户不存在", status_code=404)
        roles = RoleInfo.objects.filter(kind=kind, kind_id=kind_id)
        if roles:
            has_role_ids = roles.values_list("ID", flat=True)
            if role_ids:
                user_roles = UserRole.objects.filter(role_id__in=role_ids, user_id=user.user_id)
            else:
                user_roles = UserRole.objects.filter(role_id__in=has_role_ids, user_id=user.user_id)
            user_roles.delete()

    def delete_users_role(self, kind, kind_id, role_id):
        roles = RoleInfo.objects.filter(kind=kind, kind_id=kind_id)
        if roles:
            has_role_ids = roles.values_list("ID", flat=True)
            if role_id in has_role_ids:
                user_roles = UserRole.objects.filter(role_id=role_id)
                user_roles.delete()


perms_repo = PermsRepo()
role_repo = RoleRepo()
role_perm_relation_repo = RolePermRelationRepo()
role_kind_repo = RoleKindRepo()
user_kind_role_repo = UserKindRoleRepo()
