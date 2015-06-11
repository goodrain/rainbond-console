# -*- coding: utf8 -*-
import logging
import uuid
import hashlib
import datetime
import json

from django.views.decorators.cache import never_cache
from django.template.response import TemplateResponse
from django.http.response import HttpResponse
from www.views import BaseView, AuthedView
from www.decorator import perm_required
from www.models import Users, Tenants, ServiceInfo, TenantServiceInfo, TenantServiceLog, ServiceDomain, PermRelService, PermRelTenant, TenantServiceRelation
from service_http import RegionServiceApi
from gitlab_http import GitlabApi
from goodrain_web.tools import BeanStalkClient
from www.tenantservice.baseservice import BaseTenantService
from www.inflexdb.inflexdbservice import InflexdbService
from www.tenantfee.feeservice import TenantFeeService
from www.db import BaseConnection

client = RegionServiceApi()

logger = logging.getLogger('default')

gitClient = GitlabApi()

beanlog = BeanStalkClient()

class ServiceAppCreate(AuthedView):
    
    def get_media(self):
        media = super(AuthedView, self).get_media() + self.vendor(
            'www/css/okooostyle.css', 'www/js/jquery.cookie.js', 'www/js/service.js', 'www/layer/layer.js', 
            'www/js/common-scripts.js', 'www/js/jquery.dcjqaccordion.2.7.js', 'www/js/jquery.scrollTo.min.js')
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
            cacheServiceList = ServiceInfo.objects.filter(status="published", category__in=["cache", "store"])
            context["cacheServiceList"] = cacheServiceList
            
            tenant_id = self.tenant.tenant_id
            deployTenantServices = TenantServiceInfo.objects.filter(tenant_id=tenant_id, category__in=["cache", "store"])
            context["deployTenantServices"] = deployTenantServices
            
            # if self.user.git_user_id > 0:
            #    gitClient.getUser(self.user.git_user_id)
        except Exception as e:
            logger.exception(e)
        return TemplateResponse(self.request, "www/app_create_step1.html", context)

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
                return HttpResponse(json.dumps(data))            
            service_desc = request.POST["service_desc"]
            service_alias = request.POST["service_name"]
            if service_alias is None or service_alias == "":
                data["status"] = "empty"
                return HttpResponse(json.dumps(data))   
            service_alias = service_alias.lower()
                    
            createService = request.POST["createService"]
            hasService = request.POST["hasService"]
            
            # get base service
            service = ServiceInfo.objects.get(service_key="application")
            # create console tenant service
            num = TenantServiceInfo.objects.filter(tenant_id=tenant_id, service_alias=service_alias).count()
            if num > 0:
                data["status"] = "exist"
                return HttpResponse(json.dumps(result))
            
            dsn = BaseConnection()
            query_sql = '''
                select sum(s.min_node * s.min_memory) as totalMemory from tenant_service s where s.tenant_id = "{tenant_id}"
                '''.format(tenant_id=tenant_id)
            sqlobj = dsn.query(query_sql)
            totalMemory = int(sqlobj[0]["totalMemory"]) + service.min_memory
            if totalMemory > 1024:
                data["status"] = "overtop"
                return HttpResponse(json.dumps(data))
            
            baseService = BaseTenantService()
            service.desc = service_desc
            newTenantService = baseService.create_service(service_id, tenant_id, service_alias, service)
            # create git
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
                    ts.save()                     
            # create region tenantservice
            baseService.create_region_service(newTenantService, service, self.tenantName)
            # create service dependency
            if createService is not None and createService != "":
                serviceKeys = createService.split(",")
                for skey in serviceKeys:
                    try:
                        dep_service = ServiceInfo.objects.get(service_key=skey)
                        tempUuid = str(uuid.uuid4()) + skey
                        dep_service_id = hashlib.md5(tempUuid.encode("UTF-8")).hexdigest()
                        depTenantService = baseService.create_service(dep_service_id, tenant_id, dep_service.service_key + "_" + service_alias, dep_service)
                        baseService.create_region_service(depTenantService, dep_service, self.tenantName)
                        baseService.create_service_dependency(tenant_id, service_id, dep_service_id)
                    except Exception as e:
                       logger.exception(e)
            # exist service dependency
            if hasService is not None and hasService != "":
                serviceIds = hasService.split(",")
                for sid in serviceIds:
                    try:
                        baseService.create_service_dependency(tenant_id, service_id, sid) 
                    except Exception as e:
                       logger.exception(e)
            # record log
            task = {}
            task["log_msg"] = "应用创建成功。."
            task["service_id"] = newTenantService.service_id
            task["tenant_id"] = newTenantService.tenant_id
            beanlog.put("app_log", json.dumps(task))
            
            data["status"] = "success"
            data["service_alias"] = service_alias
            data["service_id"] = service_id 
        except Exception as e:
            logger.exception(e)
            TenantServiceInfo.objects.get(service_id=service_id).delete()
            data["status"] = "failure"
        return HttpResponse(json.dumps(data))
    
    

