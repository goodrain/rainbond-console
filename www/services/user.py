# -*- coding: utf8 -*-

from www.models.main import Tenants, PermRelTenant, Users, TenantEnterprise, TenantRegionInfo


class UserService(object):
    def get_user_by_id(self, user_id):
        try:
            return Users.objects.get(user_id=user_id)
        except Users.DoesNotExist:
            return None

    def get_default_tenant_by_user(self, user_id):
        try:
            return Tenants.objects.get(creater=user_id)
        except Tenants.DoesNotExist:
            tenants = self.list_user_tenants(user_id)
            return tenants[0] if tenants else None

    def list_user_tenants(self, user_id):
        if not user_id:
            return []

        perms = PermRelTenant.objects.filter(user_id=user_id)
        tenant_ids = [t.tenant_id for t in perms]

        return Tenants.objects.filter(ID__in=tenant_ids)

    def delete_tenant(self, user_id):
        """
        清理云帮用户信息
        :param user_id: 
        :return: 
        """
        user = Users.objects.get(user_id=user_id)
        tenants = Tenants.objects.filter(creater=user.user_id)
        for tenant in tenants:
            TenantRegionInfo.objects.filter(tenant_id=tenant.tenant_id).delete()
            tenant.delete()

        PermRelTenant.objects.filter(user_id=user.user_id).delete()
        TenantEnterprise.objects.filter(enterprise_id=user.enterprise_id).delete()
        user.delete()
