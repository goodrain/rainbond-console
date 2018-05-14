# -*- coding: utf-8 -*-
from www.models import PermRelTenant, PermRelService
from django.db import transaction
from django.db.models import Q
from console.models.main import TenantUserRole, TenantUserPermission, TenantUserRolePermission, PermGroup
from console.repositories.team_repo import team_repo
from www.models import Tenants


class PermsRepo(object):
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


class ServicePermRepo(object):
    def get_service_perm_by_user_pk(self, service_pk, user_pk):
        try:
            return PermRelService.objects.get(user_id=user_pk, service_id=service_pk)
        except PermRelService.DoesNotExist:
            return None

    def get_service_perms(self, service_pk):
        return PermRelService.objects.filter(service_id=service_pk)

    def add_service_perm(self, user_id, service_pk, identity):
        return PermRelService.objects.create(user_id=user_id, service_id=service_pk, identity=identity)


class RoleRepo(object):
    def get_default_role_by_role_name(self, role_name, is_default=True):
        return TenantUserRole.objects.get(role_name=role_name, is_default=is_default)

    def get_tenant_role_by_tenant_id(self, tenant_id):
        """获取一个团队中的所有角色和角色对应的权限信息"""
        default_role_list = []
        team_role_list = []

        default_role_queryset = TenantUserRole.objects.filter(Q(is_default=True) & ~Q(role_name="owner"))
        for role_obj in default_role_queryset:
            role_dict = {}
            default_role_perm_list = []

            per_id_list = TenantUserRolePermission.objects.filter(role_id=role_obj.pk).values_list("per_id", flat=True)
            for perm_obj in TenantUserPermission.objects.filter(ID__in=per_id_list):
                perm_dict = {}
                perm_dict["perm_id"] = perm_obj.pk
                perm_dict["codename"] = perm_obj.codename
                perm_dict["perm_info"] = perm_obj.per_info
                perm_dict["is_select"] = perm_obj.is_select
                perm_dict["group_id"] = perm_obj.group
                if perm_obj.group:
                    perm_dict["group_name"] = PermGroup.objects.get(ID=perm_obj.group).group_name
                else:
                    perm_dict["group_name"] = None
                default_role_perm_list.append(perm_dict)
            role_dict["role_id"] = role_obj.pk
            role_dict["role_name"] = role_obj.role_name
            role_dict["is_default"] = role_obj.is_default
            role_dict["role_perm"] = default_role_perm_list
            default_role_list.append(role_dict)

        team_role_queryset = TenantUserRole.objects.filter(tenant_id=tenant_id, is_default=False)
        for role_obj in team_role_queryset:
            role_dict = {}
            team_role_perm_list = []
            per_id_list = TenantUserRolePermission.objects.filter(role_id=role_obj.pk).values_list("per_id", flat=True)
            for perm_obj in TenantUserPermission.objects.filter(ID__in=per_id_list):
                perm_dict = {}
                perm_dict["perm_id"] = perm_obj.pk
                perm_dict["codename"] = perm_obj.codename
                perm_dict["perm_info"] = perm_obj.per_info
                perm_dict["is_select"] = perm_obj.is_select
                perm_dict["group_id"] = perm_obj.group
                if perm_obj.group:
                    perm_dict["group_name"] = PermGroup.objects.get(ID=perm_obj.group).group_name
                else:
                    perm_dict["group_name"] = None
                team_role_perm_list.append(perm_dict)
            role_dict["role_id"] = role_obj.pk
            role_dict["role_name"] = role_obj.role_name
            role_dict["is_default"] = role_obj.is_default
            role_dict["role_perm"] = team_role_perm_list
            team_role_list.append(role_dict)

        return default_role_list + team_role_list

    def get_default_role(self):
        """获取默认的角色"""
        return TenantUserRole.objects.filter(is_default=True).values_list("role_name", flat=True)

    def get_default_role_id(self):
        """获取默认的角色ID"""
        return TenantUserRole.objects.filter(is_default=True).values_list("pk", flat=True)

    def team_role_is_exist_by_role_name_team_id(self, tenant_name, role_id):
        """判断一个角色在一个团队中是否存在"""

        tenant = team_repo.get_tenant_by_tenant_name(tenant_name=tenant_name)
        if not tenant:
            raise Tenants.DoesNotExist

        role_obj = TenantUserRole.objects.filter(tenant_id=tenant.pk, ID=role_id)

        return role_obj

    def team_role_is_exist_by_role_name_team_id_2(self, tenant_name, role_name):
        """判断一个角色在一个团队中是否存在"""

        tenant = team_repo.get_tenant_by_tenant_name(tenant_name=tenant_name)
        if not tenant:
            raise Tenants.DoesNotExist

        role_obj = TenantUserRole.objects.filter(tenant_id=tenant.pk, role_name=role_name)

        return role_obj

    def get_role_name_by_role_id(self, role_id):
        """获取角色名称"""
        return TenantUserRole.objects.get(pk=role_id).role_name

    def get_role_id_by_role_name(self, role_name):
        """获取角色ID"""
        return TenantUserRole.objects.get(role_name=role_name).pk

    def add_role_by_tenant_pk_perm_list(self, role_name, tenant_pk, perm_id_list):
        """创建一个角色"""
        with transaction.atomic():
            role_obj = TenantUserRole.objects.create(role_name=role_name, tenant_id=tenant_pk, is_default=False)
            for perm_id in perm_id_list:
                TenantUserRolePermission.objects.create(role_id=role_obj.pk, per_id=perm_id)
        return role_obj

    def del_role_by_team_pk_role_name_role_id(self, tenant_pk, role_id):
        """删除一个角色"""
        with transaction.atomic():
            TenantUserRole.objects.get(tenant_id=tenant_pk, ID=role_id, is_default=False).delete()
            TenantUserRolePermission.objects.filter(role_id=role_id).delete()

    def update_role_by_team_name_role_name_perm_list(self, tenant_pk,
                                                     role_id,
                                                     new_role_name,
                                                     perm_id_list):
        """更新一个自定义角色的权限"""
        with transaction.atomic():
            role_obj = TenantUserRole.objects.filter(ID=role_id, tenant_id=tenant_pk,
                                                     is_default=False).update(role_name=new_role_name)
            TenantUserRolePermission.objects.filter(role_id=role_id).delete()
            for perm_id in perm_id_list:
                TenantUserRolePermission.objects.create(role_id=role_id, per_id=perm_id)
        if role_obj:

            return TenantUserRole.objects.get(ID=role_id, role_name=new_role_name, tenant_id=tenant_pk,
                                              is_default=False)
        else:
            return None

    def update_user_role_in_tenant_by_user_id_tenant_id_role_id(self, user_id, tenant_id, role_id_list, enterprise_id):
        """修改一个用户在一个团队中的角色"""
        with transaction.atomic():
            PermRelTenant.objects.filter(user_id=user_id, tenant_id=tenant_id, enterprise_id=enterprise_id).delete()
            for role_id in role_id_list:
                PermRelTenant.objects.create(user_id=user_id, tenant_id=tenant_id, enterprise_id=enterprise_id,
                                             role_id=role_id)


