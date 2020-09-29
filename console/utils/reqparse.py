# coding: utf-8
"""请求参数解析"""
from enum import Enum

from console.exception.main import AbortRequest


def parse_argument(request, key, default=None, value_type=str, required=False, error=''):
    """解析请求参数

    :param request: django request 对象
    :param key: 想要获取的请求参数名
    :param default: 如果 get 不到数据返回的默认值
    :param value_type: 获取到请求参数后转换的类型，支持 int, str, list
                 如果为 list 返回参数名为key的请求参数列表，列表内对象为 str
    :param required: 如果为 True，获取必填对象，获取不到返回400
    :param error: 如果是必填参数，get不到时返回的错误信息
    :return: key's value
    """
    if value_type not in (bool, int, str, list):
        raise TypeError("value_type not in (bool, int, str, list)")

    if default and not isinstance(default, value_type):
        raise TypeError("{} isn't {}".format(default, value_type))

    if value_type is bool:
        value_type = bool_argument

    get = request.GET

    value = get.getlist(key, default=default) if value_type is list else get.get(key, default=default)
    if required and (value is None or value == []):
        raise AbortRequest(error)
    return (value or None) if value_type is list else (None if value is None else value_type(value))


def parse_args(request, argument_tuple):
    """ 解析多个 request.GET 请求参数

    :type request: rest_framework.request.Request
    :param tuple[dict] argument_tuple: 解析参数组成的元组
    :rtype: dict
    """
    return {
        argument['key']: parse_argument(request, **argument)
        for argument in argument_tuple if parse_argument(request, **argument) is not None
    }


def parse_item(request, key, default=None, required=False, error=''):
    """ 解析某一个data参数
    :type request: rest_framework.request.Request
    """

    data = {}
    if isinstance(request, dict):
        data = request
    else:
        data = request.data

    value = data.get(key, default)
    if required and value is None:
        if error == '':
            error = "the filed '{}' is required".format(key)
        raise AbortRequest(error)
    return value


def parse_date(request, argument_tuple):
    """ 解析 request date

    :type request: rest_framework.request.Request
    :param tuple[dict] argument_tuple: 解析参数组成的元组
    :rtype: dict
    """

    return {
        argument['key']: parse_item(request, **argument)
        for argument in argument_tuple if parse_item(request, **argument) is not None
    }


class Bool(Enum):
    """bool"""
    true = True
    false = False


def bool_argument(value):
    """
    :type value: str or bool
    :param value: value in {'true', 'false'} or value is bool type
    :rtype: bool
    """
    try:
        return Bool[value].value
    except KeyError:
        if isinstance(value, bool):
            return value
        else:
            raise AbortRequest(msg="{} not in ('true', 'false')".format(value))
