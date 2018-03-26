# -*- coding: utf8 -*-
"""
  Created by leon on 18/1/5.
"""
import logging

from django.views.decorators.cache import never_cache
from rest_framework.response import Response

from console.exception.main import ResourceNotEnoughException
from console.services.app import app_service
from console.views.base import RegionTenantHeaderView
from www.decorator import perm_required
from www.utils.return_message import error_message, general_message
from console.services.group_service import group_service

logger = logging.getLogger("default")


class DockerRunCreateView(RegionTenantHeaderView):
    @never_cache
    @perm_required('create_service')
    def post(self, request, *args, **kwargs):
        """
        image和docker-run创建应用
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
              description: 应用名称
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

        try:
            if not image_type:
                return Response(general_message(400, "image_type cannot be null", "参数错误"), status=400)
            if not docker_cmd:
                return Response(general_message(400, "docker_cmd cannot be null", "参数错误"), status=400)

            code, msg_show, new_service = app_service.create_docker_run_app(self.response_region, self.tenant,
                                                                            self.user, service_cname, docker_cmd,
                                                                            image_type)
            if code != 200:
                return Response(general_message(code, "service create fail", msg_show), status=code)

            code, msg_show = group_service.add_service_to_group(self.tenant, self.response_region, group_id,
                                                                new_service.service_id)
            if code != 200:
                logger.debug("service.create", msg_show)
            result = general_message(200, "success", "创建成功", bean=new_service.to_dict())
        except ResourceNotEnoughException as re:
            logger.exception(re)
            return Response(general_message(10406, "resource is not enough", re.message), status=412)
        except Exception as e:
            logger.exception(e)
            result = error_message()
        return Response(result, status=result["code"])
