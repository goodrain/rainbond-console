# -*- coding: utf8 -*-
import urllib
import hashlib
from django.template.response import TemplateResponse
from django.http import JsonResponse, HttpResponse
from django.http import Http404
from django.shortcuts import redirect
from django.conf import settings

from www.auth import authenticate, login
from www.models import WeChatConfig, WeChatUser, Users, PermRelTenant, Tenants, TenantRegionInfo, WeChatUnBind
from www.utils.crypt import AuthCode

from www.views import BaseView
from www.monitorservice.monitorhook import MonitorHook

from www.wechat.openapi import OpenWeChatAPI
from www.tenantservice.baseservice import CodeRepositoriesService

import logging
logger = logging.getLogger('default')

# 用户行为监控
monitorhook = MonitorHook()
# git逻辑
codeRepositoriesService = CodeRepositoriesService()
# 微信开放平台API
WECHAT_USER = "user"
WECHAT_GOODRAIN = "goodrain"


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def is_weixin(request):
    agent = request.META.get("HTTP_USER_AGENT", "")
    # 判断是否MicroMessenger
    if "micromessenger" in agent.lower():
        return True
    return False


class WeChatCheck(BaseView):
    """微信公众平台检测"""
    def get(self, request, *args, **kwargs):
        signature = request.GET.get("signature")
        timestamp = request.GET.get("timestamp")
        nonce = request.GET.get("nonce")
        echostr = request.GET.get("echostr")

        config = WeChatConfig.objects.get(config=WECHAT_GOODRAIN)
        token = config.token
        wx_array = [token, timestamp, nonce]
        wx_array.sort()
        wx_string = ''.join(wx_array)
        wx_string = hashlib.sha1(wx_string).hexdigest()

        logger.debug("signature:" + signature)
        logger.debug("timestamp:" + timestamp)
        logger.debug("nonce:" + nonce)
        logger.debug("echostr:" + echostr)
        logger.debug("token:" + token)
        logger.debug("wx_string:" + wx_string)
        logger.debug(signature == wx_string)
        if signature == wx_string:
            return HttpResponse(echostr)
        else:
            return HttpResponse("")


class WeChatLogin(BaseView):
    """微信用户登录
    type=wechat来自pc端微信登录
    type=market来自微信端云市登录
    type=''来自微信端云帮登录"""
    def get(self, request, *args, **kwargs):
        if not settings.MODULES["WeChat_Module"]:
            index_url = settings.WECHAT_CALLBACK.get("index")
            return self.redirect_to(index_url)
        # 获取cookie中的corf
        csrftoken = request.COOKIES.get('csrftoken')
        if csrftoken is None:
            csrftoken = "csrf"
        # 判断登录来源,默认从微信上登录
        tye = request.GET.get("type", "uu")
        next_url = request.GET.get("next_url", "next_url")
        state = AuthCode.encode(','.join([csrftoken, tye, next_url]), 'we_chat_login')
        logger.debug("here is encode:" + state)
        config = WECHAT_GOODRAIN
        oauth2 = 'https://open.weixin.qq.com/connect/oauth2/authorize'
        scope = 'snsapi_userinfo'
        # 判断是否微信浏览器
        if not is_weixin(request):
            if tye == 'wechat':
                config = WECHAT_USER
                oauth2 = 'https://open.weixin.qq.com/connect/qrconnect'
                scope = 'snsapi_login'

        # 获取user对应的微信配置
        config = WeChatConfig.objects.get(config=config)
        app_id = config.app_id
        # 扫码后微信的回跳页面
        redirect_url = settings.WECHAT_CALLBACK.get("console_goodrain")
        if not is_weixin(request):
            if tye == 'wechat':
                redirect_url = settings.WECHAT_CALLBACK.get("console")

        redirect_url = urllib.urlencode({"1": redirect_url})[2:]
        # 微信登录扫码路径
        url = "{0}?appid={1}" \
              "&redirect_uri={2}" \
              "&response_type=code" \
              "&scope={3}" \
              "&state={4}#wechat_redirect".format(oauth2,
                                                  app_id,
                                                  redirect_url,
                                                  scope,
                                                  state)
        logger.debug(url)
        return self.redirect_to(url)


