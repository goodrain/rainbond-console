# -*- coding: utf8 -*-
"""
  Created on 18/1/9.
"""
import logging

from django.shortcuts import redirect
from django.views.decorators.cache import never_cache
from rest_framework.response import Response

from console.services.git_service import GitCodeService
from console.services.user_services import user_services
from console.views.app_config.base import AppBaseView
from console.views.base import RegionTenantHeaderView, JWTAuthApiView
from www.utils.return_message import general_message
from www.utils.url import get_redirect_url

logger = logging.getLogger("default")
git_service = GitCodeService()

class ServiceCodeBranch(AppBaseView):
    def get(self, request, *args, **kwargs):
        """
        获取组件代码仓库分支
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
        branches = git_service.get_service_code_branch(self.user, self.service)
        bean = {"current_version": self.service.code_version}
        result = general_message(200, "success", "查询成功", bean=bean, list=branches)
        return Response(result, status=result["code"])

    def put(self, request, *args, **kwargs):
        """
        修改组件代码仓库分支
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
            - name: branch
              description: 代码分支
              required: true
              type: string
              paramType: form
        """
        branch = request.data.get('branch', None)
        if not branch:
            return Response(general_message(400, "params error", "请指定具体分支"), status=400)
        self.service.code_version = branch
        self.service.save(update_fields=['code_version'])
        result = general_message(200, "success", "代码仓库分支修改成功")
        return Response(result, status=result["code"])
