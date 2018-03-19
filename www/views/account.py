# -*- coding: utf8 -*-
from django.conf import settings
from django.http.response import HttpResponseRedirect
from django.views.decorators.cache import never_cache
from django.template.response import TemplateResponse
from django.http import JsonResponse
from django.http import HttpResponse, Http404
from django.views.decorators.clickjacking import xframe_options_exempt
from django.shortcuts import redirect

from www.auth import authenticate, login, logout
from www.forms.account import UserLoginForm, RegisterForm, PasswordResetForm, PasswordResetBeginForm
from www.models import Users, Tenants, TenantRegionInfo, TenantServiceInfo, AnonymousUser, PermRelTenant, \
    PermRelService, PhoneCode, TenantRecharge, TenantEnterprise
from www.models import WeChatUser
from www.utils.crypt import AuthCode
from www.utils import crypt
from www.utils.mail import send_reset_pass_mail
from www.sms_service import send_phone_message
from www.db import BaseConnection
from www.services import enterprise_svc, user_svc
from www.services.sso import GoodRainSSOApi, SSO_BASE_URL
from www.models.activity import TenantActivity
import datetime
import time
import random
import re
import urllib
import json
import os

from www.region import RegionInfo
from www.views import BaseView
from www.monitorservice.monitorhook import MonitorHook
from www.tenantservice.baseservice import CodeRepositoriesService
from www.views.wechat import is_weixin
from www.utils import sn
from www.utils.license import LICENSE

import logging

logger = logging.getLogger('default')

codeRepositoriesService = CodeRepositoriesService()

monitorhook = MonitorHook()


class Login(BaseView):
    def get_context(self):
        context = super(Login, self).get_context()
        context.update({
            'form': self.form,
        })
        return context

    def get_media(self):
        media = super(Login, self).get_media() + self.vendor(
            'www/css/goodrainstyle.css', 'www/js/jquery.cookie.js')
        return media

    def get_response(self):
        return TemplateResponse(self.request, 'www/account/login.html',
                                self.get_context())

    def redirect_view(self):
        tenants_has = PermRelTenant.objects.filter(user_id=self.user.pk)
        if tenants_has:
            tenant_pk = tenants_has[0].tenant_id
            tenant = Tenants.objects.get(pk=tenant_pk)
            response_tenant_name = self.request.COOKIES.get(
                'tenant_name', None)
            tenant_name = tenant.tenant_name if response_tenant_name is None else response_tenant_name
            return self.redirect_to('/apps/{0}/'.format(tenant_name))
        else:
            logger.error(
                'account.login_error',
                'user {0} with id {1} has no tenants to redirect login'.format(
                    self.user.nick_name, self.user.pk))
            return Http404

    def get(self, request, *args, **kwargs):
        user_count = Users.objects.all().count()
        if user_count == 0:
            return self.redirect_to("/wizard/prefix/")

        user = request.user
        referer = request.get_full_path()
        next_url = ""
        origin = ""
        if referer != '':
            # 获取next、origin
            tmp = referer.split("?")
            sub_tmp = "?".join(tmp[1:])
            key_tmp = sub_tmp.split("&")
            for key in key_tmp:
                if key.startswith("origin="):
                    origin = key[7:]
                    key_tmp.remove(key)
                    break
            next_url = "&".join(key_tmp)
            if next_url.startswith("next="):
                next_url = next_url[5:]

        app_url = request.GET.get('redirect_url', None)
        if isinstance(user, AnonymousUser):
            # 安装了SSO模块用户用SSO进行登陆
            if settings.MODULES.get('SSO_LOGIN'):
                # 临时，如果cookies里面有sso的uid跟token则使用此信息自动登录, 否则跳到sso进行登录
                domain = os.getenv('GOODRAIN_DOMAIN', 'https://user.goodrain.com')
                redirect_url = '{0}/sso_callback'.format(domain)
                if request.COOKIES.get('uid', 'null') != 'null' and request.COOKIES.get('token', 'null') != 'null':
                    if next_url:
                        redirect_url = '{0}?next={1}'.format(redirect_url, next_url)
                    return self.redirect_to(redirect_url)
                return redirect('https://sso.goodrain.com/#/login/{0}'.format(urllib.quote_plus(redirect_url)))

            # 判断是否MicroMessenger
            if is_weixin(request):
                redirect_url = "/wechat/login?time=1257"
                if origin is not None and origin != "":
                    redirect_url += "&origin={0}".format(origin)
                if next_url is not None and next_url != "":
                    redirect_url += "&next={0}".format(next_url)
                if origin == "app" and app_url is not None:
                    redirect_url += "&redirect_url={0}".format(app_url)
                logger.debug("account.login",
                             "weixin login,url:{0}".format(redirect_url))
                return self.redirect_to(redirect_url)

            self.form = UserLoginForm(next_url=next_url, origin=origin)
            return self.get_response()
        else:
            # 判断是否有跳转参数,有参数跳转到返回页面
            # 这里只有app请求过来
            next_url = request.GET.get('next', None)
            origin = request.GET.get('origin', None)

            if next_url is not None and next_url != "" \
                    and next_url != "none" and next_url != "None":
                if origin == "app":
                    if app_url is None or app_url == "":
                        app_url = settings.APP_SERVICE_API.get("url")
                    union_id = user.union_id
                    wechat_user = None
                    if union_id is not None \
                            or union_id is not "" \
                            or union_id is not "null" \
                            or union_id is not "NULL":
                        wechat_user_list = WeChatUser.objects.filter(
                            union_id=union_id)
                        if len(wechat_user_list) > 0:
                            wechat_user = wechat_user_list[0]
                    payload = {
                        "nick_name": user.nick_name,
                        "user_id": str(user.user_id),
                        "next_url": next_url,
                        "action": "login"
                    }
                    if wechat_user is not None:
                        payload["wechat_name"] = wechat_user.nick_name
                    ticket = AuthCode.encode(json.dumps(payload), "goodrain")
                    next_url = "{0}/login/{1}/success?ticket={2}".format(
                        app_url, sn.instance.cloud_assistant, ticket)
                elif origin == "discourse":
                    sig = request.GET.get("sig")
                    next_url = "{0}&sig={1}".format(next_url, sig)
                return self.redirect_to(next_url)
            return self.redirect_view()

    @never_cache
    def post(self, request, *args, **kwargs):
        self.form = UserLoginForm(request.POST)
        next_url = request.GET.get('next', None)
        origin = request.GET.get("origin", None)
        username = request.POST.get('email')
        password = request.POST.get('password')

        if not self.form.is_valid():
            logger.info('account.login_error',
                        "login form is not right: %s" % self.form.errors)
            return self.get_response()
        user = authenticate(username=username, password=password)
        login(request, user)
        logger.info('account.login',
                    "user {0} success login in".format(user.nick_name))
        self.user = request.user

        # create git user
        if user.email is not None and user.email != "":
            codeRepositoriesService.createUser(user, user.email, password,
                                               user.nick_name, user.nick_name)

        # to judge from www create servcie
        app_ty = request.COOKIES.get('app_ty')
        if app_ty is not None:
            return self.redirect_to("/autodeploy?fr=www_app")

        if next_url is not None and next_url != "" \
                and next_url != "none" and next_url != "None":
            if origin == "app":
                app_url = request.GET.get('redirect_url', None)
                if app_url is None:
                    app_url = settings.APP_SERVICE_API.get("url")
                union_id = user.union_id
                wechat_user = None
                if union_id is not None \
                        or union_id is not "" \
                        or union_id is not "null" \
                        or union_id is not "NULL":
                    wechat_user_list = WeChatUser.objects.filter(
                        union_id=union_id)
                    if len(wechat_user_list) > 0:
                        wechat_user = wechat_user_list[0]
                payload = {
                    "nick_name": user.nick_name,
                    "user_id": str(user.user_id),
                    "next_url": next_url,
                    "action": "login"
                }
                if wechat_user is not None:
                    payload["wechat_name"] = wechat_user.nick_name
                ticket = AuthCode.encode(json.dumps(payload), "goodrain")
                next_url = "{0}/login/{1}/success?ticket={2}".format(
                    app_url, sn.instance.cloud_assistant, ticket)
                logger.debug(next_url)
            elif origin == "discourse":
                sig = request.GET.get("sig")
                next_url = "{0}&sig={1}".format(next_url, sig)
            return self.redirect_to(next_url)
        else:
            # 处理用户登录时没有租户情况
            tenant_num = PermRelTenant.objects.filter(
                user_id=self.user.pk).count()
            if tenant_num == 0:
                if sn.instance.is_private():
                    logger.error(
                        'account.login_error',
                        'user {0} with id {1} has no tenants to redirect login'.
                            format(self.user.nick_name, self.user.pk))
                    self.form.add_error("", "你已经不属于任何团队，请联系管理员加入团队!")
                    return self.get_response()
                else:
                    region = self.request.COOKIES.get('region', None)
                    if region is None:
                        region = RegionInfo.regions()[0]["name"]
                    tenant_name = self.user.nick_name

                    # add by tanm
                    regions = [region]
                    enterprise_svc.create_and_init_tenant(self.user.pk, tenant_name, regions, self.user.enterprise_id)

                    return self.redirect_to('/apps/{0}/'.format(tenant_name))
            return self.redirect_view()


