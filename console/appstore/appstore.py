# -*- coding: utf8 -*-
import logging

import os

from cadmin.models import ConsoleSysConfig
from www.apiclient.marketclient import MarketOpenAPI
from www.utils.json_tool import json_load
from console.repositories.team_repo import team_repo

logger = logging.getLogger('default')
market_api = MarketOpenAPI()

class AppStore(object):
    def __init__(self):
        pass

    def judge_service_type(self, scope, team_name, service):
        image = service.get("image", None)
        if image == "goodrain.me/runner":
            is_slug = True
            if is_slug:
                return is_slug, self.get_slug_connection_info(scope=scope)
            else:
                return is_slug, self.get_image_connection_info(scope=scope, team_name=team_name, service=service)
        else:
            is_slug = False
            return is_slug, self.get_image_connection_info(scope=scope, team_name=team_name, service=service)

    def get_image_connection_info(self, scope, team_name):
        """
        :param scope: enterprise(企业) team(团队) goodrain(好雨云市)
        :param service: 应用模型
        :return: image_info

        hub.goodrain.com/goodrain/xxx:lasted
        """
        try:
            team = team_repo.get_team_by_team_name(team_name)
            if not team:
                return {}
            if scope == "goodrain":
                info = market_api.get_share_hub_info(team.tenant_id, "image")
                return info["image_repo"]
            else:
                image_config = ConsoleSysConfig.objects.filter(key='APPSTORE_IMAGE_HUB')
                if not image_config:
                    return {"hub_url": 'goodrain.me', "namespace": team_name}
                image_config_dict = json_load(image_config[0].value)
                hub_url = image_config_dict.get("hub_url", None)
                hub_user = image_config_dict.get("hub_user", None)
                hub_password = image_config_dict.get("hub_password", None)
                namespace = image_config_dict.get("namespace", team_name)
                image_info = {"hub_url": hub_url, "hub_user": hub_user, "hub_password": hub_password, "namespace": namespace}
                return image_info
        except Exception as e:
            logger.exception(e)
            return {}

    def get_slug_connection_info(self, scope, team_name):
        """
        :param scope: enterprise(企业) team(团队) goodrain(好雨云市)
        :return: slug_info

        /grdata/build/tenant/
        """
        try:
            team = team_repo.get_team_by_team_name(team_name)
            if not team:
                return {}
            if scope == "goodrain":
                info = market_api.get_share_hub_info(team.tenant_id, "slug")
                return info["slug_repo"]
            else:
                slug_config = ConsoleSysConfig.objects.filter(key='APPSTORE_SLUG_PATH')
                if not slug_config:
                    return {"namespace": team_name}
                slug_config_dict = json_load(slug_config[0].value)
                ftp_host = slug_config_dict.get("ftp_host", None)
                ftp_port = slug_config_dict.get("ftp_port", None)
                ftp_namespace = slug_config_dict.get("namespace", None)
                ftp_username = slug_config_dict.get("ftp_username", None)
                ftp_password = slug_config_dict.get("ftp_password", None)
                slug_info = {
                    "ftp_host": ftp_host,
                    "ftp_port": ftp_port,
                    "namespace": ftp_namespace + "/" + team_name,
                    "ftp_username": ftp_username,
                    "ftp_password": ftp_password
                }
                return slug_info
        except Exception as e:
            logger.exception(e)
            return {}


app_store = AppStore()
