# -*- coding: utf8 -*-
from django import http

from django.conf import settings

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
        if not request.user.is_sys_admin:
            if request.user.user_id == 1:
                pass
            else:
                raise http.Http404

    def get_context(self):
        context = super(ShareBaseView, self).get_context()
        context['MODULES'] = settings.MODULES
        context['is_private'] = sn.instance.is_private()
        return context