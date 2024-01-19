# -*- coding: utf8 -*-
"""
  Created on 18/2/1.
"""
import logging

from console.cloud.services import check_memory_quota
from console.exception.bcode import ErrComponentBuildFailed
from console.exception.main import (ErrInsufficientResource, ServiceHandleException)
from console.repositories.deploy_repo import deploy_repo
from console.services.app import app_service
from console.services.app_actions import app_manage_service, event_service
from console.services.app_config import (dependency_service, env_var_service, port_service, probe_service, volume_service)
from console.services.app_config.arch_service import arch_service
from console.services.compose_service import compose_service
from console.views.app_config.base import AppBaseView
from console.views.base import (CloudEnterpriseCenterView, RegionTenantHeaderCloudEnterpriseCenterView)
from django.db import transaction
from django.views.decorators.cache import never_cache
from rest_framework.response import Response
from www.apiclient.baseclient import HttpClient
from www.utils.return_message import error_message, general_message

logger = logging.getLogger("default")


class AppBuild(AppBaseView, CloudEnterpriseCenterView):
    @never_cache
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        """
        组件构建
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
        probe = None
        is_deploy = request.data.get("is_deploy", True)
        try:
            if not check_memory_quota(self.oauth_instance, self.tenant.enterprise_id, self.service.min_memory,
                                      self.service.min_node):
                raise ServiceHandleException(msg="not enough quota", error_code=20002)
            if self.service.service_source == "third_party":
                is_deploy = False
                # create third component from region
                new_service = app_service.create_third_party_service(self.tenant, self.service, self.user.nick_name)
            else:
                # 数据中心创建组件
                new_service = app_service.create_region_service(self.tenant, self.service, self.user.nick_name)

            self.service = new_service
            if is_deploy:
                try:
                    arch_service.update_affinity_by_arch(self.service.arch, self.tenant, self.region.region_name, self.service)
                    app_manage_service.deploy(self.tenant, self.service, self.user, oauth_instance=self.oauth_instance)
                except ErrInsufficientResource as e:
                    result = general_message(e.error_code, e.msg, e.msg_show)
                    return Response(result, status=e.status_code)
                except Exception as e:
                    logger.exception(e)
                    err = ErrComponentBuildFailed()
                    result = general_message(err.error_code, e, err.msg_show)
                    return Response(result, status=400)
                # 添加组件部署关系
                deploy_repo.create_deploy_relation_by_service_id(service_id=self.service.service_id)

            result = general_message(200, "success", "构建成功")
            return Response(result, status=result["code"])
        except HttpClient.CallApiError as e:
            logger.exception(e)
            if e.status == 403:
                result = general_message(10407, "no cloud permission", e.message)
                status = e.status
            elif e.status == 400:
                if "is exist" in e.message.get("body", ""):
                    result = general_message(400, "the service is exist in region", "该组件在数据中心已存在，你可能重复创建？")
                else:
                    result = general_message(400, "call cloud api failure", e.message)
                status = e.status
            else:
                result = general_message(400, "call cloud api failure", e.message)
                status = 400
        # 删除probe
        # 删除region端数据
        if probe:
            probe_service.delete_service_probe(self.tenant, self.service, probe.probe_id)
        if self.service.service_source != "third_party":
            event_service.delete_service_events(self.service)
            port_service.delete_region_port(self.tenant, self.service)
            volume_service.delete_region_volumes(self.tenant, self.service)
            env_var_service.delete_region_env(self.tenant, self.service)
            dependency_service.delete_region_dependency(self.tenant, self.service)
            app_manage_service.delete_region_service(self.tenant, self.service)
        self.service.create_status = "checked"
        self.service.save()
        return Response(result, status=status)

    def is_need_to_add_default_probe(self):
        if self.service.service_source != "source_code":
            return True
        else:
            ports = port_service.get_service_ports(self.service)
            for p in ports:
                if p.container_port == 5000:
                    return False
            return True


class ComposeBuildView(RegionTenantHeaderCloudEnterpriseCenterView):
    @never_cache
    def post(self, request, *args, **kwargs):
        """
        docker-compose组件检测
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: group_id
              description: 组ID
              required: true
              type: string
              paramType: path
            - name: compose_id
              description: group_compose ID
              required: true
              type: string
              paramType: form
        """
        probe_map = dict()
        services = None

        try:
            compose_id = request.data.get("compose_id", None)
            if not compose_id:
                return Response(general_message(400, "params error", "参数异常"), status=400)
            group_compose = compose_service.get_group_compose_by_compose_id(compose_id)
            services = compose_service.get_compose_services(compose_id)
            # 数据中心创建组件
            new_app_list = []
            for service in services:
                new_service = app_service.create_region_service(self.tenant, service, self.user.nick_name)
                new_app_list.append(new_service)
            group_compose.create_status = "complete"
            group_compose.save()
            for s in new_app_list:
                try:
                    app_manage_service.deploy(self.tenant, s, self.user, oauth_instance=self.oauth_instance)
                except ErrInsufficientResource as e:
                    result = general_message(e.error_code, e.msg, e.msg_show)
                    return Response(result, status=e.status_code)
                except Exception as e:
                    logger.exception(e)
                    continue

            result = general_message(200, "success", "构建成功")
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            if services:
                for service in services:
                    if probe_map:
                        probe_id = probe_map.get(service.service_id)
                        probe_service.delete_service_probe(self.tenant, service, probe_id)
                    event_service.delete_service_events(service)
                    port_service.delete_region_port(self.tenant, service)
                    volume_service.delete_region_volumes(self.tenant, service)
                    env_var_service.delete_region_env(self.tenant, service)
                    dependency_service.delete_region_dependency(self.tenant, service)
                    app_manage_service.delete_region_service(self.tenant, service)
                    service.create_status = "checked"
                    service.save()
            raise e
        return Response(result, status=result["code"])


class CodeBuildLangVersionView(AppBaseView):
    @never_cache
    def get(self, request, *args, **kwargs):
        """
        源码构建组件获取构建环境版本。
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: group_id
              description: 组ID
              required: true
              type: string
              paramType: path
            - name: compose_id
              description: group_compose ID
              required: true
              type: string
              paramType: path
        """
        lang = request.GET.get("lang", "")
        data = app_service.get_code_long_build_version(self.enterprise.enterprise_id, self.region_name, lang)
        result = general_message(200, "success", "查询成功", list=data)
        return Response(result, status=result["code"])
