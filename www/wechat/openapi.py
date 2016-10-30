# -*- coding: utf8 -*-

import time
import logging
import requests
import json

from django.conf import settings
from www.models.main import WeChatConfig, WeChatUser

logger = logging.getLogger('default')


class OpenWeChatAPI(object):
    """user.goodrain.com对应的开放平台API"""
    def __init__(self, config, *args, **kwargs):
        if settings.MODULES["WeChat_Module"]:
            logger.debug("OpenWeChatAPI", "now init wechat config.config is " + config)
            self.config = WeChatConfig.objects.get(config=config)

    def __save_to_db(self, access_token, refresh_token, access_token_expires_at):
        if not settings.MODULES["WeChat_Module"]:
            return
        self.config.access_token = access_token
        self.config.access_token_expires_at = access_token_expires_at
        self.config.refresh_token = refresh_token
        self.config.save()

    @property
    def access_token(self):
        # 从当前内存中读取
        if not settings.MODULES["WeChat_Module"]:
            return None
        now = time.time()
        access_token = self.config.access_token
        access_token_expires_at = self.config.access_token_expires_at
        if access_token:
            if access_token_expires_at - now > 60:
                return access_token
        return None

    def access_token_refresh(self):
        """ 根据fresh_token刷新token, 返回None需要跳转到授权页面进行重新授权 """
        # 查询oauth2接口
        if not settings.MODULES["WeChat_Module"]:
            return None, None
        payload = {'grant_type': 'refresh_token',
                   'appid': self.config.app_id,
                   'refresh_token': self.config.refresh_token}
        url = "https://api.weixin.qq.com/sns/oauth2/refresh_token"
        res = requests.get(url, params=payload)
        if res.status_code == 200:
            try:
                now = int(time.time())
                jd = res.json()
                access_token = jd.get("access_token")
                access_token_expires_at = now + jd.get("expires_in")
                refresh_token = jd.get("refresh_token")
                self.__save_to_db(access_token, refresh_token, access_token_expires_at)
                return access_token, jd.openid
            except Exception as e:
                logger.exception("wechatapi", e)
                logger.error("wechatapi", "save data error. res: " + res.content)
        else:
            logger.error("wechatapi", "refresh access_token failed. result:" + res.content)
        return None, None

    def access_token_oauth2(self, code):
        if not settings.MODULES["WeChat_Module"]:
            return None, None
        payload = {'grant_type': 'authorization_code',
                   'appid': self.config.app_id,
                   'secret': self.config.app_secret,
                   'code': code}
        url = "https://api.weixin.qq.com/sns/oauth2/access_token"
        res = requests.get(url, params=payload)
        if res.status_code == 200:
            try:
                now = int(time.time())
                jd = res.json()
                access_token = jd.get("access_token")
                access_token_expires_at = now + jd.get("expires_in")
                refresh_token = jd.get("refresh_token")
                self.__save_to_db(access_token, refresh_token, access_token_expires_at)
                return access_token, jd.get("openid")
            except Exception as e:
                logger.exception("wechatapi", e)
                logger.error("wechatapi", "save data error. res: " + res.content)
        else:
            logger.error("wechatapi", "query access_token failed. result:" + res.content)
        return None, None

    def access_token_check(self, open_id, access_token=None):
        """检查token是否有效"""
        if not settings.MODULES["WeChat_Module"]:
            return False
        payload = {'access_token': access_token or self.config.access_token,
                   'openid': open_id}
        url = "https://api.weixin.qq.com/sns/auth"
        res = requests.get(url, params=payload)
        if res.status_code == 200:
            try:
                jd = res.json()
                errcode = jd.get("errcode")
                if errcode == 0:
                    return True
            except Exception as e:
                logger.exception("wechatapi", e)
                logger.error("wechatapi", "object json failed! res: " + res.content)
        else:
            logger.error("wechatapi", "query access_token failed. result:" + res.content)
        return False

    def query_userinfo(self, open_id, access_token=None):
        if not settings.MODULES["WeChat_Module"]:
            return None
        """snsapi_userinfo"""
        payload = {'access_token': access_token or self.config.access_token,
                   'openid': open_id}
        url = "https://api.weixin.qq.com/sns/userinfo"
        res = requests.get(url, params=payload)
        if res.status_code == 200:
            try:
                jd = res.json()
                wechat_user = WeChatUser(open_id=jd.get("openid"),
                                         nick_name=jd.get("nickname"),
                                         union_id=jd.get("unionid"),
                                         sex=jd.get("sex"),
                                         city=jd.get("city"),
                                         province=jd.get("province"),
                                         country=jd.get("country"),
                                         headimgurl=jd.get("headimgurl"),
                                         config=self.config.config)
                wechat_user.save()
                return wechat_user
            except Exception as e:
                logger.exception("wechatapi", e)
                logger.error("wechatapi", "object json failed! res: " + res.content)
        else:
            return None

    @staticmethod
    def access_token_oauth2_static(app_id, app_secret, code):
        if not settings.MODULES["WeChat_Module"]:
            return None, None
        payload = {'grant_type': 'authorization_code',
                   'appid': app_id,
                   'secret': app_secret,
                   'code': code}
        url = "https://api.weixin.qq.com/sns/oauth2/access_token"
        res = requests.get(url, params=payload)
        if res.status_code == 200:
            try:
                jd = res.json()
                return jd.get("access_token"), jd.get("openid")
            except Exception as e:
                logger.exception("wechatapi", e)
                logger.error("wechatapi", "save data error. res: " + res.content)
        else:
            logger.error("wechatapi", "query access_token failed. result:" + res.content)
        return None, None

    @staticmethod
    def query_userinfo_static(open_id, access_token):
        if not settings.MODULES["WeChat_Module"]:
            return None
        payload = {'access_token': access_token,
                   'openid': open_id}
        url = "https://api.weixin.qq.com/sns/userinfo"
        res = requests.get(url, params=payload)
        res.encoding = "utf-8"
        if res.status_code == 200:
            try:
                return res.json()
            except Exception as e:
                logger.exception("wechatapi", e)
                logger.error("wechatapi", "object json failed! res: " + res.content)
        else:
            return None


