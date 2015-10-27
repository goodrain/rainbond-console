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
        s = SSO_AuthHandle('abcdefghijklmn')
        payload = s.extra_payload(sso, sig)
        logger.debug("debug", "auth info: sso: {0}, sig: {1}, payload: {2}".format(sso, sig, payload))
        if payload is None:
            return HttpResponse("sig is uncorrect", status=403)

        if isinstance(self.user, AnonymousUser):
            return self.redirect_to('/login', request)
