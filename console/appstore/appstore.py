# -*- coding: utf8 -*-
import logging

from console.exception.main import ServiceHandleException
from console.models.main import ConsoleSysConfig
from console.repositories.team_repo import team_repo
from goodrain_web import settings
from www.apiclient.baseclient import HttpClient
from www.apiclient.marketclient import MarketOpenAPI
from www.utils.json_tool import json_load

logger = logging.getLogger('default')
market_api = MarketOpenAPI()


class AppStore(object):
    def __init__(self):
        pass

    def get_image_connection_info(self, scope, eid, team_name):
        """
        :param scope: enterprise(企业) team(团队) goodrain(好雨云市)
        :param team_name: 租户名称
        :return: image_info

        hub.goodrain.com/goodrain/xxx:lasted
        """
        try:
            team = team_repo.get_team_by_team_name(team_name)
            if not team and scope == "team":
                return {}
            if scope.startswith("goodrain"):
                info = market_api.get_enterprise_share_hub_info(eid, "image")
                return info["image_repo"]
            else:
                image_config = ConsoleSysConfig.objects.filter(key='APPSTORE_IMAGE_HUB', enterprise_id=eid)
                namespace = eid if scope == "enterprise" else team_name
                if not image_config or not image_config[0].enable:
                    return {"hub_url": settings.IMAGE_REPO, "namespace": namespace}
                image_config_dict = eval(image_config[0].value)
                hub_url = image_config_dict.get("hub_url", None)
                hub_user = image_config_dict.get("hub_user", None)
                hub_password = image_config_dict.get("hub_password", None)
                namespace = (image_config_dict.get("namespace") if image_config_dict.get("namespace") else namespace)
                is_trust = hub_url == 'hub.goodrain.com'
                image_info = {
                    "hub_url": hub_url,
                    "hub_user": hub_user,
                    "hub_password": hub_password,
                    "namespace": namespace,
                    "is_trust": is_trust
                }
                return image_info
        except HttpClient.CallApiError as e:
            logger.exception(e)
            if e.status == 403:
                raise ServiceHandleException("no cloud permission", msg_show="云市授权不通过", status_code=403, error_code=10407)
            else:
                raise ServiceHandleException("call cloud api failure", msg_show="云市请求错误", status_code=500, error_code=500)
        except Exception as e:
            logger.exception(e)
            return {}

    # deprecated
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
                if not slug_config or not slug_config[0].enable:
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
        except HttpClient.CallApiError as e:
            logger.exception(e)
            if e.status == 403:
                raise ServiceHandleException("no cloud permission", msg_show="云市授权不通过", status_code=403, error_code=10407)
            else:
                raise ServiceHandleException("call cloud api failure", msg_show="云市请求错误", status_code=500, error_code=500)
        except Exception as e:
            logger.exception(e)
            return {}


app_store = AppStore()
