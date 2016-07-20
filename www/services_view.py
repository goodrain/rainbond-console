# -*- coding: utf8 -*-
import logging
import json

from django.views.decorators.cache import never_cache
from django.template.response import TemplateResponse
from django.shortcuts import redirect
from django.http import Http404
from www.views import BaseView, AuthedView, LeftSideBarMixin
from www.decorator import perm_required
from www.models import (Users, ServiceInfo, TenantRegionInfo, TenantServiceInfo,
                        ServiceDomain, PermRelService, PermRelTenant,
                        TenantServiceRelation, TenantServicesPort, TenantServiceEnv,
                        TenantServiceEnvVar, TenantServiceMountRelation,
                        ServiceExtendMethod, TenantServiceVolume)
from www.region import RegionInfo
from service_http import RegionServiceApi
from django.conf import settings
from www.tenantservice.baseservice import BaseTenantService, TenantUsedResource, TenantAccountService, CodeRepositoriesService
from www.monitorservice.monitorhook import MonitorHook
from www.utils.url import get_redirect_url
from www.utils.md5Util import md5fun

logger = logging.getLogger('default')
regionClient = RegionServiceApi()
monitorhook = MonitorHook()
tenantAccountService = TenantAccountService()
baseService = BaseTenantService()
tenantUsedResource = TenantUsedResource()
codeRepositoriesService = CodeRepositoriesService()


class TenantServiceAll(LeftSideBarMixin, AuthedView):

    def get_media(self):
        media = super(TenantServiceAll, self).get_media() + self.vendor(
            'www/css/owl.carousel.css', 'www/css/goodrainstyle.css',
            'www/js/jquery.cookie.js', 'www/js/service.js', 'www/js/common-scripts.js', 'www/js/jquery.dcjqaccordion.2.7.js',
            'www/js/jquery.scrollTo.min.js')
        return media

    def check_region(self):
        region = self.request.GET.get('region', None)
        if region is not None:
            if region in RegionInfo.region_names():
                if region == 'aws-bj-1' and self.tenant.region != 'aws-bj-1':
                    raise Http404
                self.response_region = region
            else:
                raise Http404

        if self.cookie_region == 'aws-bj-1':
            self.response_region == 'ali-sh'

        try:
            t_region, created = TenantRegionInfo.objects.get_or_create(tenant_id=self.tenant.tenant_id, region_name=self.response_region)
            self.tenant_region = t_region
        except Exception, e:
            logger.error(e)

    @never_cache
    @perm_required('tenant.tenant_access')
    def get(self, request, *args, **kwargs):
        self.check_region()

        context = self.get_context()
        try:
            num = TenantServiceInfo.objects.filter(tenant_id=self.tenant.tenant_id, service_region=self.response_region).count()
            # if num < 1:
            #     return self.redirect_to('/apps/{0}/app-create/'.format(self.tenant.tenant_name))
            tenantServiceList = context["tenantServiceList"]
            context["totalAppStatus"] = "active"
            context["totalFlow"] = 0
            context["totalAppNumber"] = len(tenantServiceList)
            context["tenantName"] = self.tenantName
            totalNum = PermRelTenant.objects.filter(tenant_id=self.tenant.ID).count()
            context["totalNum"] = totalNum
            context["curTenant"] = self.tenant
            context["tenant_balance"] = self.tenant.balance
            if self.tenant_region.service_status == 0:
                logger.debug("tenant.pause", "unpause tenant_id=" + self.tenant_region.tenant_id)
                regionClient.unpause(self.response_region, self.tenant_region.tenant_id)
                self.tenant_region.service_status = 1
                self.tenant_region.save()
            elif self.tenant_region.service_status == 3:
                logger.debug("tenant.pause", "system unpause tenant_id=" + self.tenant_region.tenant_id)
                regionClient.systemUnpause(self.response_region, self.tenant_region.tenant_id)
                self.tenant_region.service_status = 1
                self.tenant_region.save()
        except Exception as e:
            logger.exception(e)
        return TemplateResponse(self.request, "www/service_my.html", context)


