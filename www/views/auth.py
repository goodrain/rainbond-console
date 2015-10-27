# -*- coding: utf8 -*-
from django.conf import settings
from django.views.decorators.cache import never_cache
from django.shortcuts import redirect
from django.http import HttpResponse

from www.auth.discourse import SSO_AuthHandle
from www.models import AnonymousUser, Users
from www.views.base import BaseView

import logging
logger = logging.getLogger('default')


class DiscourseAuthView(BaseView):

    def get(self, request, *args, **kwargs):
        sso = request.GET.get('sso')
        sig = request.GET.get('sig')
        logger.debug("debug", "auth info: sso: {0}, sig: {1}".format(sso, sig))
        return HttpResponse("ok")
