# -*- coding: utf8 -*-
import hashlib
import urllib


def verfy_ac(secret_key, params):
    keys = params.keys()
    # 请求参数串
    keys.sort()
    # 将参数串排序
    params_data = ""
    pairs = []
    for key in keys:
        value = str(params[key])
        params_data = params_data + str(key) + value
        pairs.append(urllib.quote(key) + '=' + urllib.quote(value))
    params_data = params_data + secret_key
    sign = hashlib.sha1()
    sign.update(params_data)
    signature = sign.hexdigest()
    qs = '&'.join(pairs)
    return qs, signature
