# -*- coding: utf-8 -*-
import logging
import os
from datetime import datetime

from django.conf import settings
from django.db.models import Q

from console.exception.exceptions import ConfigExistError
from console.models.main import ConsoleSysConfig, OAuthServices
from console.repositories.user_repo import user_repo
from console.services.enterprise_services import enterprise_services
from console.utils.oauth.oauth_types import (NoSupportOAuthType, get_oauth_instance)
from goodrain_web.custom_config import custom_config as custom_settings
from console.enum.system_config import ConfigKeyEnum

logger = logging.getLogger("default")


class ConfigService(object):
    def __init__(self):
        self.base_cfg_keys = None
        self.cfg_keys = None
        self.cfg_keys_value = None
        self.base_cfg_keys_value = None
        self.enterprise_id = ""

    def init_base_config_value(self):
        # no need
        pass

    @property
    def initialization_or_get_config(self):
        self.init_base_config_value()
        rst_datas = {}
        for key in self.base_cfg_keys:
            tar_key = self.get_config_by_key(key)
            if not tar_key:
                enable = self.base_cfg_keys_value[key]["enable"]
                value = self.base_cfg_keys_value[key]["value"]
                desc = self.base_cfg_keys_value[key]["desc"]
                config_type = "string"
                if isinstance(value, (dict, list)):
                    config_type = "json"
                rst_key = self.add_config(key=key, default_value=value, type=config_type, enable=enable, desc=desc)

                value = rst_key.value
                enable = rst_key.enable
                rst_data = {key.lower(): {"enable": enable, "value": value}}
                rst_datas.update(rst_data)
            else:
                if tar_key.type == "json":
                    rst_value = eval(tar_key.value)
                else:
                    rst_value = tar_key.value
                rst_data = {key.lower(): {"enable": tar_key.enable, "value": rst_value}}
                rst_datas.update(rst_data)
                rst_datas[key.lower()] = {"enable": tar_key.enable, "value": self.base_cfg_keys_value[key]["value"]}

        for key in self.cfg_keys:
            tar_key = self.get_config_by_key(key)
            if not tar_key:
                enable = self.cfg_keys_value[key]["enable"]
                value = self.cfg_keys_value[key]["value"]
                desc = self.cfg_keys_value[key]["desc"]
                config_type = "string"
                if isinstance(value, (dict, list)):
                    config_type = "json"
                rst_key = self.add_config(key=key, default_value=value, type=config_type, enable=enable, desc=desc)

                value = rst_key.value
                enable = rst_key.enable
                rst_data = {key.lower(): {"enable": enable, "value": value}}
                rst_datas.update(rst_data)
            else:
                if tar_key.type == "json":
                    rst_value = eval(tar_key.value)
                else:
                    rst_value = tar_key.value
                rst_data = {key.lower(): {"enable": tar_key.enable, "value": rst_value}}
                rst_datas.update(rst_data)

        rst_datas["default_market_url"] = os.getenv("DEFAULT_APP_MARKET_URL", "https://hub.grapps.cn")
        return rst_datas

    def update_config(self, key, value):
        return self.update_config_by_key(key, value)

    def delete_config(self, key):
        return self.delete_config_by_key(key)

    def add_config(self, key, default_value, type, enable=True, desc=""):
        if not ConsoleSysConfig.objects.filter(key=key, enterprise_id=self.enterprise_id).exists():
            create_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            config = ConsoleSysConfig.objects.create(
                key=key,
                type=type,
                value=default_value,
                desc=desc,
                create_time=create_time,
                enable=enable,
                enterprise_id=self.enterprise_id)
            custom_settings.reload()
            return config
        else:
            raise ConfigExistError("配置{}已存在".format(key))

    def get_config_by_key(self, key):
        try:
            return ConsoleSysConfig.objects.get(key=key, enterprise_id=self.enterprise_id)
        except ConsoleSysConfig.DoesNotExist:
            return None

    def update_config_by_key(self, key, data):
        enable = data["enable"]
        value = data["value"]
        if key in self.base_cfg_keys:
            return self.update_config_enable_status(key, enable)
        if enable:
            self.update_config_enable_status(key, enable)
            config = self.update_config_value(key, value)
        else:
            config = self.update_config_enable_status(key, enable)
        return config

    def update_config_enable_status(self, key, enable):
        self.init_base_config_value()

        config = ConsoleSysConfig.objects.get(key=key, enterprise_id=self.enterprise_id)
        if key in self.base_cfg_keys:
            return {key.lower(): {"enable": enable, "value": self.base_cfg_keys_value[key]["value"]}}
        return {key.lower(): {"enable": enable, "value": (eval(config.value) if config.type == "json" else config.value)}}

    def update_config_value(self, key, value):
        config = ConsoleSysConfig.objects.get(key=key, enterprise_id=self.enterprise_id)
        config.value = value
        if isinstance(value, (dict, list)):
            type = "json"
        else:
            type = "string"
        config.type = type
        config.save()
        return {key.lower(): {"enable": True, "value": config.value}}

    def delete_config_by_key(self, key):
        rst = ConsoleSysConfig.objects.get(key=key, enterprise_id=self.enterprise_id)
        rst.enable = self.cfg_keys_value[key]["enable"]
        rst.value = self.cfg_keys_value[key]["value"]
        rst.desc = self.cfg_keys_value[key]["desc"]
        if isinstance(rst.value, (dict, list)):
            rst.type = "json"
        else:
            rst.type = "string"
        rst.save()
        return {key.lower(): {"enable": rst.enable, "value": rst.value}}