class ServiceAppDeploy(AuthedView):
    
    def get_media(self):
        media = super(AuthedView, self).get_media() + self.vendor(
            'www/css/okooostyle.css', 'www/js/jquery.cookie.js', 'www/js/service.js', 'www/js/common-scripts.js', 
            'www/js/jquery.dcjqaccordion.2.7.js', 'www/js/jquery.scrollTo.min.js')
        return media
    
    @never_cache
    @perm_required('code_deploy')
    def get(self, request, *args, **kwargs):
        context = self.get_context()
        try:                    
            tenant_id = self.tenant.tenant_id
            tenantServiceList = TenantServiceInfo.objects.filter(tenant_id=tenant_id)
            context["tenantServiceList"] = tenantServiceList
            context["tenantName"] = self.tenantName
            context["myAppStatus"] = "active"
            context['serviceAlias'] = self.serviceAlias
            context["gitUrl"] = "git@code.goodrain.com:app/" + self.tenantName + "_" + self.serviceAlias + ".git"
            context["httpUrl"] = "http://code.goodrain.com/app/" + self.tenantName + "_" + self.serviceAlias + ".git"
        except Exception as e:
            logger.exception(e)                   
        return TemplateResponse(self.request, "www/service_git.html", context)
    

class ServiceMarket(AuthedView):
    def get_media(self):
        media = super(AuthedView, self).get_media() + self.vendor(
            'www/assets/jquery-easy-pie-chart/jquery.easy-pie-chart.css', 'www/css/owl.carousel.css',
            'www/css/okooostyle.css', 'www/js/jquery.cookie.js', 'www/js/service.js', 'www/js/common-scripts.js', 
            'www/js/jquery.dcjqaccordion.2.7.js', 'www/js/jquery.scrollTo.min.js')
        return media

    @never_cache
    @perm_required('tenant_access')
    def get(self, request, *args, **kwargs):
        try:
            context = self.get_context()
            baseService = BaseTenantService()
            tenantServiceList = baseService.get_service_list(self.tenant.pk, self.user.pk, self.tenant.tenant_id)
            context["tenantServiceList"] = tenantServiceList            
            cacheServiceList = ServiceInfo.objects.filter(status="published")
            context["cacheServiceList"] = cacheServiceList
            context["serviceMarketStatus"] = "active"
            context["tenantName"] = self.tenantName
        except Exception as e:
            logger.exception(e)
        return TemplateResponse(self.request, "www/service_market.html", context)
    
