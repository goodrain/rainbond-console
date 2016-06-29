# -*- coding: utf8 -*-
import urllib
import hashlib
from django.template.response import TemplateResponse
from django.http import JsonResponse, HttpResponse
from django.http import Http404

from www.auth import authenticate, login
from www.models import WeChatConfig, WeChatUser, Users, PermRelTenant, Tenants, TenantRegionInfo
from www.utils.crypt import AuthCode

from www.views import BaseView, RegionOperateMixin
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

        logger.debug("signature:"+signature)
        logger.debug("timestamp:"+timestamp)
        logger.debug("nonce:"+nonce)
        logger.debug("echostr:"+echostr)
        logger.debug("token:"+token)
        logger.debug("wx_string:"+wx_string)
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
        # 获取cookie中的corf
        csrftoken = request.COOKIES.get('csrftoken')
        if csrftoken is None:
            csrftoken = "csrf"
        # 判断登录来源,默认从微信上登录
        tye = request.GET.get("type", "uu")
        state = AuthCode.encode(','.join([csrftoken, tye]), 'we_chat_login')
        logger.debug("here is encode:" + state)
        config = WECHAT_GOODRAIN
        oauth2 = 'https://open.weixin.qq.com/connect/oauth2/authorize'
        scope = 'snsapi_userinfo'
        if tye == 'wechat':
            config = WECHAT_USER
            oauth2 = 'https://open.weixin.qq.com/connect/qrconnect'
            scope = 'snsapi_login'

        # 获取user对应的微信配置
        config = WeChatConfig.objects.get(config=config)
        app_id = config.app_id
        # 扫码后微信的回跳页面
        redirect_url = "https://dev.goodrain.com/wechat/callback"
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
        return self.redirect_to("http://www.goodrain.com/product/")


class WeChatCallBack(BaseView, RegionOperateMixin):
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
        oldcsrftoken, tye = AuthCode.decode(str(state), 'we_chat_login').split(',')
        logger.debug(oldcsrftoken)
        logger.debug(tye)
        config = WECHAT_GOODRAIN
        err_url = "http://www.goodrain.com/product/"
        if tye == 'wechat':
            config = WECHAT_USER
            err_url = "http://www.goodrain.com/product/"

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
            begin_index = len(union_id)-8
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
        # 创建租户
        if need_new:
            union_id = wechat_user.union_id
            begin_index = len(union_id)-8
            tenant_name = union_id[begin_index:]
            email = tenant_name + "@wechat.com"
            logger.debug("new wx regist user.email:{0} tenant_name:{1}".format(email, tenant_name))
            # 创建用户,邮箱为openid后8位@wechat.comemail=email,
            user = Users(nick_name=tenant_name,
                         phone=0,
                         client_ip=get_client_ip(request),
                         rf="open_wx",
                         status=2,
                         union_id=union_id)
            user.set_password("wechat")
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
            init_result = self.init_for_region(tenant.region, tenant_name, tenant.tenant_id)
            monitorhook.tenantMonitor(tenant, user, "init_tenant", init_result)
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
            ticket = AuthCode.encode(','.join([user.nick_name, str(user.user_id)]), 'goodrain')
            url = 'http://app.goodrain.com/login/goodrain/success/?ticket=' + ticket
            return self.redirect_to(url)

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
        return TemplateResponse(self.request, page, context)

    def post(self, request, *args, **kwargs):
        # 获取用户信息
        user = Users.objects.get(pk=self.user.pk)
        user.email = request.POST.get("email")
        user.nick_name = request.POST.get("nick_name")
        user.phone = request.POST.get("phone")
        user.client_ip = get_client_ip(request)
        password = request.POST.get("password")
        password_repeat = request.POST.get("password_repeat")
        success = True
        err = {}
        # 校验
        try:
            Users.objects.get(email=user.email)
            success = False
            err['email'] = "邮件地址已经存在"
        except Users.DoesNotExist:
            pass

        try:
            Users.objects.get(nick_name=user.nick_name)
            success = False
            err['name'] = "用户名已经存在"
        except Users.DoesNotExist:
            pass

        if password_repeat != password:
            success = False
            err['password'] = "两次输入的密码不一致"

        if user.phone is not None and user.phone != "":
            phoneNumber = Users.objects.filter(phone=user.phone).count()
            logger.debug('form_valid.register', phoneNumber)
            if phoneNumber > 0:
                success = False
                err['phone'] = "手机号已存在"
        # 参数错误,返回原页面
        if not success:
            context = self.get_context()
            context['error'] = err.values()
            page = "www/account/wechatinfo.html"
            context["user"] = self.user
            logger.error(err)
            return TemplateResponse(self.request, page, context)

        logger.debug("now update user...")
        user.set_password(password)
        user.status = 3  # 微信注册,补充信息
        user.save()
        # 创建git用户
        codeRepositoriesService.createUser(user,
                                           user.email,
                                           password,
                                           user.nick_name,
                                           user.nick_name)
        return self.redirect_to("/")