class EnterpriseConfigService(ConfigService):
    def __init__(self, eid):
        super(EnterpriseConfigService, self).__init__()
        self.enterprise_id = eid
        self.base_cfg_keys = ["OAUTH_SERVICES"]
        self.cfg_keys = [
            "APPSTORE_IMAGE_HUB",
            "NEWBIE_GUIDE",
            "EXPORT_APP",
            "CLOUD_MARKET",
            "OBJECT_STORAGE",
            "AUTO_SSL",
            "VISUAL_MONITOR",
        ]
        self.cfg_keys_value = {
            "APPSTORE_IMAGE_HUB": {
                "value": {
                    "hub_user": None,
                    "hub_url": None,
                    "namespace": None,
                    "hub_password": None
                },
                "desc": "AppStore镜像仓库配置",
                "enable": False
            },
            "NEWBIE_GUIDE": {
                "value": None,
                "desc": "开启/关闭新手引导",
                "enable": True
            },
            "EXPORT_APP": {
                "value": None,
                "desc": "开启/关闭导出应用",
                "enable": False
            },
            "CLOUD_MARKET": {
                "value": None,
                "desc": "开启/关闭云应用市场",
                "enable": True
            },
            "OBJECT_STORAGE": {
                "value": {
                    "provider": "",
                    "endpoint": "",
                    "access_key": "",
                    "secret_key": "",
                    "bucket_name": "",
                },
                "desc": "云端备份使用的对象存储信息",
                "enable": False
            },
            "AUTO_SSL": {
                "value": None,
                "desc": "证书自动签发",
                "enable": False
            },
            "VISUAL_MONITOR": {
                "value": {
                    "home_url": "",
                    "cluster_monitor_suffix": "/d/cluster/ji-qun-jian-kong-ke-shi-hua",
                    "node_monitor_suffix": "/d/node/jie-dian-jian-kong-ke-shi-hua",
                    "component_monitor_suffix": "/d/component/zu-jian-jian-kong-ke-shi-hua",
                    "slo_monitor_suffix": "/d/service/fu-wu-jian-kong-ke-shi-hua",
                },
                "desc": "可视化监控配置(链接外部监控)",
                "enable": False
            },
        }

    def init_base_config_value(self):
        self.base_cfg_keys_value = {
            "OAUTH_SERVICES": {
                "value": self.get_oauth_services(),
                "desc": "开启/关闭OAuthServices功能",
                "enable": False
            },
        }

    def get_oauth_services(self):
        rst = []
        enterprise = enterprise_services.get_enterprise_by_enterprise_id(self.enterprise_id)
        if enterprise.ID != 1:
            oauth_services = OAuthServices.objects.filter(
                ~Q(oauth_type="enterprisecenter"), eid=enterprise.enterprise_id, is_deleted=False, enable=True)
        else:
            oauth_services = OAuthServices.objects.filter(eid=enterprise.enterprise_id, is_deleted=False, enable=True)
        if oauth_services:
            for oauth_service in oauth_services:
                try:
                    api = get_oauth_instance(oauth_service.oauth_type, oauth_service, None)
                    authorize_url = api.get_authorize_url()
                    rst.append({
                        "service_id": oauth_service.ID,
                        "enable": oauth_service.enable,
                        "name": oauth_service.name,
                        "oauth_type": oauth_service.oauth_type,
                        "is_console": oauth_service.is_console,
                        "home_url": oauth_service.home_url,
                        "eid": oauth_service.eid,
                        "is_auto_login": oauth_service.is_auto_login,
                        "is_git": oauth_service.is_git,
                        "authorize_url": authorize_url,
                    })
                except NoSupportOAuthType:
                    continue
        return rst

    def get_cloud_obj_storage_info(self):
        cloud_obj_storage_info = self.get_config_by_key("OBJECT_STORAGE")
        if not cloud_obj_storage_info or not cloud_obj_storage_info.enable:
            return None
        return eval(cloud_obj_storage_info.value)

    def get_auto_ssl_info(self):
        auto_ssl_config = self.get_config_by_key("AUTO_SSL")
        if not auto_ssl_config or not auto_ssl_config.enable:
            return None
        return eval(auto_ssl_config.value)


