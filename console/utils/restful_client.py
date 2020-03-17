# -*- coding: utf8 -*-
import os
import market_client
from market_client.configuration import Configuration
import entsrv_client
from entsrv_client.configuration import Configuration as enter_Configuration

ENTERPRISE_SERVER_API = "http://8080.gr7030d7.2c9v614j.17f4cc.grapps.cn"


def get_market_client(enterpriseID, enterpriseToken, host=None):
    configuration = Configuration()
    configuration.host = host if host else os.environ.get('APP_CLOUD_API', 'http://api.goodrain.com:80')
    configuration.api_key['X_ENTERPRISE_TOKEN'] = enterpriseToken
    configuration.api_key['X_ENTERPRISE_ID'] = enterpriseID
    # create an instance of the API class
    return market_client.AppsApi(market_client.ApiClient(configuration))


def get_default_market_client():
    configuration = Configuration()
    configuration.host = os.environ.get('APP_CLOUD_API', 'http://api.goodrain.com:80')
    # create an instance of the API class
    return market_client.AppsApi(market_client.ApiClient(configuration)).get_app_version()


def get_enterprise_server_client(token, host=None):
    configuration = enter_Configuration()
    configuration.host = host if host else os.environ.get(
        'ENTERPRISE_SERVER_API', 'http://8080.gr7030d7.2c9v614j.17f4cc.grapps.cn')
    configuration.api_key['Connection'] = "close"
    configuration.api_key['Authorization'] = token

    # create an instance of the API class
    return entsrv_client.AuthApi(entsrv_client.ApiClient(configuration))
