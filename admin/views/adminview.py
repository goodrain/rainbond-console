# -*- coding: utf8 -*-
import logging
import uuid
import hashlib
import datetime
import json

from django.views.decorators.cache import never_cache
from django.template.response import TemplateResponse
from django.http.response import HttpResponse
from www.base import BaseView
from django.conf import settings
from www.models import CloudServiceRelation

logger = logging.getLogger('default')

class AdminViews(BaseView):

    def get_media(self):
        media = super(CloudViews, self).get_media() + self.vendor('admin/css/jquery-ui.css', 'admin/css/jquery-ui-timepicker-addon.css',
            'admin/js/jquery.cookie.js', 'admin/js/common-scripts.js', 'admin/js/jquery.dcjqaccordion.2.7.js',
            'admin/js/jquery.scrollTo.min.js', 'admin/layer/layer.js', 'admin/js/jquery-ui.js', 'admin/js/jquery-ui-timepicker-addon.js', 'admin/js/jquery-ui-timepicker-addon-i18n.min.js', 'admin/js/jquery-ui-sliderAccess.js')
        return media

    def init_context(self, context):
        context["config"] = "active"
        context["base_config"] = "active"
        

    @never_cache
    def get(self, request, *args, **kwargs):
        context = self.get_context()
        self.init_context(context)
        return TemplateResponse(self.request, "admin/config.html", context)