# -*- coding: utf-8 -*-
from www.models import PermRelTenant, PermRelService
from console.models.main import TenantUserRole, TenantUserPermission, TenantUserRolePermission

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

    def get_service_perms(self,service_pk):
        return PermRelService.objects.filter(service_id=service_pk)

    def add_service_perm(self, user_id, service_pk, identity):
        return PermRelService.objects.create(user_id=user_id, service_id=service_pk, identity=identity)

class RoleRepo(object):
    def get_default_role_by_role_name(self, role_name, is_default=True):
        return TenantUserRole.objects.get(role_name=role_name, is_default=is_default)

class RolePermRepo(object):
    def get_perm_by_role_id(self,role_id):
        perm_id_list = TenantUserRolePermission.objects.filter(role_id=role_id).values_list("per_id",flat=True)
        perm_codename_list = TenantUserPermission.objects.filter(ID__in=perm_id_list).values_list("codename",flat=True)
        return tuple(perm_codename_list)


perms_repo = PermsRepo()
service_perm_repo = ServicePermRepo()
role_repo = RoleRepo()
role_perm_repo = RolePermRepo()