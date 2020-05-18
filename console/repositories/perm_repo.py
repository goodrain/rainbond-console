# -*- coding: utf-8 -*-
import logging

from django.db import transaction
from django.db.models import Q

from console.exception.main import ServiceHandleException
from www.models.main import PermRelTenant
from console.models.main import PermsInfo
from console.models.main import RoleInfo
from console.models.main import RolePerms
from console.models.main import UserRole

from console.utils.perms import get_perms_metadata

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

    # def add_user_tenant_perm(self, perm_info):
    #     perm_re_tenant = PermRelTenant(**perm_info)
    #     perm_re_tenant.save()
    #     return perm_re_tenant
    #
    # def get_user_tenant_perm(self, tenant_pk, user_pk):
    #     """
    #     获取用户在某个团队下的权限
    #     """
    #     prts = PermRelTenant.objects.filter(tenant_id=tenant_pk, user_id=user_pk)
    #     if prts:
    #         return prts[0]
    #     return None


class ServicePermRepo(object):
    pass
#     def get_service_perm_by_user_pk(self, service_pk, user_pk):
#         try:
#             return PermRelService.objects.get(user_id=user_pk, service_id=service_pk)
#         except PermRelService.DoesNotExist:
#             return None
#
#     def get_service_perms(self, service_pk):
#         return PermRelService.objects.filter(service_id=service_pk)
#
#     def add_service_perm(self, user_id, service_pk, identity):
#         return PermRelService.objects.create(user_id=user_id, service_id=service_pk, identity=identity)
#
#     def get_user_id_in_service(self, service_pk):
#         return ServiceRelPerms.objects.filter(service_id=service_pk).values_list("user_id", flat=True)
#
#     def get_service_perm_by_user_pk_service_pk(self, service_pk, user_pk):
#         """判断一个用户在一个应用中有没有权限"""
#
#         query = ServiceRelPerms.objects.filter(user_id=user_pk, service_id=service_pk)
#         if not query:
#             return None
#         return query
#
#     def add_user_service_perm(self, user_ids, service_pk, perm_ids):
#         """添加用户应用权限"""
#         with transaction.atomic():
#             for user_id in user_ids:
#                 for perm_id in perm_ids:
#                     ServiceRelPerms.objects.create(user_id=user_id, service_id=service_pk, perm_id=perm_id)
#
#     def get_service_perm_by_service_pk_user_pk(self, service_pk, user_pk):
#         """判断一个用户在一个应用中是否存在权限"""
#
#         service_perm = ServiceRelPerms.objects.filter(user_id=user_pk, service_id=service_pk)
#         if not service_perm:
#             return None
#         return service_perm
#
#     def update_service_perm_by_service_id_user_id_perm_list(self, user_id, service_id, perm_list):
#         """更新用户在一个应用中的权限"""
#         with transaction.atomic():
#             ServiceRelPerms.objects.filter(user_id=user_id, service_id=service_id).delete()
#             for perm_id in perm_list:
#                 ServiceRelPerms.objects.create(user_id=user_id, service_id=service_id, perm_id=perm_id)
#
#     def get_perms_by_user_id_service_id(self, user_id, service_id):
#         """获取一个用户在一个团队中的权限id列表"""
#         return ServiceRelPerms.objects.filter(user_id=user_id, service_id=service_id).values_list("perm_id", flat=True)
#
#     def delete_service_perm(self, sid):
#         ServiceRelPerms.objects.filter(service_id=sid).delete()
#         PermRelService.objects.filter(service_id=sid).delete()
#
#     def get_service_perms_by_service_pk(self, sid):
#         return ServiceRelPerms.objects.filter(service_id=sid)
#
#
# class RoleRepo(object):
#
#     def get_default_role_by_role_name(self, role_name, is_default=True):
#         return TenantUserRole.objects.get(role_name=role_name, is_default=is_default)
#
#     def get_tenant_role_by_tenant_id(self, tenant_id, allow_owner=False):
#         """获取一个团队中的所有角色和角色对应的权限信息"""
#         default_role_list = []
#         team_role_list = []
#
#         filter = Q(is_default=True)
#         if not allow_owner:
#             filter &= ~Q(role_name="owner")
#         default_role_queryset = TenantUserRole.objects.filter(filter)
#         for role_obj in default_role_queryset:
#             role_dict = {}
#             default_role_perm_list = []
#
#             per_id_list = TenantUserRolePermission.objects.filter(role_id=role_obj.pk).values_list("per_id", flat=True)
#             for perm_obj in TenantUserPermission.objects.filter(ID__in=per_id_list):
#                 perm_dict = {}
#                 perm_dict["perm_id"] = perm_obj.pk
#                 perm_dict["codename"] = perm_obj.codename
#                 perm_dict["perm_info"] = perm_obj.per_info
#                 perm_dict["is_select"] = perm_obj.is_select
#                 perm_dict["group_id"] = perm_obj.group
#                 if perm_obj.group:
#                     perm_dict["group_name"] = PermGroup.objects.get(ID=perm_obj.group).group_name
#                 else:
#                     perm_dict["group_name"] = None
#                 default_role_perm_list.append(perm_dict)
#             role_dict["role_id"] = role_obj.pk
#             role_dict["role_name"] = role_obj.role_name
#             role_dict["is_default"] = role_obj.is_default
#             role_dict["role_perm"] = default_role_perm_list
#             default_role_list.append(role_dict)
#
#         team_role_queryset = TenantUserRole.objects.filter(tenant_id=tenant_id, is_default=False)
#         for role_obj in team_role_queryset:
#             role_dict = {}
#             team_role_perm_list = []
#             per_id_list = TenantUserRolePermission.objects.filter(role_id=role_obj.pk).values_list("per_id", flat=True)
#             for perm_obj in TenantUserPermission.objects.filter(ID__in=per_id_list):
#                 perm_dict = dict()
#                 perm_dict["perm_id"] = perm_obj.pk
#                 perm_dict["codename"] = perm_obj.codename
#                 perm_dict["perm_info"] = perm_obj.per_info
#                 perm_dict["is_select"] = perm_obj.is_select
#                 perm_dict["group_id"] = perm_obj.group
#                 if perm_obj.group:
#                     perm_dict["group_name"] = PermGroup.objects.get(ID=perm_obj.group).group_name
#                 else:
#                     perm_dict["group_name"] = None
#                 team_role_perm_list.append(perm_dict)
#             role_dict["role_id"] = role_obj.pk
#             role_dict["role_name"] = role_obj.role_name
#             role_dict["is_default"] = role_obj.is_default
#             role_dict["role_perm"] = team_role_perm_list
#             team_role_list.append(role_dict)
#
#         return default_role_list + team_role_list
#
#     def get_default_role(self):
#         """获取默认的角色"""
#         return TenantUserRole.objects.filter(is_default=True).values_list("role_name", flat=True)
#
#     def get_default_role_id(self):
#         """获取默认的角色ID"""
#         return TenantUserRole.objects.filter(is_default=True).values_list("pk", flat=True)
#
#     def team_role_is_exist_by_role_name_team_id(self, tenant_name, role_id):
#         """判断一个角色在一个团队中是否存在"""
#
#         tenant = team_repo.get_tenant_by_tenant_name(tenant_name=tenant_name)
#         if not tenant:
#             raise Tenants.DoesNotExist
#
#         role_obj = TenantUserRole.objects.filter(tenant_id=tenant.pk, ID=role_id)
#
#         return role_obj
#
#     def team_role_is_exist_by_role_name_team_id_2(self, tenant_name, role_name):
#         """判断一个角色在一个团队中是否存在"""
#
#         tenant = team_repo.get_tenant_by_tenant_name(tenant_name=tenant_name)
#         if not tenant:
#             raise Tenants.DoesNotExist
#
#         role_obj = TenantUserRole.objects.filter(tenant_id=tenant.pk, role_name=role_name)
#
#         return role_obj
#
#     def team_user_is_exist_by_role_id_tenant_name(self, role_id, tenant_name):
#         """判断团队中一个角色是否有绑定的人"""
#         tenant = team_repo.get_tenant_by_tenant_name(tenant_name=tenant_name)
#         if not tenant:
#             raise Tenants.DoesNotExist
#         return PermRelTenant.objects.filter(tenant_id=tenant.ID, role_id=role_id)
#
#     def get_role_name_by_role_id(self, role_id):
#         """获取角色名称"""
#         return TenantUserRole.objects.get(pk=role_id).role_name
#
#     def get_role_id_by_role_name(self, role_name):
#         """获取角色ID"""
#         role_query = TenantUserRole.objects.filter(role_name=role_name)
#         if role_query:
#             return role_query[0].pk
#         else:
#             return None
#
#     def add_role_by_tenant_pk_perm_list(self, role_name, tenant_pk, perm_id_list):
#         """创建一个角色"""
#         with transaction.atomic():
#             role_obj = TenantUserRole.objects.create(role_name=role_name, tenant_id=tenant_pk, is_default=False)
#             for perm_id in perm_id_list:
#                 TenantUserRolePermission.objects.create(role_id=role_obj.pk, per_id=perm_id)
#         return role_obj
#
#     def del_role_by_team_pk_role_name_role_id(self, tenant_pk, role_id):
#         """删除一个角色"""
#         with transaction.atomic():
#             TenantUserRole.objects.get(tenant_id=tenant_pk, ID=role_id, is_default=False).delete()
#             TenantUserRolePermission.objects.filter(role_id=role_id).delete()
#
#     def update_role_by_team_name_role_name_perm_list(self, tenant_pk, role_id, new_role_name, perm_id_list):
#         """更新一个自定义角色的权限"""
#         with transaction.atomic():
#             role_obj = TenantUserRole.objects.filter(
#                 ID=role_id, tenant_id=tenant_pk, is_default=False).update(role_name=new_role_name)
#             TenantUserRolePermission.objects.filter(role_id=role_id).delete()
#             for perm_id in perm_id_list:
#                 TenantUserRolePermission.objects.create(role_id=role_id, per_id=perm_id)
#         if role_obj:
#
#             return TenantUserRole.objects.get(ID=role_id, role_name=new_role_name, tenant_id=tenant_pk, is_default=False)
#         else:
#             return None
#
#     def update_user_role_in_tenant_by_user_id_tenant_id_role_id(self, user_id, tenant_id, role_id_list, enterprise_id):
#         """修改一个用户在一个团队中的角色"""
#         with transaction.atomic():
#             PermRelTenant.objects.filter(user_id=user_id, tenant_id=tenant_id, enterprise_id=enterprise_id).delete()
#             for role_id in role_id_list:
#                 PermRelTenant.objects.create(user_id=user_id, tenant_id=tenant_id, enterprise_id=enterprise_id, role_id=role_id)
#
#     def add_user_role_in_tenant_by_user_id_tenant_id_role_id(self, user_id, tenant_id, role_id_list, enterprise_id):
#         """修改一个用户在一个团队中的角色"""
#         for role_id in role_id_list:
#             PermRelTenant.objects.create(user_id=user_id, tenant_id=tenant_id, enterprise_id=enterprise_id, role_id=role_id)
#

