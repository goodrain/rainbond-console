# coding=utf-8

# Note:
#     支付宝 API

from alipay_config import *
from alipay_submit import *
from alipay_notify import *


class Alipay_API(object):
    payment_type = "1"          # 支付类型
    return_url = "https://user.goodrain.com/apps/{0}/recharge/alipay-return"      # 页面跳转同步通知页面路径
    notify_url = "https://user.goodrain.com/apps/{0}/recharge/alipay-notify"      # 服务器异步通知页面路径
    seller_email = ''                                    # 卖家支付宝帐户
    anti_phishing_key = ""      # 防钓鱼时间戳
    exter_invoke_ip = ""        # 客户端的IP地址
    alipay_config = ''

    def __init__(self):
        alipay_config = Alipay_Config()

        self.seller_email = alipay_config.seller_email
        self.partner = alipay_config.partner
        self.key = alipay_config.key
        self.sign_type = alipay_config.sign_type
        self.input_charset = alipay_config.input_charset
        self.cacert = alipay_config.cacert
        self.transport = alipay_config.transport

    # out_trade_no: 商户订单号, 商户网站订单系统中唯一订单号，必填
    # subject: 订单名称
    # total_fee: 付款金额
    # body: 订单描述
    # show_url: 商品展示地址, 需以http://开头的完整路径
    def alipay_submit(self, paymethod, tenantName, out_trade_no, subject, total_fee, body, show_url):
        parameter = {
            'service': "create_direct_pay_by_user",
            'partner': self.partner,
            'payment_type': Alipay_API.payment_type,
            'notify_url': Alipay_API.notify_url.format(tenantName),
            'return_url': Alipay_API.return_url.format(tenantName),
            'seller_email': self.seller_email,
            'out_trade_no': out_trade_no,
            'subject': subject,
            'total_fee': total_fee,
            'body': body,
            'show_url': show_url,
            'anti_phishing_key': Alipay_API.anti_phishing_key,
            'exter_invoke_ip': Alipay_API.exter_invoke_ip,
            '_input_charset': self.input_charset,
        }
        if paymethod != "zhifubao":
            parameter["paymethod"] = "bankPay"
            parameter['defaultbank'] = paymethod
        submit = AlipaySubmit()
        html_text = submit.buildRequestForm(parameter, 'get', '确定')
        return html_text

    def get_notify(self):
        notify = AlipayNotify()
        return notify.verifyReturn()   # True/False