class TenantService(LeftSideBarMixin, AuthedView):

    def init_request(self, *args, **kwargs):
        fr = self.request.GET.get('fr', None)
        if fr is not None and fr == 'statistic':
            self.statistic = True
            self.statistic_type = self.request.GET.get('type', 'history')
        else:
            self.statistic = False

    def get_media(self):
        media = super(TenantService, self).get_media() + self.vendor(
            'www/assets/jquery-easy-pie-chart/jquery.easy-pie-chart.css',
            'www/css/owl.carousel.css', 'www/css/goodrainstyle.css', 'www/css/style.css',
            'www/css/bootstrap-switch.min.css', 'www/css/bootstrap-editable.css',
            'www/css/style-responsive.css', 'www/js/jquery.cookie.js', 'www/js/service.js',
            'www/js/gr/basic.js', 'www/css/gr/basic.css', 'www/js/perms.js',
            'www/js/common-scripts.js', 'www/js/jquery.dcjqaccordion.2.7.js', 'www/js/jquery.scrollTo.min.js',
            'www/js/swfobject.js', 'www/js/web_socket.js', 'www/js/websoket-goodrain.js',
            'www/js/bootstrap-switch.min.js', 'www/js/bootstrap-editable.min.js', 'www/js/gr/multi_port.js'
        )
        if self.statistic:
            if self.statistic_type == 'history':
                append_media = (
                    'www/assets/nvd3/nv.d3.css', 'www/assets/nvd3/d3.min.js',
                    'www/assets/nvd3/nv.d3.min.js', 'www/js/gr/nvd3graph.js',
                )
            elif self.statistic_type == 'realtime':
                append_media = ('www/js/gr/ws_top.js',)
            media = media + self.vendor(*append_media)
        return media

    def get_context(self):
        context = super(TenantService, self).get_context()
        return context

    def get_user_perms(self):
        perm_users = []
        perm_template = {
            'name': None,
            'adminCheck': False,
            'developerCheck': False,
            'developerDisable': False,
            'viewerCheck': False,
            'viewerDisable': False,
        }
        identities = PermRelService.objects.filter(service_id=self.service.pk)
        for i in identities:
            user_perm = perm_template.copy()
            user = Users.objects.get(pk=i.user_id)
            user_perm['name'] = user.nick_name
            user_perm['email'] = user.email
            if i.identity == 'admin':
                user_perm.update({
                    'adminCheck': True,
                    'developerCheck': True,
                    'developerDisable': True,
                    'viewerCheck': True,
                    'viewerDisable': True,
                })
            elif i.identity == 'developer':
                user_perm.update({
                    'developerCheck': True,
                    'viewerCheck': True,
                    'viewerDisable': True,
                })
            elif i.identity == 'viewer':
                user_perm.update({'viewerCheck': True, 'viewerDisable': True})

            perm_users.append(user_perm)

        return perm_users

    def get_manage_app(self, http_port_str):
        service_manager = {"deployed": False}
        if self.service.service_key == 'mysql':
            has_managers = TenantServiceInfo.objects.filter(
                tenant_id=self.tenant.tenant_id, service_region=self.service.service_region, service_key='phpmyadmin')
            if has_managers:
                service_manager['deployed'] = True
                manager = has_managers[0]
                service_manager[
                    'url'] = 'http://{0}.{1}.{2}{3}:{4}'.format(manager.service_alias, self.tenant.tenant_name, self.service.service_region, settings.WILD_DOMAIN, http_port_str)
            else:
                service_manager['url'] = '/apps/{0}/service-deploy/?service_key=phpmyadmin'.format(self.tenant.tenant_name)
        return service_manager

    def memory_choices(self):
        memory_dict = {}
        memory_dict["128"] = '128M'
        memory_dict["256"] = '256M'
        memory_dict["512"] = '512M'
        memory_dict["1024"] = '1G'
        memory_dict["2048"] = '2G'
        memory_dict["4096"] = '4G'
        memory_dict["8192"] = '8G'
        memory_dict["16384"] = '16G'
        memory_dict["32768"] = '32G'
        memory_dict["65536"] = '64G'
        return memory_dict

    def extends_choices(self):
        extends_dict = {}
        extends_dict["state"] = u'有状态'
        extends_dict["stateless"] = u'无状态'
        extends_dict["state-expend"] = u'有状态可水平扩容'
        return extends_dict

    @never_cache
    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        self.response_region = self.service.service_region
        self.tenant_region = TenantRegionInfo.objects.get(tenant_id=self.service.tenant_id, region_name=self.service.service_region)
        context = self.get_context()
        context["tenantName"] = self.tenantName
        context['serviceAlias'] = self.serviceAlias
        fr = request.GET.get("fr", "deployed")
        context["fr"] = fr
        try:
            if self.service.category == "application":
                # forbidden blank page
                if self.service.code_version is None or self.service.code_version == "" or (self.service.git_project_id == 0 and self.service.git_url is None):
                    codeRepositoriesService.initRepositories(self.tenant, self.user, self.service, "gitlab_new", "", "", "master")
                # no upload code
                if self.service.language == "" or self.service.language is None:
                    codeRepositoriesService.codeCheck(self.service)
                    return self.redirect_to('/apps/{0}/{1}/app-waiting/'.format(self.tenant.tenant_name, self.service.service_alias))
                tse = TenantServiceEnv.objects.get(service_id=self.service.service_id)
                if tse.user_dependency is None or tse.user_dependency == "":
                    return self.redirect_to('/apps/{0}/{1}/app-waiting/'.format(self.tenant.tenant_name, self.service.service_alias))

            context["tenantServiceInfo"] = self.service
            tenantServiceList = context["tenantServiceList"]
            context["myAppStatus"] = "active"
            context["perm_users"] = self.get_user_perms()
            context["totalMemory"] = self.service.min_node * self.service.min_memory
            context["tenant"] = self.tenant
            context["region_name"] = self.service.service_region
            context["websocket_uri"] = settings.WEBSOCKET_URL[self.service.service_region]
            context["wild_domain"] = settings.WILD_DOMAINS[self.service.service_region]
            service_domain = False
            if TenantServicesPort.objects.filter(service_id=self.service.service_id, is_outer_service=True, protocol='http').exists():
                context["hasHttpServices"] = True
                service_domain = True

            http_port_str = settings.WILD_PORTS[self.response_region]
            context['http_port_str'] = ":" + http_port_str

            if fr == "deployed":
                if self.service.category == 'store':
                    service_manager = self.get_manage_app(http_port_str)
                    context['service_manager'] = service_manager

                # inner service
                innerPorts = {}
                tsps = TenantServicesPort.objects.filter(service_id=self.service.service_id, is_inner_service=True)
                for tsp in tsps:
                    innerPorts[tsp.container_port] = True

                if len(tsps) > 0:
                    context["hasInnerServices"] = True

                envMap = {}
                envVarlist = TenantServiceEnvVar.objects.filter(service_id=self.service.service_id, scope__in=("outer", "both"))
                if len(envVarlist) > 0:
                    for evnVarObj in envVarlist:
                        arr = envMap.get(evnVarObj.service_id)
                        if arr is None:
                            arr = []
                        arr.append(evnVarObj)
                        envMap[evnVarObj.service_id] = arr
                context["envMap"] = envMap
                
                baseservice = ServiceInfo.objects.get(service_key=self.service.service_key, version=self.service.version)
                if baseservice.update_version != self.service.update_version:
                    context["updateService"] = True

                context["docker_console"] = settings.MODULES["Docker_Console"]
                context["publish_service"] = settings.MODULES["Publish_Service"]

            elif fr == "relations":
                # service relationships
                tsrs = TenantServiceRelation.objects.filter(service_id=self.service.service_id)
                relationsids = []
                if len(tsrs) > 0:
                    for tsr in tsrs:
                        relationsids.append(tsr.dep_service_id)
                context["serviceIds"] = relationsids
                # service map
                map = {}
                sids = [self.service.service_id]
                for tenantService in tenantServiceList:
                    if TenantServicesPort.objects.filter(service_id=tenantService.service_id, is_inner_service=True).exists():
                        sids.append(tenantService.service_id)
                        map[tenantService.service_id] = tenantService
                    if tenantService.service_id in relationsids:
                        map[tenantService.service_id] = tenantService
                context["serviceMap"] = map
                # env map
                envMap = {}
                envVarlist = TenantServiceEnvVar.objects.filter(service_id__in=sids, scope__in=("outer", "both"))
                for evnVarObj in envVarlist:
                    arr = envMap.get(evnVarObj.service_id)
                    if arr is None:
                        arr = []
                    arr.append(evnVarObj)
                    envMap[evnVarObj.service_id] = arr
                context["envMap"] = envMap

                # add dir mnt
                mtsrs = TenantServiceMountRelation.objects.filter(service_id=self.service.service_id)
                mntsids = []
                if len(mtsrs) > 0:
                    for mnt in mtsrs:
                        mntsids.append(mnt.dep_service_id)
                context["mntsids"] = mntsids

            elif fr == "statistic":
                context['statistic_type'] = self.statistic_type
                if self.service.service_type in ('mysql',):
                    context['ws_topic'] = '{0}.{1}.statistic'.format(''.join(list(self.tenant.tenant_id)[1::2]), ''.join(list(self.service.service_id)[::2]))
                else:
                    context['ws_topic'] = '{0}.{1}.statistic'.format(self.tenant.tenant_name, self.service.service_alias)
            elif fr == "log":
                pass
            elif fr == "settings":
                nodeList = []
                memoryList = []
                try:
                    sem = ServiceExtendMethod.objects.get(service_key=self.service.service_key, app_version=self.service.version)
                    nodeList.append(sem.min_node)
                    next_node = sem.min_node + sem.step_node
                    while(next_node <= sem.max_node):
                        nodeList.append(next_node)
                        next_node = next_node + sem.step_node

                    num = 1
                    memoryList.append(str(sem.min_memory))
                    next_memory = sem.min_memory * pow(2, num)
                    while(next_memory <= sem.max_memory):
                        memoryList.append(str(next_memory))
                        num = num + 1
                        next_memory = sem.min_memory * pow(2, num)
                except Exception as e:
                    pass
                context["nodeList"] = nodeList
                context["memoryList"] = memoryList
                context["memorydict"] = self.memory_choices()
                context["extends_choices"] = self.extends_choices()
                context["add_port"] = settings.MODULES["Add_Port"]
                context["git_tag"] = settings.MODULES["GitLab_Project"]

                if service_domain:
                    # service git repository
                    context["httpGitUrl"] = codeRepositoriesService.showGitUrl(self.service)
                    # service domain
                    try:
                        domain = ServiceDomain.objects.get(service_id=self.service.service_id)
                        context["serviceDomain"] = domain
                    except Exception as e:
                        pass
                context["ports"] = TenantServicesPort.objects.filter(service_id=self.service.service_id)
                context["envs"] = TenantServiceEnvVar.objects.filter(service_id=self.service.service_id, scope="inner").exclude(container_port= -1)

                # 获取挂载信息,查询
                volume_list = TenantServiceVolume.objects.filter(service_id=self.service.service_id)
                result_list = []
                if self.service.category == "application":
                    for volume in list(volume_list):
                        tmp_path = volume.volume_path
                        if tmp_path:
                            volume.volume_path = tmp_path.replace("/app", "", 1)
                        # tmp_path = volume.host_path
                        # if tmp_path:
                        #     tmp_array = tmp_path.split(self.service.service_id)
                        #     if len(tmp_array) == 2:
                        #         volume.host_path = "/data" + tmp_array[1]
                        #     else:
                        #         volume.host_path = "/data" + tmp_path
                        result_list.append(volume)
                context["volume_list"] = result_list
            else:
                return self.redirect_to('/apps/{0}/{1}/detail/'.format(self.tenant.tenant_name, self.service.service_alias))

            if self.tenant_region.service_status == 0:
                logger.debug("tenant.pause", "unpause tenant_id=" + self.tenant_region.tenant_id)
                regionClient.unpause(self.service.service_region, self.tenant_region.tenant_id)
                self.tenant_region.service_status = 1
                self.tenant_region.save()

            elif self.tenant_region.service_status == 3:
                logger.debug("tenant.pause", "system unpause tenant_id=" + self.tenant_region.tenant_id)
                regionClient.systemUnpause(self.service.service_region, self.tenant_region.tenant_id)
                self.tenant_region.service_status = 1
                self.tenant_region.save()
        except Exception as e:
            logger.exception(e)
        return TemplateResponse(self.request, "www/service_detail.html", context)


