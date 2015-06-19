#coding=utf-8

# Note:
#     Alipay Config Class
#     基础配置

class Alipay_Config:
    def __init__(self):
        self.seller_email = ''          # 卖家的支付宝账户，E-mail
        self.partner = ''               # 合作身份者id，以2088开头的16位纯数字
        self.key = ''                   # 安全检验码，以数字和字母组成的32位字符

        self.sign_type = 'MD5'          # 签名方式
        self.input_charset = 'utf-8'    # 字符编码
        self.cacert = ''                # ca证书路径地址，用于curl中ssl校验
        self.transport = 'http'         # 访问模式,根据自己的服务器是否支持ssl访问，若支持请选择https；若不支持请选择http