class WeChatLogout(BaseView):
    def get(self, request, *args, **kwargs):
        logger.debug("out wechat")
        index_url = settings.WECHAT_CALLBACK.get("index")
        return self.redirect_to(index_url)


class WeChatCallBack(BaseView):
    """微信登录后返回"""

    def get(self, request, *args, **kwargs):
        # 获取cookie中的csrf
        csrftoken = request.COOKIES.get('csrftoken')
        if csrftoken is None:
            csrftoken = "csrf"
        # 获取statue
        state = request.GET.get("state")
        # 解码toke, type
        logger.debug("here is decode:" + state)
        oldcsrftoken, tye, next_url = AuthCode.decode(str(state), 'we_chat_login').split(',')
        logger.debug(oldcsrftoken)
        logger.debug(tye)
        config = WECHAT_GOODRAIN
        err_url = settings.WECHAT_CALLBACK.get("index")
        if tye == 'wechat':
            config = WECHAT_USER

        if csrftoken != oldcsrftoken:
            return self.redirect_to(err_url)
        # 获取的code
        code = request.GET.get("code")
        if code is None:
            return self.redirect_to(err_url)
        # 根据code获取access_token
        wechat_config = WeChatConfig.objects.get(config=config)
        access_token, open_id = OpenWeChatAPI.access_token_oauth2_static(
            wechat_config.app_id,
            wechat_config.app_secret,
            code)
        if access_token is None:
            # 登录失败,跳转到失败页面
            return self.redirect_to(err_url)
        # 检查用户的open_id是否已经存在
        need_new = False
        wechat_user = None
        try:
            wechat_user = WeChatUser.objects.get(open_id=open_id)
        except WeChatUser.DoesNotExist:
            logger.warning("open_id is first to access console. now regist...")
            need_new = True

        # 添加wechatuser
        if need_new:
            jsondata = OpenWeChatAPI.query_userinfo_static(open_id, access_token)
            union_id = jsondata.get("unionid")
            begin_index = len(union_id) - 8
            tenant_name = union_id[begin_index:]
            wechat_user = WeChatUser(open_id=jsondata.get("openid"),
                                     nick_name=tenant_name,
                                     union_id=jsondata.get("unionid"),
                                     sex=jsondata.get("sex"),
                                     city=jsondata.get("city"),
                                     province=jsondata.get("province"),
                                     country=jsondata.get("country"),
                                     headimgurl=jsondata.get("headimgurl"),
                                     config=config)
            wechat_user.save()

        # 根据微信的union_id判断用户是否已经注册
        need_new = False
        user = None
        try:
            user = Users.objects.get(union_id=wechat_user.union_id)
        except Users.DoesNotExist:
            logger.warning("union id is first to access console. now create user...")
            need_new = True
        # 用户表中不存在对应用户,判断是否已经解绑
        if need_new:
            try:
                binding = WeChatUnBind.objects.get(union_id=wechat_user.union_id,
                                                   status=0)
                user = Users.objects.get(pk=binding.user_id)
                user.union_id = wechat_user.union_id
                user.save()
                need_new = False
            except WeChatUnBind.DoesNotExist:
                pass

        # 创建租户
        if need_new:
            union_id = wechat_user.union_id
            begin_index = len(union_id) - 8
            tenant_name = union_id[begin_index:]
            email = tenant_name + "@wechat.com"
            logger.debug("new wx regist user.email:{0} tenant_name:{1}".format(email, tenant_name))
            # 创建用户,邮箱为openid后8位@wechat.comemail=email,
            # 统计当前wx数量
            count = Users.objects.filter(rf="open_wx").count()
            count += 1989
            nick_name = "wxgd0" + str(count)
            user = Users(nick_name=nick_name,
                         phone="",
                         client_ip=get_client_ip(request),
                         rf="open_wx",
                         status=2,
                         union_id=union_id)
            user.set_password("wechatpwd")
            user.save()
            monitorhook.registerMonitor(user, 'register')
            # 创建租户,默认为alish
            region = "ali-sh"
            # 租户名称必须唯一,这里取open_id的后面8位
            tenant = Tenants.objects.create(
                tenant_name=tenant_name,
                pay_type='free',
                creater=user.pk,
                region=region)
            monitorhook.tenantMonitor(tenant, user, "create_tenant", True)
            # 微信用户授权
            PermRelTenant.objects.create(user_id=user.pk, tenant_id=tenant.pk, identity='admin')
            logger.info("account.register", "new registation, nick_name: {0}, tenant: {1}, region: {2}, tenant_id: {3}".format(email, tenant_name, region, tenant.tenant_id))
            # 租户与区域中心绑定
            TenantRegionInfo.objects.create(tenant_id=tenant.tenant_id, region_name=tenant.region)
            # create gitlab user 微信注册默认不支持
            # codeRepositoriesService.createUser(user, email, password, nick_name, nick_name)

        if user is None:
            logger.error("微信用户登录失败!")
            return self.redirect_to(err_url)
        # 微信用户登录
        user = authenticate(union_id=user.union_id)
        login(request, user)

        # 回跳到云市
        if tye == "market":
            logger.debug("now return to cloud market login..")
            ticket = AuthCode.encode(','.join([user.nick_name, str(user.user_id), next_url]), 'goodrain')
            url = settings.APP_SERVICE_API.get("url") + '/login/goodrain/success?ticket=' + ticket
            return redirect(url)

        return self.redirect_view()

    def redirect_view(self):
        tenants_has = PermRelTenant.objects.filter(user_id=self.user.pk)
        if tenants_has:
            tenant_pk = tenants_has[0].tenant_id
            tenant = Tenants.objects.get(pk=tenant_pk)
            tenant_name = tenant.tenant_name
            return self.redirect_to('/apps/{0}/'.format(tenant_name))
        else:
            logger.error('account.login_error', 'user {0} with id {1} has no tenants to redirect login'.format(
                self.user, self.user.pk))
            return Http404


