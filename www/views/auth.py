# -*- coding: utf8 -*-
import urllib
from django.conf import settings
from django.views.decorators.cache import never_cache
from django.http import HttpResponse

from www.auth.discourse import SSO_AuthHandle
from www.models import AnonymousUser
from www.views.base import BaseView

import logging
logger = logging.getLogger('default')


class DiscourseAuthView(BaseView):

    @never_cache
    def get(self, request, *args, **kwargs):
        sso = request.GET.get('sso')
        sig = request.GET.get('sig')
        s = SSO_AuthHandle(settings.DISCOURSE_SECRET_KEY)
        payload = s.extra_payload(sso, sig)
        logger.debug("auth.discourse", "receive auth info: sso: {0}, sig: {1}, payload: {2}".format(sso, sig, payload))
        if payload is None:
            logger.info("auth.discourse", "sig %s is uncorrect" % sig)
            return HttpResponse("sig is uncorrect", status=403)

        user = self.user
        if isinstance(user, AnonymousUser):
            logger.info("auth.discourse", "AnonymousUser, redirect to login")
            response = self.redirect_to('/login?next={0}&origin=discourse'.format(request.get_full_path()))
            # response.set_cookie("discourse_url", request.get_full_path())
            return response
        else:
            logger.info("auth.discourse", "user %s authed for discourse login" % user.nick_name)
            # fix bug: discourse login no email
            email = user.email
            if email is None or email == "":
                email = user.nick_name + "@goodrain.com.cn"
            user_info = {
                "name": user.nick_name, "external_id": user.nick_name,
                "username": user.nick_name, "email": email,
                "nonce": payload['nonce']
            }
            url_encoded_sso, sig = s.create_auth(user_info)
            redirect_url = '{0}?sso={1}&sig={2}'.format(payload['return_sso_url'], url_encoded_sso, sig)
            return self.redirect_to(redirect_url)
