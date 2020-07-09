# -*- coding: utf8 -*-
"""
  Created on 18/1/29.
"""
import base64
import datetime
import json
import logging
import os
import pickle

from django.db import transaction
from django.views.decorators.cache import never_cache
from rest_framework.response import Response

from console.exception.main import ServiceHandleException
from console.constants import AppConstants, PluginCategoryConstants
from console.exception.main import MarketAppLost, RbdAppNotFound
from console.repositories.app import (service_repo, service_source_repo, service_webhooks_repo)
from console.repositories.app_config import service_endpoints_repo
from console.repositories.deploy_repo import deploy_repo
from console.repositories.market_app_repo import rainbond_app_repo
from console.repositories.oauth_repo import oauth_repo, oauth_user_repo
from console.services.app import app_service
from console.services.app_actions import ws_service
from console.services.app_config import port_service
from console.services.compose_service import compose_service
from console.services.group_service import group_service
from console.services.market_app_service import market_app_service
from console.services.plugin import app_plugin_service
from console.services.team_services import team_services
from console.utils.oauth.oauth_types import get_oauth_instance
from console.views.app_config.base import AppBaseView
from console.views.base import RegionTenantHeaderView
from www.apiclient.regionapi import RegionInvokeApi
from www.utils.return_message import error_message, general_message

logger = logging.getLogger("default")
region_api = RegionInvokeApi()


class AppDetailView(AppBaseView):
    @never_cache
    def get(self, request, *args, **kwargs):
        """
        组件详情信息
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 组件别名
              required: true
              type: string
              paramType: path
        """
        bean = dict()
        service_model = self.service.to_dict()
        group_map = group_service.get_services_group_name([self.service.service_id])
        group_name = group_map.get(self.service.service_id)["group_name"]
        group_id = group_map.get(self.service.service_id)["group_id"]
        service_model["group_name"] = group_name
        service_model["group_id"] = group_id
        bean.update({"service": service_model})
        event_websocket_url = ws_service.get_event_log_ws(self.request, self.service.service_region)
        bean.update({"event_websocket_url": event_websocket_url})
        if self.service.service_source == "market":
            service_source = service_source_repo.get_service_source(self.tenant.tenant_id, self.service.service_id)
            if not service_source:
                result = general_message(200, "success", "查询成功", bean=bean)
                return Response(result, status=result["code"])
            rainbond_app, rainbond_app_version = rainbond_app_repo.get_rainbond_app_and_version(
                self.tenant.enterprise_id, service_source.group_key, service_source.version)
            if not rainbond_app:
                result = general_message(200, "success", "当前云市组件已删除", bean=bean)
                return Response(result, status=result["code"])

            bean.update({"rain_app_name": rainbond_app.app_name})
            apps_template = json.loads(rainbond_app_version.app_template)
            apps_list = apps_template.get("apps")
            for app in apps_list:
                if app["service_key"] == self.service.service_key:
                    if self.service.deploy_version and int(app["deploy_version"]) > int(self.service.deploy_version):
                        self.service.is_upgrate = True
                        self.service.save()
                        bean.update({"service": service_model})
            try:
                apps_template = json.loads(rainbond_app_version.app_template)
                apps_list = apps_template.get("apps")
                service_source = service_source_repo.get_service_source(self.service.tenant_id, self.service.service_id)
                if service_source and service_source.extend_info:
                    extend_info = json.loads(service_source.extend_info)
                    if extend_info:
                        for app in apps_list:
                            if "service_share_uuid" in app:
                                if app["service_share_uuid"] == extend_info["source_service_share_uuid"]:
                                    new_version = int(app["deploy_version"])
                                    old_version = int(extend_info["source_deploy_version"])
                                    if new_version > old_version:
                                        self.service.is_upgrate = True
                                        self.service.save()
                                        service_model["is_upgrade"] = True
                                        bean.update({"service": service_model})
                            elif "service_share_uuid" not in app and "service_key" in app:
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
            service_endpoints = service_endpoints_repo.get_service_endpoints_by_service_id(self.service.service_id).first()
            if service_endpoints:
                bean["register_way"] = service_endpoints.endpoints_type
                if service_endpoints.endpoints_type == "api":
                    # 从环境变量中获取域名，没有在从请求中获取
                    host = os.environ.get('DEFAULT_DOMAIN', "http://" + request.get_host())
                    bean["api_url"] = host + "/console/" + "third_party/{0}".format(self.service.service_id)
                    key_repo = deploy_repo.get_service_key_by_service_id(service_id=self.service.service_id)
                    if key_repo:
                        bean["api_service_key"] = pickle.loads(base64.b64decode(key_repo.secret_key)).get("secret_key")
                if service_endpoints.endpoints_type == "discovery":
                    # 返回类型和key
                    endpoints_info_dict = json.loads(service_endpoints.endpoints_info)

                    bean["discovery_type"] = endpoints_info_dict["type"]
                    bean["discovery_key"] = endpoints_info_dict["key"]

        result = general_message(200, "success", "查询成功", bean=bean)
        return Response(result, status=result["code"])


