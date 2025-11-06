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

from console.views.base import RegionTenantHeaderView, JWTAuthApiView
from rest_framework.response import Response
from www.apiclient.regionapi import RegionInvokeApi
from www.utils.return_message import error_message, general_message
from console.services.team_services import team_services

region_api = RegionInvokeApi()
logger = logging.getLogger("default")


class ClusterGPUOverviewView(JWTAuthApiView):
    """
    集群 GPU 总览视图
    """
    def get(self, request, *args, **kwargs):
        """
        获取集群 GPU 总览信息
        ---
        """
        try:
            region_name = request.GET.get("region_name")
            if not region_name:
                return Response(general_message(400, "region_name is required", "集群名称不能为空"), status=400)

            # 调用 Rainbond API 获取集群 GPU 总览
            res, body = region_api.get_cluster_gpu_overview(region_name)

            if res.get("status") != 200:
                return Response(general_message(500, "failed to get GPU overview", "获取GPU总览失败"), status=500)

            result = general_message(200, "success", "获取GPU总览成功", bean=body.get("overview"))
            return Response(result, status=200)
        except Exception as e:
            logger.exception(e)
            result = error_message(str(e))
            return Response(result, status=500)


class NodeGPUDetailView(JWTAuthApiView):
    """
    节点 GPU 详情视图
    """
    def get(self, request, node_name, *args, **kwargs):
        """
        获取节点 GPU 详细信息
        ---
        parameters:
            - name: node_name
              description: 节点名称
              required: true
              type: string
              paramType: path
        """
        try:
            region_name = request.GET.get("region_name")
            if not region_name:
                return Response(general_message(400, "region_name is required", "集群名称不能为空"), status=400)

            # 调用 Rainbond API 获取节点 GPU 详情
            res, body = region_api.get_node_gpu_detail(region_name, node_name)

            if res.get("status") != 200:
                return Response(general_message(500, "failed to get node GPU detail", "获取节点GPU详情失败"), status=500)

            result = general_message(200, "success", "获取节点GPU详情成功", bean=body)
            return Response(result, status=200)
        except Exception as e:
            logger.exception(e)
            result = error_message(str(e))
            return Response(result, status=500)


class AvailableGPUModelsView(JWTAuthApiView):
    """
    可用 GPU 型号列表视图
    """
    def get(self, request, *args, **kwargs):
        """
        获取可用的 GPU 型号列表
        ---
        """
        try:
            region_name = request.GET.get("region_name")
            if not region_name:
                return Response(general_message(400, "region_name is required", "集群名称不能为空"), status=400)

            # 调用 Rainbond API 获取 GPU 型号列表
            res, body = region_api.get_available_gpu_models(region_name)

            if res.get("status") != 200:
                return Response(general_message(500, "failed to get GPU models", "获取GPU型号列表失败"), status=500)

            result = general_message(200, "success", "获取GPU型号列表成功", list=body.get("models", []))
            return Response(result, status=200)
        except Exception as e:
            logger.exception(e)
            result = error_message(str(e))
            return Response(result, status=500)


class HAMiStatusView(JWTAuthApiView):
    """
    HAMi 状态检测视图
    """
    def get(self, request, *args, **kwargs):
        """
        检测 HAMi 是否安装
        ---
        """
        try:
            region_name = request.GET.get("region_name")
            if not region_name:
                return Response(general_message(400, "region_name is required", "集群名称不能为空"), status=400)

            # 调用 Rainbond API 检测 HAMi 状态
            res, body = region_api.detect_hami_status(region_name)

            if res.get("status") != 200:
                return Response(general_message(500, "failed to detect HAMi", "检测HAMi状态失败"), status=500)

            result = general_message(200, "success", "检测HAMi状态成功", bean={"installed": body.get("installed", False)})
            return Response(result, status=200)
        except Exception as e:
            logger.exception(e)
            result = error_message(str(e))
            return Response(result, status=500)
