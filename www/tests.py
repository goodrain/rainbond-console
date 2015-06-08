# -*- coding: utf8 -*-

from django.views.decorators.cache import never_cache
from django.template.response import TemplateResponse
from www.views import BaseView


class RasterView(BaseView):

    def get_media(self):
        media = super(BaseView, self).get_media()
        return media

    @never_cache
    def get(self, request):
        context = self.get_context()
        return TemplateResponse(self.request, "www/raster.html", context)


class ServiceListView(RasterView):
    @never_cache
    def get(self, request):
        context = self.get_context()
        return TemplateResponse(self.request, "www/service_list.html", context)
