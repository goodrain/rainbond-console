# -*- coding: utf8 -*-
"""
  Created on 18/2/6.
"""
import os

from django.http import FileResponse, Http404
from django.template.response import TemplateResponse
from django.views.generic import View
from goodrain_web.sentry_config import get_frontend_posthog_config_json, get_frontend_sentry_config_json
from console.services.telemetry import telemetry_service


class IndexTemplateView(View):
    def get(self, request, *args, **kwargs):
        telemetry_service.boot()
        return TemplateResponse(self.request, "index.html", {
            "sentry_config_json": get_frontend_sentry_config_json(),
            "posthog_config_json": get_frontend_posthog_config_json(),
        })


class GithubCallBackView(View):
    def get(self, request, *args, **kwargs):
        return TemplateResponse(self.request, "githubcallback.html")


class RKE2Install(View):
    def get(self, request, *args, **kwargs):
        # 文件的路径（需要根据实际情况进行修改）
        file_path = './script/install-cluster.sh'
        # 检查文件是否存在
        if not os.path.exists(file_path):
            raise Http404("File does not exist")
        # 打开文件并返回 FileResponse
        response = FileResponse(open(file_path, 'rb'))
        # 设置文件在浏览器中直接显示
        response['Content-Disposition'] = 'inline; filename="install-cluster.sh"'
        response['Content-Type'] = 'text/x-shellscript'
        return response