class ServiceMarketDeploy(AuthedView):
    
    
    def get_media(self):
        media = super(AuthedView, self).get_media() + self.vendor(
            'www/assets/jquery-easy-pie-chart/jquery.easy-pie-chart.css', 'www/css/owl.carousel.css',
            'www/css/okooostyle.css', 'www/js/jquery.cookie.js', 'www/js/service.js', 'www/js/common-scripts.js', 
            'www/js/jquery.dcjqaccordion.2.7.js', 'www/js/jquery.scrollTo.min.js')
        return media

    @never_cache
    @perm_required('code_deploy')
    def get(self, request, *args, **kwargs):
        context = self.get_context()
        try:
            service_key = request.GET.get("service_key", "")
            serviceObj = ServiceInfo.objects.get(service_key=service_key)
            context["service"] = serviceObj
            context["tenantName"] = self.tenantName
        except Exception as e:
            logger.exception(e)
        return TemplateResponse(self.request, "www/service_deploy.html", context)

    @never_cache
    @perm_required('code_deploy')
    def post(self, request, *args, **kwargs):
        service_alias = ""
        uid = str(uuid.uuid4()) + self.tenant.tenant_id
        service_id = hashlib.md5(uid.encode("UTF-8")).hexdigest()
        result = {}
        try:
            tenant_id = self.tenant.tenant_id
            if tenant_id == "" or self.user.pk == "":
                result["status"] = "failure"
                return HttpResponse(json.dumps(result))            
             
            service_key = request.POST["service_key"]
            
            service = ServiceInfo.objects.get(service_key=service_key)
            
            service_alias = request.POST["service_name"]
            if service_alias == "":
               result["status"] = "failure"
               return HttpResponse(json.dumps(result))
            service_alias = service_alias.lower()
                                    
            num = TenantServiceInfo.objects.filter(tenant_id=tenant_id, service_alias=service_alias).count()
            if num > 0:
                result["status"] = "exist"
                return HttpResponse(json.dumps(result))
            
            dsn = BaseConnection()
            query_sql = '''
                select sum(s.min_node * s.min_memory) as totalMemory from tenant_service s where s.tenant_id = "{tenant_id}"
                '''.format(tenant_id=tenant_id)
            sqlobj = dsn.query(query_sql)
            totalMemory = int(sqlobj[0]["totalMemory"]) + service.min_memory
            if totalMemory > 1024:
                data["status"] = "overtop"
                return HttpResponse(json.dumps(data))
            
            # create console service
            baseService = BaseTenantService()
            newTenantService = baseService.create_service(service_id, tenant_id, service_alias, service)
            # create region tenantservice
            baseService.create_region_service(newTenantService, service, self.tenantName)
            # record service log
            task = {}
            task["log_msg"] = "服务创建成功，开始部署....."
            task["service_id"] = newTenantService.service_id
            task["tenant_id"] = newTenantService.tenant_id
            logger.info(task)
            beanlog.put("app_log", json.dumps(task))
            
            result["status"] = "success"
            result["service_id"] = service_id
            result["service_alias"] = service_alias
        except Exception as e:
            logger.exception(e)
            TenantServiceInfo.objects.get(service_id=service_id).delete()
            logger.info(self.tenantName, service_alias, "%s" % e)
            result["status"] = "failure"
        return HttpResponse(json.dumps(result))


class TenantServiceAll(AuthedView):
    def get_media(self):
        media = super(AuthedView, self).get_media() + self.vendor('www/css/owl.carousel.css', 'www/css/okooostyle.css',
            'www/js/jquery.cookie.js', 'www/js/service.js', 'www/js/common-scripts.js', 'www/js/jquery.dcjqaccordion.2.7.js', 
            'www/js/jquery.scrollTo.min.js')
        return media

    @never_cache
    @perm_required('tenant.tenant_access')
    def get(self, request, *args, **kwargs):
        context = self.get_context()
        try:
            baseService = BaseTenantService()
            tenantServiceList = baseService.get_service_list(self.tenant.pk, self.user.pk, self.tenant.tenant_id)
            context["tenantServiceList"] = tenantServiceList
            context["totalAppStatus"] = "active"
            context["totalFlow"] = 0
            context["totalAppNumber"] = len(tenantServiceList)
            context["tenantName"] = self.tenantName
            totalNum = PermRelTenant.objects.filter(tenant_id=self.tenant.ID).count()
            context["totalNum"] = totalNum
        except Exception as e:
            logger.exception(e)
        return TemplateResponse(self.request, "www/service_my.html", context)


