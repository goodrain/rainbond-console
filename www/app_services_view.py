# -*- coding: utf8 -*-
import logging
import uuid
import hashlib
import datetime
import json

from django.views.decorators.cache import never_cache
from django.template.response import TemplateResponse
from django.http.response import HttpResponse
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from www.views import BaseView, AuthedView
from www.decorator import perm_required
from www.models import Users, Tenants, ServiceInfo, TenantServiceInfo, ServiceDomain, TenantServiceRelation, TenantServiceEnv, TenantServiceAuth
from service_http import RegionServiceApi
from gitlab_http import GitlabApi
from github_http import GitHubApi
from goodrain_web.tools import BeanStalkClient
from www.tenantservice.baseservice import BaseTenantService
from www.db import BaseConnection
from www.utils.language import is_redirect

client = RegionServiceApi()

logger = logging.getLogger('default')

gitClient = GitlabApi()

beanclient = BeanStalkClient()

gitHubClient = GitHubApi()

class AppCreateView(AuthedView):
    
    def get_media(self):
        media = super(AuthedView, self).get_media() + self.vendor(
            'www/css/goodrainstyle.css', 'www/css/style.css', 'www/css/style-responsive.css', 'www/js/jquery.cookie.js',
            'www/js/common-scripts.js', 'www/js/jquery.dcjqaccordion.2.7.js', 'www/js/jquery.scrollTo.min.js',
            'www/js/respond.min.js', 'www/js/app-create.js')
        return media

    @never_cache
    @perm_required('create_service')
    def get(self, request, *args, **kwargs):
        try:
            context = self.get_context()            
            baseService = BaseTenantService()
            tenantServiceList = baseService.get_service_list(self.tenant.pk, self.user.pk, self.tenant.tenant_id)
            context["tenantServiceList"] = tenantServiceList                
            context["tenantName"] = self.tenantName
            context["createApp"] = "active"
            request.session["app_tenant"] = self.tenantName
        except Exception as e:
            logger.exception(e)
        return TemplateResponse(self.request, "www/app_create_step_1.html", context)

    @never_cache
    @perm_required('create_service')
    def post(self, request, *args, **kwargs):
        
        service_alias = ""
        uid = str(uuid.uuid4())
        service_id = hashlib.md5(uid.encode("UTF-8")).hexdigest()
        data = {}
        try:
            tenant_id = self.tenant.tenant_id
            if tenant_id == "" or self.user.pk == "":
                data["status"] = "failure"
                return JsonResponse(data, status=200)            
            service_desc = ""
            service_alias = request.POST.get("create_app_name", "")
            service_code_from = request.POST.get("service_code_from", "")
            if service_code_from is None or service_code_from == "":
                data["status"] = "code_from"
                return JsonResponse(data, status=200)
            if service_alias is None or service_alias == "":
                data["status"] = "empty"
                return JsonResponse(data, status=200)   
            service_alias = service_alias.lower()
            # get base service
            service = ServiceInfo.objects.get(service_key="application")
            # create console tenant service
            num = TenantServiceInfo.objects.filter(tenant_id=tenant_id, service_alias=service_alias).count()
            if num > 0:
                data["status"] = "exist"
                return JsonResponse(data, status=200)
            
            if self.tenant.tenant_name != "goodrain": 
                dsn = BaseConnection()
                query_sql = '''
                    select sum(s.min_node * s.min_memory) as totalMemory from tenant_service s where s.tenant_id = "{tenant_id}"
                    '''.format(tenant_id=tenant_id)
                sqlobj = dsn.query(query_sql)
                if sqlobj is not None and len(sqlobj) > 0:
                    oldMemory = sqlobj[0]["totalMemory"]
                    if oldMemory is not None:
                        totalMemory = int(oldMemory) + service.min_memory
                        if totalMemory > 1024:
                            data["status"] = "overtop"
                            return JsonResponse(data, status=200)
            
            baseService = BaseTenantService()
            service.desc = service_desc
            newTenantService = baseService.create_service(service_id, tenant_id, service_alias, service, self.user.pk)
            
            # code repos
            if service_code_from == "gitlab_new":
                project_id = 0
                if self.user.git_user_id > 0:
                    project_id = gitClient.createProject(self.tenantName + "_" + service_alias)
                    logger.debug(project_id)
                    if project_id > 0:
                        gitClient.addProjectMember(project_id, self.user.git_user_id, 40)
                        gitClient.addProjectMember(project_id, 2, 20)                                        
                        ts = TenantServiceInfo.objects.get(service_id=service_id)
                        ts.git_project_id = project_id
                        ts.git_url = "git@git.goodrain.me:app/" + self.tenantName + "_" + service_alias + ".git"
                        ts.code_from = service_code_from
                        ts.code_version = "master"
                        ts.save()  
                        gitClient.createWebHook(project_id)         
            elif service_code_from == "gitlab_exit":
                code_clone_url = request.POST.get("service_code_clone_url", "")
                code_id = request.POST.get("service_code_id", "")
                code_version = request.POST.get("service_code_version", "master")
                if code_id == "" or code_clone_url == "":
                    data["status"] = "code_repos"
                    return JsonResponse(data, status=200)
                ts = TenantServiceInfo.objects.get(service_id=service_id)
                ts.git_project_id = code_id
                ts.git_url = code_clone_url
                ts.code_from = service_code_from
                ts.code_version = code_version
                ts.save()
                                
                task = {}
                task["tenant_id"] = ts.tenant_id
                task["service_id"] = ts.service_id
                task["git_url"] = "--branch " + ts.code_version + " --depth 1 " + ts.git_url
                logger.debug(json.dumps(task))
                beanclient.put("code_check", json.dumps(task))     
            elif service_code_from == "github":
                code_id = request.POST.get("service_code_id", "")
                code_clone_url = request.POST.get("service_code_clone_url", "")
                code_version = request.POST.get("service_code_version", "master")
                if code_id == "" or code_clone_url == "":
                    data["status"] = "code_repos"
                    return JsonResponse(data, status=200)
                ts = TenantServiceInfo.objects.get(service_id=service_id)
                ts.git_project_id = code_id
                ts.git_url = code_clone_url
                ts.code_from = service_code_from
                ts.code_version = code_version
                ts.save()
                code_user = code_clone_url.split("/")[3]
                code_project_name = code_clone_url.split("/")[4].split(".")[0]
                createUser = Users.objects.get(user_id=ts.creater)
                gitHubClient.createReposHook(code_user, code_project_name, createUser.github_token)
                
                task = {}
                task["tenant_id"] = ts.tenant_id
                task["service_id"] = ts.service_id
                clone_url = "https://" + createUser.github_token + "@github.com/" + code_user + "/" + code_project_name + ".git"
                task["git_url"] = "--branch " + ts.code_version + " --depth 1 " + clone_url
                logger.debug(json.dumps(task))
                beanclient.put("code_check", json.dumps(task))
        
            # create region tenantservice
            baseService.create_region_service(newTenantService, service, self.tenantName)
            
            # record log
            task = {}
            task["log_msg"] = "应用创建成功"
            task["service_id"] = newTenantService.service_id
            task["tenant_id"] = newTenantService.tenant_id
            beanclient.put("app_log", json.dumps(task))
            
            data["status"] = "success"
            data["service_alias"] = service_alias
            data["service_id"] = service_id 
        except Exception as e:
            logger.exception(e)
            TenantServiceInfo.objects.get(service_id=service_id).delete()
            TenantServiceAuth.objects.get(service_id=service_id).delete()
            data["status"] = "failure"
        return JsonResponse(data, status=200)
    