class Index(Login):
    def get(self, request, *args, **kwargs):
        user = request.user
        if isinstance(user, AnonymousUser):
            return self.redirect_to('/login')
        else:
            return self.redirect_view()

    def post(self, request, *args, **kwargs):
        return HttpResponse("POST METHOD IS NOT ALLOWED")


class Logout(BaseView):
    def init_request(self, *args, **kwargs):
        self.template = 'www/logout.html'

    def get_context(self):
        context = super(Logout, self).get_context()
        context.update({
            'form': self.form,
        })
        return context

    def get_media(self):
        media = super(Logout, self).get_media()
        return media

    def get_response(self):
        return TemplateResponse(self.request, self.template,
                                self.get_context())

    def get(self, request, *args, **kwargs):
        user = request.user
        if isinstance(user, AnonymousUser):
            return HttpResponse("未登录状态, 不需注销")
        else:
            logout(request)
            logger.info('account.login',
                        'user {0} logout'.format(user.nick_name))
            # 判断是否MicroMessenger
            if is_weixin(request):
                return self.redirect_to("/wechat/logout")
            response = HttpResponseRedirect(settings.LOGIN_URL)
            response.delete_cookie('tenant_name')
            response.delete_cookie('uid', domain='.goodrain.com')
            response.delete_cookie('token', domain='.goodrain.com')
            return response
            # return self.redirect_to(settings.LOGIN_URL)

    @never_cache
    def post(self, request, *args, **kwargs):
        logout(request)
        return self.redirect_to(settings.LOGIN_URL)


class PasswordResetBegin(BaseView):
    def get_context(self):
        context = super(PasswordResetBegin, self).get_context()
        context.update({
            'form': self.form,
            'title': u'账号确认',
        })
        return context

    def get_media(self):
        media = super(PasswordResetBegin, self).get_media()
        return media

    def get_response(self):
        return TemplateResponse(self.request,
                                'www/account/reset_password.html',
                                self.get_context())

    def get(self, request, *args, **kwargs):
        self.form = PasswordResetBeginForm()
        return self.get_response()

    def post(self, request, *args, **kwargs):
        self.form = PasswordResetBeginForm(request.POST)
        if self.form.is_valid():
            account = request.POST.get('account')
            logger.info('account.passwdreset',
                        "account {0} apply for reset password".format(account))
            tag = '{0}:{1}'.format(int(time.time()), account)
            return self.redirect_to('/account/select_verify_method?tag=%s' %
                                    AuthCode.encode(tag, 'reset_password'))
        return self.get_response()


