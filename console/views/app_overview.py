# -*- coding: utf8 -*-
"""
  Created on 18/1/29.
"""
import logging

from django.shortcuts import redirect
from django.views.decorators.cache import never_cache
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.response import Response

from console.views.app_config.base import AppBaseView
from www.apiclient.regionapi import RegionInvokeApi
from www.decorator import perm_required
from www.utils.return_message import general_message, error_message
from console.services.app import app_service
from console.services.plugin import app_plugin_service
from console.services.app_actions import ws_service
from console.services.app_config import port_service
from console.services.group_service import group_service
from console.services.region_services import region_services
from console.services.compose_service import compose_service
from www.utils.url import get_redirect_url
from www.utils.md5Util import md5fun
from django.conf import settings
from console.constants import AppConstants, PluginCategoryConstants

logger = logging.getLogger("default")
region_api = RegionInvokeApi()


class AppDetailView(AppBaseView):
    @never_cache
    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        """
        应用详情信息
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
        bean = dict()
        try:
            # status_map = app_service.get_service_status(self.tenant, self.service)
            # used_resource = app_service.get_service_resource_with_plugin(self.tenant, self.service,
            #                                                              status_map["status"])
            # service_abled_plugins = app_plugin_service.get_service_abled_plugin(self.service)
            # plugin_list = [p.to_dict() for p in service_abled_plugins]
            # bean.update(status_map)
            # bean.update(used_resource)
            # bean.update({"plugin_list": plugin_list})
            service_model = self.service.to_dict()
            group_map = group_service.get_services_group_name([self.service.service_id])
            group_name = group_map.get(self.service.service_id)["group_name"]
            group_id = group_map.get(self.service.service_id)["group_id"]
            service_model["group_name"] = group_name
            service_model["group_id"] = group_id
            if self.service.service_source == AppConstants.DOCKER_COMPOSE:
                if self.service.create_status != "complete":
                    compose_service_relation = compose_service.get_service_compose_id(self.service)
                    if compose_service_relation:
                        service_model["compose_id"] = compose_service_relation.compose_id
            bean.update({"service": service_model})
            tenant_actions = self.user.actions.tenant_actions
            bean.update({"tenant_actions": tenant_actions})
            service_actions = self.user.actions.service_actions
            bean.update({"service_actions": service_actions})

            event_websocket_url = ws_service.get_event_log_ws(self.request, self.service.service_region)
            # monitor_websocket_uri = ws_service.get_monitor_log_ws(self.request, self.response_region, self.tenant,
            #                                                       self.service)
            bean.update({"event_websocket_url": event_websocket_url})
            result = general_message(200, "success", "查询成功", bean=bean)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class AppBriefView(AppBaseView):
    @never_cache
    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        """
        应用详情信息
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

            result = general_message(200, "success", "查询成功", bean=self.service.to_dict())
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @never_cache
    @perm_required('manage_service_config')
    def put(self, request, *args, **kwargs):
        """
        修改应用名称
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
            - name: service_cname
              description: 服务名称
              required: true
              type: string
              paramType: form
        """

        try:
            service_cname = request.data.get("service_cname", None)
            is_pass, msg = app_service.check_service_cname(self.tenant, service_cname, self.service.service_region)
            if not is_pass:
                return Response(general_message(400, "param error", msg), status=400)
            self.service.service_cname = service_cname
            self.service.save()
            result = general_message(200, "success", "查询成功", bean=self.service.to_dict())
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class AppStatusView(AppBaseView):
    @never_cache
    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        """
        获取应用状态
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
        bean = dict()
        try:
            status_map = app_service.get_service_status(self.tenant, self.service)
            bean.update(status_map)
            result = general_message(200, "success", "查询成功", bean=bean)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class AppPodsView(AppBaseView):
    @never_cache
    @perm_required('manage_service_container')
    def get(self, request, *args, **kwargs):
        """
        获取应用实例
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
            data = region_api.get_service_pods(self.service.service_region, self.tenant.tenant_name,
                                               self.service.service_alias,
                                               self.tenant.enterprise_id)
            rt_list = []
            for d in data["list"]:
                bean = dict()
                bean["pod_name"] = d["PodName"]
                bean["manage_name"] = "manager"
                rt_list.append(bean)
            result = general_message(200, "success", "操作成功", list=rt_list)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @never_cache
    @perm_required('manage_service_container')
    def post(self, request, *args, **kwargs):
        """
        进入应用实例
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
            - name: c_id
              description: container_id
              required: true
              type: string
              paramType: form
            - name: h_id
              description: host_id
              required: true
              type: string
              paramType: form

        """
        bean = dict()
        try:
            c_id = request.data.get("c_id", "")
            h_id = request.data.get("h_id", "")
            logger.info("c_id = {0} h_id = {1}".format(c_id, h_id))
            result = general_message(200, "success", "操作成功", bean=bean)
            response = Response(result, status=result["code"])
            if c_id != "" and h_id != "":
                response.set_cookie('docker_h_id', h_id)
                response.set_cookie('docker_c_id', c_id)
                response.set_cookie('docker_s_id', self.service.service_id)
            return response
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class AppVisitView(AppBaseView):
    @never_cache
    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        """
        获取应用访问信息
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
        bean = dict()
        try:
            access_type, data = port_service.get_access_info(self.tenant, self.service)
            bean["access_type"] = access_type
            bean["access_info"] = data
            result = general_message(200, "success", "操作成功", bean=bean)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class AppPluginsBriefView(AppBaseView):
    @never_cache
    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        """
        获取应用安装的插件的简要信息
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
        bean = dict()
        try:
            service_abled_plugins = app_plugin_service.get_service_abled_plugin(self.service)
            plugin_list = [p.to_dict() for p in service_abled_plugins]
            result = general_message(200, "success", "操作成功", bean=bean, list=plugin_list)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class AppDockerView(AppBaseView):
    # 指明为模板render
    renderer_classes = (TemplateHTMLRenderer,)

    @never_cache
    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        """
        获取console TTY页面
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
        response = redirect(get_redirect_url("/index#/index", request))
        try:
            docker_c_id = request.COOKIES.get('docker_c_id', '')
            docker_h_id = request.COOKIES.get('docker_h_id', '')
            docker_s_id = request.COOKIES.get('docker_s_id', '')
            bean = dict()
            if docker_c_id != "" and docker_h_id != "" and docker_s_id != "" and docker_s_id == self.service.service_id:
                t_docker_h_id = docker_h_id.lower()
                bean["tenant_id"] = self.service.tenant_id
                bean["service_id"] = docker_s_id
                bean["ctn_id"] = docker_c_id
                bean["md5"] = md5fun(self.service.tenant_id + "_" + docker_s_id + "_" + docker_c_id)
                main_url = region_services.get_region_wsurl(self.service.service_region)
                if main_url == "auto":
                    bean["ws_uri"] = '{}://{}:6060/docker_console?nodename={}'.format(settings.DOCKER_WSS_URL["type"],
                                                                                      settings.DOCKER_WSS_URL[
                                                                                          self.service.service_region],
                                                                                      t_docker_h_id)
                else:
                    bean["ws_uri"] = "{0}/docker_console?nodename={1}".format(main_url, t_docker_h_id)
                response = Response(general_message(200, "success", "信息获取成功"), status=200,
                                    template_name="www/console.html")
        except Exception as e:
            logger.exception(e)

        return response


class AppGroupView(AppBaseView):

    @never_cache
    @perm_required('manage_group')
    def put(self, request, *args, **kwargs):
        """
        修改应用所在组
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
            - name: group_id
              description: 组ID
              required: true
              type: integer
              paramType: form
        """

        try:
            group_id = request.data.get("group_id", None)
            if group_id is None:
                return Response(general_message(400, "param error", "请指定修改的组"), status=400)
            group_id = int(group_id)
            if group_id == -1:
                group_service.delete_service_group_relation_by_service_id(self.service.service_id)
            else:
                code, msg, group = group_service.get_group_by_id(self.tenant, self.service.service_region, group_id)
                if code != 200:
                    return Response(general_message(code, "group not found", "未找到需要修改的组信息"))
                group_service.update_or_create_service_group_relation(self.tenant, self.service, group_id)

            result = general_message(200, "success", "修改成功")
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class AppAnalyzePluginView(AppBaseView):
    @never_cache
    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        """
        查询应用的性能分析插件
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
            service_abled_plugins = app_plugin_service.get_service_abled_plugin(self.service)
            analyze_plugins = []
            for plugin in service_abled_plugins:
                if plugin.category == PluginCategoryConstants.PERFORMANCE_ANALYSIS:
                    analyze_plugins.append(plugin)

            result = general_message(200, "success", "查询成功", list=[p.to_dict() for p in analyze_plugins])
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])