class WeChatInfoView(BaseView):

    def get(self, request, *args, **kwargs):
        page = "www/account/wechatinfo.html"
        context = self.get_context()
        if self.user.phone == None:
            self.user.phone = ""
        context["user"] = self.user
        if self.user.rf == "open_wx":
            self.user.nick_name = ""  # 默认不现实微信名称
            context["disable_nick_name"] = False
        else:
            context["disable_nick_name"] = True
        return TemplateResponse(self.request, page, context)

    def post(self, request, *args, **kwargs):
        # 获取用户信息
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        password = request.POST.get("password")

        err_info = {}
        success = True
        # 校验邮箱
        if email is None or email == "":
            success = False
            err_info['email'] = "邮件地址不能为空"
        else:
            count = Users.objects.filter(email=email).count()
            if count > 0:
                success = False
                err_info['email'] = "邮件地址已经存在"
        # 校验手机号码
        if phone is not None and phone != "":
            count = Users.objects.filter(phone=phone).count()
            if count > 0:
                success = False
                err_info['phone'] = "手机号已存在"

        if self.user.rf == "open_wx":
            # 重置用户名、密码、邮箱、手机号
            # nick_name
            nick_name = request.POST.get("nick_name")
            if nick_name is None or nick_name == "":
                success = False
                err_info['name'] = "用户名不能为空"
            else:
                count = Users.objects.filter(nick_name=nick_name).count()
                if count > 0:
                    success = False
                    err_info['name'] = "用户名已经存在"
            # password
            if password is None or password == "":
                success = False
                err_info['password'] = "密码不能为空"

            password_repeat = request.POST.get("password_repeat")
            if password_repeat != password:
                success = False
                err_info['password'] = "两次输入的密码不一致"

            self.user.nick_name = nick_name
        else:
            # 根据用户名、密码重新设置邮箱,手机号
            if not self.user.check_password(password):
                success = False
                err_info['password'] = "密码错误"

        # 参数错误,返回原页面
        if not success:
            context = self.get_context()
            context['error'] = err_info.values()
            page = "www/account/wechatinfo.html"
            self.user.email = email
            context["user"] = self.user
            context["disable_nick_name"] = self.user.rf != "open_wx"
            return TemplateResponse(self.request, page, context)

        logger.debug("now update user...")
        self.user.email = email
        self.user.set_password(password)
        self.user.client_ip = get_client_ip(request)
        if self.user.rf == "open_wx":
            self.user.status = 3
        self.user.save()
        # 创建git用户
        codeRepositoriesService.createUser(self.user,
                                           email,
                                           password,
                                           self.user.nick_name,
                                           self.user.nick_name)
        # 获取next_url
        next_url = request.GET.get("next_url")
        if next_url:
            return self.redirect_to(next_url)
        return self.redirect_to("/")