class PasswordResetMethodSelect(BaseView):
    def get_context(self):
        context = super(PasswordResetMethodSelect, self).get_context()
        context.update({
            'title':
                u'验证方式',
            'account':
                self.account,
            'methods': [
                {
                    "value": "email",
                    "desc": "密保邮箱 <%s>" % self.user.safe_email
                },
                # {"value": "phone", "desc": self.user.phone},
            ],
        })
        return context

    def get_media(self):
        media = super(PasswordResetMethodSelect, self).get_media()
        return media

    def get_response(self):
        return TemplateResponse(self.request,
                                'www/account/select_verify_method.html',
                                self.get_context())

    def get_user_instance(self, account):
        try:
            if '@' in account:
                user = Users.objects.get(email=account)
            else:
                user = Users.objects.get(phone=account)
            self.user = user
            return user
        except user.DoesNotExist:
            return None

    def get(self, request, *args, **kwargs):
        tag = str(request.GET.get('tag'))
        old_timestamp, account = AuthCode.decode(tag,
                                                 'reset_password').split(':')
        timestamp = int(time.time())
        if (timestamp - int(old_timestamp)) > 60:
            return HttpResponse("过期的URL, 请重新开始")

        self.account = account
        self.user = self.get_user_instance(account)
        if self.user is None:
            return HttpResponse(u"账号不存在")
        return self.get_response()

    def post(self, request, *args, **kwargs):
        tag = str(request.GET.get('tag'))
        old_timestamp, account = AuthCode.decode(tag,
                                                 'reset_password').split(':')
        verify_method = request.POST.get('verify_method')
        self.user = self.get_user_instance(account)
        self.account = account

        if verify_method == 'email':
            domain = self.request.META.get('HTTP_HOST')
            timestamp = str(int(time.time()))
            tag = AuthCode.encode(','.join([self.user.email, timestamp]),
                                  'password')
            link_url = 'https://{0}/account/reset_password?tag={1}'.format(
                domain, tag)
            try:
                send_reset_pass_mail(self.user.email, link_url)
            except Exception, e:
                logger.error(
                    "account.passwdreset",
                    "send email to {0} failed".format(self.user.email))
                logger.exception("account.passwdreset", e)
            mail_address = 'http://mail.' + self.user.email.split('@')[1]
            return TemplateResponse(self.request,
                                    'www/account/email_sended.html', {
                                        "safe_email": self.user.safe_email,
                                        "mail_address": mail_address
                                    })
        return self.get_response()


class PasswordReset(BaseView):
    def get_context(self):
        context = super(PasswordReset, self).get_context()
        context.update({
            'form': self.form,
            'title': u'重置密码',
        })
        return context

    def get_media(self):
        media = super(PasswordReset, self).get_media()
        return media

    def get_response(self):
        return TemplateResponse(self.request,
                                'www/account/reset_password.html',
                                self.get_context())

    def get_user_instance(self, account):
        try:
            if '@' in account:
                user = Users.objects.get(email=account)
            else:
                user = Users.objects.get(phone=account)
            self.user = user
            return user
        except user.DoesNotExist:
            return None

    def create_git_user(self, user, password):
        logger.info(
            "account.passwdreset",
            "user {0} didn't owned a gitlab user_id, will create it".format(
                user.nick_name))
        codeRepositoriesService.createUser(user, user.email, password,
                                           user.nick_name, user.nick_name)

    def get(self, request, *args, **kwargs):
        self.form = PasswordResetForm()
        return self.get_response()

    def post(self, request, *args, **kwargs):
        tag = str(request.GET.get('tag'))
        email, old_timestamp = AuthCode.decode(tag, 'password').split(',')
        timestamp = int(time.time())
        if (timestamp - int(old_timestamp)) > 3600:
            logger.info("account.passwdreset",
                        "link expired, email: {0}, link_timestamp: {1}".format(
                            email, old_timestamp))
            return HttpResponse(u"处理已过期, 请重新开始")

        user = self.get_user_instance(email)
        self.form = PasswordResetForm(request.POST)
        if self.form.is_valid():
            raw_password = request.POST.get('password')
            user.set_password(raw_password)
            user.save()
            flag = True
            logger.info("account.passwdreset",
                        "reset password for user {0} in my database".format(
                            user.nick_name))
            if user.git_user_id != 0:
                try:
                    codeRepositoriesService.modifyUser(user, raw_password)
                    logger.info("account.passwdreset",
                                "reset password for user {0} in gitlab".format(
                                    user.nick_name))
                except Exception, e:
                    logger.error(
                        "account.passwdreset",
                        "reset password for user {0} in gitlab failed".format(
                            user.nick_name))
                    logger.exception("account.passwdreset", e)
                    flag = False
            else:
                self.create_git_user(user, raw_password)
            monitorhook.passwdResetMonitor(user, flag)
            return self.redirect_to('/login')
        logger.info("account.passwdreset",
                    "passwdreset form error: %s" % self.form.errors)
        return self.get_response()


