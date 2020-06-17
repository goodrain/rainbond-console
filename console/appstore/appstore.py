# -*- coding: utf8 -*-
import logging

from console.exception.main import ServiceHandleException
from console.models.main import ConsoleSysConfig
from console.repositories.team_repo import team_repo
from goodrain_web import settings
import openapi_client
from console.utils.restful_client import get_market_client
from console.utils.restful_client import apiException
from console.services.config_service import EnterpriseConfigService
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


class AppStoreV1(object):
    @apiException
    def get_app_hub_info(self, store=None, app_id=None):
        image_config = {
            "hub_url": None,
            "hub_user": None,
            "hub_password": None,
            "namespace": None,
        }
        data = None
        if store:
            store_client = get_market_client(store.access_key, store.url)
            data = store_client.get_app_hub_info(app_id=app_id, market_domain=store.domain, _return_http_data_only=True)
            image_config["hub_url"] = data.hub_url
            image_config["hub_user"] = data.hub_user
            image_config["hub_password"] = data.hub_password
            image_config["namespace"] = data.namespace
        if not data:
            data = EnterpriseConfigService(store.enterprise_id).get_config_by_key("APPSTORE_IMAGE_HUB")
            if data:
                image_config_dict = eval(image_config[0].value)
                namespace = (image_config_dict.get("namespace") if image_config_dict.get("namespace") else store.enterprise_id)
                image_config["hub_url"] = image_config_dict.get("hub_url", None)
                image_config["hub_user"] = image_config_dict.get("hub_user", None)
                image_config["hub_password"] = image_config_dict.get("hub_password", None)
                image_config["namespace"] = namespace
        return image_config

    @apiException
    def get_market(self, store):
        store_client = get_market_client(store.access_key, store.url)
        data = store_client.get_market_info(market_domain=store.domain)
        return data

    @apiException
    def get_apps(self, store, query, page=1, page_size=10):
        store_client = get_market_client(store.access_key, store.url)
        data = store_client.get_user_app_list(page=page, page_size=page_size, market_domain=store.domain, query=query)
        return data

    @apiException
    def get_app(self, store, app_id):
        store_client = get_market_client(store.access_key, store.url)
        data = store_client.get_user_app_detail(app_id=app_id, market_domain=store.domain, _return_http_data_only=True)
        return data

    @apiException
    def get_app_versions(self, store, app_id):
        store_client = get_market_client(store.access_key, store.url)
        data = store_client.get_user_app_versions(app_id=app_id, market_domain=store.domain, _return_http_data_only=True)
        return data

    @apiException
    def get_app_version(self, store, app_id, version, for_install=False):
        store_client = get_market_client(store.access_key, store.url)
        data = store_client.get_user_app_version_detail(
            app_id=app_id, version=version, market_domain=store.domain, for_install=for_install)
        return data

    @apiException
    def update_app(self, store, app_id, body):
        store_client = get_market_client(store.access_key, store.url)
        data = store_client.update_app(app_id=app_id, body=body, market_domain=store.domain)
        return data

    @apiException
    def create_app(self, store, body):
        store_client = get_market_client(store.access_key, store.url)
        body = openapi_client.V1AppCreateRequest(**body)
        data = store_client.create_app(body=body, market_domain=store.domain)
        return data

    @apiException
    def create_app_version(self, store, app_id, body):
        store_client = get_market_client(store.access_key, store.url)
        body = openapi_client.V1CreateAppPaaSVersionRequest(**body)
        data = store_client.create_app_version(app_id=app_id, body=body, market_domain=store.domain)
        return data


app_store = AppStoreV1()
# app_store = AppStoreV1()
