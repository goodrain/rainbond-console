#coding=utf-8

from alipay_config import *
from alipay_core import *
from alipay_md5 import *

class AlipaySubmit:
    # 支付宝网关地址（新）
    alipay_gateway_new = 'https://mapi.alipay.com/gateway.do?'

    def __init__(self):
        alipay_config = Alipay_Config()

        self.seller_email = alipay_config.seller_email
        self.partner = alipay_config.partner
        self.key = alipay_config.key
        self.sign_type = alipay_config.sign_type
        self.input_charset = alipay_config.input_charset
        self.cacert = alipay_config.cacert
        self.transport = alipay_config.transport

    def buildRequestMysign(self, para_sort):  # 生成签名结果, para_sort 已排序要签名的数组
        prestr = createLinkstring(para_sort)
        mysign = ''
        if self.sign_type == 'MD5':
            mysign = md5Sign(prestr, self.key)
        return mysign

    def buildRequestPara(self, para_temp):  # 生成要请求给支付宝的参数数组, para_temp 请求前的参数数组
        para_filter = paraFilter(para_temp)
        para_sort = argSort(para_filter)
        mysign = self.buildRequestMysign(para_sort)

        para_sort['sign'] = mysign
        para_sort['sign_type'] = self.sign_type
        return para_sort

    def buildRequestParaToString(self, para_temp):  # 生成要请求给支付宝的参数数组
        para = self.buildRequestPara(para_temp)

        # 把参数组中所有元素，按照“参数=参数值”的模式用“&”字符拼接成字符串，并对字符串做urlencode编码
        request_data = createLinkstringUrlencode(para)
        return request_data

    # 建立请求，以表单HTML形式构造（默认）
    # method 提交方式。两个值可选：post、get
    # button_name 确认按钮显示文字
    def buildRequestForm(self, para_temp, method, button_name):
        para = self.buildRequestPara(para_temp)
        sHtml = "<form id='alipaysubmit' name='alipaysubmit' action='" + AlipaySubmit.alipay_gateway_new + \
                "_input_charset=" + self.input_charset + "' method='" + method + "'>"
        keys = para.keys()
        keys.sort()
        for key in keys:
            sHtml = sHtml + "<input type='hidden' name='" + key + "' value='" + para[key] + "'/>"

        # //submit按钮控件请不要含有name属性
        sHtml = sHtml + "<input type='submit' value='" + button_name + "'></form>"
        sHtml = sHtml + "<script>document.forms['alipaysubmit'].submit();</script>"
        return sHtml

    def buildRequestHttp(self, para_temp):  # 建立请求，以模拟远程HTTP的POST请求方式构造并获取支付宝的处理结果
        sResult = ''
        request_data = self.buildRequestPara(para_temp)

        sResult = getHttpResponsePOST(AlipaySubmit.alipay_gateway_new, self.cacert, request_data, self.input_charset)
        return sResult

    # 建立请求，以模拟远程HTTP的POST请求方式构造并获取支付宝的处理结果，带文件上传功能
    def buildRequestHttpInFile(self, para_temp, file_para_name, file_name):
        para = self.buildRequestPara(para_temp)
        para[file_para_name] = "@" + file_name
        sResult = getHttpResponsePOST(AlipaySubmit.alipay_gateway_new, self.cacert, para, self.input_charset)
        return sResult
