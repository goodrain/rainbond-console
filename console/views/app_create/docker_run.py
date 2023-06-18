# -*- coding: utf8 -*-
"""
  Created by leon on 18/1/5.
"""
import logging

from django.views.decorators.cache import never_cache
from rest_framework.response import Response

from console.exception.bcode import ErrK8sComponentNameExists
from console.exception.main import ResourceNotEnoughException, AccountOverdueException
from console.services.app import app_service
from console.views.base import RegionTenantHeaderView
from www.utils.crypt import make_uuid
from www.models.main import ServiceGroup
from www.utils.return_message import general_message
from console.services.group_service import group_service

logger = logging.getLogger("default")


class DockerRunCreateView(RegionTenantHeaderView):
    @never_cache
    def post(self, request, *args, **kwargs):
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
        k8s_component_name = request.data.get("k8s_component_name", "")
        arch = request.data.get("arch", "amd64")
        if is_demo:
            groups = ServiceGroup.objects.filter(tenant_id=self.tenant.tenant_id,
                                                 region_name=self.region_name,
                                                 group_name="镜像构建示例")
            k8s_app_name = "image-demo"
            if groups:
                group_id = groups[0].ID
            else:
                k8s_apps = ServiceGroup.objects.filter(tenant_id=self.tenant.tenant_id,
                                                       region_name=self.region_name,
                                                       k8s_app="image-demo")
                if k8s_apps:
                    k8s_app_name += make_uuid()[:6]
                data = group_service.create_app(self.tenant,
                                                self.region_name,
                                                "镜像构建示例",
                                                None,
                                                self.user.get_username(),
                                                None,
                                                None,
                                                None,
                                                None,
                                                self.user.enterprise_id,
                                                None,
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

            code, msg_show, new_service = app_service.create_docker_run_app(self.response_region, self.tenant, self.user,
                                                                            service_cname, docker_cmd, image_type,
                                                                            k8s_component_name, "", arch)
            if code != 200:
                return Response(general_message(code, "service create fail", msg_show), status=code)

            # 添加username,password信息
            if docker_password or docker_user_name:
                app_service.create_service_source_info(self.tenant, new_service, docker_user_name, docker_password)

            code, msg_show = group_service.add_service_to_group(self.tenant, self.response_region, group_id,
                                                                new_service.service_id)
            if code != 200:
                logger.debug("service.create", msg_show)
            result = general_message(200, "success", "创建成功", bean=new_service.to_dict())
        except ResourceNotEnoughException as re:
            raise re
        except AccountOverdueException as re:
            logger.exception(re)
            return Response(general_message(10410, "resource is not enough", re.message), status=412)
        return Response(result, status=result["code"])
