# -*- coding: utf8 -*-
import logging
import uuid
import hashlib
import json

from django.views.decorators.cache import never_cache
from django.template.response import TemplateResponse
from django.http.response import HttpResponse
from django.http import JsonResponse
from www.views import BaseView, AuthedView, LeftSideBarMixin
from www.decorator import perm_required
from www.models import Users, ServiceInfo, TenantRegionInfo, TenantServiceInfo, TenantServiceRelation, TenantServiceEnv, TenantServiceAuth
from service_http import RegionServiceApi
from gitlab_http import GitlabApi
from github_http import GitHubApi
from www.tenantservice.baseservice import BaseTenantService, TenantUsedResource
from www.utils.language import is_redirect
from www.monitorservice.monitorhook import MonitorHook

logger = logging.getLogger('default')

gitClient = GitlabApi()
gitHubClient = GitHubApi()
regionClient = RegionServiceApi()
monitorhook = MonitorHook()


class AppCreateView(LeftSideBarMixin, AuthedView):

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
        service_code_from = ""
        uid = str(uuid.uuid4())
        service_id = hashlib.md5(uid.encode("UTF-8")).hexdigest()
        data = {}
        try:
            tenant_id = self.tenant.tenant_id
            if tenant_id == "" or self.user.pk == "":
                data["status"] = "failure"
                return JsonResponse(data, status=200)

            self.tenant_region = TenantRegionInfo.objects.get(tenant_id=self.tenant.tenant_id, region_name=self.response_region)
            if self.tenant_region.service_status == 2 and self.tenant.pay_type == "payed":
                data["status"] = "owed"
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

            # calculate resource
            tenantUsedResource = TenantUsedResource()
            flag = tenantUsedResource.predict_next_memory(self.tenant, service.min_memory)
            if not flag:
                if self.tenant.pay_type == "free":
                    data["status"] = "over_memory"
                else:
                    data["status"] = "over_money"
                return JsonResponse(data, status=200)

            # create console service
            baseService = BaseTenantService()
            service.desc = service_desc
            newTenantService = baseService.create_service(
                service_id, tenant_id, service_alias, service, self.user.pk, region=self.response_region)
            monitorhook.serviceMonitor(self.user.nick_name, newTenantService, 'create_service', True)

            # code repos
            if service_code_from == "gitlab_new":
                project_id = 0
                if self.user.git_user_id > 0:
                    project_id = gitClient.createProject(self.tenantName + "_" + service_alias)
                    logger.debug(project_id)
                    monitorhook.gitProjectMonitor(self.user.nick_name, newTenantService, 'create_git_project', project_id)
                    if project_id > 0:
                        gitClient.addProjectMember(project_id, self.user.git_user_id, 'master')
                        gitClient.addProjectMember(project_id, 2, 'reporter')
                        ts = TenantServiceInfo.objects.get(service_id=service_id)
                        ts.git_project_id = project_id
                        ts.git_url = "git@code.goodrain.com:app/" + self.tenantName + "_" + service_alias + ".git"
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
                code_clone_url = request.POST.get("service_code_clone_url", "")
                code_id = request.POST.get("service_code_id", "")
                code_version = request.POST.get("service_code_version", "master")
                if code_id == "" or code_clone_url == "" or code_version == "":
                    data["status"] = "code_repos"
                    TenantServiceInfo.objects.get(service_id=service_id).delete()
                    return JsonResponse(data, status=200)
                ts = TenantServiceInfo.objects.get(service_id=service_id)
                ts.git_project_id = code_id
                ts.git_url = code_clone_url
                ts.code_from = service_code_from
                ts.code_version = code_version
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
                regionClient.writeToRegionBeanstalk(self.response_region, ts.service_id, json.dumps(task))
            elif service_code_from == "github":
                code_id = request.POST.get("service_code_id", "")
                code_clone_url = request.POST.get("service_code_clone_url", "")
                code_version = request.POST.get("service_code_version", "master")
                if code_id == "" or code_clone_url == "" or code_version == "":
                    data["status"] = "code_repos"
                    TenantServiceInfo.objects.get(service_id=service_id).delete()
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

                data = {}
                data["tenant_id"] = ts.tenant_id
                data["service_id"] = ts.service_id
                clone_url = "https://" + createUser.github_token + "@github.com/" + code_user + "/" + code_project_name + ".git"
                data["git_url"] = "--branch " + ts.code_version + " --depth 1 " + clone_url
                task = {}
                task["data"] = data
                task["tube"] = "code_check"
                task["service_id"] = ts.service_id
                logger.debug(json.dumps(task))
                regionClient.writeToRegionBeanstalk(self.response_region, ts.service_id, json.dumps(task))

            # create region tenantservice
            baseService.create_region_service(newTenantService, self.tenantName, self.response_region, self.user.nick_name)
            monitorhook.serviceMonitor(self.user.nick_name, newTenantService, 'init_region_service', True)
            # create service env
            baseService.create_service_env(tenant_id, service_id, self.response_region)
            # record log
            data["status"] = "success"
            data["service_alias"] = service_alias
            data["service_id"] = service_id
        except Exception as e:
            logger.exception(e)
            tempTenantService = TenantServiceInfo.objects.get(service_id=service_id)
            if service_code_from == "gitlab_new" and tempTenantService.git_project_id > 0:
                gitClient.deleteProject(tempTenantService.git_project_id)
            TenantServiceInfo.objects.filter(service_id=service_id).delete()
            TenantServiceAuth.objects.filter(service_id=service_id).delete()
            TenantServiceRelation.objects.get(service_id=service_id).delete()
            monitorhook.serviceMonitor(self.user.nick_name, tempTenantService, 'create_service_error', False)
            data["status"] = "failure"
        return JsonResponse(data, status=200)


