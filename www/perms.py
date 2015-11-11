# -*- coding: utf8 -*-
from www.models import Tenants, TenantServiceInfo, PermRelService, PermRelTenant, AnonymousUser
from goodrain_web.errors import UrlParseError, PermissionDenied

import logging
logger = logging.getLogger('default')


class PermActions(object):
    tenant_access_actions = (
        ('tenant_access', u"登入团队"),
        ('tenant_account', u"租户账户"),
    )

    tenant_viewer_actions = (
        ('list_all_services', u"查看所有服务"),
        ('view_service', u"查看单个服务"),
    ) + tenant_access_actions

    tenant_developer_actions = (
        ('git_pull', u"拉取git代码"), ('git_push', u"推送git代码"),
        ('code_deploy', u"部署代码"),
    ) + tenant_viewer_actions

    tenant_admin_actions = (
        ('create_service', u"创建服务"), ('delete_service', u"删除服务"),
        ('deploy_service', u"部署服务"), ('manage_service', u"维护服务"),
        ('setting', u"租户设置"), ('perm_setting', u"权限管理")
    ) + tenant_developer_actions

    tenant_owner_actions = (
        ('drop_tenant', u"删除团队"), ('transfer_ownership', u"移交所有权"),
    ) + tenant_admin_actions

    service_viewer_actions = (
        ('view_service', u"查看单个服务"),
    )

    service_developer_actions = (
        ('git_pull', u"拉取git代码"), ('git_push', u"推送git代码"),
        ('code_deploy', u"部署代码"),
    ) + service_viewer_actions

    service_admin_actions = (
        ('manage_service', u"维护服务"),
        ('setting', u"服务设置"), ('perm_setting', u"权限管理")
    ) + service_developer_actions

    def keys(self, tag):
        if hasattr(self, tag):
            return tuple([e[0] for e in getattr(self, tag)])
        else:
            return ()


class UserActions(dict):

    def __init__(self):
        self.tenant_actions = []
        self.service_actions = []

    def __contains__(self, perm):
        if '.' in perm:
            perm_type, action = perm.split('.')
        else:
            perm_type, action = ('both', perm)

        if perm_type == 'tenant':
            check_type_list = ['tenant']
        elif perm_type == 'service':
            check_type_list = ['service']
        elif perm_type == 'both':
            check_type_list = ['service', 'tenant']
        else:
            return False

        for i in check_type_list:
            actions = getattr(self, '%s_actions' % i)
            if action in actions:
                return True

        return False

    def __str__(self):
        return str({
            'tenant_actions': self.tenant_actions,
            'service_actions': self.service_actions,
        })

    def set_actions(self, name, actions):
        if name not in ('tenant', 'service'):
            return False
        setattr(self, '%s_actions' % name, actions)


def check_perm(perm, user, tenantName=None, serviceAlias=None):
    if isinstance(user, AnonymousUser):
        raise PermissionDenied('this resource need login status', redirect_url='/login')

    if tenantName is None:
        raise UrlParseError(500, 'tenantName is None')

    if not hasattr(user, 'actions'):
        user.actions = UserActions()

        p = PermActions()

        try:
            tenant = Tenants.objects.get(tenant_name=tenantName)
            tenant_identity = PermRelTenant.objects.get(user_id=user.pk, tenant_id=tenant.pk).identity
            tenant_actions = p.keys('tenant_{0}_actions'.format(tenant_identity))
            user.actions.set_actions('tenant', tenant_actions)
            if serviceAlias is not None:
                service = TenantServiceInfo.objects.get(tenant_id=tenant.tenant_id, service_alias=serviceAlias)
                service_identity = PermRelService.objects.get(user_id=user.pk, service_id=service.pk).identity
                service_actions = p.keys('service_{0}_actions'.format(service_identity))
                user.actions.set_actions('service', service_actions)
        except Tenants.DoesNotExist:
            raise UrlParseError(404, 'no matching tenantName for {0}'.format(tenantName))
        except TenantServiceInfo.DoesNotExist:
            raise UrlParseError(404, 'no matching serviceAlias for {0}'.format(serviceAlias))
        except PermRelTenant.DoesNotExist:
            if not user.is_sys_admin:
                raise UrlParseError(403, 'no permissions for user {0} on tenant {1}'.format(user.nick_name, tenant.tenant_name))
        except PermRelService.DoesNotExist:
            pass

    if user.is_sys_admin:
        return True

    if perm in user.actions:
        return True

    raise PermissionDenied("you don't not enough permissions")