class AppWaitingCodeView(AuthedView):
    
    def get_service_list(self):
        baseService = BaseTenantService()
        services = baseService.get_service_list(self.tenant.pk, self.user.pk, self.tenant.tenant_id)
        for s in services:
            if s.service_alias == self.serviceAlias:
                s.is_selected = True
                break
        return services
    
    def get_media(self):
        media = super(AuthedView, self).get_media() + self.vendor(
            'www/css/goodrainstyle.css', 'www/css/style.css', 'www/css/style-responsive.css', 'www/js/jquery.cookie.js',
            'www/js/common-scripts.js', 'www/js/jquery.dcjqaccordion.2.7.js', 'www/js/jquery.scrollTo.min.js',
            'www/js/respond.min.js', 'www/js/app-waiting.js')
        return media
    
    @never_cache
    @perm_required('create_service')
    def get(self, request, *args, **kwargs):
        try:
            if self.service.language != "" and self.service.language is not None:
                return redirect('/apps/{0}/{1}/app-language/'.format(self.tenant.tenant_name, self.service.service_alias))
            else:
                context = self.get_context()      
                context["myAppStatus"] = "active"
                context["tenantServiceList"] = self.get_service_list()                
                context["tenantName"] = self.tenantName
                context["tenantService"] = self.service
                
                httpGitUrl = ""
                if self.service.code_from == "gitlab_new" or self.service.code_from == "gitlab_exit":
                    cur_git_url = self.service.git_url.split("/")
                    httpGitUrl = "http://code.goodrain.com/app/" + cur_git_url[1]
                else:
                    httpGitUrl = self.service.git_url
                context["httpGitUrl"] = httpGitUrl
                
                tenant_id = self.tenant.tenant_id
                deployTenantServices = TenantServiceInfo.objects.filter(tenant_id=tenant_id, category__in=["cache", "store"])
                context["deployTenantServices"] = deployTenantServices
                if len(deployTenantServices) > 0:
                    sids = []
                    for dts in deployTenantServices:
                        sids.append(dts.service_id)
                        
                    authList = TenantServiceAuth.objects.filter(service_id__in=sids)
                    if len(authList) > 0:
                        authMap = {}
                        for auth in authList:
                            authMap[auth.service_id] = auth
                        context["authMap"] = authMap
                
        except Exception as e:
            logger.exception(e)
        return TemplateResponse(self.request, "www/app_create_step_3_waiting.html", context)
    
