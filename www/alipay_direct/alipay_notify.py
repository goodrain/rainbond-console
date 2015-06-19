#coding=utf-8

# Note:
#     支付宝通知处理

from alipay_config import *
from alipay_core import *
from alipay_md5 import *

import urllib2

class AlipayNotify:
    https_verify_url = 'https://mapi.alipay.com/gateway.do?service=notify_verify&'
    http_verify_url = 'http://notify.alipay.com/trade/notify_query.do?'

    def __init__(self):
        alipay_config = Alipay_Config()
        self.seller_email = alipay_config.seller_email
        self.partner = alipay_config.partner
        self.key = alipay_config.key
        self.sign_type = alipay_config.sign_type
        self.input_charset = alipay_config.input_charset
        self.cacert = alipay_config.cacert
        self.transport = alipay_config.transport


    def verifyNotify(self, post_arr):  # 针对notify_url验证消息是否是支付宝发出的合法消息
        if not post_arr:
            return False

        isSgin = getSignVeryfy(post_arr, post_arr['sign'])
        responseTxt = 'true'
        if post_arr['notify_id']:
            responseTxt = getResponse(post_arr['notify_id'])
        if responseTxt == 'true' and isSgin:
            return True
        return False


    def verifyReturn(self, get_arr):  # 针对return_url验证消息是否是支付宝发出的合法消息
        if not get_arr:
            return False

        isSgin = getSignVeryfy(get_arr, get_arr['sign'])
        responseTxt = 'true'
        if get_arr['notify_id']:
            responseTxt = getResponse(get_arr['notify_id'])
        if responseTxt == 'true' and isSgin:
            return True
        return False


    def getSignVeryfy(self, para_temp, sign):  # 获取返回时的签名验证结果
        para_filter = paraFilter(para_temp)
        para_sort = argSort(para_filter)
        prestr = createLinkstring(para_sort)

        isSgin = False
        if self.sign_type.upper() == 'MD5':
            isSgin = md5Verify(prestr, sign, self.key)
        return isSgin


    def getResponse(self, notify_id):       # 获取远程服务器ATN结果,验证返回URL
        transport = self.transport.lower()
        partner = self.partner.strip()
        veryfy_url = ''

        if transport == 'https':
            veryfy_url = AlipayNotify.https_verify_url
        else:
            veryfy_url = AlipayNotify.http_verify_url

        veryfy_url = veryfy_url + 'partner=' + partner + '&notify_id=' + notify_id
        responseTxt = getHttpResponseGET(veryfy_url, self.cacert)
        return responseTxt