class AppDependencyCodeView(LeftSideBarMixin, AuthedView):

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
            context["tenantName"] = self.tenantName
            context["tenantService"] = self.service

            cacheServiceList = ServiceInfo.objects.filter(status="published", category__in=["cache", "store"])
            context["cacheServiceList"] = cacheServiceList

            tenant_id = self.tenant.tenant_id
            deployTenantServices = TenantServiceInfo.objects.filter(
                tenant_id=tenant_id, service_region=self.response_region, category__in=["cache", "store"])
            context["deployTenantServices"] = deployTenantServices
        except Exception as e:
            logger.exception(e)
        return TemplateResponse(self.request, "www/app_create_step_2_dependency.html", context)

    @never_cache
    @perm_required('create_service')
    def post(self, request, *args, **kwargs):
        data = {}
        try:
            self.tenant_region = TenantRegionInfo.objects.get(tenant_id=self.service.tenant_id, region_name=self.service.service_region)
            if self.tenant_region.service_status == 2 and self.tenant.pay_type == "payed":
                data["status"] = "owed"
                return JsonResponse(data, status=200)

            tenant_id = self.tenant.tenant_id
            service_alias = self.service.service_alias
            service_id = self.service.service_id
            # create service dependency
            createService = request.POST.get("createService", "")
            logger.debug(createService)
            if createService is not None and createService != "":
                serviceKeys = createService.split(",")
                # resource check
                tenantUsedResource = TenantUsedResource()
                flag = tenantUsedResource.predict_next_memory(self.tenant, self.service.min_memory + len(serviceKeys) * 128)
                if not flag:
                    if self.tenant.pay_type == "free":
                        data["status"] = "over_memory"
                    else:
                        data["status"] = "over_money"
                    return JsonResponse(data, status=200)

                # create service
                baseService = BaseTenantService()
                for skey in serviceKeys:
                    try:
                        dep_service = ServiceInfo.objects.get(service_key=skey)
                        tempUuid = str(uuid.uuid4()) + skey
                        dep_service_id = hashlib.md5(tempUuid.encode("UTF-8")).hexdigest()
                        depTenantService = baseService.create_service(
                            dep_service_id, tenant_id, dep_service.service_key + "_" + service_alias, dep_service, self.user.pk, region=self.response_region)
                        monitorhook.serviceMonitor(self.user.nick_name, depTenantService, 'create_service', True)
                        baseService.create_region_service(depTenantService, self.tenantName, self.response_region, self.user.nick_name)
                        monitorhook.serviceMonitor(self.user.nick_name, depTenantService, 'init_region_service', True)
                        baseService.create_service_env(tenant_id, dep_service_id, self.response_region)
                        baseService.create_service_dependency(tenant_id, service_id, dep_service_id, self.response_region)
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
                        baseService.create_service_dependency(tenant_id, service_id, sid, self.response_region)
                    except Exception as e:
                        logger.exception(e)
            data["status"] = "success"
        except Exception as e:
            logger.exception(e)
            data["status"] = "failure"
        return JsonResponse(data, status=200)


