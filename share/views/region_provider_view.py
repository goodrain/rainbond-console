# -*- coding: utf8 -*-
import logging

from base_view import ShareBaseView
from django.template.response import TemplateResponse

logger = logging.getLogger('default')


class RegionOverviewView(ShareBaseView):
    def get(self, request, *args, **kwargs):
        return TemplateResponse(request, "share/region_overview.html", self.get_context())


class RegionResourcePriceView(ShareBaseView):
    def get(self, request, *args, **kwargs):
        return TemplateResponse(request, "share/region_resource_price.html", self.get_context())

    def post(self, request, *args, **kwargs):
        return TemplateResponse(request, "share/region_resource_price.html", self.get_context())


class RegionResourceConsumeView(ShareBaseView):
    def get(self, request, *args, **kwargs):
        return TemplateResponse(request, "share/region_resource_consume.html", self.get_context())

    def post(self, request, *args, **kwargs):
        return TemplateResponse(request, "share/region_resource_consume.html", self.get_context())