class PlatformConfigService(ConfigService):
    def __init__(self):
        super(PlatformConfigService, self).__init__()
        self.base_cfg_keys = ["IS_PUBLIC", "MARKET_URL", "ENTERPRISE_CENTER_OAUTH", "VERSION", "IS_USER_REGISTER"]
        if not os.getenv('IS_PUBLIC', False):
            self.base_cfg_keys.append("OAUTH_SERVICES")

        self.cfg_keys = [
            "TITLE",
            "LOGO",
            "FAVICON",
            "IS_REGIST",
            "IS_ALARM",
            "DOCUMENT",
            "OFFICIAL_DEMO",
            ConfigKeyEnum.ENTERPRISE_EDITION.name,
        ]
        self.cfg_keys_value = {
            "TITLE": {
                "value": "Rainbond",
                "desc": "Rainbond web tile",
                "enable": True
            },
            "LOGO": {
                "value": None,
                "desc": "Rainbond Logo url",
                "enable": True
            },
            "FAVICON": {
                "value": None,
                "desc": "Rainbond web favicon url",
                "enable": True
            },
            "DOCUMENT": {
                "value": {
                    "platform_url": "https://www.rainbond.com/",
                },
                "desc": "开启/关闭文档",
                "enable": True
            },
            "OFFICIAL_DEMO": {
                "value": None,
                "desc": "开启/关闭官方Demo",
                "enable": True
            },
            "IS_REGIST": {
                "value": None,
                "desc": "是否允许注册",
                "enable": True
            },
            "IS_ALARM": {
                "value": None,
                "desc": "是否展示报警",
                "enable": True
            },
            ConfigKeyEnum.ENTERPRISE_EDITION.name: {
                "value": "false",
                "desc": "是否是企业版",
                "enable": True
            },
        }

    def init_base_config_value(self):
        self.base_cfg_keys_value = {
            "IS_PUBLIC": {
                "value": os.getenv('IS_PUBLIC', False),
                "desc": "是否是Cloud",
                "enable": True
            },
            "MARKET_URL": {
                "value": os.getenv('GOODRAIN_APP_API', settings.APP_SERVICE_API["url"]),
                "desc": "商店路由",
                "enable": True
            },
            "ENTERPRISE_CENTER_OAUTH": {
                "value": self.get_enterprise_center_oauth(),
                "desc": "enterprise center oauth 配置",
                "enable": True
            },
            "VERSION": {
                "value": os.getenv("RELEASE_DESC", "public-cloud"),
                "desc": "平台版本",
                "enable": True
            },
            "IS_USER_REGISTER": {
                "value": self.is_user_register(),
                "desc": "开启/关闭OAuthServices功能",
                "enable": True
            },
        }
        if not os.getenv('IS_PUBLIC', False):
            self.base_cfg_keys_value["OAUTH_SERVICES"] = {
                "value": self.get_all_oauth_service(),
                "desc": "开启/关闭OAuthServices功能",
                "enable": True
            }

    def get_enterprise_center_oauth(self):
        try:
            oauth_service = OAuthServices.objects.get(is_deleted=False, enable=True, oauth_type="enterprisecenter", ID=1)
            pre_enterprise_center = os.getenv("PRE_ENTERPRISE_CENTER", None)
            if pre_enterprise_center:
                oauth_service = OAuthServices.objects.get(name=pre_enterprise_center, oauth_type="enterprisecenter")
        except OAuthServices.DoesNotExist:
            return None
        try:
            api = get_oauth_instance(oauth_service.oauth_type, oauth_service, None)
            authorize_url = api.get_authorize_url()
            return {
                "service_id": oauth_service.ID,
                "enable": oauth_service.enable,
                "name": oauth_service.name,
                "oauth_type": oauth_service.oauth_type,
                "is_console": oauth_service.is_console,
                "home_url": oauth_service.home_url,
                "eid": oauth_service.eid,
                "is_auto_login": oauth_service.is_auto_login,
                "is_git": oauth_service.is_git,
                "authorize_url": authorize_url,
            }
        except NoSupportOAuthType:
            return None

    def is_user_register(self):
        if user_repo.get_all_users():
            return True
        return False

    def add_config_without_reload(self, key, default_value, type, desc=""):
        if not ConsoleSysConfig.objects.filter(key=key).exists():
            create_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            config = ConsoleSysConfig.objects.create(
                key=key, type=type, value=default_value, desc=desc, create_time=create_time, enterprise_id="")
            return config
        else:
            raise ConfigExistError("配置{}已存在".format(key))

    def get_all_oauth_service(self):
        rst = []
        oauth_services = OAuthServices.objects.filter(is_deleted=False, enable=True)
        if oauth_services:
            for oauth_service in oauth_services:
                try:
                    api = get_oauth_instance(oauth_service.oauth_type, oauth_service, None)
                    authorize_url = api.get_authorize_url()
                    rst.append({
                        "service_id": oauth_service.ID,
                        "enable": oauth_service.enable,
                        "name": oauth_service.name,
                        "oauth_type": oauth_service.oauth_type,
                        "is_console": oauth_service.is_console,
                        "home_url": oauth_service.home_url,
                        "eid": oauth_service.eid,
                        "is_auto_login": oauth_service.is_auto_login,
                        "is_git": oauth_service.is_git,
                        "authorize_url": authorize_url,
                    })
                except NoSupportOAuthType:
                    continue
        return rst


platform_config_service = PlatformConfigService()
