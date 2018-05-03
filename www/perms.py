# -*- coding: utf8 -*-
import logging

from rest_framework.response import Response

from console.exception.main import BusinessException
from goodrain_web.errors import UrlParseError, PermissionDenied
from www.models import Tenants, TenantServiceInfo, PermRelService, PermRelTenant, AnonymousUser
from www.utils.return_message import general_message

logger = logging.getLogger('default')


class PermActions(object):
    tenant_access_actions = (
        ('tenant_access', u"登入团队"),
        ('tenant_account', u"租户账户"),
        ('app_add_advantage', u"评论应用"),
        ('app_vote', u"对应用投票"),
        ('view_service', u"查看单个服务"),
    )

    tenant_viewer_actions = (
                                ('list_all_services', u"查看所有服务"),
                                ('view_service', u"查看单个服务"),
                                ('view_plugin', u"查看插件"),
                            ) + tenant_access_actions

    tenant_developer_actions = (
                                   ('git_pull', u"拉取git代码"), ('git_push', u"推送git代码"),
                                   ('code_deploy', u"部署代码"), ('deploy_service', u"部署服务"),
                                   ('manage_service', u"维护服务"),
                               ) + tenant_viewer_actions

    tenant_admin_actions = (
                               ('modify_team_member_permissions', u'编辑权限'), ('add_tenant_members', u'添加团队成员'),
                               ('create_service', u"创建服务"), ('delete_service', u"删除服务"),
                               ('setting', u"租户设置"), ('perm_setting', u"权限管理"),
                               ('service_monitor', u"服务资源监控"), ('service_alert', u"服务资源报警"),
                               ('share_service', u"分享服务"), ('manage_group', u"操作服务组"), ('create_plugin', u"创建插件"),
                               ('manage_plugin', u"创建插件"), ('drop_tenant_members', u'删除团队成员'),
                               ('app_publish', u"应用发布"), ('app_download', u"应用下载")
                           ) + tenant_developer_actions

    tenant_owner_actions = (
                               ('drop_tenant', u"删除团队"), ('transfer_ownership', u"移交所有权"),
                               ('modify_team_name', u'修改团队名称')
                           ) + tenant_admin_actions

    tenant_gray_actions = (
                          ) + tenant_admin_actions

    service_viewer_actions = (
        ('view_service', u"查看单个服务"),
    )

    service_developer_actions = (
                                    ('git_pull', u"拉取git代码"), ('git_push', u"推送git代码"),
                                    ('manage_service', u"维护服务"),
                                    ('code_deploy', u"部署代码"), ('deploy_service', u"部署服务"),
                                ) + service_viewer_actions

    service_admin_actions = (
                                ('code_deploy', u"部署代码"),
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


def get_highest_identity(identitys):
    """
    获取最高权限
    :param identitys:
    :return:
    """
    identity_map = {"access": 1, "viewer": 2, "developer": 3, "admin": 4, "owner": 5}
    final_identity = identitys[0]
    identity_num = -1
    for i in identitys:
        num = identity_map.get(final_identity)
        if num > identity_num:
            final_identity = i
            identity_num = num
    return final_identity

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
            identitys = PermRelTenant.objects.filter(user_id=user.pk, tenant_id=tenant.pk).values_list("identity",
                                                                                                       flat=True)
            if not identitys:
                raise PermRelTenant.DoesNotExist
            # 获取最高权限
            tenant_identity = get_highest_identity(identitys)
            # 获取团队所有的可操作内容
            tenant_actions = p.keys('tenant_{0}_actions'.format(tenant_identity))
            # 封装设置权限
            user.actions.set_actions('tenant', tenant_actions)
            if serviceAlias is not None:
                # 应用对象
                service = TenantServiceInfo.objects.get(tenant_id=tenant.tenant_id, service_alias=serviceAlias)
                # 应用权限
                service_identity = PermRelService.objects.get(user_id=user.pk, service_id=service.pk).identity
                # 获取应用所有的可操作内容
                service_actions = p.keys('service_{0}_actions'.format(service_identity))
                # 封装应用权限信息
                user.actions.set_actions('service', service_actions)
        except Tenants.DoesNotExist:
            raise UrlParseError(404, 'no matching tenantName for {0}'.format(tenantName))
        except TenantServiceInfo.DoesNotExist:
            raise UrlParseError(404, 'no matching serviceAlias for {0}'.format(serviceAlias))
        except PermRelTenant.DoesNotExist:
            tenant = Tenants.objects.filter(tenant_name=tenantName)[0]
            if not user.is_sys_admin and tenantName != "grdemo":
                raise UrlParseError(403, 'no permissions for user {0} on tenant {1}'.format(user.nick_name,
                                                                                            tenant.tenant_name))
            user.actions.set_actions('tenant', p.keys('tenant_viewer_actions'))
        except PermRelService.DoesNotExist:
            pass

    # if user.is_sys_admin:
    #     return True

    if perm in user.actions:
        return True
    raise BusinessException(
        Response(general_message(403, "you don't have enough permissions", "您无权限执行此操作"), status=403))

    # raise PermissionDenied("you don't have enough permissions")