class AppWaitingCodeView(LeftSideBarMixin, AuthedView):

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
            # if self.service.language != "" and self.service.language is not None:
            #    return self.redirect_to('/apps/{0}/{1}/app-language/'.format(self.tenant.tenant_name, self.service.service_alias))

            context = self.get_context()
            context["myAppStatus"] = "active"
            context["tenantName"] = self.tenantName
            context["tenantService"] = self.service

            httpGitUrl = ""
            if self.service.code_from == "gitlab_new" or self.service.code_from == "gitlab_exit":
                cur_git_url = self.service.git_url.split("/")
                httpGitUrl = "http://code.goodrain.com/app/" + cur_git_url[1]
            else:
                httpGitUrl = self.service.git_url
            context["httpGitUrl"] = httpGitUrl

            tenantServiceRelations = TenantServiceRelation.objects.filter(
                tenant_id=self.tenant.tenant_id, service_id=self.service.service_id)
            if len(tenantServiceRelations) > 0:
                dpsids = []
                for tsr in tenantServiceRelations:
                    dpsids.append(tsr.dep_service_id)
                deployTenantServices = TenantServiceInfo.objects.filter(service_id__in=dpsids)
                context["deployTenantServices"] = deployTenantServices
                authList = TenantServiceAuth.objects.filter(service_id__in=dpsids)
                if len(authList) > 0:
                    authMap = {}
                    for auth in authList:
                        authMap[auth.service_id] = auth
                    context["authMap"] = authMap
        except Exception as e:
            logger.exception(e)
        return TemplateResponse(self.request, "www/app_create_step_3_waiting.html", context)


class AppLanguageCodeView(LeftSideBarMixin, AuthedView):

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
            if self.service.language == "" or self.service.language is None:
                return self.redirect_to('/apps/{0}/{1}/app-waiting/'.format(self.tenant.tenant_name, self.service.service_alias))

            tenantServiceEnv = TenantServiceEnv.objects.get(service_id=self.service.service_id)
            if tenantServiceEnv.user_dependency is not None and tenantServiceEnv.user_dependency != "":
                return self.redirect_to('/apps/{0}/{1}/detail/'.format(self.tenant.tenant_name, self.service.service_alias))

            context = self.get_context()
            context["myAppStatus"] = "active"
            context["tenantName"] = self.tenantName
            context["tenantService"] = self.service
            language = self.service.language
            data = json.loads(tenantServiceEnv.check_dependency)
            context["dependencyData"] = data
            redirectme = is_redirect(self.service.language, data)
            context["redirectme"] = redirectme
            if redirectme:
                language = "default"
        except Exception as e:
            logger.exception(e)
        if self.service.language == 'docker':
            self.service.cmd = ''
            self.service.save()
            regionClient.update_service(self.response_region, self.service.service_id, {"cmd": ""})
            return TemplateResponse(self.request, "www/app_create_step_4_default.html", context)
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
                    data = {}
                    data["tenant_id"] = ts.tenant_id
                    data["service_id"] = ts.service_id
                    gitUrl = "--branch " + ts.code_version + " --depth 1 " + ts.git_url
                    data["git_url"] = gitUrl
                    task = {}
                    task["data"] = data
                    task["service_id"] = ts.service_id
                    task["tube"] = "code_check"
                    logger.debug(json.dumps(task))
                    regionClient.writeToRegionBeanstalk(ts.service_region, ts.service_id, json.dumps(task))
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
                    data = {}
                    data["tenant_id"] = ts.tenant_id
                    data["service_id"] = ts.service_id
                    clone_url = ts.git_url
                    code_user = clone_url.split("/")[3]
                    code_project_name = clone_url.split("/")[4].split(".")[0]
                    createUser = Users.objects.get(user_id=ts.creater)
                    clone_url = "https://" + createUser.github_token + "@github.com/" + code_user + "/" + code_project_name + ".git"
                    gitUrl = "--branch " + ts.code_version + " --depth 1 " + clone_url
                    data["git_url"] = gitUrl

                    task = {}
                    task["service_id"] = ts.service_id
                    task["data"] = data
                    task["tube"] = "code_check"
                    logger.debug(json.dumps(task))
                    regionClient.writeToRegionBeanstalk(ts.service_region, ts.service_id, json.dumps(task))
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
            if service_id is not None and service_id != "":
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
            if service_id is not None and service_id != "" and dependency != "":
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
                    if language != "false":
                        if language.find("Java") > -1:
                            service.min_memory = 256
                            data = {}
                            data["language"] = "java"
                            regionClient.changeMemory(service.service_region, service_id, json.dumps(data))
                        service.language = language
                        service.save()
            result["status"] = "success"
        except Exception as e:
            logger.exception(e)
            result["status"] = "failure"
        return HttpResponse(json.dumps(result))