class ServiceGitHub(BaseView):

    @never_cache
    def get(self, request, *args, **kwargs):
        code = request.GET.get("code", "")
        state = request.GET.get("state", "")
        if code != "" and state != "" and int(state) == self.user.pk:
            result = codeRepositoriesService.get_gitHub_access_token(code)
            content = json.loads(result)
            token = content["access_token"]
            user = Users.objects.get(user_id=int(state))
            user.github_token = token
            user.save()
        tenantName = request.session.get("app_tenant")
        logger.debug(tenantName)
        return self.redirect_to("/apps/" + tenantName + "/app-create/?from=git")


class ServiceLatestLog(AuthedView):

    def get_media(self):
        media = super(ServiceLatestLog, self).get_media() + self.vendor('www/css/owl.carousel.css', 'www/css/goodrainstyle.css',
                                                                        'www/js/jquery.cookie.js', 'www/js/common-scripts.js', 'www/js/jquery.dcjqaccordion.2.7.js', 'www/js/jquery.scrollTo.min.js')
        return media

    @never_cache
    def get(self, request, *args, **kwargs):
        try:
            context = self.get_context()
            data = {}
            data['number'] = 1000
            body = regionClient.latest_log(self.service.service_region, self.service.service_id, json.dumps(data))
            context["lines"] = body["lines"]
        except Exception as e:
            logger.exception(e)
        return TemplateResponse(self.request, "www/service_docker_log.html", context)