class AppLanguageCodeView(AuthedView):
    
    def get_service_list(self):
        baseService = BaseTenantService()
        services = baseService.get_service_list(self.tenant.pk, self.user.pk, self.tenant.tenant_id)
        for s in services:
            if s.service_alias == self.serviceAlias:
                s.is_selected = True
                break
        return services
    
    def get_media(self):
        media = super(AuthedView, self).get_media() + self.vendor(
            'www/css/goodrainstyle.css', 'www/css/style.css', 'www/css/style-responsive.css', 'www/js/jquery.cookie.js',
            'www/js/common-scripts.js', 'www/js/jquery.dcjqaccordion.2.7.js', 'www/js/jquery.scrollTo.min.js',
            'www/js/respond.min.js', 'www/js/app-language.js')
        return media
    
    @never_cache
    @perm_required('create_service')
    def get(self, request, *args, **kwargs):
        language = "none"
        try:
            context = self.get_context()            
            if self.service.language == "" or self.service.language is None:
                return redirect('/apps/{0}/{1}/app-waiting/'.format(self.tenant.tenant_name, self.service.service_alias))
            else:
                context["myAppStatus"] = "active"
                context["tenantServiceList"] = self.get_service_list()                
                context["tenantName"] = self.tenantName
                context["tenantService"] = self.service
                language = self.service.language
                tenantServiceEnv = TenantServiceEnv.objects.get(service_id=self.service.service_id)
                data = json.loads(tenantServiceEnv.check_dependency)
                context["dependencyData"] = data
                redirectme = is_redirect(self.service.language, data)
                if redirectme:
                    return redirect('/apps/{0}/{1}/detail/'.format(self.tenant.tenant_name, self.service.service_alias))
        except Exception as e:
            logger.exception(e)
        return TemplateResponse(self.request, "www/app_create_step_4_" + language.replace(".", "").lower() + ".html", context)
    
    @never_cache
    @perm_required('create_service')
    def post(self, request, *args, **kwargs):
        data = {}
        try:
            service_version = request.POST.get("service_version", "")
            service_server = request.POST.get("service_server", "")
            service_dependency = request.POST.get("service_dependency", "")
            logger.debug(service_dependency)
            checkJson = {}
            checkJson["language"] = self.service.language
            if service_version != "":
                checkJson["runtimes"] = service_version
            else:
                checkJson["runtimes"] = ""
            if service_server != "":
                checkJson["procfile"] = service_server
            else:
                checkJson["procfile"] = ""
            if service_dependency != "":
                dps = service_dependency.split(",")
                d = {}
                for dp in dps:
                    if dp is not None and dp != "":
                        d["ext-" + dp] = "*"
                checkJson["dependencies"] = d
            else:
                checkJson["dependencies"] = {}            
            
            tenantServiceEnv = TenantServiceEnv.objects.get(service_id=self.service.service_id)
            tenantServiceEnv.user_dependency = json.dumps(checkJson)
            tenantServiceEnv.save()
            data["status"] = "success"
        except Exception as e:
            logger.exception(e)
            data["status"] = "failure"
        return JsonResponse(data, status=200)
    