class AppBriefView(AppBaseView):
    @never_cache
    def get(self, request, *args, **kwargs):
        """
        组件详情信息
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 组件别名
              required: true
              type: string
              paramType: path
        """
        msg = "查询成功"
        if self.service.service_source == "market":
            try:
                market_app_service.check_market_service_info(self.tenant, self.service)
            except MarketAppLost as e:
                msg = e.msg
            except RbdAppNotFound as e:
                msg = e.msg
            except ServiceHandleException as e:
                logger.debug(e)
        result = general_message(200, "success", msg, bean=self.service.to_dict())
        return Response(result, status=result["code"])

    @never_cache
    def put(self, request, *args, **kwargs):
        """
        修改组件名称
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 组件别名
              required: true
              type: string
              paramType: path
            - name: service_cname
              description: 组件名称
              required: true
              type: string
              paramType: form
        """
        service_cname = request.data.get("service_cname", None)
        is_pass, msg = app_service.check_service_cname(self.tenant, service_cname, self.service.service_region)
        if not is_pass:
            return Response(general_message(400, "param error", msg), status=400)
        self.service.service_cname = service_cname
        self.service.save()
        result = general_message(200, "success", "查询成功", bean=self.service.to_dict())
        return Response(result, status=result["code"])


class AppStatusView(AppBaseView):
    @never_cache
    def get(self, request, *args, **kwargs):
        """
        获取组件状态
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 组件别名
              required: true
              type: string
              paramType: path
        """
        bean = dict()
        bean["check_uuid"] = self.service.check_uuid
        status_map = app_service.get_service_status(self.tenant, self.service)
        bean.update(status_map)
        result = general_message(200, "success", "查询成功", bean=bean)
        return Response(result, status=result["code"])


