# -*- coding: utf8 -*-
"""
  Created on 18/1/24.
"""
import datetime
import logging

from django.conf import settings

from console.constants import LogConstants, ServiceEventConstants
from console.repositories.event_repo import event_repo
from console.repositories.group import group_service_relation_repo
from console.repositories.region_repo import region_repo
from console.services.plugin.app_plugin import AppPluginService
from console.utils.timeutil import str_to_time, time_to_str
from goodrain_web.tools import JuncheePaginator
from www.apiclient.regionapi import RegionInvokeApi
from console.services.group_service import group_service
from console.repositories.app import service_repo
from console.repositories.team_repo import team_repo
from www.utils.crypt import make_uuid

app_plugin_service = AppPluginService()
region_api = RegionInvokeApi()
logger = logging.getLogger("default")


class AppWebSocketService(object):
    def get_log_instance_ws(self, request, region):
        sufix_uri = "docker_log"
        ws_url = self.__event_ws(request, region, sufix_uri)
        return ws_url

    def get_event_log_ws(self, request, region):
        sufix_uri = "event_log"
        ws_url = self.__event_ws(request, region, sufix_uri)
        return ws_url

    def get_monitor_log_ws(self, request, region, tenant, service):
        # tenant_plugin_relations = app_plugin_service.get_service_abled_plugin(service)
        sufix_uri = "new_monitor_message"
        # for tpr in tenant_plugin_relations:
        #     plugin = plugin_repo.get_plugin_by_plugin_id(tenant.tenant_id, tpr.plugin_id)
        #     if plugin.category == "analyst-plugin:perf" or plugin.category == "performance_analysis":
        #         sufix_uri = "new_monitor_message"
        #         break

        ws_url = self.__event_ws(request, region, sufix_uri)
        return ws_url

    def __event_ws(self, request, region, sufix_uri):
        region = region_repo.get_region_by_region_name(region_name=region)
        if not region:
            default_uri = settings.EVENT_WEBSOCKET_URL[region]
            if default_uri == "auto":
                host = request.META.get('HTTP_HOST').split(':')[0]
                return "ws://{0}:6060/{1}".format(host, sufix_uri)
            else:
                return "{0}/{1}".format(default_uri, sufix_uri)
        else:
            if region.wsurl == "auto":
                host = request.META.get('HTTP_HOST').split(':')[0]
                return "ws://{0}:6060/{1}".format(host, sufix_uri)
            else:
                return "{0}/{1}".format(region.wsurl, sufix_uri)

    def get_log_domain(self, request, region):
        region = region_repo.get_region_by_region_name(region_name=region)
        if not region:
            default_uri = settings.LOG_DOMAIN[region]
            if default_uri == "auto":
                host = request.META.get('HTTP_HOST').split(':')[0]
                return '{0}:6060'.format(host)
            return default_uri
        else:
            if region.wsurl == "auto":
                host = request.META.get('HTTP_HOST').split(':')[0]
                return '{0}:6060'.format(host)
            else:
                if "://" in region.wsurl:
                    ws_info = region.wsurl.split("://", 1)
                    if ws_info[0] == "wss":
                        return "https://{0}".format(ws_info[1])
                    else:
                        return "http://{0}".format(ws_info[1])
                return region.wsurl


