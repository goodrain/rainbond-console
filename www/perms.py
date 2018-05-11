# -*- coding: utf8 -*-
import logging

from rest_framework.response import Response

from console.exception.main import BusinessException
from console.repositories.perm_repo import role_perm_repo
from goodrain_web.errors import UrlParseError, PermissionDenied
from www.models import Tenants, TenantServiceInfo, PermRelService, PermRelTenant, AnonymousUser
from www.utils.return_message import general_message

logger = logging.getLogger('default')


class PermActions(object):
    tenant_access_actions = (
        ('tenant_access', u"登入团队"),

        ('view_service', u"查看应用信息"),
    )

    tenant_viewer_actions = (


                                ('view_plugin', u"查看插件信息"),
                            ) + tenant_access_actions

    tenant_developer_actions = (
                                   ('manage_group', u"应用组管理"),
                                   ('deploy_service', u"部署应用"),
                                   ('create_service', u"创建应用"),
                                   ('stop_service', u"关闭应用"),
                                   ('start_service', u"启动应用"),
                                   ('restart_service', u"重启应用"),
                                   ('rollback_service', u"回滚应用"),
                                   ('manage_service_container', u"应用容器管理"),
                                   ('manage_service_log', u"应用日志管理"),
                                   ('manage_service_monitor', u"应用监控管理"),
                                   ('manage_service_extend', u"应用伸缩管理"),
                                   ('manage_service_config', u"应用配置管理"),
                                   ('manage_service_plugin', u"应用扩展管理"),
                                   ('manage_plugin', u"插件管理"),
                               ) + tenant_viewer_actions

    tenant_admin_actions = (
                               ('manage_team_member_permissions', u'团队权限设置'),
                               ('tenant_open_region', u'开通数据中心'),
                               ('delete_service', u"删除应用"),
                               ('share_service', u"应用组分享"),
                               ('manage_service_member_perms', u'应用权限设置'),
                               ('manage_financial_center', u"财务中心管理"),
                           ) + tenant_developer_actions

    tenant_owner_actions = (
                               ('drop_tenant', u"删除团队"), ('transfer_ownership', u"移交所有权"),
                               ('modify_team_name', u'修改团队名称'), ('tenant_manage_role', u'自定义角色')
                           ) + tenant_admin_actions

    tenant_gray_actions = (
                          ) + tenant_admin_actions

    service_viewer_actions = (
        ('view_service', u"查看应用信息"),
    )

    service_developer_actions = (
                                    ('deploy_service', u"部署应用"),
                                    ('stop_service', u"关闭应用"),
                                    ('start_service', u"启动应用"),
                                    ('restart_service', u"重启应用"),
                                    ('rollback_service', u"回滚应用"),
                                    ('manage_service_container', u"应用容器管理"),
                                    ('manage_service_log', u"应用日志管理"),
                                    ('manage_service_monitor', u"应用监控管理"),
                                    ('manage_service_extend', u"应用伸缩管理"),
                                    ('manage_service_config', u"应用配置管理"),
                                    ('manage_service_plugin', u"应用扩展管理"),

                                ) + service_viewer_actions

    service_admin_actions = (

                                ('manage_service_member_perms', u'应用权限设置'),
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

            role_id_list = PermRelTenant.objects.filter(user_id=user.pk, tenant_id=tenant.pk).values_list("role_id",
                                                                                                       flat=True)
            if not identitys[0] and not role_id_list[0]:
                raise PermRelTenant.DoesNotExist

            tenant_actions_tuple = ()
            if identitys[0]:
                tenant_identity = get_highest_identity(identitys)
                tenant_actions = p.keys('tenant_{0}_actions'.format(tenant_identity))
                tenant_actions_tuple += tenant_actions
            if role_id_list[0]:
                for role_id in role_id_list:
                    perm_tuple = role_perm_repo.get_perm_by_role_id(role_id=role_id)
                    tenant_actions_tuple += perm_tuple
            user.actions.set_actions('tenant', tuple(set(tenant_actions_tuple)))

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
