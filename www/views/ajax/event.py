# -*- coding: utf8 -*-
import logging
from www.views import AuthedView
from www.decorator import perm_required
from www.models import ServiceEvent
import datetime
from django.http import JsonResponse
from www.utils.crypt import make_uuid
from www.tenantservice.baseservice import BaseTenantService
from www.service_http import RegionServiceApi

baseService = BaseTenantService()
regionClient = RegionServiceApi()
logger = logging.getLogger('default')


class EventManager(AuthedView):
    @perm_required('manage_service')
    def post(self, request, *args, **kwargs):
        result = {}
        try:
            # 检查上次事件是否完成
            events = ServiceEvent.objects.filter(service_id=self.service.service_id).order_by("-start_time")
            if events:
                last_event = events[0]
                if last_event.final_status == "":
                    if not baseService.checkEventTimeOut(last_event):
                        result["status"] = "often"
                        return JsonResponse(result, status=200)
            
            action = request.POST["action"]
            event = ServiceEvent(event_id=make_uuid(), service_id=self.service.service_id,
                                 tenant_id=self.tenant.tenant_id, type=action,
                                 user_name=self.user.nick_name, start_time=datetime.datetime.now())
            event.save()
            result["status"] = "success"
            result["event"] = {}
            result["event"]["event_id"] = event.event_id
            result["event"]["user_name"] = event.user_name
            result["event"]["event_type"] = event.type
            result["event"]["event_start_time"] = event.start_time
            return JsonResponse(result, status=200)
        except Exception as e:
            
            result["status"] = "failure"
            result["message"] = e.message
            return JsonResponse(result, status=500)
    
    def get(self, request, *args, **kwargs):
        
        result = {}
        try:
            events = ServiceEvent.objects.filter(service_id=self.service.service_id).order_by("-start_time")
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
                reEvents.append(eventRe)
            result = {}
            result["log"] = reEvents
            result["num"] = len(reEvents)
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
