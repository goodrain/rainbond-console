# -*- coding: utf8 -*-
import uuid
import hashlib
import datetime
import json

from django.views.decorators.cache import never_cache
from django.template.response import TemplateResponse
from django.http import JsonResponse
from django.http import HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from www.views import BaseView, AuthedView
from www.decorator import perm_required
from www.models import ServiceInfo, TenantServiceInfo, TenantServiceRelation, TenantServiceAuth
from service_http import RegionServiceApi
from www.tenantservice.baseservice import BaseTenantService
from www.db import BaseConnection
import logging
logger = logging.getLogger('default')

regionClient = RegionServiceApi()

class ServiceMarket(AuthedView):
    def get_media(self):
        media = super(AuthedView, self).get_media() + self.vendor(
            'www/assets/jquery-easy-pie-chart/jquery.easy-pie-chart.css', 'www/css/owl.carousel.css',
            'www/css/goodrainstyle.css', 'www/js/jquery.cookie.js', 'www/js/common-scripts.js',
            'www/js/jquery.dcjqaccordion.2.7.js', 'www/js/jquery.scrollTo.min.js', 'www/js/back-service-create.js')
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
    
    def calculate_resource(self, createService, servicekeyObj):
        totalMemory = 0 
        if self.tenant.pay_type == "free":
            dsn = BaseConnection()
            query_sql = '''
                select sum(s.min_node * s.min_memory) as totalMemory from tenant_service s where s.tenant_id = "{tenant_id}"
                '''.format(tenant_id=self.tenant.tenant_id)
            sqlobj = dsn.query(query_sql)
            if sqlobj is not None and len(sqlobj) > 0:
                oldMemory = sqlobj[0]["totalMemory"]
                if oldMemory is not None:                    
                    totalMemory = int(oldMemory)
                    if createService != "":
                       serviceKeys = createService.split(",")
                       totalMemory = totalMemory + len(serviceKeys) * 128
            totalMemory = totalMemory + servicekeyObj.min_memory
        return totalMemory
    
    def get_media(self):
        media = super(AuthedView, self).get_media() + self.vendor(
            'www/assets/jquery-easy-pie-chart/jquery.easy-pie-chart.css', 'www/css/owl.carousel.css',
            'www/css/goodrainstyle.css', 'www/js/jquery.cookie.js', 'www/js/common-scripts.js',
            'www/js/jquery.dcjqaccordion.2.7.js', 'www/js/jquery.scrollTo.min.js', 'www/js/back-service-create.js')
        return media

    @never_cache
    @perm_required('code_deploy')
    def get(self, request, *args, **kwargs):
        context = self.get_context()
        try:
            service_key = request.GET.get("service_key", "")
            if service_key == "":
                return HttpResponseRedirect('/apps/{0}/service/'.format(self.tenant.tenant_name))
            
            baseService = BaseTenantService()
            tenantServiceList = baseService.get_service_list(self.tenant.pk, self.user.pk, self.tenant.tenant_id)
            context["tenantServiceList"] = tenantServiceList            
            context["serviceMarketStatus"] = "active"
            
            serviceObj = ServiceInfo.objects.get(service_key=service_key)
            context["service"] = serviceObj
            if serviceObj.dependecy is not None and serviceObj.dependecy != "":          
                tenant_id = self.tenant.tenant_id
                deployTenantServices = TenantServiceInfo.objects.filter(tenant_id=tenant_id, service_type=serviceObj.dependecy)
                context["deployTenantServices"] = deployTenantServices                 
            context["tenantName"] = self.tenantName
            context["service_key"] = service_key
        except Exception as e:
            logger.exception(e)
        return TemplateResponse(self.request, "www/back_service_create_step_1.html", context)

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
                return JsonResponse(result, status=200)            
             
            service_key = request.POST.get("service_key", "")
            if service_key == "":
                result["status"] = "notexist"
                return JsonResponse(result, status=200)
                        
            service_alias = request.POST.get("create_service_name", "")
            if service_alias == "":
               result["status"] = "empty"
               return JsonResponse(result, status=200)
           
            service_alias = service_alias.lower()        
            num = TenantServiceInfo.objects.filter(tenant_id=tenant_id, service_alias=service_alias).count()
            if num > 0:
                result["status"] = "exist"
                return JsonResponse(result, status=200)
            
            service = ServiceInfo.objects.get(service_key=service_key)
            service_memory = request.POST.get("service_memory", "")
            if service_memory != "":
                cm = int(service_memory)
                if cm >= 128:
                    ccpu = int(cm / 128) * 100
                    service.min_cpu = ccpu
                    service.min_memory = cm
            logger.debug(service.min_memory)       
            createService = request.POST.get("createService", "")
            logger.debug(createService)       
            # calculate resource
            totalMemory = self.calculate_resource(createService, service)
            if totalMemory > 1024:
                result["status"] = "overtop"
                return JsonResponse(result, status=200)
                 
            # create new service       
            if createService != "":
                baseService = BaseTenantService()
                serviceKeys = createService.split(",")
                for skey in serviceKeys:
                    try:
                        dep_service = ServiceInfo.objects.get(service_key=skey)
                        tempUuid = str(uuid.uuid4()) + skey
                        dep_service_id = hashlib.md5(tempUuid.encode("UTF-8")).hexdigest()
                        depTenantService = baseService.create_service(dep_service_id, tenant_id, dep_service.service_key + "_" + service_alias, dep_service, self.user.pk)
                        baseService.create_region_service(depTenantService, dep_service, self.tenantName, self.tenant.region)
                        baseService.create_service_dependency(tenant_id, service_id, dep_service_id, self.tenant.region)
                    except Exception as e:
                       logger.exception(e)

            # exist service dependency
            hasService = request.POST.get("hasService", "")
            logger.debug(hasService)
            if hasService != "":
                baseService = BaseTenantService()
                serviceIds = hasService.split(",")
                for sid in serviceIds:
                    try:
                        baseService.create_service_dependency(tenant_id, service_id, sid, self.tenant.region) 
                    except Exception as e:
                       logger.exception(e)
            
            # create console service
            baseService = BaseTenantService()
            newTenantService = baseService.create_service(service_id, tenant_id, service_alias, service, self.user.pk)
            # create region tenantservice
            baseService.create_region_service(newTenantService, service, self.tenantName, self.tenant.region)
            # record service log
            data = {}
            data["log_msg"] = "服务创建成功，开始部署....."
            data["service_id"] = newTenantService.service_id
            data["tenant_id"] = newTenantService.tenant_id
            task = {}
            task["data"] = data
            task["tube"] = "app_log"
            task["service_id"] = newTenantService.service_id
            logger.info(task)
            regionClient.writeToRegionBeanstalk(self.tenant.region, newTenantService.service_id, json.dumps(task))
            
            result["status"] = "success"
            result["service_id"] = service_id
            result["service_alias"] = service_alias
        except Exception as e:
            logger.exception(e)
            TenantServiceInfo.objects.filter(service_id=service_id).delete()
            TenantServiceAuth.objects.filter(service_id=service_id).delete()
            result["status"] = "failure"
        return JsonResponse(result, status=200)
