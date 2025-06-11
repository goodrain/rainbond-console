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

from console.constants import AppConstants, PluginCategoryConstants
from console.exception.bcode import ErrK8sComponentNameExists
from console.exception.main import (MarketAppLost, RbdAppNotFound, ServiceHandleException)
from console.repositories.app import (service_repo, service_source_repo, service_webhooks_repo)
from console.repositories.app_config import service_endpoints_repo, volume_repo
from console.repositories.deploy_repo import deploy_repo
from console.repositories.market_app_repo import rainbond_app_repo
from console.repositories.oauth_repo import oauth_repo, oauth_user_repo
from console.services.app import app_service, package_upload_service
from console.services.app_actions import ws_service
from console.services.app_config import port_service
from console.services.app_config.arch_service import arch_service
from console.services.compose_service import compose_service
from console.services.group_service import group_service
from console.services.market_app_service import market_app_service
from console.services.operation_log import operation_log_service, Operation
from console.services.plugin import app_plugin_service
from console.services.region_services import region_services
from console.services.team_services import team_services
from console.utils.oauth.oauth_types import get_oauth_instance
from console.views.app_config.base import AppBaseView
from console.views.base import RegionTenantHeaderView
from django.db import transaction
from django.views.decorators.cache import never_cache
from rest_framework.response import Response
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
        vm_url = request.GET.get("vm_url", "")
        bean = dict()
        namespace = self.tenant.namespace
        service_model = self.service.to_dict()
        group_map = group_service.get_services_group_name([self.service.service_id])
        group_name = group_map.get(self.service.service_id)["group_name"]
        app_k8s_name = group_map.get(self.service.service_id)["k8s_app"]
        group_id = group_map.get(self.service.service_id)["group_id"]
        service_model["group_name"] = group_name
        service_model["group_id"] = group_id
        service_model["namespace"] = namespace
        volumes = volume_repo.get_service_volumes_with_config_file(self.service.service_id)
        service_model["disk_cap"] = 10
        if self.service.extend_method == "vm":
            namespace = self.tenant.namespace
            name = app_k8s_name + "-" + self.service.k8s_component_name
            base_vm_url = "{}/vnc_lite.html?path=".format(vm_url)
            base_path = "k8s/apis/subresources.kubevirt.io/v1alpha3/"
            path = base_path + "namespaces/{}/virtualmachineinstances/{}/vnc".format(namespace, name)
            vm_url = base_vm_url + path
            bean["vm_url"] = vm_url
        if volumes:
            service_model["disk_cap"] = volumes[0].volume_capacity
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
                result = general_message(200, "success", "当前组件安装源模版已删除", bean=bean)
                return Response(result, status=result["code"])

            bean.update({"rain_app_name": rainbond_app.app_name})
            try:
                if rainbond_app_version:
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
                bean["endpoints_type"] = service_endpoints.endpoints_type
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
                if service_endpoints.endpoints_type == "kubernetes":
                    bean["kubernetes"] = json.loads(service_endpoints.endpoints_info)

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
        k8s_component_name = request.data.get("k8s_component_name", "")
        app = group_service.get_service_group_info(self.service.service_id)
        if app:
            if app_service.is_k8s_component_name_duplicate(app.ID, k8s_component_name, self.service.service_id):
                raise ErrK8sComponentNameExists
        original_component_name = self.service.service_cname
        is_pass, msg = app_service.check_service_cname(self.tenant, service_cname, self.service.service_region)
        if not is_pass:
            return Response(general_message(400, "param error", msg), status=400)
        self.service.k8s_component_name = k8s_component_name
        old_information = json.dumps({"组件名称": self.service.service_cname}, ensure_ascii=False)
        new_information = json.dumps({"组件名称": service_cname}, ensure_ascii=False)
        self.service.service_cname = service_cname
        region_api.update_service(self.service.service_region, self.tenant.tenant_name, self.service.service_alias,
                                  {"k8s_component_name": k8s_component_name})

        modified_name = operation_log_service.process_component_name(
            name=self.service.service_cname,
            region=self.service.service_region,
            team_name=self.tenant.tenant_name,
            service_alias=self.service.service_alias,
        )
        comment = operation_log_service.generate_component_comment(
            operation=Operation.CHANGE, module_name=original_component_name, suffix=" 的名称为 {}".format(modified_name))
        operation_log_service.create_component_log(
            user=self.user,
            comment=comment,
            enterprise_id=self.user.enterprise_id,
            team_name=self.tenant.tenant_name,
            app_id=self.app.ID,
            service_alias=self.service.service_alias,
            new_information=new_information,
            old_information=old_information)

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
                    for key, val in list(container.items()):
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
                        if self.service.k8s_component_name in key and 'default-tcpmesh' not in key:
                            if len(container_list) > 1:
                                container_list[0], container_list[len(container_list) - 1] = container_list[
                                                                                                 len(container_list) - 1], \
                                                                                             container_list[0]
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
            app = group_service.get_group_by_id(self.tenant, self.service.service_region, group_id)
            app_old = group_service.get_group_by_id(self.tenant, self.service.service_region, self.app.ID)
            # update service relation
            group_service.update_or_create_service_group_relation(self.tenant, self.service, group_id)
            app_name = operation_log_service.process_app_name(
                app.get("group_name", ""), self.service.service_region, self.tenant.tenant_name, group_id)
            old_information = json.dumps({"组件所属应用": app_old["group_name"]}, ensure_ascii=False)
            new_information = json.dumps({"组件所属应用": app["group_name"]}, ensure_ascii=False)
            comment = operation_log_service.generate_component_comment(
                operation=Operation.BATCH_MOVE,
                module_name=self.service.service_cname,
                region=self.service.service_region,
                team_name=self.tenant.tenant_name,
                service_alias=self.service.service_alias,
                suffix=" 到应用 {}".format(app_name))
            operation_log_service.create_component_log(
                user=self.user,
                comment=comment,
                enterprise_id=self.user.enterprise_id,
                team_name=self.tenant.tenant_name,
                app_id=group_id,
                service_alias=self.service.service_alias,
                old_information=old_information,
                new_information=new_information)
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
        service_ids = [self.service.service_id]
        build_infos = base_service.get_build_infos(self.tenant, service_ids)
        bean = build_infos.get(self.service.service_id, None)
        if bean["server_type"] == "pkg":
            package_names = package_upload_service.get_name_by_component_id(service_ids)
            if package_names:
                bean["package_name"] = package_names[0]
        res, body = region_api.get_cluster_nodes_arch(self.region_name)
        bean["arch"] = list(set(body.get("list")))
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
            server_type = request.data.get("server_type", "")
            arch = request.data.get("arch", "amd64")
            if not service_source:
                return Response(general_message(400, "param error", "参数错误"), status=400)

            service_source_user = service_source_repo.get_service_source(
                team_id=self.service.tenant_id, service_id=self.service.service_id)
            new_information = service_source_repo.json_service_source(image=image, cmd=cmd)
            old_information = service_source_repo.json_service_source(image=self.service.image, cmd=self.service.cmd)
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
                elif server_type == "oss":
                    self.service.code_version = ""
                else:
                    self.service.code_version = "master"
                if git_url:
                    if is_oauth:
                        try:
                            oauth_service = oauth_repo.get_oauth_services_by_service_id(service_id=oauth_service_id)
                            oauth_user = oauth_user_repo.get_user_oauth_by_user_id(service_id=oauth_service_id, user_id=user_id)
                        except Exception as e:
                            logger.debug(e)
                            rst = {"data": {"bean": None}, "status": 400, "msg_show": "Oauth服务可能已被删除，请重新配置"}
                            return Response(rst, status=200)
                        try:
                            instance = get_oauth_instance(oauth_service.oauth_type, oauth_service, oauth_user)
                        except Exception as e:
                            logger.debug(e)
                            rst = {"data": {"bean": None}, "status": 400, "msg_show": "未找到OAuth服务"}
                            return Response(rst, status=200)
                        if not instance.is_git_oauth():
                            rst = {"data": {"bean": None}, "status": 400, "msg_show": "该OAuth服务不是代码仓库类型"}
                            return Response(rst, status=200)
                        service_code_from = "oauth_" + oauth_service.oauth_type
                        self.service.code_from = service_code_from
                        self.service.git_url = git_url
                        self.service.git_full_name = git_full_name
                        self.service.oauth_service_id = oauth_service_id
                        self.service.creater = user_id
                    else:
                        self.service.git_url = git_url
                self.service.service_source = service_source
                self.service.code_from = ""
                self.service.server_type = server_type
                self.service.cmd = ""
                self.service.image = ""
                self.service.service_key = "application"
                self.service.save()
                transaction.savepoint_commit(s_id)
            elif service_source == "docker_run":
                self.service.service_source = "docker_image"
                if image:
                    version = image.split(':')[-1]
                    if not version:
                        version = "latest"
                        image = image + ":" + version
                    self.service.image = image
                    self.service.version = version
                self.service.cmd = cmd
                self.server_type = server_type
                self.service.git_url = ""
                self.service.code_from = "image_manual"
                self.service.service_key = "application"
                self.service.language = ""
                self.service.save()
                transaction.savepoint_commit(s_id)
            self.service.arch = arch
            comment = operation_log_service.generate_component_comment(
                operation=Operation.CHANGE,
                module_name=self.service.service_cname,
                region=self.service.service_region,
                team_name=self.tenant.tenant_name,
                service_alias=self.service.service_alias,
                suffix=" 的构建源")
            operation_log_service.create_component_log(
                user=self.user,
                comment=comment,
                enterprise_id=self.user.enterprise_id,
                team_name=self.tenant.tenant_name,
                app_id=self.app.ID,
                service_alias=self.service.service_alias,
                old_information=old_information,
                new_information=new_information,
            )

            self.service.save()
            arch_service.update_affinity_by_arch(arch, self.tenant, self.region_name, self.service)
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
        keyword = request.data.get("keyword", "")

        is_pass, msg = app_service.check_service_cname(self.tenant, self.service.service_region, None)
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


