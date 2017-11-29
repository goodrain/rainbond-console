# -*- coding: utf8 -*-


def generate_result(code, msg, msg_show, bean={}, list=[], *args, **kwargs):
    result = {}
    data = {}
    result["code"] = code
    result["msg"] = msg
    result["msg_show"] = msg_show
    data["bean"] = bean
    data["list"] = list
    data.update(kwargs)
    result["data"] = data
    return result


def generate_error_result():
    return generate_result("9999", "system error", "系统异常")
