# -*- coding: utf-8 -*-
from www.models import PermRelTenant, PermRelService


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


perms_repo = PermsRepo()
service_perm_repo = ServicePermRepo()