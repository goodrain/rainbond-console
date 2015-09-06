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
from django.views.decorators.csrf import csrf_exempt
from www.views import BaseView, AuthedView
from www.decorator import perm_required
from www.models import Users, Tenants, ServiceInfo, TenantServiceInfo, TenantServiceLog, ServiceDomain, PermRelService, PermRelTenant, TenantServiceRelation, TenantServiceEnv, TenantServiceAuth, TenantConsume
from service_http import RegionServiceApi
from gitlab_http import GitlabApi
from github_http import GitHubApi
from www.tenantservice.baseservice import BaseTenantService
from www.tenantfee.feeservice import TenantFeeService
from www.utils.language import is_redirect
from www.db import BaseConnection
from django.conf import settings

logger = logging.getLogger('default')

gitClient = GitlabApi()

gitHubClient = GitHubApi()

regionClient = RegionServiceApi()

class TenantServiceAll(AuthedView):
    def get_media(self):
        media = super(AuthedView, self).get_media() + self.vendor('www/css/owl.carousel.css', 'www/css/goodrainstyle.css',
            'www/js/jquery.cookie.js', 'www/js/service.js', 'www/js/common-scripts.js', 'www/js/jquery.dcjqaccordion.2.7.js',
            'www/js/jquery.scrollTo.min.js')
        return media

    @never_cache
    @perm_required('tenant.tenant_access')
    def get(self, request, *args, **kwargs):
        context = self.get_context()
        try:
            num = TenantServiceInfo.objects.filter(tenant_id=self.tenant.tenant_id).count()
            if num < 1:
                return HttpResponseRedirect('/apps/{0}/app-create/'.format(self.tenant.tenant_name))
            baseService = BaseTenantService()
            tenantServiceList = baseService.get_service_list(self.tenant.pk, self.user.pk, self.tenant.tenant_id)
            context["tenantServiceList"] = tenantServiceList
            context["totalAppStatus"] = "active"
            context["totalFlow"] = 0
            context["totalAppNumber"] = len(tenantServiceList)
            context["tenantName"] = self.tenantName
            totalNum = PermRelTenant.objects.filter(tenant_id=self.tenant.ID).count()
            context["totalNum"] = totalNum
            context["curTenant"] = self.tenant
            tenant_balance = self.tenant.balance
            if self.tenant.pay_type == "payed":
                dsn = BaseConnection()
                query_sql = "select sum(cost_money) as cost_money from tenant_consume where tenant_id='" + self.tenant.tenant_id + "' and pay_status='unpayed'"
                sqlobj = dsn.query(query_sql)
                if sqlobj is not None and len(sqlobj) > 0:
                    cost_money = sqlobj[0]["cost_money"]
                    if cost_money > 0:
                        tenant_balance = float(tenant_balance) - float(cost_money)
            context["tenant_balance"] = tenant_balance
            if self.tenant.service_status == 0:
                logger.debug("unpause tenant_id=" + self.tenant.tenant_id)
                regionClient.unpause(self.tenant.region, self.tenant.tenant_id)
                self.tenant.service_status = 1
                self.tenant.save()
        except Exception as e:
            logger.exception(e)
        return TemplateResponse(self.request, "www/service_my.html", context)


