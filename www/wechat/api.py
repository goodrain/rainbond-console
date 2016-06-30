# # -*- coding: utf8 -*-
#
# from django.conf import settings
#
# from wechat_sdk import WechatConf
# from wechat_sdk import WechatBasic
# from wechat_sdk.exceptions import ParseError
#
# from www.models import WeChatConfig
#
# import logging
# logger = logging.getLogger("default")
#
#
# class WeChatAPI:
#     """公众平台API"""
#
#     def __init__(self, config, get_function, set_function):
#         if settings.WECHAT_ENABLE:
#             logger.debug("wechat enable.. now init wechat api")
#             self.config = WeChatConfig.objects.get(config=config)
#             self.conf = WechatConf(
#                 token=self.config.token,
#                 appid=self.config.app_id,
#                 appsecret=self.config.app_secret,
#                 # 可选项：normal/compatible/safe，分别对应于 明文/兼容/安全 模式
#                 encrypt_mode=self.config.encrypt_mode,
#                 # 如果传入此值则必须保证同时传入 token, appid
#                 encoding_aes_key=self.config.encoding_aes_key,
#                 # access_token=access_token,
#                 # access_token_expires_at=access_token_expires_at,
#                 access_token_getfunc=get_function,
#                 access_token_setfunc=set_function,
#             )
#             # 初始化实例
#             self.wechat = WechatBasic(conf=self.conf)
#
#     def check_signature(self, signature, timestamp, nonce):
#         try:
#             return self.wechat.check_signature(signature, timestamp, nonce)
#         except Exception as e:
#             logger.error("wechat", "check signature error!")
#             logger.exception("wechat", e)
#         return False
#
#     def parse_xml(self, body):
#         try:
#             self.wechat.parse_data(body)
#             return self.wechat.get_message()
#         except ParseError as e:
#             logger.error("wechat", "parse xml error!")
#             logger.exception("wechat", e)
#         return None
#
#
#
