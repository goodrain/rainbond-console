# -*- coding: utf8 -*-
"""
  Created on 18/2/1.
"""
import logging

from django.views.decorators.cache import never_cache
from rest_framework.response import Response

from console.services.app import app_service
from console.views.app_config.base import AppBaseView
from www.decorator import perm_required
from www.utils.return_message import general_message, error_message
from console.services.app_config import label_service, probe_service, port_service, volume_service, env_var_service, \
    dependency_service
from console.services.app_actions import app_manage_service, event_service
from console.services.compose_service import compose_service
from console.views.base import RegionTenantHeaderView

logger = logging.getLogger("default")


class AppBuild(AppBaseView):
    @never_cache
    @perm_required('deploy_service')
    def post(self, request, *args, **kwargs):
        """
        服务构建
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
        probe = None
        try:
            # 数据中心创建应用
            new_service = app_service.create_region_service(self.tenant, self.service, self.user.nick_name)
            self.service = new_service
            # 为服务添加默认探针
            if self.is_need_to_add_default_probe():
                code, msg, probe = app_service.add_service_default_porbe(self.tenant, self.service)
            # 添加服务有无状态标签
            label_service.update_service_state_label(self.tenant, self.service)
            # 部署应用
            app_manage_service.deploy(self.tenant, self.service, self.user)

            result = general_message(200, "success", "构建成功")
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            # 删除probe
            # 删除region端数据
            if probe:
                probe_service.delete_service_probe(self.tenant, self.service, probe.probe_id)
            event_service.delete_service_events(self.service)
            port_service.delete_region_port(self.tenant, self.service)
            volume_service.delete_region_volumes(self.tenant, self.service)
            env_var_service.delete_region_env(self.tenant, self.service)
            dependency_service.delete_region_dependency(self.tenant, self.service)

            app_manage_service.delete_region_service(self.tenant, self.service)
            self.service.create_status = "checked"
            self.service.save()

        return Response(result, status=result["code"])

    def is_need_to_add_default_probe(self):
        if self.service.service_source != "source_code":
            return True
        else:
            ports = port_service.get_service_ports(self.service)
            for p in ports:
                if p.container_port == 5000:
                    return False
            return True


class ComposeBuildView(RegionTenantHeaderView):
    @never_cache
    @perm_required('create_service')
    def post(self, request, *args, **kwargs):
        """
        docker-compose应用检测
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
            # 数据中心创建应用
            new_app_list = []
            for service in services:
                new_service = app_service.create_region_service(self.tenant, service, self.user.nick_name)
                new_app_list.append(new_service)
                # 为服务添加默认探针
                code, msg, probe = app_service.add_service_default_porbe(self.tenant, new_service)
                if probe:
                    probe_map[service.service_id] = probe.probe_id
                # 添加服务有无状态标签
                label_service.update_service_state_label(self.tenant, new_service)

            group_compose.create_status = "complete"
            group_compose.save()
            for s in new_app_list:
                try:
                    app_manage_service.deploy(self.tenant, s, self.user)
                except Exception as e:
                    logger.exception(e)
                    continue

            result = general_message(200, "success", "构建成功")
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            # 删除probe
            # 删除region端数据
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

        return Response(result, status=result["code"])
