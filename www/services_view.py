# -*- coding: utf8 -*-
import logging
import uuid
import hashlib
import datetime
import json

from django.views.decorators.cache import never_cache
from django.template.response import TemplateResponse
from django.http.response import HttpResponse
from django.shortcuts import redirect
from django.http import Http404
from www.views import BaseView, AuthedView, LeftSideBarMixin, RegionOperateMixin
from www.decorator import perm_required
from www.models import Users, ServiceInfo, TenantRegionInfo, Tenants, TenantServiceInfo, ServiceDomain, PermRelService, PermRelTenant, TenantServiceRelation, TenantServiceAuth, TenantServiceEnv, TenantServiceEnvVar
from www.region import RegionInfo
from service_http import RegionServiceApi
from gitlab_http import GitlabApi
from github_http import GitHubApi
from django.conf import settings
from www.tenantservice.baseservice import BaseTenantService, TenantUsedResource
from www.monitorservice.monitorhook import MonitorHook

logger = logging.getLogger('default')
gitClient = GitlabApi()
gitHubClient = GitHubApi()
regionClient = RegionServiceApi()
monitorhook = MonitorHook()

class TenantServiceAll(LeftSideBarMixin, RegionOperateMixin, AuthedView):

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
            if created or not t_region.is_active:
                logger.info("tenant.region_init", "init region {0} for tenant {1}".format(self.response_region, self.tenant.tenant_name))
                success = self.init_for_region(self.response_region, self.tenant.tenant_name, self.tenant.tenant_id)
                t_region.is_active = True if success else False
                t_region.save()
        except Exception, e:
            logger.error(e)

    @never_cache
    @perm_required('tenant.tenant_access')
    def get(self, request, *args, **kwargs):
        self.check_region()

        context = self.get_context()
        try:
            num = TenantServiceInfo.objects.filter(tenant_id=self.tenant.tenant_id, service_region=self.response_region).count()
            if num < 1:
                return self.redirect_to('/apps/{0}/app-create/'.format(self.tenant.tenant_name))
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
            'www/css/style-responsive.css', 'www/js/jquery.cookie.js', 'www/js/service.js',
            'www/js/gr/basic.js', 'www/css/gr/basic.css', 'www/js/perms.js',
            'www/js/common-scripts.js', 'www/js/jquery.dcjqaccordion.2.7.js', 'www/js/jquery.scrollTo.min.js',
            'www/js/swfobject.js', 'www/js/web_socket.js', 'www/js/websoket-goodrain.js'
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

    def createGitProject(self):
        if self.service.code_from == "gitlab_new" and self.service.git_project_id == 0 and self.user.git_user_id > 0:
            project_id = gitClient.createProject(self.tenantName + "_" + self.serviceAlias)
            logger.debug(project_id)
            if project_id > 0:
                gitClient.addProjectMember(project_id, self.user.git_user_id, 'master')
                gitClient.addProjectMember(project_id, 2, 'reporter')
                ts = TenantServiceInfo.objects.get(service_id=self.service.service_id)
                ts.git_project_id = project_id
                ts.git_url = "git@code.goodrain.com:app/" + self.tenantName + "_" + self.serviceAlias + ".git"
                ts.save()

    def sendCodeCheckMsg(self):
        data = {}
        data["tenant_id"] = self.service.tenant_id
        data["service_id"] = self.service.service_id
        if self.service.code_from != "github":
            gitUrl = "--branch " + self.service.code_version + " --depth 1 " + self.service.git_url
            data["git_url"] = gitUrl
        else:
            clone_url = self.service.git_url
            code_user = clone_url.split("/")[3]
            code_project_name = clone_url.split("/")[4].split(".")[0]
            createUser = Users.objects.get(user_id=self.service.creater)
            clone_url = "https://" + createUser.github_token + "@github.com/" + code_user + "/" + code_project_name + ".git"
            gitUrl = "--branch " + self.service.code_version + " --depth 1 " + clone_url
            data["git_url"] = gitUrl
        task = {}
        task["service_id"] = self.service.service_id
        task["data"] = data
        task["tube"] = "code_check"
        logger.debug(json.dumps(task))
        regionClient.writeToRegionBeanstalk(self.service.service_region, self.service.service_id, json.dumps(task))

    def get_manage_app(self, http_port_str):
        service_manager = {"deployed": False}
        if self.service.service_key == 'mysql':
            has_managers = TenantServiceInfo.objects.filter(
                tenant_id=self.tenant.tenant_id, service_region=self.service.service_region, service_key='phpmyadmin')
            if has_managers:
                service_manager['deployed'] = True
                manager = has_managers[0]
                service_manager[
                    'url'] = 'http://{0}.{1}.{2}.goodrain.net{3}'.format(manager.service_alias, self.tenant.tenant_name, self.service.service_region, http_port_str)
            else:
                service_manager['url'] = '/apps/{0}/service-deploy/?service_key=phpmyadmin'.format(self.tenant.tenant_name)
        return service_manager

    def memory_choices(self):
        choices = [(128, '128M'), (256, '256M'), (512, '512M'), (1024, '1G'), (2048, '2G'), (4096, '4G'), (8192, '8G')]
        if self.service.service_key == 'mysql':
            choices.extend([
                (16384, '16G'), (32768, '32G'), (65536, '64G')
            ])
        choice_list = []
        for value, label in choices:
            choice_list.append({"label": label, "value": value})
        return choice_list

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
            if self.service.category == "application" and self.service.ID > 598:
                # no create gitlab repos
                self.createGitProject()
                # no upload code
                if self.service.language == "" or self.service.language is None:
                    self.sendCodeCheckMsg()
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

            if fr == "deployed":
                http_port_str = '' if self.response_region == 'aws-jp-1' else ':10080'
                context['http_port_str'] = http_port_str
                if self.service.category == 'store':
                    service_manager = self.get_manage_app(http_port_str)
                    context['service_manager'] = service_manager
                # relationships password
                if self.service.is_service:
                    sids = [self.service.service_id]
                    envMap = {}
                    envVarlist = TenantServiceEnvVar.objects.filter(service_id__in=sids)
                    logger.debug(len(envVarlist))
                    if len(envVarlist) > 0:
                        for evnVarObj in envVarlist:
                            arr = envMap.get(evnVarObj.service_id)
                            if arr is None:
                                arr = []
                            arr.append(evnVarObj)
                            envMap[evnVarObj.service_id] = arr
                    context["envMap"] = envMap
            elif fr == "relations":
                # service relationships
                tsrs = TenantServiceRelation.objects.filter(tenant_id=self.tenant.tenant_id, service_id=self.service.service_id)
                relationsids = []
                if len(tsrs) > 0:
                    for tsr in tsrs:
                        relationsids.append(tsr.dep_service_id)
                context["serviceIds"] = relationsids
                # service map
                map = {}
                sids = [self.service.service_id]
                for tenantService in tenantServiceList:
                    if tenantService.is_service:
                        sids.append(tenantService.service_id)
                        map[tenantService.service_id] = tenantService
                context["serviceMap"] = map
                # env map
                envMap = {}
                envVarlist = TenantServiceEnvVar.objects.filter(service_id__in=sids)
                for evnVarObj in envVarlist:
                    arr = envMap.get(evnVarObj.service_id)
                    if arr is None:
                        arr = []
                    arr.append(evnVarObj)
                    envMap[evnVarObj.service_id] = arr
                context["envMap"] = envMap
            elif fr == "statistic":
                context['statistic_type'] = self.statistic_type
                if self.service.service_key in ('mysql',):
                    context['ws_topic'] = '{0}.{1}.statistic'.format(''.join(list(self.tenant.tenant_id)[1::2]), ''.join(list(self.service.service_id)[::2]))
                else:
                    context['ws_topic'] = '{0}.{1}.statistic'.format(self.tenant.tenant_name, self.service.service_alias)
            elif fr == "log":
                pass
            elif fr == "settings":
                context["nodeList"] = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
                context["memoryList"] = self.memory_choices()
                if self.service.category == "application" or self.service.category == "manager":
                    # service git repository
                    httpGitUrl = ""
                    if self.service.code_from == "gitlab_new" or self.service.code_from == "gitlab_exit":
                        cur_git_url = self.service.git_url.split("/")
                        httpGitUrl = "http://code.goodrain.com/app/" + cur_git_url[1]
                    else:
                        httpGitUrl = self.service.git_url
                    context["httpGitUrl"] = httpGitUrl
                    # service domain
                    try:
                        domain = ServiceDomain.objects.get(service_id=self.service.service_id)
                        context["serviceDomain"] = domain
                    except Exception as e:
                        pass
                if self.service.is_service:
                    sids = [self.service.service_id]
                    envMap = {}
                    envVarlist = TenantServiceEnvVar.objects.filter(service_id__in=sids)
                    for evnVarObj in envVarlist:
                        arr = envMap.get(evnVarObj.service_id)
                        if arr is None:
                            arr = []
                        arr.append(evnVarObj)
                        envMap[evnVarObj.service_id] = arr
                    context["envMap"] = envMap
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
            result = gitHubClient.get_access_token(code)
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
        media = super(ServiceLatestLog, self).get_media() + self.vendor('www/css/owl.carousel.css', 'www/css/goodrainstyle.css', 'www/css/jquery-ui.css',
                                                                        'www/js/jquery.cookie.js', 'www/js/common-scripts.js', 'www/js/jquery.dcjqaccordion.2.7.js',
                                                                        'www/js/jquery.scrollTo.min.js')
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
        media = super(ServiceHistoryLog, self).get_media() + self.vendor('www/css/owl.carousel.css', 'www/css/goodrainstyle.css', 'www/css/jquery-ui.css',
                                                                         'www/js/jquery.cookie.js', 'www/js/common-scripts.js', 'www/js/jquery.dcjqaccordion.2.7.js',
                                                                         'www/js/jquery.scrollTo.min.js')
        return media

    @never_cache
    def get(self, request, *args, **kwargs):
        try:
            context = self.get_context()
            body = regionClient.history_log(self.service.service_region, self.service.service_id)
            context["log_paths"] = body["log_path"]
            context["tenantService"] = self.service
        except Exception as e:
            logger.exception(e)
        return TemplateResponse(self.request, "www/service_history_log.html", context)
    
    
