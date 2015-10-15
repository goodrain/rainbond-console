# -*- coding: utf8 -*-
import logging
import uuid
import hashlib
import datetime
import json

from django.views.decorators.cache import never_cache
from django.template.response import TemplateResponse
from django.http.response import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from www.views import BaseView, AuthedView, LeftSideBarMixin
from www.decorator import perm_required
from www.models import Users, TenantServiceInfo, ServiceDomain, PermRelService, PermRelTenant, TenantServiceRelation, TenantServiceEnv, TenantServiceEnvVar
from service_http import RegionServiceApi
from gitlab_http import GitlabApi
from github_http import GitHubApi
from django.conf import settings

logger = logging.getLogger('default')

gitClient = GitlabApi()

gitHubClient = GitHubApi()

regionClient = RegionServiceApi()


class TenantServiceAll(LeftSideBarMixin, AuthedView):

    def get_media(self):
        media = super(TenantServiceAll, self).get_media() + self.vendor(
            'www/css/owl.carousel.css', 'www/css/goodrainstyle.css',
            'www/js/jquery.cookie.js', 'www/js/service.js', 'www/js/common-scripts.js', 'www/js/jquery.dcjqaccordion.2.7.js',
            'www/js/jquery.scrollTo.min.js')
        return media

    @never_cache
    @perm_required('tenant.tenant_access')
    def get(self, request, *args, **kwargs):
        region = self.request.GET.get('region', None)
        if region is not None:
            self.response_region = region

        context = self.get_context()
        try:
            num = TenantServiceInfo.objects.filter(tenant_id=self.tenant.tenant_id, service_region=self.response_region).count()
            if num < 1:
                return HttpResponseRedirect('/apps/{0}/app-create/'.format(self.tenant.tenant_name))
            tenantServiceList = context["tenantServiceList"]
            context["totalAppStatus"] = "active"
            context["totalFlow"] = 0
            context["totalAppNumber"] = len(tenantServiceList)
            context["tenantName"] = self.tenantName
            totalNum = PermRelTenant.objects.filter(tenant_id=self.tenant.ID).count()
            context["totalNum"] = totalNum
            context["curTenant"] = self.tenant
            context["tenant_balance"] = self.tenant.balance
            if self.tenant.service_status == 0:
                logger.debug("tenant.pause", "unpause tenant_id=" + self.tenant.tenant_id)
                regionClient.unpause(self.response_region, self.tenant.tenant_id)
                self.tenant.service_status = 1
                self.tenant.save()
            if self.tenant.service_status == 3:
                logger.debug("tenant.pause", "system unpause tenant_id=" + self.tenant.tenant_id)
                regionClient.systemUnpause(self.response_region, self.tenant.tenant_id)
                self.tenant.service_status = 1
                self.tenant.save()
        except Exception as e:
            logger.exception(e)
        return TemplateResponse(self.request, "www/service_my.html", context)


