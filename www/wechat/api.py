# -*- coding: utf8 -*-

from wechat_sdk import WechatConf
from wechat_sdk import WechatBasic
from wechat_sdk.exceptions import ParseError

from ..models import WeChatConfig

import logging
logger = logging.getLogger("default")


GOODRAIN_WECHAT = "wechat"


def get_access_token_function():
    try:
        at = WeChatConfig.objects.get(config=GOODRAIN_WECHAT)  # 好雨的微信公众号
        return at.access_token, at.access_token_expires_at
    except WeChatConfig.DoesNotExist:
        # 调用wechat接口获取access_token
        return None, 0


def set_access_token_function(access_token, access_token_expires_at):
    # 此处通过你自己的方式设置 access_token
    try:
        at = WeChatConfig.objects.get(config=GOODRAIN_WECHAT)
        at.access_token = access_token
        at.access_token_expires_at = access_token_expires_at
        at.save()
    except WeChatConfig.DoesNotExist:
        logger.error("WeChatAPI", "config is not exists!")


class WeChatAPI:
    """公众平台API"""

    def __init__(self, config):
        self.config = WeChatConfig.objects.get(config=config)
        self.conf = WechatConf(
            token=self.config.token,
            appid=self.config.app_id,
            appsecret=self.config.app_secret,
            # 可选项：normal/compatible/safe，分别对应于 明文/兼容/安全 模式
            encrypt_mode=self.config.encrypt_mode,
            # 如果传入此值则必须保证同时传入 token, appid
            encoding_aes_key=self.config.encoding_aes_key,
            # access_token=access_token,
            # access_token_expires_at=access_token_expires_at,
            access_token_getfunc=get_access_token_function,
            access_token_setfunc=set_access_token_function,
        )
        # 初始化实例
        self.wechat = WechatBasic(conf=self.conf)

    def check_signature(self, signature, timestamp, nonce):
        try:
            return self.wechat.check_signature(signature, timestamp, nonce)
        except Exception as e:
            logger.error("wechat", "check signature error!")
            logger.exception("wechat", e)
        return False

    def parse_xml(self, body):
        try:
            self.wechat.parse_data(body)
            return self.wechat.get_message()
        except ParseError as e:
            logger.error("wechat", "parse xml error!")
            logger.exception("wechat", e)
        return None