class AppEventService(object):
    def checkEventTimeOut(self, event):
        """检查事件是否超时，应用起停操作30s超时，其他操作3m超时"""
        start_time = event.start_time
        if event.type == "deploy" or event.type == "create":
            if (datetime.datetime.now() - start_time).seconds > 180:
                event.final_status = "timeout"
                event.status = "timeout"
                event.save()
                return True
        else:
            if (datetime.datetime.now() - start_time).seconds > 30:
                event.final_status = "timeout"
                event.status = "timeout"
                event.save()
                return True
        return False

    def create_event(self, tenant, service, user, action, committer_name=None, deploy_version=None):
        last_event = event_repo.get_last_event(tenant.tenant_id, service.service_id)
        # 提前从数据中心更新event信息
        if last_event:
            self.__sync_region_service_event_status(service.service_region, tenant.tenant_name, [last_event], timeout=True)
        old_deploy_version = ""
        if last_event:
            if last_event.final_status == "":
                if not self.checkEventTimeOut(last_event):
                    return 409, "操作太频繁，请等待上次操作完成", None
            old_deploy_version = last_event.deploy_version

        if not action:
            return 400, "操作类型参数不存在", None
        event_id = make_uuid()
        event_info = {
            "event_id": event_id,
            "service_id": service.service_id,
            "tenant_id": tenant.tenant_id,
            "type": action,
            "deploy_version": service.deploy_version,
            "old_deploy_version": old_deploy_version,
            "region": service.service_region,
            "user_name": user.nick_name,
            "start_time": datetime.datetime.now()
        }
        if committer_name:
            event_info["user_name"] = committer_name
        if deploy_version:
            event_info["deploy_version"] = deploy_version

        if action == "deploy":
            last_deploy_event = event_repo.get_last_deploy_event(tenant.tenant_id, service.service_id)
            if last_deploy_event:
                old_code_version = last_deploy_event.code_version
            else:
                old_code_version = service.deploy_version
            event_info.update({"old_code_version": old_code_version})

        new_event = event_repo.create_event(**event_info)
        return 200, "success", new_event

    def update_event(self, event, message, status):
        event.status = status
        event.final_status = "complete"
        event.message = message[0:200]
        event.end_time = datetime.datetime.now()
        if event.status == "failure" and event.type == "callback":
            event.deploy_version = event.old_deploy_version
        event.save()
        return event

    def get_service_event(self, tenant, service, page, page_size, start_time_str):
        # 前端传入时间到分钟，默认会加上00，这样一来刚部署的组件的日志无法查询到，所有将当前时间添加一分钟
        if start_time_str:
            start_time = str_to_time(start_time_str, fmt="%Y-%m-%d %H:%M")
            start_time_str = time_to_str(start_time + datetime.timedelta(minutes=1))

        events = event_repo.get_events_before_specify_time(tenant.tenant_id, service.service_id, start_time_str)
        event_paginator = JuncheePaginator(events, int(page_size))
        total = event_paginator.count
        page_events = event_paginator.page(page)
        has_next = True
        if page_size * page >= total:
            has_next = False
        self.__sync_region_service_event_status(service.service_region, tenant.tenant_name, page_events)

        re_events = []
        for event in list(page_events):
            event_re = event.to_dict()
            # codeVersion = "版本:4c042b9 上传者:黄峻贤 Commit:Merge branch 'developer' into 'test'"
            version_info = self.wrapper_code_version(service, event)
            if version_info:
                event_re["code_version"] = version_info
            type_cn = self.translate_event_type(event.type)
            event_re["type_cn"] = type_cn
            re_events.append(event_re)
        return re_events, has_next

    def translate_event_type(self, action_type):
        TYPE_MAP = ServiceEventConstants.TYPE_MAP
        return TYPE_MAP.get(action_type, action_type)

    def get_service_event_log(self, tenant, service, level, event_id):
        body = {"event_id": event_id, "level": level, "enterprise_id": tenant.enterprise_id}
        msg_list = []
        try:
            res, rt_data = region_api.get_event_log(service.service_region, tenant.tenant_name, service.service_alias, body)
            if int(res.status) == 200:
                msg_list = rt_data["list"]
        except region_api.CallApiError as e:
            logger.debug(e)
        return msg_list

    def wrapper_code_version(self, service, event):
        if event.code_version:
            info = event.code_version.split(" ", 2)
            if len(info) == 3:
                versioninfo = {}
                ver = info[0].split(":", 1)
                versioninfo["code_version"] = ver[1]
                user = info[1].split(":", 1)
                versioninfo["user"] = user[1]
                commit = info[2].split(":", 1)
                if len(commit) > 1:
                    versioninfo["commit"] = commit[1]
                else:
                    versioninfo["commit"] = info[2]
                # deprecated
                if event.deploy_version == service.deploy_version:
                    versioninfo["rollback"] = False
                else:
                    versioninfo["rollback"] = True
                return versioninfo
        return {}

    def sync_region_service_event_status(self, region, tenant_name, events):
        return self.__sync_region_service_event_status(region, tenant_name, events)

    def __sync_region_service_event_status(self, region, tenant_name, events, timeout=False):
        local_events_not_complete = dict()
        for event in events:
            if not event.final_status or not event.status:
                local_events_not_complete[event.event_id] = event

        if not local_events_not_complete:
            return

        try:
            body = region_api.get_tenant_events(region, tenant_name, list(local_events_not_complete.keys()))
        except Exception as e:
            logger.exception(e)
            return

        region_events = body.get('list')
        for region_event in region_events:
            local_event = local_events_not_complete.get(region_event.get('EventID'))
            if not local_event:
                continue
            if not region_event.get('Status'):
                if timeout:
                    self.checkEventTimeOut(local_event)
            else:
                local_event.status = region_event.get('Status')
                local_event.message = region_event.get('Message')
                local_event.code_version = region_event.get('CodeVersion')
                local_event.deploy_version = region_event.get('DeployVersion')
                local_event.final_status = 'complete'
                endtime = datetime.datetime.strptime(region_event.get('EndTime')[0:19], '%Y-%m-%d %H:%M:%S')
                if endtime:
                    local_event.end_time = endtime
                else:
                    local_event.end_time = datetime.datetime.now()
                local_event.save()

    def delete_service_events(self, service):
        event_repo.delete_events(service.service_id)

    def get_target_events(self, target, target_id, tenant, region, page, page_size):
        msg_list = []
        has_next = False
        total = 0
        res, rt_data = region_api.get_target_events_list(region, tenant.tenant_name, target, target_id, page, page_size)
        if int(res.status) == 200:
            msg_list = rt_data.get("list", [])
            total = rt_data.get("number", 0)
            has_next = True
            if page_size * page >= total:
                has_next = False
        return msg_list, total, has_next

    def get_myteams_events(self, tenant, tenant_id_list, enterprise_id, region, page, page_size):
        msg_list = []
        has_next = False
        total = 0
        res, rt_data = region_api.get_myteams_events_list(region, enterprise_id, tenant, tenant_id_list, page, page_size)
        if int(res.status) == 200:
            msg_list = rt_data.get("list", [])
            total = rt_data.get("number", 0)
            has_next = True
            if page_size * page >= total:
                has_next = False
        my_teams_all_events = []
        if msg_list:
            for msg in msg_list:
                # TODO: 需要将数据库查询放在循环外
                msg.to_dict()
                current_build_info = msg["build_list"]["list"]
                every_event_log = msg["service_event"]
                group_info = group_service.get_service_group_info(every_event_log["TargetID"])
                group = group_service_relation_repo.get_group_by_service_id(every_event_log["TargetID"])
                service_info = service_repo.get_service_by_service_id(every_event_log["TargetID"])
                tenant_info = team_repo.get_team_by_team_id(every_event_log["TenantID"])
                every_event_log["build_version"] = current_build_info["build_version"]
                every_event_log["kind"] = current_build_info["kind"]
                every_event_log["delivered_type"] = current_build_info["image"]
                every_event_log["delivered_path"] = current_build_info["delivered_path"]
                every_event_log["code_commit_msg"] = current_build_info["code_commit_msg"]
                every_event_log["code_commit_author"] = current_build_info["code_commit_author"]
                every_event_log["create_time"] = current_build_info["create_time"]
                every_event_log["finish_time"] = current_build_info["finish_time"]
                every_event_log["final_status"] = current_build_info["final_status"]
                every_event_log["group_name"] = group_info.group_name
                every_event_log["group_id"] = group.group_id
                every_event_log["team_alias"] = tenant_info.tenant_alias
                every_event_log["team_name"] = tenant_info.tenant_name
                every_event_log["team_namespace"] = tenant_info.namespace
                every_event_log["service_name"] = service_info.service_cname
                every_event_log["service_alias"] = service_info.service_alias
                every_event_log["service_group_id"] = service_info.tenant_service_group_id
                every_event_log["region_name"] = group_info.region_name
                my_teams_all_events.append(every_event_log)
        return my_teams_all_events, total, has_next

    def get_event_log(self, tenant, region_name, event_id):
        content = []
        try:
            res, rt_data = region_api.get_events_log(tenant.tenant_name, region_name, event_id)
            if int(res.status) == 200:
                content = rt_data["list"]
        except region_api.CallApiError as e:
            logger.debug(e)
        return content


class AppLogService(object):
    def get_service_logs(self, tenant, service, action="service", lines=100):
        log_list = []
        try:
            if action == LogConstants.SERVICE:
                body = region_api.get_service_logs(service.service_region, tenant.tenant_name, service.service_alias, lines)
                log_list = body["list"]
            return 200, "success", log_list
        except region_api.CallApiError as e:
            logger.exception(e)
            return 200, "success", []

    def get_docker_log_instance(self, tenant, service):
        try:
            re = region_api.get_docker_log_instance(service.service_region, tenant.tenant_name, service.service_alias,
                                                    tenant.enterprise_id)
            bean = re["bean"]

            host_id = bean["host_id"]
            return 200, "success", host_id
        except region_api.CallApiError as e:
            logger.exception(e)
            return 400, "系统异常", None

    def get_history_log(self, tenant, service):
        try:
            body = region_api.get_service_log_files(service.service_region, tenant.tenant_name, service.service_alias,
                                                    tenant.enterprise_id)
            file_list = body["list"]
            return 200, "success", file_list
        except region_api.CallApiError as e:
            logger.exception(e)
            return 200, "success", []
