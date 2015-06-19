#coding=utf-8

# Note:
#     alipay core funcs

from urllib import quote
import os
import httplib

def createLinkstring(para):  # 把数组所有元素，按照“参数=参数值”的模式用“&”字符拼接成字符串
    arg = ''
    data = []
    keys = para.keys()
    keys.sort()
    for key in keys:
        tmp_str = key + '=' + para[key]
        data.append(tmp_str)

    arg = '&'.join(data)
    return arg

def createLinkstringUrlencode(para): # 把数组所有元素，按照“参数=参数值”的模式用“&”字符拼接成字符串，并对字符串做urlencode编码
    arg = ''
    data = []
    keys = para.keys()
    keys.sort()
    for key in keys:
        tmp_str = key + '=' + quote(para[key])
        data.append(tmp_str)

    arg = '&'.join(data)
    return arg

def paraFilter(para):  # 除去数组中的空值和签名参数
    para_filter = {}
    keys = para.keys()
    keys.sort()
    for key in keys:
        if key == 'sign' or key == 'sign_type' or para[key] == '':
            continue
        else:
            para_filter[key] = para[key]
    return para_filter

def argSort(para):  # 对数组排序
    data = {}
    keys = para.keys()
    keys.sort()
    for key in keys:
        data[key] = para[key]
    return data

def logResult(msg):  # 写日志，方便测试（看网站需求，也可以改成把记录存入数据库）
    pass

def getHttpResponsePOST(url, cacert_url, para, input_charset):  # 远程获取数据，POST模式
    alipay_gateway_new = 'https://mapi.alipay.com'

    input_charset = input_charset.strip()
    url = url + '_input_charset=' + input_charset

    responseText = ''
    conn = httplib.HTTPConnection(alipay_gateway_new, cert_file=cacert_url)
    conn.request('POST', url, para)
    res = conn.getresponse()
    responseText = res.read()
    conn.close()

    return responseText


def getHttpResponseGET(url, cacert_url):
    alipay_gateway_new = 'https://mapi.alipay.com'

    responseText = ''
    conn = httplib.HTTPConnection(alipay_gateway_new, cert_file=cacert_url)
    conn.request('GET', url)
    res = conn.getresponse()
    responseText = res.read()
    conn.close()

    return responseText
