# -*- coding: utf8 -*-
import os
import market_client
from market_client.configuration import Configuration
import entsrv_client
from entsrv_client.configuration import Configuration as enter_Configuration


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


def get_enterprise_server_auth_client(home_url, token):
    configuration = enter_Configuration()
    configuration.host = home_url
    configuration.api_key['Authorization'] = token

    # create an instance of the API class
    return entsrv_client.AuthApi(entsrv_client.ApiClient(configuration))


def get_enterprise_server_ent_client(home_url, token):
    configuration = enter_Configuration()
    configuration.host = home_url
    configuration.api_key['Authorization'] = token

    # create an instance of the API class
    return entsrv_client.EnterpriseApi(entsrv_client.ApiClient(configuration))
