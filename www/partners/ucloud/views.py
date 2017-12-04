# -*- coding: utf8 -*-
import hashlib
from django.http import JsonResponse
from django.conf import settings
from django.template.response import TemplateResponse

from www.views import BaseView, RegionOperateMixin, LoginRedirectMixin
from www.utils.encode import decode_base64
from www.apis.ucloud import UCloudApi
from www.models import AnonymousUser, Users, Tenants, PermRelTenant, TenantRegionInfo
from www.auth import authenticate, login, logout
from www.monitorservice.monitorhook import MonitorHook
from www.tenantservice.baseservice import CodeRepositoriesService
from www.services import enterprise_svc
from forms import AppendInfoForm
import datetime
import time

import logging
logger = logging.getLogger('default')

monitorhook = MonitorHook()
codeRepositoriesService = CodeRepositoriesService()


class EntranceView(BaseView, LoginRedirectMixin):

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
        logger.debug("partners.auth_ucloud", u_response)

        if u_response.RetCode != 0:
            info = "get_user_info got retcode: {0}".format(u_response.RetCode)
            logger.error("partners.auth_ucloud", info)
            return None

        return u_response.DataSet[0]

    def post(self, request, *args, **kwargs):
        AccessToken = request.POST.get('AccessToken', None)
        if AccessToken is None:
            return JsonResponse({"ok": False, "info": "need AccessToken field"}, status=400)

        remote_user = self.get_remote_user(AccessToken)
        if remote_user is None:
            return JsonResponse({"ok": False, "info": "用户验证失败"}, status=403)

        if isinstance(request.user, AnonymousUser):
            pass
        else:
            user = request.user
            if user.email == remote_user.UserEmail:
                if user.is_active:
                    return self.redirect_view()
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
                    return self.redirect_view(request)
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


class UserInfoView(BaseView, RegionOperateMixin, LoginRedirectMixin):

    def get_context(self):
        context = super(UserInfoView, self).get_context()
        context.update({
            'form': self.form,
        })
        return context

    def get_media(self):
        media = super(UserInfoView, self).get_media(
        ) + self.vendor('www/css/goodrainstyle.css', 'www/js/jquery.cookie.js', 'www/js/validator.min.js')
        return media

    def get_response(self):
        return TemplateResponse(self.request, 'www/account/ucloud_init.html', self.get_context())

    def update_response(self, response):
        cookie_region = self.request.COOKIES.get('region', None)
        if cookie_region is None or cookie_region != 'ucloud-bj-1':
            response.set_cookie('region', 'ucloud-bj-1')
        return response

    def get(self, request, *args, **kwargs):
        user = request.user
        if isinstance(user, AnonymousUser):
            return JsonResponse({"info": "anonymoususer"}, status=403)

        if user.is_active:
            return self.redirect_view()
        else:
            if user.origion != 'ucloud':
                return JsonResponse({"info": "you are not from ucloud"}, status=403)
            self.form = AppendInfoForm()
            return self.get_response()

    def post(self, request, *args, **kwargs):
        self.form = AppendInfoForm(request.POST)
        if not self.form.is_valid():
            return self.get_response()

        post_data = request.POST.dict()

        try:
            user = request.user
            if isinstance(user, AnonymousUser):
                return JsonResponse({"info": "anonymoususer"}, status=403)

            nick_name = post_data.get('nick_name')
            tenant_name = post_data.get('tenant')
            git_pass = post_data.get('password')
            user.nick_name = nick_name
            user.is_active = True
            user.save(update_fields=['nick_name', 'is_active'])
            monitorhook.registerMonitor(user, 'register from ucloud')

            # init tenant
            region_names = ['ucloud-bj-1']
            enterprise_svc.create_and_init_tenant(user.pk, tenant_name, region_names, user.enterprise_id)

            # create gitlab user
            if user.email is not None and user.email != "":
                codeRepositoriesService.createUser(user.email, git_pass, nick_name, nick_name)
            
            return self.redirect_view()
        except Exception, e:
            logger.exception(e)
            return JsonResponse({"info": "server error"}, status=500)