class ServiceAutoDeploy(BaseView):
    
    def getTenants(self, user_id):
        tenants_has = PermRelTenant.objects.filter(user_id=user_id)
        if tenants_has:
            tenant_pk = tenants_has[0].tenant_id
            tenant = Tenants.objects.get(pk=tenant_pk)
            return tenant
        else:
            return None

    def app_create(self, user, tenant, app_name, git_url, service_code_from):
        status = ""
        uid = str(uuid.uuid4())
        service_id = hashlib.md5(uid.encode("UTF-8")).hexdigest()
        try:
            tenant_id = tenant.tenant_id
            
            if tenant.pay_type == "payed":
                tenant_region = TenantRegionInfo.objects.get(tenant_id=tenant.tenant_id, region_name=tenant.region)
                if tenant_region.service_status == 2:
                    status = "owed"
                    return  status
            
            service_alias = app_name.lower()
            # get base service
            service = ServiceInfo.objects.get(service_key="application")
            # create console tenant service
            num = TenantServiceInfo.objects.filter(tenant_id=tenant_id, service_alias=service_alias).count()
            if num > 0:
                status = "exist"
                return  status             
            # calculate resource
            tenantUsedResource = TenantUsedResource()
            flag = tenantUsedResource.predict_next_memory(tenant, service.min_memory)
            if not flag:
                if tenant.pay_type == "free":
                    status = "over_memory"
                else:
                    status = "over_money"
                return  status
            # create console service
            baseService = BaseTenantService()
            service.desc = ""
            newTenantService = baseService.create_service(
                service_id, tenant_id, service_alias, service, user.pk, region=tenant.region)
            monitorhook.serviceMonitor(user.nick_name, newTenantService, 'create_service', True)
            # code repos
            if service_code_from == "gitlab_new":
                project_id = 0
                if user.git_user_id > 0:
                    project_id = gitClient.createProject(tenant.tenant_name + "_" + service_alias)
                    logger.debug(project_id)
                    monitorhook.gitProjectMonitor(user.nick_name, newTenantService, 'create_git_project', project_id)
                    if project_id > 0:
                        gitClient.addProjectMember(project_id, user.git_user_id, 'master')
                        gitClient.addProjectMember(project_id, 2, 'reporter')
                        ts = TenantServiceInfo.objects.get(service_id=service_id)
                        ts.git_project_id = project_id
                        ts.git_url = "git@code.goodrain.com:app/" + tenant.tenant_name + "_" + service_alias + ".git"
                        ts.code_from = service_code_from
                        ts.code_version = "master"
                        ts.save()
                        gitClient.createWebHook(project_id)
                    else:
                        ts = TenantServiceInfo.objects.get(service_id=service_id)
                        ts.code_from = service_code_from
                        ts.code_version = "master"
                        ts.save()
            elif service_code_from == "gitlab_exit":
                ts = TenantServiceInfo.objects.get(service_id=service_id)
                ts.git_project_id = "0"
                ts.git_url = git_url
                ts.code_from = service_code_from
                ts.code_version = "master"
                ts.save()

                data = {}
                data["tenant_id"] = ts.tenant_id
                data["service_id"] = ts.service_id
                data["git_url"] = "--branch " + ts.code_version + " --depth 1 " + ts.git_url
                task = {}
                task["tube"] = "code_check"
                task["service_id"] = ts.service_id
                task["data"] = data
                logger.debug(json.dumps(task))
                regionClient.writeToRegionBeanstalk(tenant.region, ts.service_id, json.dumps(task))
            # create region tenantservice
            baseService.create_region_service(newTenantService, tenant.tenant_name, tenant.region, user.nick_name)
            monitorhook.serviceMonitor(user.nick_name, newTenantService, 'init_region_service', True)
            # create service env
            baseService.create_service_env(tenant_id, service_id, tenant.region)
            # record log
            status = "success"
        except Exception as e:
            logger.exception(e)
            TenantServiceInfo.objects.filter(service_id=service_id).delete()
            tempTenantService = TenantServiceInfo.objects.get(service_id=service_id)
            monitorhook.serviceMonitor(user.nick_name, tempTenantService, 'create_service_error', False)
            status = "failure"
        return status
    
    @never_cache
    def get(self, request, *args, **kwargs):
        app_ty = request.GET.get("ty", "")
        app_an = request.GET.get("an", "")
        app_sd = request.GET.get("sd", "")
        fr = request.GET.get("fr", "")
        if fr != "" and fr == "www_app":
            app_ty = request.COOKIES.get('app_ty', '')            
            app_an = request.COOKIES.get('app_an', '')            
            app_sd = request.COOKIES.get('app_sd', '') 
        logger.debug("app_ty=" + app_ty)
        logger.debug("app_an=" + app_an)
        logger.debug("app_sd=" + app_sd)                                
        status = ""
        if self.user is not None and self.user.pk is not None:
            tenant = self.getTenants(self.user.pk)
            if tenant is None:
                return self.redirect_to("/login")            
            isSetAppName = False
            if app_ty == "1":
                if app_an != "" and app_sd != "":
                    status = self.app_create(self.user, tenant, app_an, app_sd, "gitlab_exit")
                    if status == "success":
                        response = redirect("/apps/{0}/{1}/app-dependency/".format(tenant.tenant_name, app_an))
                    else:
                        response = redirect("/apps/{0}/app-create/".format(tenant.tenant_name))
                        response.set_cookie('app_status', status)
                        isSetAppName = True
                else:
                    response = redirect("/apps/{0}/app-create/".format(tenant.tenant_name))
            elif app_ty == "2":
                if app_an == "":
                    app_an = "demo"
                if app_sd == "":
                    status = self.app_create(self.user, tenant, app_an, app_sd, "gitlab_new")
                else:
                    status = self.app_create(self.user, tenant, app_an, app_sd, "gitlab_exit")
                if status == "success":
                    response = redirect("/apps/{0}/{1}/app-dependency/".format(tenant.tenant_name, app_an))
                else:
                    response = redirect("/apps/{0}/app-create/".format(tenant.tenant_name))
                    response.set_cookie('app_status', status)
                    isSetAppName = True
            elif app_ty == "3":                    
                response = redirect("/apps/{0}/service-deploy/?service_key={1}".format(tenant.tenant_name, app_sd))
            else:
                response = redirect("/apps/{0}".format(tenant.tenant_name))
            
            response.delete_cookie('app_ty')            
            response.delete_cookie('app_sd')
            if not isSetAppName:
                response.delete_cookie('app_an')
        else:
            response = redirect("/login")
            if app_ty != "":
                response.set_cookie('app_ty', app_ty)
                response.set_cookie('app_an', app_an)
                response.set_cookie('app_sd', app_sd)
        return response
    
    @never_cache
    def post(self, request, *args, **kwargs):
        app_ty = request.POST.get("ty", "")
        app_an = request.POST.get("an", "")
        app_sd = request.POST.get("sd", "")
        fr = request.GET.get("fr", "")
        if fr != "" and fr == "www_app":
            app_ty = request.COOKIES.get('app_ty', '')            
            app_an = request.COOKIES.get('app_an', '')            
            app_sd = request.COOKIES.get('app_sd', '') 
        logger.debug("app_ty=" + app_ty)
        logger.debug("app_an=" + app_an)
        logger.debug("app_sd=" + app_sd)                                
        status = ""
        if self.user is not None and self.user.pk is not None:
            tenant = self.getTenants(self.user.pk)
            if tenant is None:
                return self.redirect_to("/login")            
            isSetAppName = False
            if app_ty == "1":
                if app_an != "" and app_sd != "":
                    status = self.app_create(self.user, tenant, app_an, app_sd, "gitlab_exit")
                    if status == "success":
                        response = redirect("/apps/{0}/{1}/app-dependency/".format(tenant.tenant_name, app_an))
                    else:
                        response = redirect("/apps/{0}/app-create/".format(tenant.tenant_name))
                        response.set_cookie('app_status', status)
                        isSetAppName = True
                else:
                    response = redirect("/apps/{0}/app-create/".format(tenant.tenant_name))
            elif app_ty == "2":
                if app_an == "":
                    app_an = "demo"
                if app_sd == "":
                    status = self.app_create(self.user, tenant, app_an, app_sd, "gitlab_new")
                else:
                    status = self.app_create(self.user, tenant, app_an, app_sd, "gitlab_exit")
                if status == "success":
                    response = redirect("/apps/{0}/{1}/app-dependency/".format(tenant.tenant_name, app_an))
                else:
                    response = redirect("/apps/{0}/app-create/".format(tenant.tenant_name))
                    response.set_cookie('app_status', status)
                    isSetAppName = True
            elif app_ty == "3":                    
                response = redirect("/apps/{0}/service-deploy/?service_key={1}".format(tenant.tenant_name, app_sd))
            else:
                response = redirect("/apps/{0}".format(tenant.tenant_name))
            
            response.delete_cookie('app_ty')            
            response.delete_cookie('app_sd')
            if not isSetAppName:
                response.delete_cookie('app_an')
        else:
            response = redirect("/login")
            if app_ty != "":
                response.set_cookie('app_ty', app_ty)
                response.set_cookie('app_an', app_an)
                response.set_cookie('app_sd', app_sd)
        return response

class GitLabManager(AuthedView):

    @never_cache
    def get(self, request, *args, **kwargs):
        # result=gitClient.createUser("git2@goodrain.com ", "12345678", "git2", "git2")
        # logger.debug(result)
        # result = gitClient.getProjectEvent(2)
        project_id = 0
        # if self.user.git_user_id > 0:
        #    project_id = gitClient.createProject("test"+"_"+"app")
        #    logger.debug(project_id)
        #    if project_id > 0:
        # ts = TenantServiceInfo.objects.get(service_id=service_id)
        # ts.git_project_id = project_id
        # ts.save()
        #        gitClient.addProjectMember(project_id,self.user.git_user_id,30)
        #        gitClient.addProjectMember(project_id,2,20)
        return HttpResponse(str(project_id))