class AppDependencyCodeView(AuthedView):
    
    def get_service_list(self):
        baseService = BaseTenantService()
        services = baseService.get_service_list(self.tenant.pk, self.user.pk, self.tenant.tenant_id)
        for s in services:
            if s.service_alias == self.serviceAlias:
                s.is_selected = True
                break
        return services
    
    def calculate_resource(self, createService):
        totalMemory = 0
        if self.tenant.tenant_name != "goodrain":  
            serviceKeys = createService.split(",")
            dsn = BaseConnection()
            query_sql = '''
                select sum(s.min_node * s.min_memory) as totalMemory from tenant_service s where s.tenant_id = "{tenant_id}"
                '''.format(tenant_id=self.tenant.tenant_id)
            sqlobj = dsn.query(query_sql)
            if sqlobj is not None and len(sqlobj) > 0:
                oldMemory = sqlobj[0]["totalMemory"]
                if oldMemory is not None:                    
                    totalMemory = int(oldMemory) + len(serviceKeys) * 128
        return totalMemory
    
    def get_media(self):
        media = super(AuthedView, self).get_media() + self.vendor(
            'www/css/goodrainstyle.css', 'www/css/style.css', 'www/css/style-responsive.css', 'www/js/jquery.cookie.js',
            'www/js/common-scripts.js', 'www/js/jquery.dcjqaccordion.2.7.js', 'www/js/jquery.scrollTo.min.js',
            'www/js/respond.min.js', 'www/js/app-dependency.js')
        return media
    
    @never_cache
    @perm_required('create_service')
    def get(self, request, *args, **kwargs):
        try:
            context = self.get_context()           
            context["myAppStatus"] = "active"
            context["tenantServiceList"] = self.get_service_list()                
            context["tenantName"] = self.tenantName
            context["tenantService"] = self.service
            
            cacheServiceList = ServiceInfo.objects.filter(status="published", category__in=["cache", "store"])
            context["cacheServiceList"] = cacheServiceList
            
            tenant_id = self.tenant.tenant_id
            deployTenantServices = TenantServiceInfo.objects.filter(tenant_id=tenant_id, category__in=["cache", "store"])
            context["deployTenantServices"] = deployTenantServices 
        except Exception as e:
            logger.exception(e)
        return TemplateResponse(self.request, "www/app_create_step_2_dependency.html", context)
    
    @never_cache
    @perm_required('create_service')
    def post(self, request, *args, **kwargs):
        data = {}
        try:
            tenant_id = self.tenant.tenant_id
            service_alias = self.service.service_alias
            service_id = self.service.service_id
             # create service dependency
            createService = request.POST.get("createService", "")
            logger.debug(createService)            
            if createService is not None and createService != "":
                totalMemory = self.calculate_resource(createService)
                if totalMemory > 1024:
                    data["status"] = "overtop"
                    return JsonResponse(data, status=200)
                
                baseService = BaseTenantService()
                serviceKeys = createService.split(",")
                for skey in serviceKeys:
                    try:
                        dep_service = ServiceInfo.objects.get(service_key=skey)
                        tempUuid = str(uuid.uuid4()) + skey
                        dep_service_id = hashlib.md5(tempUuid.encode("UTF-8")).hexdigest()
                        depTenantService = baseService.create_service(dep_service_id, tenant_id, dep_service.service_key + "_" + service_alias, dep_service, self.user.pk)
                        baseService.create_region_service(depTenantService, dep_service, self.tenantName)
                        baseService.create_service_dependency(tenant_id, service_id, dep_service_id)
                    except Exception as e:
                       logger.exception(e)
            # exist service dependency.
            hasService = request.POST.get("hasService", "")
            logger.debug(hasService)
            if hasService is not None and hasService != "":
                baseService = BaseTenantService()
                serviceIds = hasService.split(",")
                for sid in serviceIds:
                    try:
                        baseService.create_service_dependency(tenant_id, service_id, sid) 
                    except Exception as e:
                       logger.exception(e)
            data["status"] = "success"
        except Exception as e:
            logger.exception(e)
            data["status"] = "failure"
        return JsonResponse(data, status=200)
    
