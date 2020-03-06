# -*- coding: utf8 -*-
import os
import market_client
from market_client.configuration import Configuration


def get_market_client(enterpriseID, enterpriseToken, host=None):
    configuration = Configuration()
    configuration.host = host if host else os.environ.get('APP_CLOUD_API', 'http://9000.gr054bca.23ehgni5.0196bd.grapps.cn')
    configuration.api_key['X_ENTERPRISE_TOKEN'] = enterpriseToken
    configuration.api_key['X_ENTERPRISE_ID'] = enterpriseID
    # create an instance of the API class
    return market_client.AppsApi(market_client.ApiClient(configuration))


def get_default_market_client():
    configuration = Configuration()
    configuration.host = os.environ.get('APP_CLOUD_API', 'http://9000.gr054bca.23ehgni5.0196bd.grapps.cn')
    # create an instance of the API class
    return market_client.AppsApi(market_client.ApiClient(configuration))
