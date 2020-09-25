# coding: utf-8
"""统一响应"""
from rest_framework.response import Response


class MessageResponse(Response):
    """统一响应"""
    def __init__(self, msg, msg_show=None, status_code=200, error_code=None, bean=None, list=None, **kwargs):
        """
        :param msg: 响应信息(中文)
        :param msg_show: 响应信息(英文)
        :param status_code: http 状态码
        :param error_code: 业务状态码
        :param bean: 对象信息
        :param list: 列表信息
        :param kwargs:
        """
        response_key = {"template_name", "headers", "exception", "content_type"}
        body_kwargs = {k: v for k, v in kwargs.items() if k not in response_key}
        response_kwargs = {k: v for k, v in kwargs.items() if k in response_key}
        body = {
            "code": error_code or status_code,
            "msg": msg,
            "msg_show": msg_show or msg,
            "data": dict(bean=bean or {}, list=list or [], **body_kwargs)
        }
        super(MessageResponse, self).__init__(data=body, status=status_code, **response_kwargs)