class TenantService(AuthedView):

    def get_media(self):
        media = super(AuthedView, self).get_media() + self.vendor(
            'www/assets/jquery-easy-pie-chart/jquery.easy-pie-chart.css',
            'www/css/owl.carousel.css', 'www/css/okooostyle.css', '/static/www/css/style.css',
            '/static/www/css/style-responsive.css', 'www/js/jquery.cookie.js', 'www/js/service.js',
            'www/js/gr/basic.js', 'www/css/gr/basic.css', 'www/js/perms.js', 'www/layer/layer.js',
            'www/js/common-scripts.js', 'www/js/jquery.dcjqaccordion.2.7.js', 'www/js/jquery.scrollTo.min.js'
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

    @never_cache
    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        context = self.get_context()
        context["tenantName"] = self.tenantName
        context['serviceAlias'] = self.serviceAlias
        try:
            service_id = self.service.service_id
            context["tenantServiceInfo"] = self.service
            tenantServiceList = self.get_service_list()
            context["tenantServiceList"] = tenantServiceList
            context["tenantName"] = self.tenantName
            context["myAppStatus"] = "active"
            context["perm_users"] = self.get_user_perms()

            if self.service.category == 'application' and self.service.git_project_id == 0:
                if self.user.git_user_id > 0:
                    project_id = gitClient.createProject(self.tenantName + "_" + self.serviceAlias)
                    logger.debug(project_id)
                    if project_id > 0:
                        gitClient.addProjectMember(project_id, self.user.git_user_id, 40)
                        gitClient.addProjectMember(project_id, 2, 20)                                        
                        ts = TenantServiceInfo.objects.get(service_id=service_id)
                        ts.git_project_id = project_id
                        ts.git_url = "git@git.goodrain.me:app/" + self.tenantName + "_" + self.serviceAlias + ".git"
                        ts.save()

            if self.service.category == 'application' and not self.service.is_code_upload:
                commitTime = gitClient.getProjectCommitTime(self.service.git_project_id)
                logger.debug(commitTime)
                if commitTime < 1:
                    context["gitUrl"] = "git@code.goodrain.com:app/" + self.tenantName + "_" + self.serviceAlias + ".git"                    
                    context["httpUrl"] = "http://code.goodrain.com/app/" + self.tenantName + "_" + self.serviceAlias + ".git"
                    return TemplateResponse(self.request, "www/service_git.html", context)
                else:
                    ts = TenantServiceInfo.objects.get(service_id=service_id)
                    ts.is_code_upload = True
                    ts.save()
                    
            tsrs = TenantServiceRelation.objects.filter(tenant_id=self.tenant.tenant_id, service_id=service_id)
            sids = []
            sidMap = {}
            if len(tsrs) > 0:                
                for tsr in tsrs:
                    sids.append(tsr.dep_service_id)
                    sidMap[tsr.dep_service_id] = tsr.dep_order
            context["serviceIds"] = sids  
            context["serviceIdsMap"] = sidMap
                 
            map = {}
            for tenantService in tenantServiceList:
                if tenantService.category == "application":
                    pass
                elif tenantService.category == "manager":
                    pass
                else:
                    map[tenantService.service_id] = tenantService                    
            context["serviceMap"] = map
            
            context["nodeList"] = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
            context["memoryList"] = [128, 256, 512, 1024, 2048, 4096]      
            
            try:
                domain = ServiceDomain.objects.get(service_id=self.service.service_id)
                context["serviceDomain"] = domain     
            except Exception as e:
                pass
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
                num = ServiceDomain.objects.filter(service_name=tenantService.service_alias).count()
                old_domain_name = ""
                if(num == 0):
                    domain = {}
                    domain["service_id"] = self.service.service_id
                    domain["service_name"] = tenantService.service_alias
                    domain["domain_name"] = domain_name
                    domain["create_time"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    domaininfo = ServiceDomain(**domain)
                    domaininfo.save()
                else:
                    domain = ServiceDomain.objects.get(service_name=tenantService.service_alias)
                    old_domain_name = domain.domain_name
                    domain.domain_name = domain_name
                    domain.save()
                data = {}
                data["new_domain"] = domain_name
                data["old_domain"] = old_domain_name
                data["pool_name"] = self.tenantName + "@" + self.serviceAlias + ".Pool"                   
                client.addUserDomain(json.dumps(data))   
            result["status"] = "success"
        except Exception as e:
            logger.exception(e)
            result["status"] = "failure"
        return HttpResponse(json.dumps(result))

    
    
class ServiceStaticsManager(AuthedView):
    
    @never_cache
    def get(self, request, *args, **kwargs):
        result = {}
        try:
            action = request.GET.get("action", "")
            key = request.GET.get("key", "")
            timeStamp = request.GET.get("timeStamp", "")
            if key == "goodrain.com":
                if action == "staticsContainer":
                    inflexdbService = InflexdbService()
                    inflexdbService.serviceContainerMemoryStatics(timeStamp)
                    inflexdbService.serviceContainerDiskStatics(timeStamp)
                    inflexdbService.servicePodMemoryStatics(timeStamp)
                    result["status"] = "ok"
                elif action == "staticsNetDisk":
                    inflexdbService = InflexdbService()
                    inflexdbService.serviceDiskStatics(timeStamp)
                    result["status"] = "ok"
                elif action == "staticsAll":
                    inflexdbService = InflexdbService()
                    inflexdbService.serviceContainerMemoryStatics(timeStamp)
                    inflexdbService.serviceContainerDiskStatics(timeStamp)
                    inflexdbService.servicePodMemoryStatics(timeStamp)
                    inflexdbService.serviceDiskStatics(timeStamp)
                    result["status"] = "ok"
                elif action == "staticsFee":
                    feeService = TenantFeeService()
                    feeService.staticsFee()
                else:
                    result["status"] = "action error"
            else:
                result["status"] = "key error"
        except Exception as e:
            logger.exception(e)
        return HttpResponse(json.dumps(result))

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
