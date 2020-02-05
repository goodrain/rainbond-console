# -*- coding: utf-8 -*-
import logging
from www.apiclient.regionapi import RegionInvokeApi

region_api = RegionInvokeApi()
logger = logging.getLogger("default")


# keys 为 字符串数组
def del_etcd(region_name, tenant_name, keys):
    data = {}
    data["keys"] = keys
    logger.debug("data is : {0}".format(data))
    region_api.delete_etcd_keys(region_name, tenant_name, data)