class UnbindView(BaseView):
    """解绑微信"""
    def post(self, request, *args, **kwargs):
        success = True
        msg = "解绑成功"
        code = 200
        try:
            user = Users.objects.get(pk=self.user.pk)
            # 判断用户当前status
            if user.status == 1 or user.status == 0:
                # 1:普通注册,绑定微信
                user.status = 0
                user.union_id = ''
                user.save()
            else:
                # 判断用户信息是否完善
                union_id = user.union_id
                if union_id is None or union_id == '':
                    user.status = 4  # 微信注册,解除绑定
                    user.union_id = ''
                    user.save()
                else:
                    if user.email is None or user.email == "":
                        success = False
                        msg = "解绑后无法微信登录系统,请先完善信息后在解绑微信"
                        # 页面接受需要跳转到信息完善页面
                        code = 201
                    else:
                        user.status = 4  # 微信注册,解除绑定
                        user.union_id = ''
                        user.save()
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
        state = AuthCode.encode(','.join([csrftoken, user_id]), 'wechat')
        # 获取user对应的微信配置
        config = WeChatConfig.objects.get(config=WECHAT_USER)
        app_id = config.app_id
        # 扫码后微信的回跳页面
        redirect_url = "https://user.goodrain.com/wechat/callbackbind"
        redirect_url = urllib.urlencode({"1": redirect_url})[2:]
        # 微信登录扫码路径
        url = "https://open.weixin.qq.com/connect/qrconnect?appid={0}" \
              "&redirect_uri={1}" \
              "&response_type=code" \
              "&scope=snsapi_login" \
              "&state={2}#wechat_redirect".format(app_id, redirect_url, state)
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
        oldcsrftoken, user_id = AuthCode.decode(state, 'wechat').split(',')
        if csrftoken != oldcsrftoken:
            return JsonResponse(status=500)
        # 获取的code
        code = request.GET.get("code")
        if code is None:
            return JsonResponse(status=500)
        # 根据code获取access_token
        wechat_config = WeChatConfig.objects.get(config=WECHAT_GOODRAIN)
        access_token, open_id = OpenWeChatAPI.access_token_oauth2_static(
            wechat_config.app_id,
            wechat_config.app_secret,
            code)
        if access_token is None:
            # 登录失败,重新跳转到授权页面
            return JsonResponse(status=500)
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
            begin_index = len(union_id)-8
            tenant_name = union_id[begin_index:]
            wechat_user = WeChatUser(open_id=jsondata.get("openid"),
                                     nick_name=tenant_name,
                                     union_id=union_id,
                                     sex=jsondata.get("sex"),
                                     city=jsondata.get("city"),
                                     province=jsondata.get("province"),
                                     country=jsondata.get("country"),
                                     headimgurl=jsondata.get("headimgurl"),
                                     config=WECHAT_GOODRAIN)
            wechat_user.save()
        # 判断union_id是否已经绑定user
        Users.objects.filter(union_id=union_id).update(union_id="")
        # 根据微信的union_id判断用户是否已经注册
        user = Users.objects.get(pk=user_id)
        if user.status == 0:
            user.status = 1
        elif user.status == 4:
            user.status = 3
        user.union_id = wechat_user.union_id
        user.save()

        return JsonResponse(status=200)

