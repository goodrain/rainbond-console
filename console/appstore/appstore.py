# -*- coding: utf8 -*-
import logging

import openapi_client
from console.utils.restful_client import get_market_client
from console.utils.restful_client import apiException
from console.services.config_service import EnterpriseConfigService

logger = logging.getLogger('default')


class AppStore(object):
    @apiException
    def get_app_hub_info(self, store=None, app_id=None, enterprise_id=None):
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
            data = EnterpriseConfigService(enterprise_id).get_config_by_key("APPSTORE_IMAGE_HUB")
            if data:
                image_config_dict = eval(data.value)
                namespace = (image_config_dict.get("namespace") if image_config_dict.get("namespace") else store.enterprise_id)
                image_config["hub_url"] = image_config_dict.get("hub_url", None)
                image_config["hub_user"] = image_config_dict.get("hub_user", None)
                image_config["hub_password"] = image_config_dict.get("hub_password", None)
                image_config["namespace"] = namespace
        return image_config

    @apiException
    def get_slug_hub_info(self, store=None, app_id=None, enterprise_id=None):
        image_config = {"ftp_host": None, "ftp_port": None, "namespace": None, "ftp_username": None, "ftp_password": None}
        data = None
        if store:
            store_client = get_market_client(store.access_key, store.url)
            data = store_client.get_app_hub_info(app_id=app_id, market_domain=store.domain, _return_http_data_only=True)
            image_config["ftp_host"] = data.hub_url
            image_config["ftp_username"] = data.hub_user
            image_config["ftp_password"] = data.hub_password
            image_config["namespace"] = data.namespace
        if not data:
            data = EnterpriseConfigService(enterprise_id).get_config_by_key("APPSTORE_IMAGE_HUB")
            if data:
                image_config_dict = eval(data.value)
                namespace = (image_config_dict.get("namespace") if image_config_dict.get("namespace") else store.enterprise_id)
                image_config["ftp_host"] = image_config_dict.get("hub_url", None)
                image_config["ftp_username"] = image_config_dict.get("hub_user", None)
                image_config["ftp_password"] = image_config_dict.get("hub_password", None)
                image_config["namespace"] = namespace
        return image_config

    @apiException
    def get_market(self, store):
        store_client = get_market_client(store.access_key, store.url)
        data = store_client.get_market_info(market_domain=store.domain)
        return data

    @apiException
    def get_apps(self, store, query, query_all, page=1, page_size=10):
        store_client = get_market_client(store.access_key, store.url)
        data = store_client.get_user_app_list(
            page=page, page_size=page_size, market_domain=store.domain, query=query, query_all=query_all)
        return data

    @apiException
    def get_app(self, store, app_id):
        store_client = get_market_client(store.access_key, store.url)
        data = store_client.get_user_app_detail(app_id=app_id, market_domain=store.domain, _return_http_data_only=True)
        return data

    @apiException
    def get_app_versions(self, store, app_id, query_all=False):
        store_client = get_market_client(store.access_key, store.url)
        data = store_client.get_user_app_versions(
            app_id=app_id, market_domain=store.domain, query_all=query_all, _return_http_data_only=True)
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


app_store = AppStore()
