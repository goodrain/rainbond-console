# -*- coding: utf8 -*-
import logging
from www.views import AuthedView
from www.decorator import perm_required
from www.models import ServiceEvent, TenantServiceInfo
import datetime
from django.http import JsonResponse
from www.utils.crypt import make_uuid
from www.tenantservice.baseservice import BaseTenantService
from www.service_http import RegionServiceApi
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

baseService = BaseTenantService()
regionClient = RegionServiceApi()
logger = logging.getLogger('default')


class EventManager(AuthedView):
    @perm_required('manage_service')
    def post(self, request, *args, **kwargs):
        result = {}
        try:
            old_deploy_version = ""
            # 检查上次事件是否完成
            events = ServiceEvent.objects.filter(service_id=self.service.service_id).order_by("-start_time")
            if events:
                last_event = events[0]
                if last_event.final_status == "":
                    if not baseService.checkEventTimeOut(last_event):
                        result["status"] = "often"
                        return JsonResponse(result, status=200)
                old_deploy_version = last_event.deploy_version
            action = request.POST["action"]
            event = ServiceEvent(event_id=make_uuid(), service_id=self.service.service_id,
                                 tenant_id=self.tenant.tenant_id, type=action,
                                 deploy_version=self.service.deploy_version, old_deploy_version=old_deploy_version,
                                 user_name=self.user.nick_name, start_time=datetime.datetime.now())
            event.save()
            old_code_version = ""
            if action == "deploy":
                last_all_deploy_event = ServiceEvent.objects.filter(service_id=self.service.service_id,
                                                                    type="deploy").order_by("-start_time")
                if last_all_deploy_event.count() > 0:
                    last_deploy_event = last_all_deploy_event[0:1]
                    old_code_version = last_deploy_event.code_version
            
            result["status"] = "success"
            result["event"] = {}
            result["event"]["event_id"] = event.event_id
            result["event"]["user_name"] = event.user_name
            result["event"]["event_type"] = event.type
            result["event"]["event_start_time"] = event.start_time
            result["event"]["old_deploy_version"] = old_deploy_version
            result["event"]["old_code_version"] = old_code_version
            return JsonResponse(result, status=200)
        except Exception as e:
            
            result["status"] = "failure"
            result["message"] = e.message
            return JsonResponse(result, status=500)
    
    def get(self, request, *args, **kwargs):
        
        result = {}
        try:
            page_size = request.GET.get("page_size", 6)
            start_index = request.GET.get("start_index", 0)
            start_index = int(start_index)
            events = ServiceEvent.objects.filter(service_id=self.service.service_id).order_by("-start_time")
            count = events.count()
            result = {}
            if int(start_index + 1) > count:
                result["has_next"] = False
                result["log"] = {}
                return JsonResponse(result, status=200)
            if count - (start_index + 1) < page_size:
                result["has_next"] = False
                events = events[start_index:]
            else:
                result["has_next"] = True
                events = events[start_index:start_index + page_size]
            reEvents = []
            for event in list(events):
                eventRe = {}
                eventRe["start_time"] = event.start_time
                eventRe["end_time"] = event.end_time
                eventRe["user_name"] = event.user_name
                eventRe["message"] = event.message
                eventRe["type"] = event.type
                eventRe["status"] = event.status
                eventRe["final_status"] = event.final_status
                eventRe["event_id"] = event.event_id
                eventRe["deploy_version"] = event.deploy_version
                eventRe["old_deploy_version"] = event.old_deploy_version
                reEvents.append(eventRe)
            result["log"] = reEvents
            return JsonResponse(result, status=200)
        except Exception as e:
            logging.exception(e)
            result["status"] = "failure"
            result["message"] = repr(e)
            return JsonResponse(result, status=500)


class EventLogManager(AuthedView):
    def get(self, request, event_id, *args, **kwargs):
        
        result = {}
        try:
            level = request.GET.get("level", "info")
            result = regionClient.getEventLog(self.service.service_region, event_id, level=level)
            return JsonResponse(result, status=200)
        except Exception as e:
            result["status"] = "failure"
            result["message"] = e.message
            return JsonResponse(result, status=500)