class TenantService(LeftSideBarMixin, AuthedView):

    def init_request(self, *args, **kwargs):
        show_graph = self.request.GET.get('show_graph', None)
        if show_graph is not None and show_graph == 'yes':
            self.show_graph = True
        else:
            self.show_graph = False
        # 临时兼容
        if self.service.service_region not in settings.REGION_LIST:
            region = self.tenant.region
            self.service.service_region = region
            self.service.save()

    def get_media(self):
        media = super(TenantService, self).get_media() + self.vendor(
            'www/assets/jquery-easy-pie-chart/jquery.easy-pie-chart.css',
            'www/css/owl.carousel.css', 'www/css/goodrainstyle.css', 'www/css/style.css',
            'www/css/style-responsive.css', 'www/js/jquery.cookie.js', 'www/js/service.js',
            'www/js/gr/basic.js', 'www/css/gr/basic.css', 'www/js/perms.js',
            'www/js/common-scripts.js', 'www/js/jquery.dcjqaccordion.2.7.js', 'www/js/jquery.scrollTo.min.js',
            'www/js/swfobject.js', 'www/js/web_socket.js', 'www/js/websoket-goodrain.js'
        )
        if self.show_graph:
            media = media + self.vendor(
                'www/assets/nvd3/nv.d3.css', 'www/assets/nvd3/d3.min.js',
                'www/assets/nvd3/nv.d3.min.js', 'www/js/gr/nvd3graph.js',
            )
        return media

    def get_context(self):
        context = super(TenantService, self).get_context()
        if self.show_graph:
            context['show_graph'] = True
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
                gitClient.addProjectMember(project_id, self.user.git_user_id, 40)
                gitClient.addProjectMember(project_id, 2, 20)
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
            has_managers = TenantServiceInfo.objects.filter(tenant_id=self.tenant.tenant_id, service_key='phpmyadmin')
            if has_managers:
                service_manager['deployed'] = True
                manager = has_managers[0]
                service_manager[
                    'url'] = 'http://{0}.{1}.{2}.goodrain.net{3}'.format(manager.service_alias, self.tenant.tenant_name, self.tenant.region, http_port_str)
            else:
                service_manager['url'] = '/apps/{0}/service-deploy/?service_key=phpmyadmin'.format(self.tenant.tenant_name)
        return service_manager

    @never_cache
    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        self.response_region = self.service.service_region
        context = self.get_context()
        context["tenantName"] = self.tenantName
        context['serviceAlias'] = self.serviceAlias
        tab_index = request.GET.get("fr", "0")
        context['tab_index'] = tab_index
        http_port_str = '' if self.tenant.region == 'aws-jp-1' else ':10080'
        context['http_port_str'] = http_port_str
        try:
            if self.service.category == "application" and self.service.ID > 598:
                # no create gitlab repos
                self.createGitProject()
                # no upload code
                if self.service.language == "" or self.service.language is None:
                    self.sendCodeCheckMsg()
                    return redirect('/apps/{0}/{1}/app-waiting/'.format(self.tenant.tenant_name, self.service.service_alias))
                tse = TenantServiceEnv.objects.get(service_id=self.service.service_id)
                if tse.user_dependency is None or tse.user_dependency == "":
                    return redirect('/apps/{0}/{1}/app-waiting/'.format(self.tenant.tenant_name, self.service.service_alias))
            elif self.service.category == 'store':
                service_manager = self.get_manage_app(http_port_str)
                context['service_manager'] = service_manager

            service_id = self.service.service_id
            context["tenantServiceInfo"] = self.service
            tenantServiceList = context["tenantServiceList"]
            context["tenantName"] = self.tenantName
            context["myAppStatus"] = "active"
            context["perm_users"] = self.get_user_perms()
            context["nodeList"] = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
            context["memoryList"] = [128, 256, 512, 1024, 2048, 4096]
            context["tenant"] = self.tenant
            context["totalMemory"] = self.service.min_node * self.service.min_memory

            # service relationships
            tsrs = TenantServiceRelation.objects.filter(tenant_id=self.tenant.tenant_id, service_id=service_id)
            relationsids = []
            if len(tsrs) > 0:
                for tsr in tsrs:
                    relationsids.append(tsr.dep_service_id)
            context["serviceIds"] = relationsids

            map = {}
            sids = [service_id]
            for tenantService in tenantServiceList:
                if tenantService.is_service:
                    sids.append(tenantService.service_id)
                    map[tenantService.service_id] = tenantService
            context["serviceMap"] = map

            # relationships password
            envMap = {}
            envVarlist = TenantServiceEnvVar.objects.filter(service_id__in=sids)
            if len(envVarlist) > 0:
                for evnVarObj in envVarlist:
                    arr = envMap.get(evnVarObj.service_id)
                    if arr is None:
                        arr = []
                    arr.append(evnVarObj)
                    envMap[evnVarObj.service_id] = arr
            context["envMap"] = envMap

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

            websocket_info = settings.WEBSOCKET_URL
            context["websocket_uri"] = websocket_info[self.tenant.region]

            if self.tenant.service_status == 0:
                logger.debug("tenant.pause", "unpause tenant_id=" + self.tenant.tenant_id)
                regionClient.unpause(self.service.service_region, self.tenant.tenant_id)
                self.tenant.service_status = 1
                self.tenant.save()

            if self.tenant.service_status == 3:
                logger.debug("tenant.pause", "system unpause tenant_id=" + self.tenant.tenant_id)
                regionClient.systemUnpause(self.service.service_region, self.tenant.tenant_id)
                self.tenant.service_status = 1
                self.tenant.save()

        except Exception as e:
            logger.exception(e)
        return TemplateResponse(self.request, "www/service_detail.html", context)

# d82ebe5675f2ea0d0a7b


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
        return HttpResponseRedirect("/apps/" + tenantName + "/app-create/?from=git")


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
