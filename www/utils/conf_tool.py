# -*- coding: utf8 -*-

from goodrain_web.custom_config import custom_config as custom_settings
from django.conf import settings
import logging
import  os
from console.repositories.region_repo import region_repo

logger = logging.getLogger('default')


class RegionConfig(object):

    def regions(cls):
        configs = custom_settings.configs()
        # api_conf = custom_settings.REGION_SERVICE_API
        api_conf = configs.get("REGION_SERVICE_API", None)
        # 自定义配置不存在时访问settings文件
        if not api_conf:
            regions = region_repo.get_all_regions()
            region_list = [{"name": r.region_name, "label": r.region_alias, "enable": bool(r.status == "1")} for r in
                           regions]
            return region_list
        else:
            region_list = []
            for conf in api_conf:
                region_map = {}
                region_map["name"] = conf["region_name"]
                region_map["label"] = conf["region_alias"]
                region_map["enable"] = conf.get("enable",True)
                region_list.append(region_map)
            return region_list

    def region_service_api(cls):
        api_conf = custom_settings.REGION_SERVICE_API
        # 自定义配置不存在时访问settings文件
        if not api_conf:
            return settings.REGION_SERVICE_API
        else:
            region_service_api_list = []

            for region in api_conf:
                region_map = {}
                region_map["region_name"] = region["region_name"]
                region_map["url"] = region["url"]

                region_map["apitype"] = "region service"
                region_map["token"] = region.get("token",settings.REGION_TOKEN)
                region_service_api_list.append(region_map)
            return region_service_api_list

regionConfig = RegionConfig()