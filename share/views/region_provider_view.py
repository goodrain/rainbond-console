# -*- coding: utf8 -*-
import logging

from base_view import ShareBaseView
from django.template.response import TemplateResponse

logger = logging.getLogger('default')


class RegionOverviewView(ShareBaseView):
    def get(self, request, *args, **kwargs):
        return TemplateResponse(request, "share/info.html", self.get_context())