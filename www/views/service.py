# -*- coding: utf8 -*-
from django.http.response import JsonResponse
from django.template.response import TemplateResponse

from www.models.main import TenantServiceEnvVar, TenantServicesPort, TenantServiceInfo
from www.views import AuthedView, LeftSideBarMixin
from www.decorator import perm_required
from www.models import Users, PermRelTenant

import logging
logger = logging.getLogger('default')


class TeamInfo(LeftSideBarMixin, AuthedView):

    def get_context(self):
        context = super(TeamInfo, self).get_context()
        context.update({
            'perm_users': self.get_user_perms(),
            'tenantName': self.tenantName,
        })
        context["teamStatus"] = "active"
        return context

    def get_media(self):
        media = super(TeamInfo, self).get_media() + self.vendor(
            'www/css/goodrainstyle.css', 'www/js/jquery.cookie.js', 'www/js/service.js',
            'www/js/gr/basic.js', 'www/css/gr/basic.css', 'www/js/perms.js', 'www/js/common-scripts.js', 'www/js/jquery.dcjqaccordion.2.7.js', 'www/js/jquery.scrollTo.min.js'
        )
        return media

    def get_response(self):
        return TemplateResponse(self.request, 'www/team.html', self.get_context())

    def get_user_perms(self):
        perm_users = []
        perm_template = {
            'name': None,
            'adminCheck': False,
            'developerCheck': False, 'developerDisable': False,
            'viewerCheck': False, 'viewerDisable': False
        }

        identities = PermRelTenant.objects.filter(tenant_id=self.tenant.pk)

        user_id_list = [x.user_id for x in identities]
        user_list = Users.objects.filter(pk__in=user_id_list)
        user_map = {x.user_id: x for x in user_list}

        for i in identities:
            user_perm = perm_template.copy()
            user_info = user_map.get(i.user_id)
            if user_info is None:
                continue
            user_perm['name'] = user_info.nick_name
            if i.user_id == self.user.user_id:
                user_perm['selfuser'] = True

            if i.identity == 'admin':
                user_perm.update({
                    'adminCheck': True,
                    'developerCheck': True,
                    'developerDisable': True,
                    'viewerCheck': True,
                    'viewerDisable': True
                })
            elif i.identity == 'developer':
                user_perm.update({
                    'developerCheck': True,
                    'viewerCheck': True,
                    'viewerDisable': True
                })
            elif i.identity == 'viewer':
                user_perm.update({
                    'viewerCheck': True
                })

            perm_users.append(user_perm)

        return perm_users

    @perm_required('tenant_access')
    def get(self, request, *args, **kwargs):
        return self.get_response()


class CreateServiceDepInfo(LeftSideBarMixin, AuthedView):
    def get_context(self):
        """获取上下文对象"""
        context = super(CreateServiceDepInfo, self).get_context()
        return context

    @perm_required('tenant_access')
    def post(self, request, *args, **kwargs):
        result = {}
        try:
            # 通过service_id 获取该服务的链接信息
            service_id = request.POST.get("service_id", "")
            if service_id.strip() != "":
                envVarlist = TenantServiceEnvVar.objects.filter(service_id=service_id, scope__in=("outer", "both"),
                                                                is_change=False)

                service_name = TenantServiceInfo.objects.get(service_id=service_id).service_cname
                containerPortMap = {}
                opened_service_port_list = TenantServicesPort.objects.filter(service_id=service_id,
                                                                             is_inner_service=True)
                if len(opened_service_port_list) > 0:
                    for opened_service_port in opened_service_port_list:
                        containerPortMap[opened_service_port.container_port] = opened_service_port.port_alias

                containerPortKeys = containerPortMap.keys()
                # {"端口号":"端口号对应的环境变量"}
                env_map = {}
                for env_var in list(envVarlist):
                    if env_var.container_port in containerPortKeys or env_var.container_port < 1:
                        arr = env_map.get(env_var.container_port)
                        if arr is None:
                            arr = []
                        env_var.port_alias = containerPortMap.get(env_var.container_port)

                        arr.append(
                            {"port_alias": env_var.port_alias, "name": env_var.name, "attr_name": env_var.attr_name,
                             "attr_value": env_var.attr_value})
                        env_map[env_var.container_port] = arr

                result = {"ok": True, "obj": env_map,"service_name":service_name}
        except Exception as e:
            result = {"ok": False, "info": '获取服务信息异常'}
            logger.exception(e)
        return JsonResponse(result)
