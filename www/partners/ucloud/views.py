import hashlib
from django.http import JsonResponse
from django.conf import settings

from www.views.base import BaseView
from www.utils.encode import decode_base64
from www.apis.ucloud import UCloudApi
from www.models import AnonymousUser, Users, Tenants
from www.auth import authenticate, login, logout

import logging
logger = logging.getLogger('default')


class EntranceView(BaseView):

    def check_sig(self, sig, token):
        secret_key = settings.UCLOUD_APP.get('secret_key')
        expected_sig = hashlib.sha1(token + secret_key).hexdigest()
        return bool(expected_sig.lower() == sig.lower())

    def get_remote_user(self, AccessToken):
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
            return JsonResponse({"ok": False, "info": info}, status=403)

        logger.debug("partners.auth_ucloud", u_response)

        return u_response.DataSet[0]

    def post(self, request, *args, **kwargs):
        AccessToken = request.POST.get('AccessToken', None)
        if AccessToken is None:
            return JsonResponse({"ok": False, "info": "need AccessToken field"}, status=400)

        remote_user = self.get_remote_user(AccessToken)
        if isinstance(request.user, AnonymousUser):
            pass
        else:
            user = request.user
            if user.email == remote_user.UserEmail:
                if user.is_active:
                    return self.redirect_to('/login')
                else:
                    return self.redirect_to('/partners/ucloud/update_userinfo/')
            else:
                logout(request)

        try:
            local_user = Users.objects.get(email=remote_user.UserEmail)
            if local_user.origion == 'ucloud':
                user = authenticate(username=local_user.email, source='ucloud')
                login(request, user)
                if local_user.is_active:
                    return self.redirect_to('/login')
                else:
                    return self.redirect_to('/partners/ucloud/update_userinfo/')
            else:
                info = "user from ucloud confict by email %s" % remote_user.UserEmail
                logger.info("partners.auth_ucloud", info)
                return JsonResponse({"ok": False, "info": info}, status=409)
        except Users.DoesNotExist:
            default_nick_name = u'ucloud_{0}'.format(remote_user.UserId * 3 + 1152)

            try:
                new_user = Users.objects.create(nick_name=default_nick_name, email=remote_user.UserEmail, phone=remote_user.UserPhone, origion='ucloud',
                                                is_active=False, password='nopass')
                user = authenticate(username=new_user.email, source='ucloud')
                login(request, user)
                return self.redirect_to('/partners/ucloud/update_userinfo/')
            except Exception, e:
                logger.error("partners.auth_ucloud", e)
                return JsonResponse({"ok": False, "info": "server error"}, status=500)


class UserInfoView(BaseView):

    def get(self, request):
        return JsonResponse({"ok": True})

    def post(self, request):
        return JsonResponse({"ok": True})