class MPWeChatAPI(object):
    """好雨云公众平台账号API"""

    def __init__(self, *args, **kwargs):
        if settings.MODULES["WeChat_Module"]:
            logger.debug("wechatapi", "now init public wechat config.")
            self.config = WeChatConfig.objects.get(config="goodrain")

    def __save_to_db(self, access_token, access_token_expires_at):
        if not settings.MODULES["WeChat_Module"]:
            return

        self.config.access_token = access_token
        self.config.access_token_expires_at = access_token_expires_at
        self.config.save()

    def get_access_token(self):
        if not settings.MODULES["WeChat_Module"]:
            return None

        now = int(time.time())
        logger.debug("wechatapi",
                     "{} - {} = {}".format(self.config.access_token_expires_at, now, self.config.access_token_expires_at - now))
        if self.config.access_token_expires_at - now > 60:
            logger.info("wechatapi", "access_token available use cache: {}.".format(self.config.access_token))
            return self.config.access_token
        else:
            access_token, expires_in = self.__get_access_token_direct()
            self.__save_to_db(access_token, now + expires_in)
            logger.info("wechatapi", "access_token will expire require new: {}.".format(self.config.access_token))
            return access_token

    def __get_access_token_direct(self):
        if not settings.MODULES["WeChat_Module"]:
            return None

        _ACCESS_URL = "https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={0}&secret={1}"
        data = requests.get(_ACCESS_URL.format(self.config.app_id, self.config.app_secret))
        json_data = json.loads(data.content)

        return json_data.get("access_token"), json_data.get("expires_in")

    def get_wechat_user_info(self, openid, lang="zh_CN"):
        """获取用户基本信息"""
        if not settings.MODULES["WeChat_Module"]:
            return None

        _USER_URL = "https://api.weixin.qq.com/cgi-bin/user/info?access_token={0}&openid={1}&lang={2}"
        access_token = self.get_access_token()
        data = requests.get(_USER_URL.format(access_token, openid, lang))

        return json.loads(data.content)