class GitLabWebHook(BaseView):
    @never_cache
    def post(self, request, *args, **kwargs):
        result = {}
        try: 
            payload = request.body
            payloadJson = json.loads(payload)
            project_id = payloadJson["project_id"]
            repositoryJson = payloadJson["repository"]
            name = repositoryJson["name"]
            git_url = repositoryJson["git_http_url"]
            logger.debug(str(project_id) + "==" + name + "==" + git_url)
            listTs = TenantServiceInfo.objects.filter(git_project_id=project_id).exclude(code_from="github")
            if len(listTs) > 0:
                for ts in listTs:
                    task = {}
                    task["tenant_id"] = ts.tenant_id
                    task["service_id"] = ts.service_id
                    gitUrl = "--branch " + ts.code_version + " --depth 1 " + ts.git_url
                    task["git_url"] = gitUrl
                    logger.debug(json.dumps(task))
                    beanclient.put("code_check", json.dumps(task))
            result["status"] = "success"
        except Exception as e:
            logger.exception(e)
            result["status"] = "failure"
        return HttpResponse(json.dumps(result))

class GitHubWebHook(BaseView):
    @never_cache
    def post(self, request, *args, **kwargs):
        result = {}
        try:
            # event = request.META['HTTP_X_GITHUB_EVENT']
            # logger.debug(event)            
            payload = request.body            
            payloadJson = json.loads(payload)
            repositoryJson = payloadJson["repository"]
            fullname = repositoryJson["full_name"]
            git_url = repositoryJson["clone_url"]
            project_id = repositoryJson["id"]
            logger.debug(str(project_id) + "==" + fullname + "==" + git_url)
            listTs = TenantServiceInfo.objects.filter(git_project_id=project_id, code_from="github")
            if len(listTs) > 0:
                for ts in listTs:
                    task = {}
                    task["tenant_id"] = ts.tenant_id
                    task["service_id"] = ts.service_id
                    clone_url = ts.git_url
                    code_user = clone_url.split("/")[3]
                    code_project_name = clone_url.split("/")[4].split(".")[0]
                    createUser = Users.objects.get(user_id=ts.creater)
                    clone_url = "https://" + createUser.github_token + "@github.com/" + code_user + "/" + code_project_name + ".git"
                    gitUrl = "--branch " + ts.code_version + " --depth 1 " + clone_url
                    task["git_url"] = gitUrl
                    logger.debug(json.dumps(task))
                    beanclient.put("code_check", json.dumps(task))
            result["status"] = "success"
        except Exception as e:
            logger.exception(e)
            result["status"] = "failure"
        return HttpResponse(json.dumps(result))

class GitCheckCode(BaseView):
    @never_cache
    def get(self, request, *args, **kwargs):
        data = {}
        try:
            service_id = request.GET.get("service_id", "")
            logger.debug("git code request: " + service_id)
            tse = TenantServiceEnv.objects.get(service_id=service_id)
            result = tse.user_dependency
            if result is not None and result != "":
                data = json.loads(result)
        except Exception as e:
            logger.exception(e)            
        return JsonResponse(data, status=200)
        
    @never_cache
    def post(self, request, *args, **kwargs):
        result = {}
        try:
            service_id = request.POST.get("service_id", "")
            dependency = request.POST.get("condition", "")
            logger.debug(service_id + "=" + dependency)
            if service_id is not None and service_id != "":
                dps = json.loads(dependency)
                language = dps["language"]
                if language is not None and language != "" and language != "no":
                    try:
                        tse = TenantServiceEnv.objects.get(service_id=service_id)
                        tse.language = language
                        tse.check_dependency = dependency
                        tse.save() 
                    except Exception:
                        tse = TenantServiceEnv(service_id=service_id, language=language, check_dependency=dependency)
                        tse.save()
                    service = TenantServiceInfo.objects.get(service_id=service_id)
                    if language != "false" :
                        if language.find("Java") > -1:
                            service.min_memory = 256
                            data = {}
                            data["language"] = "java" 
                            client.changeMemory(service_id, json.dumps(data))
                        service.language = language
                        service.save()
            result["status"] = "success"
        except Exception as e:
            logger.exception(e)
            result["status"] = "failure"
        return HttpResponse(json.dumps(result))