class Registation(BaseView):
    def get_context(self):
        context = super(Registation, self).get_context()
        context.update({
            'form': self.form,
        })
        return context

    def get_media(self):
        media = super(Registation, self).get_media() + self.vendor(
            'www/css/goodrainstyle.css', 'www/js/jquery.cookie.js',
            'www/js/validator.min.js')
        return media

    def get_response(self):
        return TemplateResponse(self.request, 'www/account/register.html',
                                self.get_context())

    def get(self, request, *args, **kwargs):
        if settings.MODULES.get('SSO_LOGIN'):
            call_back_url = '{0}/sso_callback'.format(os.getenv('GOODRAIN_DOMAIN', 'https://user.goodrain.com'))
            register_url = '{0}/#/register/{1}'.format(SSO_BASE_URL, urllib.quote_plus(call_back_url))
            return redirect(register_url)

        pl = request.GET.get("pl", "")
        region_levels = pl.split(":")
        if len(region_levels) == 2:
            region = region_levels[0]
            self.form = RegisterForm(region_level={"region": region})
        else:
            self.form = RegisterForm()
        return self.get_response()

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def weixinRegister(self, tenant_id, user_id, user_name, rf):
        try:
            sendRecharge = TenantRecharge()
            sendRecharge.tenant_id = tenant_id
            sendRecharge.user_id = user_id
            sendRecharge.user_name = user_name
            sendRecharge.order_no = str(user_id)
            sendRecharge.recharge_type = "weixin100"
            sendRecharge.money = 100
            sendRecharge.subject = "免费送"
            sendRecharge.body = "注册送100"
            sendRecharge.show_url = ""
            sendRecharge.time = datetime.datetime.now().strftime(
                '%Y-%m-%d %H:%M:%S')
            sendRecharge.status = "TRADE_SUCCESS"
            sendRecharge.save()
            tenant = Tenants.objects.get(tenant_id=tenant_id)
            tenant.balance = tenant.balance + 100
            tenant.save()
        except Exception as e:
            logger.exception(e)

    def post(self, request, *args, **kwargs):
        querydict = request.POST
        querydict.update({
            u'real_captcha_code':
                request.session.get("captcha_code")
        })
        self.form = RegisterForm(querydict)
        if self.form.is_valid():
            rf = request.GET.get("rf", "")
            email = request.POST.get('email')
            nick_name = request.POST.get('nick_name')
            password = request.POST.get('password')
            tenant_name = request.POST.get('tenant')
            phone = request.POST.get('phone')
            region = request.POST.get('machine_region')
            if region is None or region == "" or region == "1":
                region = RegionInfo.register_choices()[0][0]
            regions = [region['name'] for region in RegionInfo.regions()]
            if region not in regions:
                region = RegionInfo.regions()[0]["name"]
            # 没有配置项默认为私有云帮,配置项为false为私有云帮
            is_private = sn.instance.is_private()
            tenants_num = 0
            # if is_private:
            tenants_num = Tenants.objects.count()
            allow_num = LICENSE.get_authorization_tenant_number()
            # 如果租户数量>license允许值
            if tenants_num > allow_num:
                self.form.add_error("", "你的授权只允许创建 {}个租户".format(allow_num))
                return self.get_response()
            # 判断租户名称是否相同
            tenants_num = Tenants.objects.filter(
                tenant_name=tenant_name).count()
            if tenants_num > 0:
                self.form.add_error("", "租户名称重复")
                return self.get_response()

            user = Users(
                email=email,
                nick_name=nick_name,
                phone=phone,
                client_ip=self.get_client_ip(request),
                rf=rf)
            user.set_password(password)
            user.save()
            monitorhook.registerMonitor(user, 'register')

            # create gitlab user
            if user.email is not None and user.email != "":
                codeRepositoriesService.createUser(user, email, password,
                                                   nick_name, nick_name)

            region_names = [region]
            tenant = enterprise_svc.create_and_init_tenant(user.user_id, tenant_name, region_names, user.enterprise_id)

            # wei xin user need to add 100
            if rf == "wx":
                self.weixinRegister(tenant.tenant_id, user.pk, user.nick_name,
                                    rf)

            user = authenticate(username=nick_name, password=password)
            login(request, user)
            self.user = request.user

            # 检测是否论坛请求
            next_url = request.GET.get("next", None)
            if next_url is not None \
                    and next_url != "" \
                    and next_url != "none" \
                    and next_url != "None":
                origin = request.GET.get("origin", "")
                if origin == "app":
                    union_id = user.union_id
                    wechat_user = None
                    if union_id is not None \
                            or union_id is not "" \
                            or union_id is not "null" \
                            or union_id is not "NULL":
                        wechat_user_list = WeChatUser.objects.filter(
                            union_id=union_id)
                        if len(wechat_user_list) > 0:
                            wechat_user = wechat_user_list[0]
                    payload = {
                        "nick_name": user.nick_name,
                        "user_id": str(user.user_id),
                        "next_url": next_url,
                        "action": "register"
                    }
                    if wechat_user is not None:
                        payload["wechat_name"] = wechat_user.nick_name
                    ticket = AuthCode.encode(json.dumps(payload), "goodrain")
                    app_url = request.GET.get('redirect_url', None)
                    if app_url is None:
                        app_url = settings.APP_SERVICE_API.get("url")
                    next_url = "{0}/login/{1}/success?ticket={2}".format(
                        app_url, sn.instance.cloud_assistant, ticket)
                logger.debug("account.register", next_url)
                return self.redirect_to(next_url)
            return self.redirect_to('/apps/{0}'.format(tenant_name))

        logger.info("account.register",
                    "register form error: %s" % self.form.errors)
        return self.get_response()


