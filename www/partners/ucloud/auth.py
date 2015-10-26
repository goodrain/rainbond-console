import hashlib
import urlparse
import urllib


def _verfy_ac(secret_key, params):
    items = params.items()
    # 请求参数串
    items.sort()
    # 将参数串排序
    params_data = ""
    for key, value in items:
        params_data = params_data + str(key) + str(value)
    params_data = params_data + secret_key
    sign = hashlib.sha1()
    sign.update(params_data)
    signature = sign.hexdigest()
    return signature
    # 生成的Signature值
