import hashlib
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.conf import settings

from www.views.base import BaseView
from www.utils.encode import decode_base64, encode_base64

import logging
logger = logging.getLogger('default')


class UcloudView(BaseView):

    def check_sig(self, sig, token):
        secret_key = settings.UCLOUD_APP.get('secret_key')
        expected_sig = hashlib.sha1(token + '.' + secret_key)
        return bool(expected_sig.lower() == sig.lower())

    @csrf_exempt
    def post(self, request, *args, **kwargs):
        AccessToken = request.POST.get('AccessToken', None)
        if AccessToken is None:
            return JsonResponse({"ok": False, "info": "need AccessToken field"}, status=400)

        logger.debug('partners.auth_ucloud', "AccessToken is %s" % AccessToken)
        encoded_sig, encoded_token = AccessToken.split('.', 1)
        sig = decode_base64(encoded_sig)
        token = decode_base64(encoded_token)
        logger.info('partners.auth_ucloud', "decoded sig: %s, token: %s" % (sig, token))

        if self.check_sig(sig, token):
            logger.debug("partners.auth_ucloud", "AccessToken check ok")
