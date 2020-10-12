# -*- coding: utf8 -*-
import logging
import os
from functools import wraps

import market_client
from market_client.configuration import Configuration

import openapi_client as store_client
from console.exception.main import ServiceHandleException, StoreNoPermissionsError
from openapi_client.configuration import Configuration as storeConfiguration
from openapi_client.rest import ApiException

logger = logging.getLogger("default")


def get_default_market_client():
    configuration = Configuration()
    configuration.host = os.environ.get('APP_CLOUD_API', 'http://api.goodrain.com:80')
    # create an instance of the API class
    return market_client.AppsApi(market_client.ApiClient(configuration))


def get_market_client(access_key, host=None):
    configuration = storeConfiguration()
    configuration.client_side_validation = False
    configuration.host = host if host else os.environ.get('APP_CLOUD_API', 'http://api.goodrain.com:80')
    configuration.api_key['api_key'] = access_key
    return store_client.MarketOpenapiApi(store_client.ApiClient(configuration))


def apiException(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ApiException as e:
            if e.status == 401:
                raise ServiceHandleException(
                    msg="no store auth token", msg_show="缺少云应用市场token", status_code=401, error_code=10421)
            if e.status == 403:
                raise StoreNoPermissionsError(bean={"name": args[1].name})
            if e.status == 404:
                raise ServiceHandleException(msg=e.body, msg_show="资源不存在", status_code=404)
            if str(e.status)[0] == '4':
                raise ServiceHandleException(msg=e.body, msg_show="获取数据失败，参数错误", status_code=e.status)
            raise ServiceHandleException(msg=e.body, msg_show="请求失败，请检查网络和配置", status_code=400)
        except ValueError as e:
            logger.debug(e)
            raise ServiceHandleException(
                msg="store return data can`t be serializer", msg_show="应用市场返回数据序列化失败，请检查配置或参数是否正确", status_code=400)

    return wrapper