class InviteRegistation(BaseView):
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def get_context(self):
        context = super(InviteRegistation, self).get_context()
        context.update({
            'form': self.form,
        })
        return context

    def get_media(self):
        media = super(InviteRegistation, self).get_media() + self.vendor(
            'www/css/goodrainstyle.css', 'www/js/jquery.cookie.js')
        return media

    def get_response(self):
        return TemplateResponse(self.request, 'www/account/register.html',
                                self.get_context())

    def register_for_tenant(self, user, password, data):
        email, tenant_name, identity = data
        tenant = Tenants.objects.get(tenant_name=tenant_name)
        PermRelTenant.objects.create(
            user_id=user.pk, tenant_id=tenant.pk, identity=identity)
        self.add_git_user(user, password)

    def register_for_service(self, user, password, data):
        email, tenant_name, service_alias, identity = data
        tenant = Tenants.objects.get(tenant_name=tenant_name)
        service = TenantServiceInfo.objects.get(
            tenant_id=tenant.tenant_id, service_alias=service_alias)
        PermRelService.objects.create(
            user_id=user.pk, service_id=service.pk, identity=identity)

        perm_t, created = PermRelTenant.objects.get_or_create(
            user_id=user.pk, tenant_id=tenant.pk)
        if created:
            perm_t.identity = 'access'
            perm_t.save()
            self.add_git_user(user, password)

        git_project_id = service.git_project_id
        if service.code_from != 'github' and git_project_id > 0 and user.git_user_id > 0:
            level = 10
            if identity == "viewer":
                level = 20
            elif identity == "developer":
                level = 30
            elif identity == "admin":
                level = 40
            codeRepositoriesService.addProjectMember(git_project_id,
                                                     user.git_user_id, level)

    def add_git_user(self, user, password):
        codeRepositoriesService.createUser(user, user.email, password,
                                           user.nick_name, user.nick_name)

    def get(self, request, *args, **kwargs):
        encoded_data = str(request.GET.get('key'))
        self.key = encoded_data
        logger.debug(self.key)
        data = AuthCode.decode(encoded_data, 'goodrain').split(',')
        logger.debug(data)
        # tenant member
        if len(data) == 3:
            self.email, self.tenant_name = data[0:2]
            self.service_name = ""
        elif len(data) == 4:
            self.email, self.tenant_name, self.service_name = data[0:3]
        else:
            self.redirect_to('/register')

        try:
            if self.email.find("@") > 0:
                Users.objects.get(email=self.email)
            else:
                Users.objects.get(phone=self.email)
            return self.redirect_to('/login')
        except Users.DoesNotExist:
            curemail = ""
            curphone = ""
            if self.email.find("@"):
                curemail = self.email
            else:
                curphone = self.email
            registerTenant = Tenants.objects.get(tenant_name=self.tenant_name)
            self.form = RegisterForm(initial={
                "tenant": self.tenant_name,
                "phone": curphone,
                "email": curemail,
                "region": registerTenant.region
            })
            return self.get_response()

    def post(self, request, *args, **kwargs):
        encoded_data = str(request.GET.get('key'))
        data = AuthCode.decode(encoded_data, 'goodrain').split(',')
        querydict = request.POST
        querydict.update({u'invite_tag': "invite"})
        querydict.update({
            u'real_captcha_code':
                request.session.get("captcha_code")
        })
        self.form = RegisterForm(querydict)
        if not self.form.is_valid():
            initial = {
                "tenant": request.POST.get('tenant'),
                "phone": request.POST.get('phone'),
                "email": request.POST.get('email'),
                "region": request.POST.get('machine_region')
            }
            querydict.update({"initial": initial})
            self.form = RegisterForm(querydict)
            return self.get_response()

        email = request.POST.get('email')
        nick_name = request.POST.get('nick_name')
        password = request.POST.get('password')
        tenant_name = request.POST.get('tenant')
        phone = request.POST.get('phone')
        user = Users(
            email=email,
            nick_name=nick_name,
            phone=phone,
            client_ip=self.get_client_ip(request))
        user.set_password(password)
        user.save()
        monitorhook.registerMonitor(user, "invite_register")

        if len(data) == 3:
            self.register_for_tenant(user, password, data)
        elif len(data) == 4:
            self.register_for_service(user, password, data)
        else:
            self.register_for_service(user, password, data)
        user = authenticate(username=email, password=password)
        login(request, user)
        return self.redirect_to('/apps/{0}'.format(tenant_name))


class PhoneCodeView(BaseView):
    def post(self, request, *args, **kwargs):
        result = {}
        phone = request.POST.get('phone')
        captcha_code = request.POST.get('captcha_code')
        real_captcha_code = request.session.get("captcha_code")
        logger.debug(captcha_code)
        logger.debug(real_captcha_code)
        if captcha_code.lower() != real_captcha_code.lower():
            result["status"] = "errorcaptchacode"
            return JsonResponse(result)

        if phone is not None:
            r = re.compile(r'^1[3578]\d{9}$|^147\d{8}$')
            if not r.match(phone):
                result["status"] = "errorphone"
                return JsonResponse(result)
        else:
            result["status"] = "errorphone"
            return JsonResponse(result)
        try:
            phoneCodes = PhoneCode.objects.filter(
                phone=phone).order_by('-ID')[:1]
            if len(phoneCodes) > 0:
                phoneCode = phoneCodes[0]
                last = int(phoneCode.create_time.strftime("%s"))
                now = int(time.time())
                if now - last < 90:
                    result["status"] = "often"
                    return JsonResponse(result)
            dsn = BaseConnection()
            query_time = datetime.datetime.now().strftime('%Y-%m-%d')
            query_sql = '''
                select count(1) as sendNumber from phone_code where phone = "{phone}" and create_time >= "{query_time}"
                '''.format(
                phone=phone, query_time=query_time + " 00:00:00")
            sqlobj = dsn.query(query_sql)
            if len(sqlobj) > 0:
                sendNumber = int(sqlobj[0]["sendNumber"])
                if sendNumber > 3:
                    result["status"] = "limited"
                    return JsonResponse(result)
            phone_code = random.randrange(0, 1000001, 6)
            send_result, message_id = send_phone_message(phone, phone_code)
            # if not send_result:
            #     send_result, message_id = send_phone_message(phone, phone_code)
            if send_result:
                newpc = PhoneCode(
                    phone=phone,
                    type="register",
                    code=phone_code,
                    message_id=message_id)
                newpc.save()
                monitorhook.phoneCodeMonitor(phone, phone_code, send_result)
                result["status"] = "success"
            else:
                result["status"] = "error"
            return JsonResponse(result)
        except Exception as e:
            logger.exception(e)
        result["status"] = "error"
        return JsonResponse(result)