# 修改job、cronjob策略配置
class JobStrategy(AppBaseView):
    @never_cache
    def get(self, request, *args, **kwargs):
        res = service_repo.get_service_by_service_id(self.service.service_id)
        if res.job_strategy:
            bean = json.loads(res.job_strategy)
            result = general_message(200, "success", "查询成功", bean=bean)
            return Response(result, status=result["code"])
        result = general_message(200, "success", "查询成功", bean={})
        return Response(result, status=result["code"])

    @never_cache
    def put(self, request, *args, **kwargs):
        job_strategy = {
            'schedule': request.data.get("schedule", ""),
            'backoff_limit': request.data.get("backoff_limit", ""),
            'parallelism': request.data.get("parallelism", ""),
            'active_deadline_seconds': request.data.get("active_deadline_seconds", ""),
            "completions": request.data.get("completions", "")
        }
        params = {'job_strategy': json.dumps(job_strategy)}
        service_repo.update(self.tenant.tenant_id, self.service.service_id, **params)
        region_api.update_service(self.service.service_region, self.tenant.tenant_name, self.service.service_alias, params)
        result = general_message(200, "success", "修改成功")
        return Response(result, status=result["code"])

# 存储文件管理
class ManageFile(AppBaseView):
    def get(self, request, *args, **kwargs):
        host_path = request.GET.get("host_path", "")
        pod_name = request.GET.get("pod_name", "")
        region_name = request.GET.get("region_name", "")
        try:
            res = group_service.get_file_and_dir(region_name, self.tenant_name, self.service.service_alias, host_path, pod_name,
                                                 self.tenant.namespace)
            region = region_services.get_region_by_region_name(region_name)
        except Exception as e:
            logger.exception(e)
            raise e
        bean = {
            "host_path": host_path,
            "ws_url": region.wsurl,
            "namespace": self.tenant.namespace,
            "container_name": self.service.k8s_component_name
        }
        result = general_message(200, "success", "获取成功", list=res, bean=bean)
        return Response(result, status=result["code"])