class TenantService(AuthedView):

    def get_media(self):
        media = super(AuthedView, self).get_media() + self.vendor(
            'www/assets/jquery-easy-pie-chart/jquery.easy-pie-chart.css',
            'www/css/owl.carousel.css', 'www/css/goodrainstyle.css', 'www/css/style.css',
            'www/css/style-responsive.css', 'www/js/jquery.cookie.js', 'www/js/service.js',
            'www/js/gr/basic.js', 'www/css/gr/basic.css', 'www/js/perms.js',
            'www/js/common-scripts.js', 'www/js/jquery.dcjqaccordion.2.7.js', 'www/js/jquery.scrollTo.min.js',
            'www/js/swfobject.js', 'www/js/web_socket.js', 'www/js/websoket-goodrain.js'
        )
        return media

    def get_service_list(self):
        baseService = BaseTenantService()
        services = baseService.get_service_list(self.tenant.pk, self.user.pk, self.tenant.tenant_id)
        for s in services:
            if s.service_alias == self.serviceAlias:
                s.is_selected = True

        return services

    def get_user_perms(self):
        perm_users = []
        perm_template = {
            'name': None,
            'adminCheck': False,
            'developerCheck': False,
            'developerDisable': False,
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
                })
            elif i.identity == 'developer':
                user_perm.update({
                    'developerCheck': True,
                })

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
        regionClient.writeToRegionBeanstalk(self.tenant.region, self.service.service_id, json.dumps(task))
    
    @never_cache
    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        context = self.get_context()
        context["tenantName"] = self.tenantName
        context['serviceAlias'] = self.serviceAlias
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
                        
            service_id = self.service.service_id
            context["tenantServiceInfo"] = self.service
            tenantServiceList = self.get_service_list()
            context["tenantServiceList"] = tenantServiceList
            context["tenantName"] = self.tenantName
            context["myAppStatus"] = "active"
            context["perm_users"] = self.get_user_perms()   
            context["nodeList"] = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
            context["memoryList"] = [128, 256, 512, 1024, 2048, 4096]         
            
            if self.service.category == "application" or  self.service.category == "manager":
                # service relationships
                tsrs = TenantServiceRelation.objects.filter(tenant_id=self.tenant.tenant_id, service_id=service_id)
                
                relationsids = []
                sidMap = {}
                if len(tsrs) > 0:
                    for tsr in tsrs:
                        relationsids.append(tsr.dep_service_id)
                        sidMap[tsr.dep_service_id] = tsr.dep_order
                context["serviceIds"] = relationsids  
                context["serviceIdsMap"] = sidMap
                    
                map = {}
                sids = []
                for tenantService in tenantServiceList:
                    if tenantService.category != "application" and tenantService.category != "manager":
                        sids.append(tenantService.service_id)
                        map[tenantService.service_id] = tenantService
                context["serviceMap"] = map
                
                # relationships password
                authMap = {}
                authList = TenantServiceAuth.objects.filter(service_id__in=sids)
                if len(authList) > 0:                    
                    for auth in authList:
                        authMap[auth.service_id] = auth
                context["authMap"] = authMap
                                
                # service git repository
                httpGitUrl = ""
                if self.service.code_from == "gitlab_new" or self.service.code_from == "gitlab_exit":
                    cur_git_url = self.service.git_url.split("/")
                    httpGitUrl = "http://code.goodrain.com/app/" + cur_git_url[1]
                else:
                    httpGitUrl = self.service.git_url
                context["httpGitUrl"] = httpGitUrl 
                # service domain
                if self.tenant.pay_type != "free":
                    try:
                        domain = ServiceDomain.objects.get(
                            service_id=self.service.service_id)
                        context["serviceDomain"] = domain
                    except Exception as e:
                        pass
                context["pay_type"] = self.tenant.pay_type
            else:
                try:
                    serviceAuth = TenantServiceAuth.objects.get(service_id=self.service.service_id)
                    context["serviceAuth"] = serviceAuth     
                except Exception as e:
                    pass
                
            if self.tenant.service_status == 0:
                logger.debug("unpause tenant_id=" + self.tenant.tenant_id)
                regionClient.unpause(self.tenant.region, self.tenant.tenant_id)
                self.tenant.service_status = 1
                self.tenant.save()
                
            websocket_info = settings.WEBSOCKET_URL
            context["websocket_uri"] = websocket_info[self.tenant.region]
            
        except Exception as e:
            logger.exception(e)
        return TemplateResponse(self.request, "www/service_detail.html", context)


class ServiceDomainManager(AuthedView):
    @never_cache
    def post(self, request, *args, **kwargs):
        service_alias = ""
        result = {}
        try:
            if(self.user.pk != ""):
                tenantService = self.service
                service_alias = self.serviceAlias
                domain_name = request.POST["domain_name"]
                                
                domainNum = ServiceDomain.objects.filter(domain_name=domain_name).count()
                if domainNum > 0:
                    result["status"] = "exist"
                    return HttpResponse(json.dumps(result))
                
                num = ServiceDomain.objects.filter(service_name=tenantService.service_alias).count()
                old_domain_name = "goodrain"
                if num == 0:
                    domain = {}
                    domain["service_id"] = self.service.service_id
                    domain["service_name"] = tenantService.service_alias
                    domain["domain_name"] = domain_name
                    domain["create_time"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    domaininfo = ServiceDomain(**domain)
                    domaininfo.save()
                else:
                    domain = ServiceDomain.objects.get(service_id=self.service.service_id)
                    old_domain_name = domain.domain_name
                    domain.domain_name = domain_name
                    domain.save()
                data = {}
                data["service_id"] = self.service.service_id
                data["new_domain"] = domain_name
                data["old_domain"] = old_domain_name
                data["pool_name"] = self.tenantName + "@" + self.serviceAlias + ".Pool"              
                regionClient.addUserDomain(self.tenant.region, json.dumps(data))   
            result["status"] = "success"
        except Exception as e:
            logger.exception(e)
            result["status"] = "failure"
        return HttpResponse(json.dumps(result))

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
