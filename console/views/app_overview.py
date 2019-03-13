# -*- coding: utf8 -*-
"""
  Created on 18/1/29.
"""
import datetime
import logging
import json
import os
import base64
import pickle

from django.db import transaction
from django.shortcuts import redirect
from django.views.decorators.cache import never_cache
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.response import Response

from console.repositories.app import service_source_repo
from console.repositories.group import tenant_service_group_repo
from console.repositories.market_app_repo import rainbond_app_repo
from console.services.team_services import team_services
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
from marketapi.services import MarketServiceAPIManager
from console.constants import AppConstants, PluginCategoryConstants
from console.repositories.app import service_repo, service_webhooks_repo
from console.views.base import JWTAuthApiView
from console.repositories.app_config import service_endpoints_repo
from console.repositories.deploy_repo import deploy_repo


logger = logging.getLogger("default")
region_api = RegionInvokeApi()
market_api = MarketServiceAPIManager()


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
            bean.update({"service": service_model})
            tenant_actions = self.user.actions.tenant_actions
            bean.update({"tenant_actions": tenant_actions})
            service_actions = self.user.actions.service_actions
            bean.update({"service_actions": service_actions})
            event_websocket_url = ws_service.get_event_log_ws(self.request, self.service.service_region)
            bean.update({"event_websocket_url": event_websocket_url})
            if self.service.service_source == "market":
                group_obj = tenant_service_group_repo.get_group_by_service_group_id(self.service.tenant_service_group_id)
                if not group_obj:
                    result = general_message(200, "success", "查询成功", bean=bean)
                    return Response(result, status=result["code"])
                rain_app = rainbond_app_repo.get_rainbond_app_by_key_and_version(group_obj.group_key, group_obj.group_version)
                if not rain_app:
                    result = general_message(200, "success", "当前云市应用已删除", bean=bean)
                    return Response(result, status=result["code"])
                else:
                    bean.update({"rain_app_name": rain_app.group_name})
                    apps_template = json.loads(rain_app.app_template)
                    apps_list = apps_template.get("apps")
                    for app in apps_list:
                        if app["service_key"] == self.service.service_key:
                            if app["deploy_version"] > self.service.deploy_version:
                                self.service.is_upgrate = True
                                self.service.save()
                                bean.update({"service": service_model})
                    try:
                        apps_template = json.loads(rain_app.app_template)
                        apps_list = apps_template.get("apps")
                        service_source = service_source_repo.get_service_source(self.service.tenant_id,
                                                                                self.service.service_id)
                        if service_source and service_source.extend_info:
                            extend_info = json.loads(service_source.extend_info)
                            if extend_info:
                                for app in apps_list:
                                    logger.debug('---------====app===============>{0}'.format(app))
                                    logger.debug('---------=====extend_info==============>{0}'.format(extend_info))

                                    if app.has_key("service_share_uuid"):
                                        if app["service_share_uuid"] == extend_info["source_service_share_uuid"]:
                                            new_version = int(app["deploy_version"])
                                            old_version = int(extend_info["source_deploy_version"])
                                            if new_version > old_version:
                                                self.service.is_upgrate = True
                                                self.service.save()
                                                service_model["is_upgrade"] = True
                                                bean.update({"service": service_model})
                                    elif not app.has_key("service_share_uuid") and app.has_key("service_key"):
                                        if app["service_key"] == extend_info["source_service_share_uuid"]:
                                            new_version = int(app["deploy_version"])
                                            old_version = int(extend_info["source_deploy_version"])
                                            if new_version > old_version:
                                                self.service.is_upgrate = True
                                                self.service.save()
                                                service_model["is_upgrade"] = True
                                                bean.update({"service": service_model})

                    except Exception as e:
                        logger.exception(e)

            if self.service.service_source == AppConstants.DOCKER_COMPOSE:
                if self.service.create_status != "complete":
                    compose_service_relation = compose_service.get_service_compose_id(self.service)
                    if compose_service_relation:
                        service_model["compose_id"] = compose_service_relation.compose_id
                        bean.update({"service": service_model})
            bean["is_third"] = False
            if self.service.service_source == "third_party":
                bean["is_third"] = True
                service_endpoints = service_endpoints_repo.get_service_endpoints_by_service_id(self.service.service_id)
                if service_endpoints:
                    bean["register_way"] = service_endpoints.endpoints_type
                    if service_endpoints.endpoints_type == "api":
                        # 从环境变量中获取域名，没有在从请求中获取
                        host = os.environ.get('DEFAULT_DOMAIN', request.get_host())
                        bean["api_url"] = "http://" + host + "/console/" + "third_party/{0}".format(self.service.service_id)
                        key_repo = deploy_repo.get_service_key_by_service_id(service_id=self.service.service_id)
                        if key_repo:
                            bean["api_service_key"] = pickle.loads(base64.b64decode(key_repo.secret_key)).get("secret_key")
                    if service_endpoints.endpoints_type == "discovery":
                        # 返回类型和key
                        endpoints_info_dict = json.loads(service_endpoints.endpoints_info)
                        logger.debug('--------endpoints_info---------->{0}'.format(endpoints_info_dict))

                        bean["discovery_type"] = endpoints_info_dict["type"]
                        bean["discovery_key"] = endpoints_info_dict["key"]

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
            if self.service.service_source == "market":
                group_obj = tenant_service_group_repo.get_group_by_service_group_id(self.service.tenant_service_group_id)
                if not group_obj:
                    result = general_message(200, "success", "当前云市应用已删除", bean=self.service.to_dict())
                    return Response(result, status=result["code"])
                rain_app = rainbond_app_repo.get_rainbond_app_by_key_and_version(group_obj.group_key, group_obj.group_version)
                if not rain_app:
                    result = general_message(200, "success", "当前云市应用已删除", bean=self.service.to_dict())
                    return Response(result, status=result["code"])
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
            bean["check_uuid"] = self.service.check_uuid
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
            if data["list"]:
                for d in data["list"]:
                    bean = dict()
                    bean["pod_name"] = d["pod_name"]
                    bean["pod_status"] = d["pod_status"]
                    bean["manage_name"] = "manager"
                    container = d["container"]
                    logger.debug('--------------11container-------------->{0}'.format(container))
                    container_list = []
                    for key, val in container.items():
                        if key == "POD":
                            continue
                        if key != self.service.service_id:
                            continue
                        container_dict = dict()
                        container_dict["container_name"] = key
                        memory_limit = float(val["memory_limit"]) / 1024 / 1024
                        memory_usage = float(val["memory_usage"]) / 1024 / 1024
                        usage_rate = 0
                        if memory_limit:
                            usage_rate = memory_usage * 100 / memory_limit
                        container_dict["memory_limit"] = round(memory_limit, 2)
                        container_dict["memory_usage"] = round(memory_usage, 2)
                        container_dict["usage_rate"] = round(usage_rate, 2)
                        container_list.append(container_dict)
                    bean["container"] = container_list
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