class RoleKindRepo(object):
    def get_roles(self, kind, kind_id, with_default=False):
        if with_default:
            return RoleInfo.objects.filter(Q(kind_id=kind_id)| Q(kind_id="default")).filter(kind=kind)
        return RoleInfo.objects.filter(kind=kind, kind_id=kind_id)

    def get_role_by_id(self, kind, kind_id, id, with_default=False):
        if with_default:
            return RoleInfo.objects.filter(Q(kind_id=kind_id)| Q(kind_id="default")).filter(kind=kind, ID=id).first()
        return RoleInfo.objects.filter(kind=kind, kind_id=kind_id, ID=id).first()

    def get_role_by_name(self, kind, kind_id, name, with_default=False):
        if with_default:
            return RoleInfo.objects.filter(Q(kind_id=kind_id)| Q(kind_id="default")).filter(kind=kind, name=name).first()
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
            raise ServiceHandleException(msg="no found user", msg_show=u"用户不存在", status_code=404)
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
            user_ids = users_roles.values_list("user_id", flat=True)
            for user_role in users_roles:
                user_roles_kv[str(user_role.user_id)].append(
                    {"role_id": user_role.role_id, "role_name": role_id_name_kv[str(user_role.role_id)]})
        for user in users:
            data.append({
                "nick_name": user.nick_name,
                "user_id": user.user_id,
                "roles": user_roles_kv.get(str(user.user_id), [])
            })
        return data

    def get_user_roles(self, kind, kind_id, user):
        if not user:
            raise ServiceHandleException(msg="no found user", msg_show=u"用户不存在", status_code=404)
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
                    user_roles_list.append({
                        "role_id": user_role.role_id,
                        "role_name": role_id_name_kv[str(user_role.role_id)]
                    })
        data = {
            "nick_name": user.nick_name,
            "user_id": user.user_id,
            "roles": user_roles_list
        }
        return data

    def update_user_roles(self, kind, kind_id, user, role_ids):
        update_role_list = []
        if not user:
            raise ServiceHandleException(msg="no found user", msg_show=u"用户不存在", status_code=404)
        roles = RoleInfo.objects.filter(kind=kind, kind_id=kind_id)
        has_role_ids = roles.values_list("ID", flat=True)
        update_role_ids = list(set(has_role_ids) & set(role_ids))
        if update_role_ids:
            for role_id in update_role_ids:
                update_role_list.append(UserRole(user_id=user.user_id, role_id=role_id))
            UserRole.objects.bulk_create(update_role_list)
        else:
            raise ServiceHandleException(msg="no found can update params", msg_show=u"传入角色不可被分配，请检查参数", status_code=404)

    def delete_user_roles(self, kind, kind_id, user, role_ids=None):
        if not user:
            raise ServiceHandleException(msg="no found user", msg_show=u"用户不存在", status_code=404)
        roles = RoleInfo.objects.filter(kind=kind, kind_id=kind_id)
        if roles:
            has_role_ids = roles.values_list("ID", flat=True)
            if role_ids:
                effective_role_ids = list(set(has_role_ids) & set(role_ids))
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


