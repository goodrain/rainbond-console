# coding: utf-8
"""
错误码约定的是业务逻辑，而 HTTP 状态码约定的是服务器的响应状态。

HTTP 状态码使用 rest_framework 已经定义好的常量
from rest_framework import status

错误码的定义：
    * 以英文大写字母加下划线的方式编码
    * 以对应的资源开头，例如：SERVICE_NOT_FOUND

"""
from __future__ import unicode_literals

# 数据中心错误码
REGION_NOT_FOUND = "REGION_NOT_FOUND"