class RolePermRepo(object):
    def get_perm_by_role_id(self, role_id):
        perm_id_list = TenantUserRolePermission.objects.filter(role_id=role_id).values_list("per_id", flat=True)
        perm_codename_list = TenantUserPermission.objects.filter(ID__in=perm_id_list).values_list("codename", flat=True)
        return tuple(perm_codename_list)

    def get_permission_options(self):
        """获取可选项"""
        options_dict = dict()

        perm_group_obj = PermGroup.objects.all()
        for group in perm_group_obj:
            perm_list = []
            perm_options_query = TenantUserPermission.objects.filter(is_select=True, group=group.pk)
            for obj in perm_options_query:
                perm_list.append(
                    {"id": obj.pk, "codename": obj.codename, "info": obj.per_info}
                )
            options_dict[group.group_name] = perm_list
        outher_perm_options_query = TenantUserPermission.objects.filter(is_select=True, group__isnull=True)

        outher_perm_list = []

        for obj in outher_perm_options_query:
            outher_perm_list.append(
                {"id": obj.pk, "codename": obj.codename, "info": obj.per_info}
            )
        options_dict["其他"] = outher_perm_list
        return options_dict

    def get_select_perm_list(self):
        """获取可以选择的权限列表"""
        select_perm_list = TenantUserPermission.objects.filter(is_select=True).values_list("pk", flat=True)
        return list(select_perm_list)


perms_repo = PermsRepo()
service_perm_repo = ServicePermRepo()
role_repo = RoleRepo()
role_perm_repo = RolePermRepo()