class ListAppPodsView(AppBaseView):
    @never_cache
    def get(self, request, *args, **kwargs):
        """
        获取组件实例
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 组件别名
              required: true
              type: string
              paramType: path
        """

        data = region_api.get_service_pods(self.service.service_region, self.tenant.tenant_name, self.service.service_alias,
                                           self.tenant.enterprise_id)
        result = {}
        if data["bean"]:

            def foobar(data):
                if data is None:
                    return
                res = []
                for d in data:
                    bean = dict()
                    bean["pod_name"] = d["pod_name"]
                    bean["pod_status"] = d["pod_status"]
                    bean["manage_name"] = "manager"
                    container = d["container"]
                    container_list = []
                    for key, val in container.items():
                        if key == "POD":
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
                    res.append(bean)
                return res

            pods = data["bean"]
            newpods = foobar(pods.get("new_pods", None))
            old_pods = foobar(pods.get("old_pods", None))
            result = {"new_pods": newpods, "old_pods": old_pods}
        result = general_message(200, "success", "操作成功", list=result)
        return Response(result, status=result["code"])

    @never_cache
    def post(self, request, *args, **kwargs):
        """
        进入组件实例
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 组件别名
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


class AppVisitView(AppBaseView):
    @never_cache
    def get(self, request, *args, **kwargs):
        """
        获取组件访问信息
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 组件别名
              required: true
              type: string
              paramType: path
        """
        bean = dict()
        access_type, data = port_service.get_access_info(self.tenant, self.service)
        bean["access_type"] = access_type
        bean["access_info"] = data
        result = general_message(200, "success", "操作成功", bean=bean)
        return Response(result, status=result["code"])


class AppGroupVisitView(RegionTenantHeaderView):
    def get(self, request, team_name, *args, **kwargs):
        """
        获取组件访问信息
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: service_list
              description: 组件别名列表
              required: true
              type: string
              paramType: path
        """

        try:
            serviceAlias = request.GET.get('service_alias')
            if not serviceAlias:
                result = general_message(200, "not service", "当前组内无组件", bean={"is_null": True})
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
    def get(self, request, *args, **kwargs):
        """
        获取组件安装的插件的简要信息
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 组件别名
              required: true
              type: string
              paramType: path
        """
        bean = dict()
        service_abled_plugins = app_plugin_service.get_service_abled_plugin(self.service)
        plugin_list = [p.to_dict() for p in service_abled_plugins]
        result = general_message(200, "success", "操作成功", bean=bean, list=plugin_list)
        return Response(result, status=result["code"])


class AppGroupView(AppBaseView):
    @never_cache
    def put(self, request, *args, **kwargs):
        """
        修改组件所在组
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 组件别名
              required: true
              type: string
              paramType: path
            - name: group_id
              description: 组ID
              required: true
              type: integer
              paramType: form
        """

        # target app id
        group_id = request.data.get("group_id", None)
        if group_id is None:
            return Response(general_message(400, "param error", "请指定修改的组"), status=400)
        group_id = int(group_id)
        if group_id == -1:
            group_service.delete_service_group_relation_by_service_id(self.service.service_id)
        else:
            # check target app exists or not
            group_service.get_group_by_id(self.tenant, self.service.service_region, group_id)
            # update service relation
            group_service.update_or_create_service_group_relation(self.tenant, self.service, group_id)

        result = general_message(200, "success", "修改成功")
        return Response(result, status=result["code"])


class AppAnalyzePluginView(AppBaseView):
    @never_cache
    def get(self, request, *args, **kwargs):
        """
        查询组件的性能分析插件
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 组件别名
              required: true
              type: string
              paramType: path
        """
        service_abled_plugins = app_plugin_service.get_service_abled_plugin(self.service)
        analyze_plugins = []
        for plugin in service_abled_plugins:
            if plugin.category == PluginCategoryConstants.PERFORMANCE_ANALYSIS:
                analyze_plugins.append(plugin)

        result = general_message(200, "success", "查询成功", list=[p.to_dict() for p in analyze_plugins])
        return Response(result, status=result["code"])


class ImageAppView(AppBaseView):
    @never_cache
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
    def get(self, request, *args, **kwargs):
        """
        查询构建源信息
        ---
        """
        from console.services.service_services import base_service
        bean = base_service.get_build_info(self.tenant, self.service)
        result = general_message(200, "success", "查询成功", bean=bean)
        return Response(result, status=result["code"])

    @never_cache
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
            is_oauth = request.data.get("is_oauth", False)
            user_id = request.user.user_id
            oauth_service_id = request.data.get("service_id")
            git_full_name = request.data.get("full_name")

            if not service_source:
                return Response(general_message(400, "param error", "参数错误"), status=400)

            service_source_user = service_source_repo.get_service_source(
                team_id=self.service.tenant_id, service_id=self.service.service_id)

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
                    if is_oauth:
                        try:
                            oauth_service = oauth_repo.get_oauth_services_by_service_id(service_id=oauth_service_id)
                            oauth_user = oauth_user_repo.get_user_oauth_by_user_id(service_id=oauth_service_id, user_id=user_id)
                        except Exception as e:
                            logger.debug(e)
                            rst = {"data": {"bean": None}, "status": 400, "msg_show": u"未找到OAuth服务, 请检查该服务是否存在且属于开启状态"}
                            return Response(rst, status=200)
                        try:
                            instance = get_oauth_instance(oauth_service.oauth_type, oauth_service, oauth_user)
                        except Exception as e:
                            logger.debug(e)
                            rst = {"data": {"bean": None}, "status": 400, "msg_show": u"未找到OAuth服务"}
                            return Response(rst, status=200)
                        if not instance.is_git_oauth():
                            rst = {"data": {"bean": None}, "status": 400, "msg_show": u"该OAuth服务不是代码仓库类型"}
                            return Response(rst, status=200)
                        service_code_from = "oauth_" + oauth_service.oauth_type
                        self.service.code_from = service_code_from
                        self.service.git_url = git_url
                        self.service.git_full_name = git_full_name
                        self.service.oauth_service_id = oauth_service_id
                        self.service.creater = user_id
                    else:
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
    def put(self, request, *args, **kwargs):
        """
        修改组件触发自动部署关键字
        """

        keyword = request.data.get("keyword", None)
        if not keyword:
            return Response(general_message(400, "param error", "参数错误"), status=400)

        is_pass, msg = app_service.check_service_cname(self.tenant, keyword, self.service.service_region)
        if not is_pass:
            return Response(general_message(400, "param error", msg), status=400)
        service_webhook = service_webhooks_repo.get_service_webhooks_by_service_id_and_type(
            self.service.service_id, "code_webhooks")
        if not service_webhook:
            return Response(general_message(412, "keyword is null", "组件自动部署属性不存在"), status=412)
        service_webhook.deploy_keyword = keyword
        service_webhook.save()
        result = general_message(200, "success", "修改成功", bean=service_webhook.to_dict())
        return Response(result, status=result["code"])