class TenantSelectView(BaseView):
    def get_tenant_names(self):
        tids = PermRelTenant.objects.filter(user_id=self.user.pk).values_list(
            "tenant_id", flat=True)
        tnames = Tenants.objects.filter(pk__in=tids).values_list(
            "tenant_name", flat=True)
        return tnames

    def get(self, request, *args, **kwargs):
        if isinstance(self.user, AnonymousUser):
            return self.redirect_to('/login')
        context = self.get_context()
        # 先获取用户关联的团队
        tenant_names = self.get_tenant_names()
        # 获取配置的可用数据中心列表
        regions = RegionInfo.register_choices()
        # 排除迅达机房
        regions = [(name, display_name) for name, display_name in regions
                   if name != "xunda-bj"]
        # 判断是否活动用户activity998

        tenant_list = Tenants.objects.filter(tenant_name__in=tenant_names)
        tenant_region_map = {}
        for tenant in tenant_list:
            tenant_region_map[tenant.tenant_name] = regions

        # 获取用户动作
        action = request.GET.get("action", None)
        # 远程安装(云市)下,需要看是否指定默认安装选项,如果有匹配选项则直接重定向到安装页,否则跳到选择页
        if action == 'remote_install':
            # 远程服务安装
            service_key = request.GET.get('service_key')
            version = request.GET.get("version")
            callback = request.GET.get("callback")
            context.update({"action": "remote_install"})

            # 获取数据中心选择模式
            region = request.GET.get('region', None)

            logger.debug("select region {} from {}".format(region, regions))
            # 如果用户只属于一个团队并且有数据中心的选择模式参数
            if region is not None and len(tenant_names) == 1:
                # 系统自动选择机房
                if region == 'auto':
                    select_tenant = tenant_names[0]
                    select_region = regions[random.randint(
                        0, len(regions) - 1)][0]
                    next_url = '/ajax/{0}/remote/market?service_key={1}&app_version={2}&callback={3}'.format(
                        select_tenant, service_key, version, callback)

                    response = self.redirect_to(next_url)
                    response.set_cookie('region', select_region)

                    logger.debug("install app to region {} , redirect to {}".
                                 format(select_region, next_url))
                    return response

                # 如果指定机房在系统配置机房范围内
                elif region in RegionInfo.valid_regions():
                    select_tenant = tenant_names[0]
                    select_region = region

                    next_url = '/ajax/{0}/remote/market?service_key={1}&app_version={2}&callback={3}'.format(
                        select_tenant, service_key, version, callback)

                    response = self.redirect_to(next_url)
                    response.set_cookie('region', select_region)

                    logger.debug("install app to region {}, redirect to {}".
                                 format(select_region, next_url))
                    return response
        if action == "remote_group_install":
            group_key = request.GET.get('group_key')
            group_version = request.GET.get('version')
            callback = request.GET.get("callback")
            # 获取数据中心选择模式
            region = request.GET.get('region', None)
            context.update({"action": "remote_group_install"})
            logger.debug("select region {} from {}".format(region, regions))
            # 如果用户只属于一个团队并且有数据中心的选择模式参数
            if region is not None and len(tenant_names) == 1:
                # 系统自动选择机房
                select_tenant = tenant_names[0]
                select_region = region
                if region == 'auto':
                    select_region = regions[random.randint(
                        0, len(regions) - 1)][0]
                # 如果指定机房在系统配置机房范围内
                elif region in RegionInfo.valid_regions():
                    select_region = region
                next_url = '/apps/{0}/group-deploy/?group_key={1}&group_version={2}&callback={3}'.format(
                    select_tenant, group_key, group_version, callback)

                response = self.redirect_to(next_url)
                response.set_cookie('region', select_region)

                logger.debug(
                    "install group_service to region {} , redirect to {}".
                        format(select_region, next_url))
                return response

        context.update({
            "tenant_names": tenant_names,
            "tenant_region_map": json.dumps(tenant_region_map)
        })

        # context.update({"tenant_names": tenant_names, "regions": regions})
        # if count > 0:
        #     context["regions"] = xunda_region

        logger.debug(
            "install app  or group apps by user self, response select_tenant.html!"
        )
        return TemplateResponse(request, 'www/account/select_tenant.html',
                                context)

    def post(self, request, *args, **kwargs):
        post_data = request.POST.dict()
        get_paras = request.GET.dict()
        action = get_paras.pop("action", None)
        tenant = post_data.get('tenant')
        region = post_data.get('region')
        logger.debug("user action is {0}".format(action))
        try:
            tenant_info = Tenants.objects.get(tenant_name=tenant)
            num = TenantRegionInfo.objects.filter(
                tenant_id=tenant_info.tenant_id, region_name=region).count()
            if num == 0:
                TenantRegionInfo.objects.create(
                    tenant_id=tenant_info.tenant_id, region_name=region)
        except Exception as e:
            logger.exception(e)
            return self.redirect_to("/")

        if action is None:
            return self.get(request, *args, **kwargs)
        elif action == 'app_install':
            service_key = get_paras.get('service_key')
            version = get_paras.get("version")
            next_url = '/apps/{0}/service-deploy/?service_key={2}&region={1}&app_version={3}'.format(
                tenant, region, service_key, version)
            return self.redirect_to(next_url)
        elif action == 'remote_install':
            # 远程服务安装
            service_key = get_paras.get('service_key')
            version = get_paras.get("version")
            callback = get_paras.get("callback")
            next_url = '/ajax/{0}/remote/market?service_key={1}&app_version={2}&callback={3}'.format(
                tenant, service_key, version, callback)
            response = self.redirect_to(next_url)
            response.set_cookie('region', region)
            return response
        elif action == 'remote_group_install':
            group_key = get_paras.get("group_key")
            group_version = get_paras.get("group_version")
            callback = get_paras.get("callback")
            next_url = '/apps/{0}/group-deploy/?group_key={1}&group_version={2}&callback={3}'.format(
                tenant, group_key, group_version, callback)
            response = self.redirect_to(next_url)
            response.set_cookie('region', region)
            return response


class AppLogin(BaseView):
    """app 用户登录接口"""

    @xframe_options_exempt
    def get(self, request, *args, **kwargs):
        context = self.get_context()
        return TemplateResponse(self.request, 'www/account/proxy.html',
                                context)

    @never_cache
    def post(self, request, *args, **kwargs):
        logger.info(request.get_host())

        username = request.POST.get('email')
        password = request.POST.get('password')
        next_url = request.POST.get('next_url', "/")
        if password:
            if len(password) < 8:
                return JsonResponse({
                    "success": False,
                    "msg": "password error!"
                })

        if username and password:
            try:
                if username.find("@") > 0:
                    user = Users.objects.get(email=username)
                else:
                    user = Users.objects.get(phone=username)
                if not user.check_password(password):
                    logger.info('form_valid.login',
                                'password is not correct for user {0}'.format(
                                    username))
                    return JsonResponse({
                        "success": False,
                        "msg": "password error!"
                    })
            except Users.DoesNotExist:
                return JsonResponse({"success": False, "msg": "email error!"})
        else:
            return JsonResponse({
                "success": False,
                "msg": "email or password cannot be null!"
            })

        user = authenticate(username=username, password=password)
        login(request, user)
        logger.info('account.login',
                    "user {0} success login in".format(user.nick_name))

        ticket = AuthCode.encode(','.join(
            [user.nick_name, str(user.user_id), next_url]), 'goodrain')
        return JsonResponse({"success": True, "ticket": ticket})


