# -*- coding: utf8 -*-
import datetime
import time
import urllib
import hashlib
import requests
import xml.etree.ElementTree as ET
from django.template.response import TemplateResponse
from django.http import JsonResponse, HttpResponse
from django.http import Http404
from django.shortcuts import redirect
from django.conf import settings

from www.auth import authenticate, login
from www.models import *
from www.utils.crypt import AuthCode
from www.utils import sn
from www.services import enterprise_svc

from www.views import BaseView
from www.region import RegionInfo
from www.monitorservice.monitorhook import MonitorHook

from www.utils.md5Util import md5fun
from www.wechat.openapi import OpenWeChatAPI, MPWeChatAPI
from www.tenantservice.baseservice import CodeRepositoriesService
from www.forms.account import is_standard_word, is_sensitive, password_len, is_phone, is_email

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
    # 需要通知的事件订阅者
    REGISTER_LISTENER = [
        "{}/user/wechat/event/subscribe".format(settings.APP_SERVICE_API["url"])
    ]
    # 当前处理通知事件类型
    ALLOW_EVENT = ["subscribe", "SCAN"]

    def get(self, request, *args, **kwargs):
        signature = request.GET.get("signature", "")
        timestamp = request.GET.get("timestamp", "")
        nonce = request.GET.get("nonce", "")
        echostr = request.GET.get("echostr", "")
        logger.info("signature:" + signature)
        logger.info("timestamp:" + timestamp)
        logger.info("nonce:" + nonce)
        logger.info("echostr:" + echostr)

        config = WeChatConfig.objects.get(config=WECHAT_GOODRAIN)
        token = config.token
        wx_array = [token, timestamp, nonce]
        wx_array.sort()
        wx_string = ''.join(wx_array)
        wx_string = hashlib.sha1(wx_string).hexdigest()

        logger.info("signature:" + signature)
        logger.info("timestamp:" + timestamp)
        logger.info("nonce:" + nonce)
        logger.info("echostr:" + echostr)
        logger.info("token:" + token)
        logger.info("wx_string:" + wx_string)
        logger.info(signature == wx_string)
        if signature == wx_string:
            return HttpResponse(echostr)
        else:
            return HttpResponse("")

    def post(self, request, *args, **kwargs):
        """微信通知处理入口, 云帮不做处理只是转发请求给云市处理"""
        body_raw = request.body
        logger.debug("account.wechat", "recv wechat notify: {}".format(body_raw))
        # 将xml转成dict
        data = dict((child.tag, child.text) for child in ET.fromstring(body_raw))
        logger.debug("account.wechat", "format to map: {}".format(data))
        msg_type = data["MsgType"]
        # 非事件类消息不处理
        if msg_type != "event":
            return HttpResponse("")

        # 当前只处理公众号订阅跟扫码消息
        event_type = data["Event"]
        if event_type not in self.ALLOW_EVENT:
            return HttpResponse("")

        post_data = {}
        if event_type == "subscribe":
            # 只处理qrscene_xxxx类型的场景关注通知
            if "EventKey" not in data:
                return HttpResponse("")

            user_id = data["EventKey"].split("_")[1]
            open_id = data["FromUserName"]
            user_id, open_id = self.bind_wechat_user_to_goodrain(user_id, open_id)
            post_data = {
                "user_id": user_id,
                "open_id": open_id,
                "event_type": "subscribe"
            }
        elif event_type == "SCAN":
            user_id = data["EventKey"]
            open_id = data["FromUserName"]
            user_id, open_id = self.bind_wechat_user_to_goodrain(user_id, open_id)
            post_data = {
                "user_id": user_id,
                "open_id": open_id,
                "event_type": "scan"
            }

        # 不管上面绑定关系如何, 用户确实完成对公众号的关注,所以将事件推送到关注的监听者
        for url in self.REGISTER_LISTENER:
            try:
                body_encode = AuthCode.encode(json.dumps(post_data), "goodrain")
                logger.debug("account.wechat", "post {} with data {}".format(url, post_data))
                # 微信端5秒内需要返回
                requests.post(url, data={"body": body_encode}, timeout=4)
            except Exception as e:
                logger.exception("push event to market failed!", e)

        return HttpResponse("")

    def bind_wechat_user_to_goodrain(self, user_id, open_id):
        user = Users.objects.get(user_id=user_id)
        try:
            wechat_user = WeChatUser.objects.get(open_id=open_id, config="goodrain")
        except Exception:
            # 这里应该去获取微信用户基本信息
            mp_api = MPWeChatAPI()
            jsondata = mp_api.get_wechat_user_info(open_id)
            wechat_user = WeChatUser(open_id=jsondata.get("openid"),
                                     nick_name=jsondata.get("nickname"),
                                     union_id=jsondata.get("unionid"),
                                     sex=jsondata.get("sex"),
                                     city=jsondata.get("city"),
                                     province=jsondata.get("province"),
                                     country=jsondata.get("country"),
                                     headimgurl=jsondata.get("headimgurl"),
                                     config="goodrain").save()
            logger.info("account.wechat", "save new wechat user {} with union_id {}!".format(wechat_user.open_id,
                                                                                             wechat_user.union_id))
        if not user.union_id:
            user.union_id = wechat_user.union_id
            user.save()
            logger.info("account.wechat", "bind user {} to union_id {}!".format(user_id, wechat_user.union_id))
        else:
            # 用户已绑定过微信, 且绑定union_id与通知union_id不一致,以已绑定union_id对应的open_id为准
            if user.union_id != wechat_user.union_id:
                open_id = WeChatUser.objects.get(union_id=user.union_id, config="goodrain").open_id

        return user_id, open_id


