# -*- coding: utf8 -*-
# Copyright (C) 2014-2024 Goodrain Co., Ltd.
# RAINBOND, Application Management Platform

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version. For any non-GPL usage of Rainbond,
# one or multiple Commercial Licenses authorized by Goodrain Co., Ltd.
# must be obtained first.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import logging

from console.views.app_config.base import AppBaseView
from rest_framework.response import Response
from www.apiclient.regionapi import RegionInvokeApi
from www.utils.return_message import error_message, general_message

region_api = RegionInvokeApi()
logger = logging.getLogger("default")


class ServiceGPUConfigView(AppBaseView):
    """
    组件 GPU 配置管理视图
    """
    def get(self, request, *args, **kwargs):
        """
        获取组件 GPU 配置
        ---
        """
        try:
            # 调用 Rainbond API 获取组件 GPU 配置
            res, body = region_api.get_service_gpu_config(
                self.service.service_region,
                self.tenant.tenant_name,
                self.service.service_alias
            )

            if res.get("status") != 200:
                return Response(general_message(500, "failed to get GPU config", "获取GPU配置失败"), status=500)

            result = general_message(200, "success", "获取GPU配置成功", bean=body.get("data"))
            return Response(result, status=200)
        except Exception as e:
            logger.exception(e)
            result = error_message(str(e))
            return Response(result, status=500)

    def put(self, request, *args, **kwargs):
        """
        设置组件 GPU 配置
        ---
        parameters:
            - name: enable_gpu
              description: 是否启用GPU
              required: true
              type: boolean
              paramType: body
            - name: gpu_count
              description: GPU卡数
              required: false
              type: integer
              paramType: body
            - name: gpu_memory
              description: GPU显存(MB)
              required: false
              type: integer
              paramType: body
            - name: gpu_cores
              description: GPU算力百分比(0-100)
              required: false
              type: integer
              paramType: body
            - name: gpu_model_preference
              description: GPU型号偏好，逗号分隔
              required: false
              type: string
              paramType: body
        """
        try:
            enable_gpu = request.data.get("enable_gpu", False)
            gpu_count = request.data.get("gpu_count", 0)
            gpu_memory = request.data.get("gpu_memory", 0)
            gpu_cores = request.data.get("gpu_cores", 0)
            gpu_model_preference = request.data.get("gpu_model_preference", "")

            # 参数验证
            if enable_gpu:
                if gpu_count < 0:
                    return Response(general_message(400, "params error", "GPU卡数不能为负数"), status=400)
                if gpu_memory < 0:
                    return Response(general_message(400, "params error", "GPU显存不能为负数"), status=400)
                if gpu_cores < 0 or gpu_cores > 100:
                    return Response(general_message(400, "params error", "GPU算力必须在0-100之间"), status=400)

            # 调用 Rainbond API 设置组件 GPU 配置
            data = {
                "enable_gpu": enable_gpu,
                "gpu_count": int(gpu_count) if gpu_count else 0,
                "gpu_memory": int(gpu_memory) if gpu_memory else 0,
                "gpu_cores": int(gpu_cores) if gpu_cores else 0,
                "gpu_model_preference": str(gpu_model_preference) if gpu_model_preference else ""
            }
            res, body = region_api.set_service_gpu_config(
                self.service.service_region,
                self.tenant.tenant_name,
                self.service.service_alias,
                data
            )

            if res.get("status") != 200:
                error_msg = body.get("msg", "设置GPU配置失败")
                return Response(general_message(500, "failed to set GPU config", error_msg), status=500)

            result = general_message(200, "success", "设置GPU配置成功")
            return Response(result, status=200)
        except Exception as e:
            logger.exception(e)
            result = error_message(str(e))
            return Response(result, status=500)

    def delete(self, request, *args, **kwargs):
        """
        删除组件 GPU 配置
        ---
        """
        try:
            # 调用 Rainbond API 删除组件 GPU 配置
            res, body = region_api.delete_service_gpu_config(
                self.service.service_region,
                self.tenant.tenant_name,
                self.service.service_alias
            )

            if res.get("status") != 200:
                return Response(general_message(500, "failed to delete GPU config", "删除GPU配置失败"), status=500)

            result = general_message(200, "success", "删除GPU配置成功")
            return Response(result, status=200)
        except Exception as e:
            logger.exception(e)
            result = error_message(str(e))
            return Response(result, status=500)