class ChangeLoginPassword(BaseView):
    """修改用户登陆密码"""

    def get(self, request, *args, **kwargs):
        if settings.MODULES.get('SSO_LOGIN'):
            domain = os.getenv('GOODRAIN_DOMAIN', 'https://user.goodrain.com')
            redirect_url = '{0}/sso_callback'.format(domain)
            return redirect('https://sso.goodrain.com/#/backpassword/{0}'.format(urllib.quote_plus(redirect_url)))

        return TemplateResponse(request, "www/account/change_password.html",
                                self.get_context())

    def post(self, request, *args, **kwargs):
        context = self.get_context()
        old_raw_password = request.POST.get("oldpwd", "")
        new_raw_password = request.POST.get("newpwd", "")
        confirm_password = request.POST.get("confirmpwd", "")

        user_id = request.user.user_id
        if new_raw_password == "" or new_raw_password != confirm_password:
            logger.error(
                "account.login",
                "modify user {} password failed, new password is empty or confirm password not equial".
                    format(user_id))
            context.update({"message": "修改密码失败, 新密码不能为空"})
            return TemplateResponse(
                request, "www/account/change_password.html", context)

        if len(new_raw_password) < 8:
            logger.error(
                "account.login",
                "modify user {} password failed, new password is too short, at least 8 characters".
                    format(user_id))
            context.update({"message": "修改密码失败, 新密码不能少于8位"})
            return TemplateResponse(
                request, "www/account/change_password.html", context)

        login_user = Users.objects.get(user_id=user_id)
        encrypt_old_password = crypt.encrypt_passwd(login_user.email +
                                                    old_raw_password)
        if encrypt_old_password != login_user.password:
            context.update({"message": "修改密码失败, 用户密码不正确"})
            return TemplateResponse(
                request, "www/account/change_password.html", context)

        login_user.set_password(new_raw_password)
        login_user.save()
        logger.info("account.login",
                    "modify user {} password from {} to {} succeed!".format(
                        user_id, encrypt_old_password, login_user.password))

        # 同时修改git的密码
        codeRepositoriesService.modifyUser(login_user, new_raw_password)
        logger.info("account.login",
                    "modify user {} git password succeed".format(user_id))

        context.update({"message": "修改密码成功!"})
        return TemplateResponse(request, "www/account/change_password.html",
                                context)


class LicenceView(BaseView):
    def get(self, request, *args, **kwargs):
        context = self.get_context()
        expired_day = sn.instance.expire_day
        context["expired_day"] = expired_day
        context["user"] = self.user.nick_name
        return TemplateResponse(request, "www/account/license.html", context)


class GoorainSSOCallBack(BaseView):
    """
    处理SSO回调登陆
    """

    def get(self, request, *args, **kwargs):
        # 获取sso的user_id
        sso_user_id = request.COOKIES.get('uid')
        sso_user_token = request.COOKIES.get('token')

        logger.debug('cookies.sso_user_id:{}'.format(sso_user_id))
        logger.debug('cookies.sso_user_token:{}'.format(sso_user_token))

        if not sso_user_id or not sso_user_token:
            logger.error('cookies uid or token not specified!')
            return self.redirect_to("/")

        if sso_user_id == 'null' or sso_user_token == 'null':
            logger.error('bad uid or token, value is null!')
            return self.redirect_to("/")

        api = GoodRainSSOApi(sso_user_id, sso_user_token)
        if not api.auth_sso_user_token():
            logger.error('Illegal user token!')
            return self.redirect_to("/")

        # 同步sso_id所代表的企业信息，没有则创建
        try:
            user = Users.objects.get(sso_user_id=sso_user_id)
            if user.sso_user_token != sso_user_token:
                user.sso_user_token = sso_user_token
                user.save()
        except Users.DoesNotExist:
            logger.debug('query user with sso_user_id does not existed, created!')
            sso_user = api.get_sso_user_info()
            logger.debug(sso_user)
            try:
                enterprise = TenantEnterprise.objects.get(enterprise_id=sso_user.eid)
            except TenantEnterprise.DoesNotExist:
                enterprise = TenantEnterprise()
                enterprise.enterprise_id = sso_user.eid
                enterprise.enterprise_name = sso_user.company
                enterprise.enterprise_alias = sso_user.company
                enterprise.is_active = 1
                enterprise.save()
                logger.info(
                    'create enterprise[{0}] with name {1}'.format(enterprise.enterprise_id,
                                                                  enterprise.enterprise_name))

            user = Users.objects.create(nick_name=sso_user.name,
                                        email=sso_user.email or '',
                                        phone=sso_user.mobile or '',
                                        password=sso_user.pwd or '',
                                        sso_user_id=sso_user.uid,
                                        enterprise_id=sso_user.eid,
                                        sso_user_token=sso_user_token,
                                        is_active=False,
                                        rf='sso')
            logger.info(
                'create user[{0}] with name [{1}] from [{2}] use sso_id [{3}]'.format(user.user_id, user.nick_name,
                                                                                      user.rf,
                                                                                      user.sso_user_id))
            monitorhook.registerMonitor(user, 'register')

        if not user.is_active:
            tenant = enterprise_svc.create_and_init_tenant(user.user_id, enterprise_id=user.enterprise_id)
        else:
            tenant = user_svc.get_default_tenant_by_user(user.user_id)
        logger.info(tenant.to_dict())

        # create gitlab user
        if user.email is not None and user.email != "":
            codeRepositoriesService.createUser(user, user.email, user.password, user.nick_name, user.nick_name)

        # SSO用户登录
        user = authenticate(user_id=user.user_id, sso_user_id=user.sso_user_id)
        login(request, user)
        self.user = request.user

        next_url = request.GET.get('next')
        if next_url:
            return self.redirect_to(next_url)
        return self.redirect_to('/apps/{0}/'.format(tenant.tenant_name))