class WeChatLogin(BaseView):
    """微信用户登录"""
    def get(self, request, *args, **kwargs):
        if not settings.MODULES["WeChat_Module"]:
            index_url = settings.WECHAT_CALLBACK.get("index")
            return self.redirect_to(index_url)
        # 获取cookie中的corf
        csrftoken = request.COOKIES.get('csrftoken')
        if csrftoken is None:
            csrftoken = "csrf"
        # 判断登录来源,默认从微信上登录
        origin = request.GET.get("origin", "console")
        origin_url = request.GET.get("redirect_url", "redirect_url")
        logger.debug("account.wechat", "origin_url=" + origin_url)
        next_url = request.GET.get("next", "")
        if origin == "discourse":
            sig = request.GET.get("sig")
            next_url = "{0}&sig={1}".format(next_url, sig)
        config = WECHAT_GOODRAIN
        oauth2 = 'https://open.weixin.qq.com/connect/oauth2/authorize'
        scope = 'snsapi_userinfo'
        # 判断是否微信浏览器
        if not is_weixin(request):
            config = WECHAT_USER
            oauth2 = 'https://open.weixin.qq.com/connect/qrconnect'
            scope = 'snsapi_login'
        state = AuthCode.encode(','.join([csrftoken, origin, next_url, config, origin_url]), 'we_chat_login')
        logger.debug("account.wechat", state)
        # 存储state
        wechat_state = WeChatState(state=state)
        wechat_state.save()

        # 获取user对应的微信配置
        config = WeChatConfig.objects.get(config=config)
        app_id = config.app_id
        # 扫码后微信的回跳页面
        redirect_url = settings.WECHAT_CALLBACK.get("console_goodrain")
        if not is_weixin(request):
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
                                                  wechat_state.ID)
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
        import datetime
        # 获取cookie中的csrf
        csrftoken = request.COOKIES.get('csrftoken')
        if csrftoken is None:
            csrftoken = "csrf"
        # 获取statue
        state = request.GET.get("state")
        # 解码toke, type
        logger.debug("account.wechat", state)
        logger.debug("account.wechat", "is_weixin:{0}".format(str(is_weixin(request))))
        # 查询数据库
        err_url = settings.WECHAT_CALLBACK.get("index")
        try:
            wechat_state = WeChatState.objects.get(pk=state)
        except Exception as e:
            logger.exception("account.wechat", e)
            logger.error("account.wechat", "wechatstate is missing,id={0}".format(state))
            return self.redirect_to(err_url)
        cry_state = wechat_state.state

        state_array = AuthCode.decode(str(cry_state), 'we_chat_login').split(',')
        oldcsrftoken = state_array[0]
        origin = state_array[1]
        next_url = state_array[2]
        config = state_array[3]
        origin_url = None
        if len(state_array) == 5:
            origin_url = state_array[4]
        logger.debug("account.wechat", oldcsrftoken)
        logger.debug("account.wechat", origin)
        logger.debug("account.wechat", next_url)
        logger.debug("account.wechat", config)
        logger.debug("account.wechat", origin_url)

        if csrftoken != oldcsrftoken:
            return self.redirect_to(err_url)
        # 获取的code
        code = request.GET.get("code")
        logger.info(code)
        if code is None:
            return self.redirect_to(err_url)
        # 根据code获取access_token
        wechat_config = WeChatConfig.objects.get(config=config)
        access_token, open_id = OpenWeChatAPI.access_token_oauth2_static(
            wechat_config.app_id,
            wechat_config.app_secret,
            code)
        logger.info(access_token)
        if access_token is None:
            # 登录失败,跳转到失败页面
            return self.redirect_to(err_url)
        # 检查用户的open_id是否已经存在
        need_new = False
        wechat_user = None
        try:
            wechat_user = WeChatUser.objects.get(open_id=open_id)
        except WeChatUser.DoesNotExist:
            logger.warning("account.wechat", "open_id is first to access console. now regist...")
            need_new = True

        # 添加wechatuser
        if need_new:
            jsondata = OpenWeChatAPI.query_userinfo_static(open_id, access_token)
            nick_name = jsondata.get("nickname")
            if nick_name:
                nick_name = nick_name.encode("utf-8")
            wechat_user = WeChatUser(open_id=jsondata.get("openid"),
                                     nick_name=nick_name,
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
            logger.warning("account.wechat", "union id is first to access console. now create user...")
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
            tmp_union_id = md5fun(union_id)
            begin_index = len(tmp_union_id) - 8
            tenant_name = tmp_union_id[begin_index:]
            tenant_name = tenant_name.replace("_", "-").lower()
            email = tenant_name + "@wechat.com"
            logger.debug("account.wechat", "new wx regist user.email:{0} tenant_name:{1}".format(email, tenant_name))
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
            region = RegionInfo.register_choices()[0][0]

            # add by tanm
            regions = [region]
            enterprise_svc.create_and_init_tenant(user.user_id, tenant_name, regions,user.enterprise_id)

            # create gitlab user
            if user.email is not None and user.email != "":
                codeRepositoriesService.createUser(user, email, password, nick_name, nick_name)
        logger.info(user)
        if user is None:
            logger.error("account.wechat", "微信用户登录失败!")
            return self.redirect_to(err_url)
        # 微信用户登录
        user = authenticate(union_id=user.union_id)
        login(request, user)
        self.user = request.user
         
        # 回跳到云市
        if next_url is not None \
                and next_url != "" \
                and next_url != "none" \
                and next_url != "None":
            if origin == "app":
                logger.debug("account.wechat", "now return to cloud market login..")
                if origin_url is None or origin_url == "redirect_url" or origin_url == "":
                    origin_url = settings.APP_SERVICE_API.get("url")
                if not origin_url.startswith("http://"):
                    origin_url = "http://" + origin_url
                # 返回参数
                payload = {
                    "nick_name": user.nick_name,
                    "user_id": str(user.user_id),
                    "next_url": next_url,
                    "action": "register" if need_new else "login"
                }
                if wechat_user is not None:
                    payload["wechat_name"] = wechat_user.nick_name
                ticket = AuthCode.encode(json.dumps(payload), "goodrain")
                next_url = "{0}/login/{1}/success?ticket={2}".format(origin_url,
                                                                     sn.instance.cloud_assistant,
                                                                     ticket)
                # next_url = settings.APP_SERVICE_API.get("url") + '/login/goodrain/success?ticket=' + ticket
                logger.debug("account.wechat", next_url)
            return redirect(next_url)

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
        if self.user.phone is None:
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
        try:
            is_email(email)
        except Exception:
            success = False
            err_info['email'] = "邮件地址不合法"
        # 校验手机号码
        if phone is not None and phone != "":
            count = Users.objects.filter(phone=phone).count()
            if count > 0:
                if self.user.phone == phone:
                    pass
                else:
                    success = False
                    err_info['phone'] = "手机号已存在"
            try:
                is_phone(phone)
            except Exception:
                success = False
                err_info['phone'] = "手机号码不合法"

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
            try:
                is_standard_word(nick_name)
                is_sensitive(nick_name)
            except Exception:
                success = False
                err_info['name'] = "用户名不能包含大写字母、中文和特殊字符"
            # password
            try:
                password_len(password)
            except Exception:
                success = False
                err_info['password'] = "密码长度至少8位"
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
        next_url = request.GET.get("next")
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
                # pc端注册用户解绑不添加解绑纪录,只修改用户状态
                # num = WeChatUnBind.objects.filter(union_id=self.user.union_id,
                #                                   user_id=self.user.pk).count()
                # if num == 0:
                #     count = WeChatUnBind.objects.filter(union_id=self.user.union_id).count()
                #     WeChatUnBind.objects.create(user_id=self.user.pk,
                #                                 union_id=self.user.union_id,
                #                                 status=count)
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
                        num = WeChatUnBind.objects.filter(union_id=self.user.union_id,
                                                          user_id=self.user.pk).count()
                        if num == 0:
                            count = WeChatUnBind.objects.filter(union_id=self.user.union_id).count()
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
        next_url = request.GET.get('next', "/")

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
        state = AuthCode.encode(','.join([csrftoken, user_id, next_url, config]), 'wechat')
        logger.debug("bind wechat, state:{0}".format(state))
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
        oldcsrftoken, user_id, next_url, config = AuthCode.decode(str(state), 'wechat').split(',')
        # 判断是否微信浏览器
        if csrftoken != oldcsrftoken:
            logger.error("csrftoken check error!")
            return self.redirect_to(next_url)
        # 获取的code
        code = request.GET.get("code")
        if code is None:
            logger.error("wechat donot return code! you do not permissioned!")
            return self.redirect_to(next_url)
        # 根据code获取access_token
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
            nick_name = jsondata.get("nickname")
            if nick_name:
                nick_name = nick_name.encode("utf-8")
            WeChatUser(open_id=jsondata.get("openid"),
                       nick_name=nick_name,
                       union_id=jsondata.get("unionid"),
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

