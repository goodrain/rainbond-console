# -*- coding: utf8 -*-
import datetime
import logging

from django.http import JsonResponse

from www.apiclient.regionapi import RegionInvokeApi
from www.models import ServiceEvent
from www.tenantservice.baseservice import BaseTenantService
from www.utils.crypt import make_uuid
from www.views import AuthedView

baseService = BaseTenantService()
logger = logging.getLogger('default')
region_api = RegionInvokeApi()


class EventManager(AuthedView):
    def post(self, request, *args, **kwargs):
        result = {}
        event_id = make_uuid()
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
            if not action:
                result["status"] = "failure"
                result["msg"] = "action cannot be empty"
                return JsonResponse(result, status=200)
            event = ServiceEvent(event_id=event_id, service_id=self.service.service_id,
                                 tenant_id=self.tenant.tenant_id, type=action,
                                 deploy_version=self.service.deploy_version, old_deploy_version=old_deploy_version,
                                 user_name=self.user.nick_name, start_time=datetime.datetime.now())
            old_code_version = ""
            if action == "deploy":
                last_all_deploy_event = ServiceEvent.objects.filter(service_id=self.service.service_id,
                                                                    type="deploy").order_by("-start_time")
                if last_all_deploy_event:
                    last_deploy_event = last_all_deploy_event[0]
                    old_code_version = last_deploy_event.code_version
                    event.old_code_version = old_code_version

            event.save()
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
            logger.exception(e)
            result["status"] = "failure"
            result["message"] = e.message
            ServiceEvent.objects.filter(event_id=event_id).delete()
            return JsonResponse(result, status=500)

    def get(self, request, *args, **kwargs):

        result = {}
        try:
            now = datetime.datetime.now() + datetime.timedelta(minutes=1)
            now_str = now.strftime("%Y-%m-%d %H:%M")
            page_size = request.GET.get("page_size", 6)
            start_index = request.GET.get("start_index", 0)
            # 2018-02-02 13:32
            start_time_str = request.GET.get("start_time", now_str)
            start_index = int(start_index)

            start_time = datetime.datetime.strptime(start_time_str, "%Y-%m-%d %H:%M")
            start_time = (start_time + datetime.timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S")

            events = ServiceEvent.objects.filter(service_id=self.service.service_id, start_time__lte=start_time).order_by("-start_time")
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

            # 同步数据中心时间状态
            self.__sync_region_service_event_status(self.service.service_region, self.tenant.tenant_name, events)

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
                eventRe["old_code_version"] = event.old_code_version
                # codeVersion = "版本:4c042b9 上传者:黄峻贤 Commit:Merge branch 'developer' into 'test'"
                if event.code_version:
                    info = event.code_version.split(" ", 2)
                    if len(info) == 3:
                        versioninfo = {}
                        ver = info[0].split(":", 1)
                        versioninfo["code_version"] = ver[1]
                        user = info[1].split(":", 1)
                        versioninfo["user"] = user[1]
                        commit = info[2].split(":", 1)
                        versioninfo["commit"] = commit[1]
                        if event.deploy_version == self.service.deploy_version:
                            versioninfo["rollback"] = False
                        else:
                            versioninfo["rollback"] = True
                        eventRe["code_version"] = versioninfo

                reEvents.append(eventRe)
            result["log"] = reEvents
            return JsonResponse(result, status=200)
        except Exception as e:
            logging.exception(e)
            result["status"] = "failure"
            result["message"] = repr(e)
            return JsonResponse(result, status=500)

    def __sync_region_service_event_status(self, region, tenant_name, events):
        local_events_not_complete = dict()
        for event in events:
            if event.final_status == '':
                local_events_not_complete[event.event_id] = event

        if not local_events_not_complete:
            return

        try:
            body = region_api.get_tenant_events(region, tenant_name, local_events_not_complete.keys())
        except Exception as e:
            logger.exception(e)
            return

        region_events = body.get('list')
        for region_event in region_events:
            local_event = local_events_not_complete.get(region_event.get('EventID'))
            if not local_event:
                continue

            if not region_event.get('Status'):
                baseService.checkEventTimeOut(local_event)
            else:
                local_event.status = region_event.get('Status')
                local_event.message = region_event.get('Message')
                local_event.code_version = region_event.get('CodeVersion')
                local_event.deploy_version = region_event.get('DeployVersion')
                local_event.final_status = 'complete'
                local_event.end_time = datetime.datetime.now()
                local_event.save()




class EventLogManager(AuthedView):
    def get(self, request, event_id, *args, **kwargs):

        result = {}
        try:
            level = request.GET.get("level", "info")
            body = {}
            body["event_id"] = event_id
            body["level"] = level
            body["enterprise_id"] = self.tenant.enterprise_id
            res, rt_data = region_api.get_event_log(self.service.service_region, self.tenantName, self.service.service_alias,
                                              body)
            if int(res.status) == 200:
                msg_list = rt_data["list"]
                result["status"] = "success"
                result["data"] = msg_list
            return JsonResponse(result, status=200)
        except Exception as e:
            result["status"] = "failure"
            result["message"] = e.message
            return JsonResponse(result, status=500)
