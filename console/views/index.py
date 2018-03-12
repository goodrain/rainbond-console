# -*- coding: utf8 -*-
"""
  Created on 18/2/6.
"""
from django.template.response import TemplateResponse
from django.views.generic import View


class IndexTemplateView(View):
    def get(self, request, *args, **kwargs):
        return TemplateResponse(self.request, "index.html")


class GithubCallBackView(View):
    def get(self, request, *args, **kwargs):
        return TemplateResponse(self.request, "githubcallback.html")