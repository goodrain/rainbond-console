# -*- coding: utf8 -*-
"""
  Created by leon on 18/1/5.
"""
import logging
from typing import Any

from console.utils.cache_decorators import never_cache
from rest_framework.request import Request
from rest_framework.response import Response

from console.exception.bcode import ErrK8sComponentNameExists
from console.exception.main import AbortRequest, ResourceNotEnoughException, AccountOverdueException
from console.services.app import app_service
from console.services.deploy_preflight_service import deploy_preflight_service
from console.views.base import RegionTenantHeaderView
from www.utils.crypt import make_uuid
from www.models.main import ServiceGroup
from www.utils.return_message import general_message
from console.services.group_service import group_service
from console.services.team_services import team_services

logger = logging.getLogger("default")


def abort_if_deploy_preflight_blocked(preflight: dict) -> None:
    if preflight.get("should_block"):
        raise AbortRequest(
            "deploy preflight blocked",
            preflight.get("summary") or "当前环境不满足部署条件",
            status_code=412,
            error_code=10412,
            bean=preflight)


class DockerRunCreateView(RegionTenantHeaderView):
    @never_cache
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """
        image和docker-run创建组件
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: group_id
              description: 组id
              required: true
              type: string
              paramType: form
            - name: service_cname
              description: 组件名称
              required: true
              type: string
              paramType: form
            - name: docker_cmd
              description: docker运行命令
              required: true
              type: string
              paramType: form
            - name: image_type
              description: 创建方式 docker_run或docker_image
              required: true
              type: string
              paramType: form

        """
        image_type = request.data.get("image_type", None)
        group_id = request.data.get("group_id", -1)
        service_cname = request.data.get("service_cname", None)
        docker_cmd = request.data.get("docker_cmd", "")
        is_demo = request.data.get("is_demo", "")
        # 私有docker仓库地址
        docker_password = request.data.get("password", None)
        docker_user_name = request.data.get("user_name", None)
        registry_auth_id = request.data.get("registry_auth_id", None)
        if registry_auth_id:
            registry_auth = team_services.resolve_registry_auth(self.user, registry_auth_id)
            docker_user_name = registry_auth.username
            docker_password = registry_auth.password
        k8s_component_name = request.data.get("k8s_component_name", "")
        arch = request.data.get("arch", "amd64")
        if is_demo:
            groups = ServiceGroup.objects.filter(
                tenant_id=self.tenant.tenant_id, region_name=self.region_name, group_name="镜像构建示例")
            k8s_app_name = "image-demo"
            if groups:
                group_id = groups[0].ID
            else:
                k8s_apps = ServiceGroup.objects.filter(
                    tenant_id=self.tenant.tenant_id, region_name=self.region_name, k8s_app="image-demo")
                if k8s_apps:
                    k8s_app_name += make_uuid()[:6]
                data = group_service.create_app(
                    self.tenant,
                    self.region_name,
                    "镜像构建示例",
                    None,  # type: ignore[arg-type] # NOTE: create_app legacy signature expects str but callers pass None
                    self.user.get_username(),
                    None,  # type: ignore[arg-type]
                    None,  # type: ignore[arg-type]
                    None,  # type: ignore[arg-type]
                    None,  # type: ignore[arg-type]
                    self.user.enterprise_id,  # type: ignore[arg-type]
                    None,  # type: ignore[arg-type]
                    k8s_app=k8s_app_name)
                group_id = data["group_id"]
        if k8s_component_name and app_service.is_k8s_component_name_duplicate(group_id, k8s_component_name):
            if is_demo:
                k8s_component_name = k8s_component_name + "-" + make_uuid()[:6]
            else:
                raise ErrK8sComponentNameExists
        try:
            if not image_type:
                return Response(general_message(400, "image_type cannot be null", "参数错误"), status=400)
            if not docker_cmd:
                return Response(general_message(400, "docker_cmd cannot be null", "参数错误"), status=400)

            deploy_type = "image" if image_type == "docker_image" else "docker_run"
            preflight = deploy_preflight_service.run(
                self.tenant, self.region, deploy_type, {
                    "group_id": group_id,
                    "service_cname": service_cname,
                    "docker_cmd": docker_cmd,
                    "image_type": image_type,
                    "user_name": docker_user_name,
                    "password": docker_password,
                    "registry_auth_id": registry_auth_id,
                    "k8s_component_name": k8s_component_name,
                    "arch": arch,
                }, self.user)
            abort_if_deploy_preflight_blocked(preflight)

            code, msg_show, new_service = app_service.create_docker_run_app(self.response_region, self.tenant, self.user,
                                                                            service_cname,  # type: ignore[arg-type]
                                                                            docker_cmd, image_type,
                                                                            k8s_component_name, "", arch)
            if code != 200:
                return Response(general_message(code, "service create fail", msg_show), status=code)

            # 添加username,password信息
            if docker_password or docker_user_name:
                # NOTE: new_service may be None; create_service_source_info also expects non-None str args; backlog
                app_service.create_service_source_info(self.tenant, new_service, docker_user_name, docker_password)  # type: ignore[arg-type]

            code, msg_show = group_service.add_service_to_group(self.tenant, self.response_region, group_id,
                                                                new_service.service_id)  # type: ignore[union-attr]
            if code != 200:
                logger.debug("service.create", msg_show)
            result = general_message(200, "success", "创建成功", bean=new_service.to_dict())  # type: ignore[union-attr]
        except ResourceNotEnoughException as re:
            raise re
        except AccountOverdueException as re:
            logger.exception(re)
            # NOTE: py2-style Exception.message
            return Response(general_message(10410, "resource is not enough", re.message), status=412)  # type: ignore[attr-defined]
        return Response(result, status=result["code"])
