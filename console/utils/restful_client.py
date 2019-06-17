# -*- coding: utf8 -*-
import os
import swagger_client
from swagger_client.configuration import Configuration

configuration = Configuration()
configuration.host = os.environ.get('APP_CLOUD_API', 'http://api.goodrain.com:80')
# create an instance of the API class
market_client = swagger_client.AppsApi(swagger_client.ApiClient(configuration))
