# -*- coding: utf8 -*-
from django import http

from django.conf import settings
from share.models.main import RegionProvider

if 'django.contrib.staticfiles' in settings.INSTALLED_APPS:
    pass
else:
    pass

from www.models import AnonymousUser
from www.utils import sn
from www.views.base import BaseView

import logging

logger = logging.getLogger('default')


class ShareBaseView(BaseView):

    """是否有权限访问share模块"""
    def __init__(self, request, *args, **kwargs):
        BaseView.__init__(self, request, *args, **kwargs)
        if isinstance(request.user, AnonymousUser):
            raise http.Http404

        try:
            provider = RegionProvider.objects.get(user_id=request.user.user_id)
        except:
            raise http.Http404
        self.provider = provider

    def get_context(self):
        context = super(ShareBaseView, self).get_context()
        return context
