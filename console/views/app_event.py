# -*- coding: utf8 -*-
"""
  Created on 18/1/15.
"""
import logging

from django.views.decorators.cache import never_cache
from rest_framework.response import Response

from console.services.app_actions import event_service, log_service, ws_service
from console.views.app_config.base import AppBaseView
from www.decorator import perm_required
from www.utils.return_message import general_message, error_message
from console.constants import LogConstants

logger = logging.getLogger("default")


class AppEventView(AppBaseView):
    @never_cache
    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        """
        获取服务的event事件
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 服务别名
              required: true
              type: string
              paramType: path
            - name: page
              description: 页号
              required: false
              type: integer
              paramType: query
            - name: page_size
              description: 每页大小
              required: false
              type: integer
              paramType: query
            - name: start_time
              description: 起始时间
              required: false
              type: string
              paramType: query
        """
        try:
            page = request.GET.get("page", 1)
            page_size = request.GET.get("page_size", 6)
            start_time = request.GET.get("start_time", None)
            events, has_next = event_service.get_service_event(self.tenant, self.service, int(page), int(page_size),
                                                               start_time)

            result = general_message(200, "success", "查询成功", list=events, has_next=has_next)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class AppEventLogView(AppBaseView):
    @never_cache
    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        """
        获取服务的event的详细日志
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 服务别名
              required: true
              type: string
              paramType: path
            - name: level
              description: 日志等级
              required: false
              type: string
              paramType: query
            - name: event_id
              description: 时间id
              required: true
              type: string
              paramType: query
        """
        try:
            level = request.GET.get("level", LogConstants.INFO)
            event_id = request.GET.get("event_id", None)
            if not event_id:
                return Response(general_message(400, "params error", "请指明具体操作事件"), status=400)

            log_list = event_service.get_service_event_log(self.tenant, self.service, level, event_id)
            result = general_message(200, "success", "查询成功", list=log_list)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class AppLogView(AppBaseView):
    @never_cache
    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        """
        获取服务的日志
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 服务别名
              required: true
              type: string
              paramType: path
            - name: action
              description: 日志类型（目前只有一个 service）
              required: false
              type: string
              paramType: query
            - name: lines
              description: 日志数量，默认为50
              required: false
              type: integer
              paramType: query

        """
        try:
            action = request.GET.get("action", "service")
            lines = request.GET.get("lines", 50)

            code, msg, log_list = log_service.get_service_logs(self.tenant, self.service, action, int(lines))
            if code != 200:
                return Response(general_message(code, "query service log error", msg), status=code)
            result = general_message(200, "success", "查询成功", list=log_list)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class AppLogInstanceView(AppBaseView):
    @never_cache
    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        """
        获取日志websocket信息
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 服务别名
              required: true
              type: string
              paramType: path
        """
        try:

            code, msg, host_id = log_service.get_docker_log_instance(self.tenant, self.service)
            web_socket_url = ws_service.get_log_instance_ws(request, self.service.service_region)
            bean = {"web_socket_url": web_socket_url}
            if code == 200:
                web_socket_url += "?host_id={0}".format(host_id)
                bean["host_id"] = host_id
                bean["web_socket_url"] = web_socket_url
            result = general_message(200, "success", "查询成功", bean=bean)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class AppHistoryLogView(AppBaseView):
    @never_cache
    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        """
        获取应用历史日志
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 服务别名
              required: true
              type: string
              paramType: path
        """
        try:

            code, msg, file_list = log_service.get_history_log(self.tenant, self.service)
            log_domain_url = ws_service.get_log_domain(request, self.service.service_region)
            if code != 200:
                file_list = []
            file_urls = []
            for f in file_list:
                file_name = f[22:]
                file_url = log_domain_url + f
                file_urls.append({
                    "file_name": file_name,
                    "file_url": file_url
                })

            result = general_message(200, "success", "查询成功", list=file_urls)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])