class GoodrainSSONotify(BaseView):
    def post(self, request, *args, **kwargs):
        # 获取sso的user_id
        sso_user_id = request.POST.get('uid')
        sso_user_token = request.POST.get('token')
        sso_enterprise_id = request.POST.get('eid')
        rf = request.POST.get('rf') or 'sso'
        rf_username = request.POST.get('rf_username') or ''

        logger.debug('account.login', 'request.sso_user_id:{}'.format(sso_user_id))
        logger.debug('account.login', 'request.sso_user_token:{}'.format(sso_user_token))
        logger.debug('account.login', 'request.sso_enterprise_id:{}'.format(sso_enterprise_id))

        if not sso_user_id or not sso_user_token or not sso_enterprise_id:
            logger.error('account.login', 'post params [uid] or [token] or [eid] not specified!')
            return JsonResponse({'success': False, 'msg': 'post params [uid] or [token] or [eid] not specified!'})

        if sso_user_id == 'null' or sso_user_token == 'null':
            logger.error('account.login', 'bad uid or token, value is null!')
            return JsonResponse({"success": False, 'msg': 'bad uid or token, value is null!'})

        api = GoodRainSSOApi(sso_user_id, sso_user_token)
        if not api.auth_sso_user_token():
            logger.error('account.login', 'Illegal user token!')
            return JsonResponse({"success": False, 'msg': 'auth from sso failed!'})

        sso_user = api.get_sso_user_info()
        logger.debug(sso_user)
        # 同步sso_id所代表的用户与企业信息，没有则创建
        sso_eid = sso_user.get('eid')
        sso_company = sso_user.get('company')
        sso_username = sso_user.get('name')
        sso_phone = sso_user.get('mobile')
        sso_pwd = sso_user.get('pwd')
        try:
            enterprise = TenantEnterprise.objects.get(enterprise_id=sso_eid)
            logger.debug('query enterprise does existed, updated!')
        except TenantEnterprise.DoesNotExist:
            logger.debug('query enterprise does not existed, created!')
            enterprise = TenantEnterprise()
            enterprise.enterprise_id = sso_eid
            enterprise.enterprise_name = sso_company
            enterprise.enterprise_alias = sso_company
            enterprise.is_active = 1
            enterprise.save()
            logger.info('account.login',
                        'create enterprise[{0}] with name {1}'.format(enterprise.enterprise_id,
                                                                      enterprise.enterprise_name))

        try:
            user = Users.objects.get(sso_user_id=sso_user_id)
            user.sso_user_token = sso_user_token
            user.password = sso_pwd or ''
            user.phone = sso_phone or ''
            user.nick_name = sso_username
            user.enterprise_id = sso_eid
            user.save()

            logger.debug('account.login', 'query user with sso_user_id existed, updated!')
        except Users.DoesNotExist:
            logger.debug('account.login', 'query user with sso_user_id does not existed, created!')
            user = Users.objects.create(nick_name=sso_username,
                                        email=sso_user.get('email') or '',
                                        phone=sso_phone or '',
                                        password=sso_pwd or '',
                                        sso_user_id=sso_user.get('uid'),
                                        enterprise_id=sso_eid,
                                        sso_user_token=sso_user_token,
                                        is_active=False,
                                        rf=rf)
            logger.info(
                'account.login',
                'create user[{0}] with name [{1}] from [{2}] use sso_id [{3}]'.format(user.user_id, user.nick_name,
                                                                                      user.rf,
                                                                                      user.sso_user_id))
            monitorhook.registerMonitor(user, 'register')

        key = request.POST.get('key')
        logger.debug('invite key: {}'.format(key))
        if key:
            logger.debug('account.login', 'invite register: {}'.format(key))
            data = AuthCode.decode(str(key), 'goodrain').split(',')
            logger.debug(data)
            action = data[0]
            if action == 'invite_tenant':
                email, tenant_name, identity = data[1], data[2], data[3]
                tenant = Tenants.objects.get(tenant_name=tenant_name)
                if PermRelTenant.objects.filter(user_id=user.user_id, tenant_id=tenant.pk).count() == 0:
                    invite_enter = TenantEnterprise.objects.get(enterprise_id=tenant.enterprise_id)
                    PermRelTenant.objects.create(user_id=user.user_id, tenant_id=tenant.pk, identity=identity,
                                                 enterprise_id=invite_enter.pk)

            elif action == 'invite_service':
                email, tenant_name, service_alias, identity = data[1], data[2], data[3], data[4]
                tenant_service = TenantServiceInfo.objects.get(service_alias=service_alias)
                if PermRelService.objects.filter(user_id=user.user_id, service_id=tenant_service.pk).count() == 0:
                    PermRelService.objects.create(user_id=user.user_id, service_id=tenant_service.pk, identity=identity)

            user.is_active = True
            user.save()
            logger.debug('account.login', 'user invite register successful')
        else:
            logger.debug('account.login', 'register/login user.is_active:{}'.format(user.is_active))
            if not user.is_active:
                tenant = enterprise_svc.create_and_init_tenant(user.user_id, enterprise_id=user.enterprise_id,
                                                               rf_username=rf_username)
            else:
                tenant = user_svc.get_default_tenant_by_user(user.user_id)
            logger.info(tenant.to_dict())
            logger.debug('account.login', 'user info notify successful')

        tenants = user_svc.get_enterprise_tenants(user.enterprise_id)
        logger.debug("Enterprise {0} have tenants {1}".format(user.enterprise_id, tenants))
        data_list = [{
                         'uid': user.sso_user_id,
                         'tenant_id': t.tenant_id,
                         'tenant_name': t.tenant_name,
                         'tenant_alias': t.tenant_alias,
                         'eid': t.enterprise_id
                     } for t in tenants]

        logger.debug('account.login', '-' * 30)
        return JsonResponse({'success': True, 'list': data_list})
