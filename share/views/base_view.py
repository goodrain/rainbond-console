# -*- coding: utf8 -*-
from django import http

from django.conf import settings
from share.models.main import *

if 'django.contrib.staticfiles' in settings.INSTALLED_APPS:
    pass
else:
    pass

from www.models import AnonymousUser, Users
from www.utils import sn
from www.views.base import BaseView
from django.shortcuts import get_object_or_404

import logging

logger = logging.getLogger('default')


class ShareBaseView(BaseView):
    ADMIN_USERS = [19, 1808, 1987, 1375]
    """是否有权限访问share模块"""
    def __init__(self, request, *args, **kwargs):
        BaseView.__init__(self, request, *args, **kwargs)
        if isinstance(request.user, AnonymousUser):
            raise http.Http404

        if request.user.user_id in self.ADMIN_USERS:
            provider = RegionProvider.objects.get(user_id=1)
        else:
            try:
                provider = RegionProvider.objects.get(user_id=request.user.user_id)
            except:
                provider = RegionProvider()
                provider.user_id = request.user.user_id
                provider.provider_name = "provider_{}".format(request.user.user_id)
                provider.save()

        self.provider = provider
        region_records = Region.objects.filter(provider_name=provider.provider_name)
        self.regions = {region.name: region for region in region_records}

    def get_context(self):
        context = super(ShareBaseView, self).get_context()
        context.update({
            "provider": self.provider,
            "regions": self.regions.values()
        })
        return context