class AppGroupVisitView(JWTAuthApiView):

    def get(self, request, team_name, *args, **kwargs):
        """
        获取应用访问信息
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: service_list
              description: 服务别名列表
              required: true
              type: string
              paramType: path
        """

        try:
            serviceAlias = request.GET.get('service_alias')
            if not serviceAlias:
                result = general_message(200, "not service", "当前组内无应用", bean={"is_null": True})
                return Response(result)
            team = team_services.get_tenant_by_tenant_name(team_name)
            service_access_list = list()
            if not team:
                result = general_message(400, "not tenant", "团队不存在")
                return Response(result)
            service_list = serviceAlias.split('-')
            for service_alias in service_list:
                bean = dict()
                service = service_repo.get_service_by_service_alias(service_alias)
                access_type, data = port_service.get_access_info(team, service)
                bean["access_type"] = access_type
                bean["access_info"] = data
                service_access_list.append(bean)
            result = general_message(200, "success", "操作成功", list=service_access_list)
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


class ImageAppView(AppBaseView):

    @never_cache
    @perm_required('manage_service_config')
    def put(self, request, *args, **kwargs):
        """
        修改镜像源地址
        ---
        """

        try:
            image = request.data.get("image")
            cmd = request.data.get("cmd", None)
            if not image:
                return Response(general_message(400, "param error", "参数错误"), status=400)
            if cmd:
                self.service.cmd = cmd

            version = image.split(':')[-1]
            if not version:
                version = "latest"
                image = image + ":" + version
            self.service.image = image
            self.service.version = version
            self.service.save()
            result = general_message(200, "success", "修改成功")
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class BuildSourceinfo(AppBaseView):

    @never_cache
    @perm_required('manage_service_config')
    def get(self, request, *args, **kwargs):
        """
        查询构建源信息
        ---
        """
        service_alias = self.service.service_alias
        try:
            service_source = team_services.get_service_source(service_alias=service_alias)
            service_source_user = service_source_repo.get_service_source(team_id=self.service.tenant_id,
                                                                         service_id=self.service.service_id)
            user = ""
            password = ""
            bean = {}
            if service_source_user:
                user = service_source_user.user_name
                password = service_source_user.password
            bean["user_name"] = user
            bean["password"] = password
            if not service_source:
                return Response(general_message(404, "no found source", "没有这个应用的构建源"), status=404)
            if service_source.service_source == 'market':
                # 获取组对象
                group_obj = tenant_service_group_repo.get_group_by_service_group_id(
                    service_source.tenant_service_group_id)
                if group_obj:
                    # 获取内部市场对象
                    rain_app = rainbond_app_repo.get_rainbond_app_by_key_and_version(group_obj.group_key,
                                                                                     group_obj.group_version)
                    if rain_app:
                        bean["rain_app_name"] = rain_app.group_name
                        bean["details"] = rain_app.details
                        bean["app_version"] = rain_app.version
                        bean["group_key"] = rain_app.group_key
            bean["service_source"] = service_source.service_source
            bean["image"] = service_source.image
            bean["cmd"] = service_source.cmd
            bean["code_from"] = service_source.code_from
            bean["version"] = service_source.version
            bean["docker_cmd"] = service_source.docker_cmd
            bean["create_time"] = service_source.create_time
            bean["git_url"] = service_source.git_url
            bean["code_version"] = service_source.code_version
            bean["server_type"] = service_source.server_type
            bean["language"] = service_source.language
            if service_source.service_source == 'market':
                # 获取组对象
                group_obj = tenant_service_group_repo.get_group_by_service_group_id(
                    service_source.tenant_service_group_id)
                if group_obj:
                    # 获取内部市场对象
                    rain_app = rainbond_app_repo.get_rainbond_app_by_key_and_version(group_obj.group_key,
                                                                                     group_obj.group_version)
                    if rain_app:
                        bean["rain_app_name"] = rain_app.group_name
                        bean["details"] = rain_app.details
                        bean["version"] = rain_app.version
                        bean["group_key"] = rain_app.group_key
            result = general_message(200, "success", "查询成功", bean=bean)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @never_cache
    @perm_required('manage_service_config')
    @transaction.atomic
    def put(self, request, *args, **kwargs):
        """
        修改构建源
        ---
        """
        s_id = transaction.savepoint()
        try:
            image = request.data.get("image", None)
            cmd = request.data.get("cmd", None)
            service_source = request.data.get("service_source")
            git_url = request.data.get("git_url", None)
            code_version = request.data.get("code_version", None)
            user_name = request.data.get("user_name", None)
            password = request.data.get("password", None)

            if not service_source:
                return Response(general_message(400, "param error", "参数错误"), status=400)

            service_source_user = service_source_repo.get_service_source(team_id=self.service.tenant_id,
                                                                         service_id=self.service.service_id)

            if not service_source_user:
                service_source_info = {
                    "service_id": self.service.service_id,
                    "team_id": self.service.tenant_id,
                    "user_name": user_name,
                    "password": password,
                    "create_time": datetime.datetime.now().strftime('%Y%m%d%H%M%S')
                }
                service_source_repo.create_service_source(**service_source_info)
            else:
                service_source_user.user_name = user_name
                service_source_user.password = password
                service_source_user.save()
            if service_source == "source_code":
                if code_version:
                    self.service.code_version = code_version
                else:
                    self.service.code_version = "master"
                if git_url:
                    self.service.git_url = git_url
                self.service.save()
                transaction.savepoint_commit(s_id)
            elif service_source == "docker_run":
                if image:
                    version = image.split(':')[-1]
                    if not version:
                        version = "latest"
                        image = image + ":" + version
                    self.service.image = image
                    self.service.version = version
                self.service.cmd = cmd
                self.service.save()
                transaction.savepoint_commit(s_id)
            result = general_message(200, "success", "修改成功")
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            transaction.savepoint_rollback(s_id)
        return Response(result, status=result["code"])


class AppKeywordView(AppBaseView):
    @never_cache
    @perm_required('manage_service_config')
    def put(self, request, *args, **kwargs):
        """
        修改服务触发自动部署关键字
        """

        try:
            keyword = request.data.get("keyword", None)
            if not keyword:
                return Response(general_message(400, "param error", "参数错误"), status=400)

            is_pass, msg = app_service.check_service_cname(self.tenant, keyword, self.service.service_region)
            if not is_pass:
                return Response(general_message(400, "param error", msg), status=400)
            service_webhook = service_webhooks_repo.get_service_webhooks_by_service_id_and_type(self.service.service_id,
                                                                                                "code_webhooks")
            if not service_webhook:
                return Response(general_message(412, "keyword is null", "服务自动部署属性不存在"), status=412)
            service_webhook.deploy_keyword = keyword
            service_webhook.save()
            result = general_message(200, "success", "修改成功", bean=service_webhook.to_dict())
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

