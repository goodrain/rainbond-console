import hashlib
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.conf import settings

from www.views.base import BaseView
from www.utils.encode import decode_base64, encode_base64
from www.apis.ucloud import UCloudApi
from www.models import Users, Tenants

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

        u_api = UCloudApi(token)
        u_response = u_api.get_user_info()
        if u_response.RetCode != 0:
            info = "get_user_info got retcode: {0}".format(u_response.RetCode)
            logger.error("partners.auth_ucloud", info)
            return JsonResponse({"ok": False, "info": info}, status=400)

        user = u_response.DataSet[0]
        try:
            Users.objects.get(email=user.UserEmail)
        except Users.DoesNotExist:
            info = "user from ucloud confict by email %s" % user.UserEmail
            logger.info("partners.auth_ucloud", info)
            return JsonResponse({"ok": False, "info": info}, status=409)

        user_exist = Users.objects.filter(nick_name=user.UserName)
        if user_exist:
            nick_name = user.UserName + '_' + 'ucloud'
        else:
            nick_name = user.UserName

        try:
            Users.objects.create(nick_name=nick_name, email=user.UserEmail, phone=user.UserPhone, rf='ucloud')
            return JsonResponse({"ok": True, "info": "created"}, status=200)
        except Exception, e:
            logger.error("partners.auth_ucloud", e)
            return JsonResponse({"ok": False, "info": "server error"}, status=500)