class ServiceHistoryLog(AuthedView):

    def get_media(self):
        media = super(ServiceHistoryLog, self).get_media() + self.vendor('www/css/owl.carousel.css', 'www/css/goodrainstyle.css',
                                                                         'www/js/jquery.cookie.js', 'www/js/common-scripts.js', 'www/js/jquery.dcjqaccordion.2.7.js', 'www/js/jquery.scrollTo.min.js')
        return media

    @never_cache
    def get(self, request, *args, **kwargs):
        try:
            context = self.get_context()
            body = regionClient.history_log(self.service.service_region, self.service.service_id)
            context["log_paths"] = body["log_path"]
            context["tenantService"] = self.service
            context["log_domain"] = settings.LOG_DOMAIN[self.service.service_region]
        except Exception as e:
            logger.exception(e)
        return TemplateResponse(self.request, "www/service_history_log.html", context)


class ServiceDockerContainer(AuthedView):

    def get_media(self):
        media = super(ServiceDockerContainer, self).get_media()
        return media

    @never_cache
    def get(self, request, *args, **kwargs):
        context = self.get_context()
        response = redirect(get_redirect_url("/apps/{0}/{1}/detail/".format(self.tenantName, self.serviceAlias), request))
        try:
            docker_c_id = request.COOKIES.get('docker_c_id', '')
            docker_h_id = request.COOKIES.get('docker_h_id', '')
            docker_s_id = request.COOKIES.get('docker_s_id', '')
            if docker_c_id != "" and docker_h_id != "" and docker_s_id != "" and docker_s_id == self.service.service_id:
                context["tenant_id"] = self.service.tenant_id
                context["service_id"] = docker_s_id
                context["ctn_id"] = docker_c_id
                context["host_id"] = docker_h_id
                context["md5"] = md5fun(self.service.tenant_id + "_" + docker_s_id + "_" + docker_c_id)
                context["wss"] = settings.DOCKER_WSS_URL.get("type", "ws") + "://" + docker_h_id + settings.DOCKER_WSS_URL[self.service.service_region] + "/ws"
                response = TemplateResponse(self.request, "www/console.html", context)
            response.delete_cookie('docker_c_id')
            response.delete_cookie('docker_h_id')
            response.delete_cookie('docker_s_id')
        except Exception as e:
            logger.exception(e)
        return response