class UnbindView(BaseView):
    """解绑微信"""
    def post(self, request, *args, **kwargs):
        success = True
        msg = "解绑成功"
        code = 200
        try:
            # 判断用户当前status
            if self.user.status == 1 or self.user.status == 0:
                # 记录user_id union_id关系
                num = WeChatUnBind.objects.filter(union_id=self.user.union_id,
                                                  user_id=self.user.pk).count()
                if num == 0:
                    count = WeChatUnBind.objects.filter(union_id=self.user.union_id).count()
                    WeChatUnBind.objects.create(user_id=self.user.pk,
                                                union_id=self.user.union_id,
                                                status=count)
                # 1:普通注册,绑定微信
                self.user.status = 0
                self.user.union_id = ''
                self.user.save()
            else:
                # 判断用户信息是否完善
                union_id = self.user.union_id
                if union_id is None or union_id == '':
                    self.user.status = 4  # 微信注册,解除绑定
                    self.user.union_id = ''
                    self.user.save()
                else:
                    if self.user.email is None or self.user.email == "":
                        success = False
                        msg = "解绑后无法微信登录系统,请先完善信息后在解绑微信"
                        # 页面接受需要跳转到信息完善页面
                        code = 201
                    else:
                        num = WeChatUnBind.objects.get(union_id=self.user.union_id,
                                                       user_id=self.user.pk).count()
                        if num == 0:
                            count = WeChatUnBind.objects.get(union_id=self.user.union_id).count()
                            WeChatUnBind.objects.create(user_id=self.user.pk,
                                                        union_id=self.user.union_id,
                                                        status=count)
                        self.user.status = 4  # 微信注册,解除绑定
                        self.user.union_id = ''
                        self.user.save()
        except Users.DoesNotExist:
            success = False
            msg = "用户不存在"
            code = 202
        except Exception as e:
            success = False
            msg = "解绑失败"
            code = 203
            logger.error("解除用户绑定失败!")
            logger.exception(e)
        # 返回数据
        status = 200 if success else 500
        data = {
            "success": success,
            "msg": msg,
            "code": code
        }
        return JsonResponse(status=status, data=data)


