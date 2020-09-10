# -*- coding: utf8 -*-


def general_message(code, msg, msg_show, bean=None, list=None, *args, **kwargs):
    """生成响应信息"""
    return {"code": code, "msg": msg, "msg_show": msg_show, "data": dict(bean=bean or {}, list=list or [], **kwargs)}


def general_data(bean=None, list=None, *args, **kwargs):
    """生成响应信息"""
    return {"data": dict(bean=bean or {}, list=list or [], **kwargs)}


def error_message(en_msg=None):
    if not en_msg:
        return general_message(500, "system error", "系统异常")
    else:
        return general_message(500, en_msg, "系统异常")


def oldResultSuitGeneralMessage(result, msgEN, data):
    if type(data) is list:
        return general_message(code=result["code"], msg=msgEN, msg_show=result["msg"], list=data)
    else:
        return general_message(code=result["code"], msg=msgEN, msg_show=result["msg"], bean=data)
