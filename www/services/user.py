# -*- coding: utf8 -*-

import random
import string
from www.models.main import Tenants, PermRelTenant, Users, TenantEnterprise, TenantRegionInfo
from django.db.models import Q

class UserService(object):
    def get_user_by_id(self, user_id):
        try:
            return Users.objects.get(user_id=user_id)
        except Users.DoesNotExist:
            return None

    def get_default_tenant_by_user(self, user_id):
        tenants = self.list_user_tenants(user_id)

        for tenant in tenants:
            if tenant.creater == user_id:
                return tenant

        return tenants[0] if tenants else None

    def list_user_tenants(self, user_id, load_region=False):
        if not user_id:
            return []

        perms = PermRelTenant.objects.filter(user_id=user_id)
        if not perms:
            return []

        tenant_ids = [t.tenant_id for t in perms]
        tenants = Tenants.objects.filter(ID__in=tenant_ids)
        if load_region:
            for tenant in tenants:
                if not hasattr(tenant, 'regions'):
                    tenant.regions = []
                tenant_regions = TenantRegionInfo.objects.filter(tenant_id=tenant.tenant_id)
                tenant.regions.extend(tenant_regions)

        return tenants


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

    def is_exist(self, username, password):
        try:
            u = Users.objects.get(Q(phone=username) | Q(email=username) | Q(nick_name=username))
            if not u.check_password(password):
                return None, '密码不正确', 400
            return u, "验证成功", 200
        except Users.DoesNotExist:
            return None, '用户不存在', 404

    def check_nick_name(self, nick_name):
        """
        判断用户是否在本地存在, 如果存在则拼接随机名字
        :param nick_name: 待注册的名字 
        :return: 
        """

        while Users.objects.filter(nick_name=nick_name).exists():
            random_str = ''.join(random.sample(string.ascii_lowercase + string.digits, 4))
            nick_name = '{0}_{1}'.format(nick_name, random_str)
        return nick_name

    def register_user_from_sso(self, sso_user):
        """
        通过云市sso的用户信息来生成本地用户信息
        :param sso_user:
        :return: 
        """
        user = Users.objects.create(nick_name=self.check_nick_name(sso_user.username),
                                    password=sso_user.get('pwd'),
                                    email=sso_user.get('email', ''),
                                    phone=sso_user.get('mobile', ''),
                                    sso_user_id=sso_user.get('uid', ''),
                                    sso_user_token=sso_user.get('sso_user_token', ''),
                                    is_active=False,
                                    rf='sso')
        return user