class BindView(BaseView):
    """绑定微信"""

    def get(self, request, *args, **kwargs):
        """正常注册用户绑定微信"""
        # 获取cookie中的corf
        csrftoken = request.COOKIES.get('csrftoken')
        if csrftoken is None:
            csrftoken = "csrf"
        user_id = str(self.user.pk)
        next_url = request.GET.get('next_url', "next_url")
        state = AuthCode.encode(','.join([csrftoken, user_id, next_url]), 'wechat')
        # 获取user对应的微信配置
        config = WECHAT_GOODRAIN
        oauth2 = 'https://open.weixin.qq.com/connect/oauth2/authorize'
        scope = 'snsapi_userinfo'
        redirect_url = settings.WECHAT_CALLBACK.get("console_bind_goodrain")
        if not is_weixin(request):
            config = WECHAT_USER
            oauth2 = 'https://open.weixin.qq.com/connect/qrconnect'
            scope = 'snsapi_login'
            redirect_url = settings.WECHAT_CALLBACK.get("console_bind")
        wechat_config = WeChatConfig.objects.get(config=config)
        app_id = wechat_config.app_id
        # 微信的回跳页面

        redirect_url = urllib.urlencode({"1": redirect_url})[2:]
        # 微信登录扫码路径
        url = "{0}?appid={1}" \
              "&redirect_uri={2}" \
              "&response_type=code" \
              "&scope={3}" \
              "&state={4}#wechat_redirect".format(oauth2,
                                                  app_id,
                                                  redirect_url,
                                                  scope,
                                                  state)
        return self.redirect_to(url)


class WeChatCallBackBind(BaseView):

    def get(self, request, *args, **kwargs):
        """正常注册用户绑定微信返回路径"""
        # 获取cookie中的csrf
        csrftoken = request.COOKIES.get('csrftoken')
        if csrftoken is None:
            csrftoken = "csrf"
        # 获取statue
        state = request.GET.get("state")
        # 解码
        oldcsrftoken, user_id, next_url = AuthCode.decode(str(state), 'wechat').split(',')
        # 判断是否微信浏览器
        if next_url == "next_url":
            next_url = "/"
        if csrftoken != oldcsrftoken:
            logger.error("csrftoken check error!")
            return self.redirect_to(next_url)
        # 获取的code
        code = request.GET.get("code")
        if code is None:
            logger.error("wechat donot return code! you do not permissioned!")
            return self.redirect_to(next_url)
        # 根据code获取access_token
        config = WECHAT_GOODRAIN
        if not is_weixin(request):
            config = WECHAT_USER
        wechat_config = WeChatConfig.objects.get(config=config)
        access_token, open_id = OpenWeChatAPI.access_token_oauth2_static(
            wechat_config.app_id,
            wechat_config.app_secret,
            code)
        if access_token is None:
            # 登录失败,重新跳转到授权页面
            logger.error("wechat oauth access token error!")
            return self.redirect_to(next_url)
        # 检查用户的open_id是否已经存在
        need_new = False
        wechat_user = None
        try:
            wechat_user = WeChatUser.objects.get(open_id=open_id)
        except WeChatUser.DoesNotExist:
            logger.warning("open_id is first to access console. now regist...")
            need_new = True
        # 添加wechatuser
        if need_new:
            jsondata = OpenWeChatAPI.query_userinfo_static(open_id, access_token)
            union_id = jsondata.get("unionid")
            begin_index = len(union_id) - 8
            tenant_name = union_id[begin_index:]
            WeChatUser(open_id=jsondata.get("openid"),
                                     nick_name=tenant_name,
                                     union_id=union_id,
                                     sex=jsondata.get("sex"),
                                     city=jsondata.get("city"),
                                     province=jsondata.get("province"),
                                     country=jsondata.get("country"),
                                     headimgurl=jsondata.get("headimgurl"),
                                     config=config).save()
        # 判断union_id是否已经绑定user

        # 根据微信的union_id判断用户是否已经注册
        try:
            old_user = Users.objects.get(union_id=wechat_user.union_id)
            num = WeChatUnBind.objects.filter(union_id=wechat_user.union_id,
                                              user_id=old_user.pk).count()
            if num == 0:
                count = WeChatUnBind.objects.filter(union_id=wechat_user.union_id).count()
                WeChatUnBind.objects.create(user_id=old_user.pk,
                                            union_id=wechat_user.union_id,
                                            status=count)
            old_user.union_id = ""
            old_user.save()
        except Exception as e:
            logger.exception(e)

        user = Users.objects.get(pk=user_id)
        if user.status == 0:
            user.status = 1
        elif user.status == 4:
            user.status = 3
        user.union_id = wechat_user.union_id
        user.save()

        return self.redirect_to(next_url)