class UserKindPermsRepo(object):
    def get_user_perms(self, kind, kind_id, user):
        pass




# class RolePermRepo(object):
        # def get_perm_by_role_id(self, role_id):
    #     perm_id_list = TenantUserRolePermission.objects.filter(role_id=role_id).values_list("per_id", flat=True)
    #     perm_codename_list = TenantUserPermission.objects.filter(ID__in=perm_id_list).values_list("codename", flat=True)
    #     return tuple(perm_codename_list)
    #
    # def get_permission_options(self):
    #     """获取可选项"""
    #     options_list = list()
    #     outher_options_dict = dict()
    #
    #     perm_group_obj = PermGroup.objects.all()
    #     for group in perm_group_obj:
    #         perm_list = []
    #         options_dict = dict()
    #         perm_options_query = TenantUserPermission.objects.filter(is_select=True, group=group.pk)
    #         for obj in perm_options_query:
    #             perm_list.append({"id": obj.pk, "codename": obj.codename, "info": obj.per_info})
    #         options_dict["group_name"] = group.group_name
    #         options_dict["perms_info"] = perm_list
    #         options_list.append(options_dict)
    #     outher_perm_options_query = TenantUserPermission.objects.filter(is_select=True, group__isnull=True)
    #
    #     outher_perm_list = []
    #
    #     for obj in outher_perm_options_query:
    #         outher_perm_list.append({"id": obj.pk, "codename": obj.codename, "info": obj.per_info})
    #     outher_options_dict["group_name"] = "其他"
    #     outher_options_dict["perms_info"] = outher_perm_list
    #     options_list.append(outher_options_dict)
    #
    #     return options_list
    #
    # def get_three_service_permission_options(self):
    #     """获取第三方组件自定义角色时可给角色绑定的权限选项"""
    #     options_list = list()
    #
    #     perm_group_obj = PermGroup.objects.all()
    #     for group in perm_group_obj:
    #         if int(group.pk) != 2 and int(group.pk) != 4:
    #             continue
    #         perm_list = []
    #         options_dict = dict()
    #         perm_options_query = TenantUserPermission.objects.filter(is_select=True, group=group.pk)
    #         for obj in perm_options_query:
    #             logger.debug('------------------>{0}'.format(group.pk))
    #             logger.debug('--------0000000---------->{0}'.format(obj.codename))
    #             if group.pk == 2 and obj.codename not in ("manage_group", "view_service", "delete_service", "share_service",
    #                                                       "manage_service_config", "manage_service_member_perms"):
    #                 continue
    #             perm_list.append({"id": obj.pk, "codename": obj.codename, "info": obj.per_info})
    #         options_dict["group_name"] = group.group_name
    #         options_dict["perms_info"] = perm_list
    #         options_list.append(options_dict)
    #
    #     return options_list
    #
    # def get_select_perm_list(self):
    #     """获取可以选择的权限列表"""
    #     select_perm_list = TenantUserPermission.objects.filter(is_select=True).values_list("pk", flat=True)
    #     return list(select_perm_list)
    #
    # def get_perm_list_by_perm_id_list(self, perm_id_list):
    #     perm_query = TenantUserPermission.objects.filter(ID__in=perm_id_list)
    #     return [perm_obj.codename for perm_obj in perm_query]
    #
    # def get_perm_obj_by_perm_id(self, perm_id):
    #
    #     if TenantUserPermission.objects.filter(ID=perm_id):
    #         return TenantUserPermission.objects.filter(ID=perm_id)[0]
    #     else:
    #         return None

class RolePermRepo(object):
    pass


# perms_repo = PermsRepo()
# service_perm_repo = ServicePermRepo()
# role_repo = RoleRepo()
# role_perm_repo = RolePermRepo()


perms_repo = PermsRepo()
service_perm_repo = ServicePermRepo()
role_repo = RoleRepo()
role_perm_repo = RolePermRepo()

role_perm_relation_repo = RolePermRelationRepo()
role_kind_repo = RoleKindRepo()
user_kind_role_repo = UserKindRoleRepo()