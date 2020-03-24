# -*- coding: utf-8 -*-
import os
import base64
import json
import logging
from datetime import datetime

from django.conf import settings
from django.db.models import Q
from console.exception.exceptions import ConfigExistError
from console.models.main import CloundBangImages
from console.models.main import ConsoleSysConfig
# from console.models.main import EnterpriseConfig
from console.models.main import OAuthServices
from console.repositories.config_repo import cfg_repo
from console.repositories.oauth_repo import oauth_repo
from console.services.enterprise_services import enterprise_services
from console.utils.oauth.oauth_types import get_oauth_instance
from console.utils.oauth.oauth_types import NoSupportOAuthType
from goodrain_web.custom_config import custom_config as custom_settings
from www.models.main import TenantEnterprise

logger = logging.getLogger("default")


# class ConfigService(object):
#     def __init__(self):
#         # TODO: use enum
#         # self.base_platform_cfg_keys = [
#         #     "IS_PUBLIC", "MARKET_URL", "ENTERPRISE_CENTER_OAUTH", "VERSION", "TITLE", "LOGO"]
#         # self.feature_cfg_keys = ["GITHUB", "GITLAB", "APPSTORE_IMAGE_HUB",
#         #                          "OPEN_DATA_CENTER_STATUS", "NEWBIE_GUIDE",
#         #                          "DOCUMENT", "OFFICIAL_DEMO", "EXPORT_APP",
#         #                          "CLOUD_MARKET", "OBJECT_STORAGE", "OAUTH_SERVICES"]
#         # self.feature_base_cfg_keys = ["IS_REGIST"]
#
#         self.platform_cfg_keys = [
#             "IS_PUBLIC", "MARKET_URL", "ENTERPRISE_CENTER_OAUTH",
#             "VERSION", "TITLE", "LOGO",
#             "DOCUMENT", "OFFICIAL_DEMO", "IS_REGIST",
#         ]
#
#         self.platform_cfg_keys_value = {
#             "IS_PUBLIC": {"value": None, "desc": u"是否是公有", "enable": True},
#             "MARKET_URL": {"value": os.getenv('GOODRAIN_APP_API', settings.APP_SERVICE_API["url"]),
#                            "desc": u"商店路由", "enable": True},
#             "ENTERPRISE_CENTER_OAUTH": {"value": "enterprisecenter",
#                                         "desc": u"enterprise center oauth 配置", "enable": True},
#             "VERSION": {"value": os.getenv("RELEASE_DESC", "public-cloud"),
#                         "desc": u"平台版本", "enable": True},
#             "TITLE": {"value": "Rainbond-企业云应用操作系统，开发、交付云解决方案",
#                       "desc": u"云帮title", "enable": True},
#             "LOGO": {"value": None, "desc": u"云帮图标", "enable": True},
#             "DOCUMENT": {"value": {"platform_url": "https://www.rainbond.com/", },
#                          "desc": u"开启/关闭文档", "enable": True},
#             "OFFICIAL_DEMO": {"value": None, "desc": u"开启/关闭官方Demo", "enable": True},
#             "IS_REGIST": {"value": None, "desc": u"是否允许注册", "enable": True},
#         }
#         self.update_or_create_funcs = {
#             "LOGO": self._update_or_create_logo,
#             "ENTERPRISE_ALIAS": self._update_entalias,
#         }
#     @property
#     def initialization_or_get_platform_config(self):
#         rst_datas = {}
#         for key in self.platform_cfg_keys:
#             tar_key = self.get_config_by_key(key)
#             if not tar_key:
#                 enable = self.platform_cfg_keys_value[key]["enable"]
#                 value = self.platform_cfg_keys_value[key]["value"]
#                 desc = self.platform_cfg_keys_value[key]["desc"]
#
#                 if isinstance(value, (dict, list)):
#                     type = "json"
#                 else:
#                     type = "string"
#                 rst_key = self.add_config(
#                     key=key, default_value=value, type=type, enable=enable, desc=desc)
#
#                 value = rst_key.value
#                 enable = rst_key.enable
#                 rst_data = {key.lower(): {"enable": enable, "value": value}}
#                 rst_datas.update(rst_data)
#             else:
#                 if tar_key.type == "json":
#                     rst_value = eval(tar_key.value)
#                 else:
#                     rst_value = tar_key.value
#                 rst_data = {key.lower(): {"enable": tar_key.enable, "value": rst_value}}
#                 rst_datas.update(rst_data)
#         return rst_datas



# self.default_feature_base_cfg_value = {
#     "IS_REGIST": {"value": True, "desc": u"是否允许注册", "enable": True},
# }
# self.default_feature_cfg_value = {
#     "OAUTH_SERVICES": {"value": None, "desc": u"开启/关闭OAuthServices功能", "enable": True},
#     "OPEN_DATA_CENTER_STATUS": {"value": None, "desc": u"开启/关闭开通数据中心功能", "enable": True},
#     "NEWBIE_GUIDE": {"value": None, "desc": u"开启/关闭新手引导", "enable": True},
#     "DOCUMENT": {"value": {"platform_url": "https://www.rainbond.com/", },
#                  "desc": u"开启/关闭文档", "enable": True},
#     "OFFICIAL_DEMO": {"value": None, "desc": u"开启/关闭官方Demo", "enable": True},
#     "EXPORT_APP": {"value": None, "desc": u"开启/关闭导出应用", "enable": False},
#     "CLOUD_MARKET": {"value": None, "desc": u"开启/关闭云应用市场", "enable": True},
#     "GITHUB": {"value": {"client_id": None, "client_secret": None, "redirect_uri": None},
#                "desc": u"开启/关闭GITHUB", "enable": False},
#     "GITLAB": {"value": {"admin_email": None, "apitype": None, "hook_url": None, "url": None},
#                "desc": u"开启/关闭GITLAB", "enable": False},
#     "APPSTORE_IMAGE_HUB": {"value": {"hub_user": None, "hub_url": None, "namespace": None, "hub_password": None},
#                            "desc": u"开启/关闭GITLAB", "enable": False},
#     "OBJECT_STORAGE":  {
#         "enable": False,
#         "value": {
#             "provider": "",
#             "endpoint": "",
#             "access_key": "",
#             "secret_key": "",
#             "bucket_name": "",
#         },
#         "desc": u"云端备份使用的对象存储信息"
#     }
# }
#
# self.update_or_create_funcs = {
#     "LOGO": self._update_or_create_logo,
#     "ENTERPRISE_ALIAS": self._update_entalias,
# }

# def initialization_or_get_base_config(self):
#     rst_datas = {}
#     for key in self.feature_base_cfg_keys:
#         tar_key = self.get_config_by_key(key)
#         if not tar_key:
#             enable = self.default_feature_base_cfg_value[key]["enable"]
#             value = self.default_feature_base_cfg_value[key]["value"]
#             desc = self.default_feature_base_cfg_value[key]["desc"]
#
#             if isinstance(value, dict):
#                 type = "json"
#             else:
#                 type = "string"
#             rst_key = self.add_config(
#                 key=key, default_value=value, type=type, enable=enable, desc=desc)
#
#             value = rst_key.value
#             rst_data = {key.lower(): value}
#             rst_datas.update(rst_data)
#         else:
#             if tar_key.type == "json":
#                 rst_value = eval(tar_key.value)
#             elif tar_key.type == "string" and (tar_key.value == "True" or tar_key.value == "False"):
#                 rst_value = eval(tar_key.value)
#             else:
#                 rst_value = tar_key.value
#             rst_data = {key.lower(): rst_value}
#             rst_datas.update(rst_data)
#     return rst_datas
#
# def initialization_or_get_config(self):
#     rst_datas = {}
#     for key in self.feature_cfg_keys:
#         tar_key = self.get_config_by_key(key)
#         if not tar_key:
#             enable = self.default_feature_cfg_value[key]["enable"]
#             value = self.default_feature_cfg_value[key]["value"]
#             desc = self.default_feature_cfg_value[key]["desc"]
#
#             if isinstance(value, dict):
#                 type = "json"
#             else:
#                 type = "string"
#             rst_key = self.add_config(
#                 key=key, default_value=value, type=type, enable=enable, desc=desc)
#
#             value = rst_key.value
#             enable = rst_key.enable
#             rst_data = {key.lower(): {"enable": enable, "value": value}}
#             rst_datas.update(rst_data)
#         else:
#             if tar_key.type == "json":
#                 rst_value = eval(tar_key.value)
#             else:
#                 rst_value = tar_key.value
#             rst_data = {key.lower(): {"enable": tar_key.enable, "value": rst_value}}
#             rst_datas.update(rst_data)
#     return rst_datas

# def list_by_keys(self, keys):
#     cfgs = cfg_repo.list_by_keys(keys)
#     res = {}
#     for item in cfgs:
#         try:
#             value = json.loads(item.value)
#         except ValueError:
#             value = item.value
#         if item.key.upper() == "LOGO":
#             try:
#                 value = self.image_to_base64(value)
#             except IOError as e:
#                 logger.exception(e)
#                 value = "image: {}; not found.".format(value)
#         res[item.key] = value
#     return res
#
# def delete_by_key(self, key):
#     key = key.upper()
#     cfg_repo.delete_by_key(key)
#     custom_settings.reload()
#
# def update_config_enable_status(self, key, enable):
#     key = ConsoleSysConfig.objects.get(key=key)
#     if key.enable != enable:
#         key.enable = enable
#         key.save()
#
# def update_config_value(self, key, value):
#     ConsoleSysConfig.objects.filter(key=key).update(value=value)
#
# def update_by_key(self, key, enable, value):
#     key = key.upper()
#     if key in self.feature_cfg_keys:
#         if enable:
#             self.update_config_enable_status(key, enable)
#             if key == "OAUTH_SERVICES":
#                 oauth_repo.create_or_update_oauth_services(value)
#             else:
#                 self.update_config_value(key, value)
#         else:
#             self.update_config_enable_status(key, enable)
#
# def update_or_create(self, eid, data):
#     for k, v in data.iteritems():
#         k = k.upper()
#         func = self.update_or_create_funcs.get(k, None)
#         if func is None:
#             # common way
#             if isinstance(v, (dict, list)):
#                 value = json.dumps(v)
#                 cfg_repo.update_or_create_by_key(k, str(value))
#             else:
#                 cfg_repo.update_or_create_by_key(k, v)
#         elif k == "ENTERPRISE_ALIAS":
#             func(eid, v)
#         else:
#             # special way
#             func(k, v)
#     custom_settings.reload()
#
# @staticmethod
# def image_to_base64(image_path):
#     """
#     raise IOError
#     """
#     suffix = image_path.split('.')[-1]
#     with open(image_path, "rb") as f:
#         data = f.read()
#         data = "data:image/{};base64,{}".format(suffix, base64.b64encode(data))
#         return data
#
# def _update_or_create_logo(self, key, value):
#     identify = "clound_bang_logo"
#     try:
#         cbi = CloundBangImages.objects.get(identify=identify)
#         cbi.logo = value
#         cbi.save()
#     except CloundBangImages.DoesNotExist:
#         cbi = CloundBangImages(
#             identify=identify,
#             logo=value,
#             create_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
#         )
#         cbi.save()
#     cfg_repo.update_or_create_by_key(key, value)
#
# def _update_entalias(self, eid, alias):
#     ent = enterprise_services.get_enterprise_by_id(eid)
#     if ent is None:
#         raise TenantEnterprise.DoesNotExist()
#     ent.enterprise_alias = alias
#     ent.save()
#
# def add_config(self, key, default_value, type, enable=True, desc=""):
#     if not ConsoleSysConfig.objects.filter(key=key).exists():
#         create_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
#         config = ConsoleSysConfig.objects.create(
#             key=key, type=type, value=default_value, desc=desc, create_time=create_time, enable=enable)
#         custom_settings.reload()
#         return config
#     else:
#         raise ConfigExistError("配置{}已存在".format(key))
#
# def add_config_without_reload(self, key, default_value, type, desc=""):
#     if not ConsoleSysConfig.objects.filter(key=key).exists():
#         create_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
#         config = ConsoleSysConfig.objects.create(
#             key=key, type=type, value=default_value, desc=desc, create_time=create_time)
#         return config
#     else:
#         raise ConfigExistError("配置{}已存在".format(key))
#
# def update_config(self, key, value):
#     ConsoleSysConfig.objects.filter(key=key).update(value=value)
#     # 更新配置
#     custom_settings.reload()
#
# def get_by_key(self, key):
#     cfg = cfg_repo.get_by_key(key)
#     return cfg.value
#
# def get_image(self):
#     identify = "clound_bang_logo"
#     try:
#         cbi = CloundBangImages.objects.get(identify=identify)
#         logo = cbi.logo.name
#     except CloundBangImages.DoesNotExist:
#         logo = ""
#     return logo
#
# def get_config_by_key(self, key):
#     if ConsoleSysConfig.objects.filter(key=key).exists():
#         console_sys_config = ConsoleSysConfig.objects.get(key=key)
#         return console_sys_config
#     else:
#         return None
#
# def get_regist_status(self):
#     is_regist = self.get_config_by_key("IS_REGIST")
#     if not is_regist:
#         config = self.add_config(key="IS_REGIST", default_value=True, type="string", desc=u"开启/关闭注册")
#         return config.value
#     else:
#         return eval(is_regist.value)
#
# def get_github_config(self):
#     github_config = self.get_config_by_key("GITHUB")
#     if not github_config:
#         github_config = "{}"
#     else:
#         github_config = github_config.value
#     github_dict = json.loads(github_config)
#     if github_dict:
#         csc = ConsoleSysConfig.objects.get(key="GITHUB")
#         github_dict["enable"] = csc.enable
#     else:
#         github_dict["enable"] = False
#     return github_dict
#
# def get_gitlab_config(self):
#     gitlab_config = self.get_config_by_key("GITLAB")
#     if not gitlab_config:
#         gitlab_config = "{}"
#     else:
#         gitlab_config = gitlab_config.value
#     gitlab_dict_all = json.loads(gitlab_config)
#     gitlab_dict = dict()
#     if gitlab_dict_all:
#         csc = ConsoleSysConfig.objects.get(key="GITLAB")
#         gitlab_dict["enable"] = csc.enable
#         gitlab_dict["admin_email"] = gitlab_dict_all["admin_email"]
#         gitlab_dict["apitype"] = gitlab_dict_all["apitype"]
#         gitlab_dict["hook_url"] = gitlab_dict_all["hook_url"]
#         gitlab_dict["url"] = gitlab_dict_all["url"]
#     else:
#         gitlab_dict["enable"] = False
#     return gitlab_dict
#
# def get_open_data_center_status(self):
#     is_open_data_center = self.get_config_by_key("OPEN_DATA_CENTER_STATUS")
#     if not is_open_data_center:
#         config = self.add_config(key="OPEN_DATA_CENTER_STATUS", default_value="True",
#                                  type="string", desc="开启/关闭开通数据中心功能")
#         return config.value
#     else:
#         return is_open_data_center.value
#
# def get_cloud_obj_storage_info(self):
#     cloud_obj_storage_info = self.get_config_by_key("OBJECT_STORAGE")
#     if not cloud_obj_storage_info or not cloud_obj_storage_info.enable:
#         return None
#     return eval(cloud_obj_storage_info.value)


class ConfigService(object):
    def __init__(self):
        self.base_cfg_keys = None
        self.cfg_keys = None
        self.cfg_keys_value = None
        self.base_cfg_keys_value = None
        self.enterprise_id = None
    @property
    def initialization_or_get_config(self):
        rst_datas = {}
        for key in self.base_cfg_keys:
            tar_key = self.get_config_by_key(key)
            if not tar_key:
                enable = self.base_cfg_keys_value[key]["enable"]
                value = self.base_cfg_keys_value[key]["value"]
                desc = self.base_cfg_keys_value[key]["desc"]

                if isinstance(value, (dict, list)):
                    type = "json"
                else:
                    type = "string"
                rst_key = self.add_config(
                    key=key, default_value=value, type=type, enable=enable, desc=desc)

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
                rst_datas[key.lower()] = {"enable": tar_key.enable,
                                          "value": self.base_cfg_keys_value[key]["value"]}

        for key in self.cfg_keys:
            tar_key = self.get_config_by_key(key)
            if not tar_key:
                enable = self.cfg_keys_value[key]["enable"]
                value = self.cfg_keys_value[key]["value"]
                desc = self.cfg_keys_value[key]["desc"]

                if isinstance(value, (dict, list)):
                    type = "json"
                else:
                    type = "string"
                rst_key = self.add_config(
                    key=key, default_value=value, type=type, enable=enable, desc=desc)

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
        return rst_datas

    def update_config(self, key, value):
        return self.update_config_by_key(key, value)

    def add_config(self, key, default_value, type, enable=True, desc=""):
        if not ConsoleSysConfig.objects.filter(key=key, enterprise_id=self.enterprise_id).exists():
            create_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            config = ConsoleSysConfig.objects.create(
                key=key, type=type, value=default_value,
                desc=desc, create_time=create_time, enable=enable,
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
        config = ConsoleSysConfig.objects.get(key=key, enterprise_id=self.enterprise_id)
        if config.enable != enable:
            config.enable = enable
            config.save()
        if key in self.base_cfg_keys:
            return {key.lower(): {"enable": enable, "value": self.base_cfg_keys_value[key]["value"]}}
        return {key.lower(): {"enable": enable, "value": config.value}}

    def update_config_value(self, key, value):
        config = ConsoleSysConfig.objects.get(key=key, enterprise_id=self.enterprise_id)
        config.value=value
        config.save()
        return {key.lower(): {"enable": True, "value": config.value}}


class EnterpriseConfigService(ConfigService):

    def __init__(self, eid):
        super(EnterpriseConfigService, self).__init__()
        self.enterprise = enterprise_services.get_enterprise_by_enterprise_id(eid)
        self.enterprise_id = eid
        self.base_cfg_keys = [
            "OAUTH_SERVICES"
        ]
        self.base_cfg_keys_value = {
            "OAUTH_SERVICES": {"value": self.get_oauth_services(), "desc": u"开启/关闭OAuthServices功能", "enable": True},
        }
        self.cfg_keys = [
            "APPSTORE_IMAGE_HUB", "NEWBIE_GUIDE", "EXPORT_APP",
            "CLOUD_MARKET", "OBJECT_STORAGE",
        ]
        self.cfg_keys_value = {
            "APPSTORE_IMAGE_HUB": {"value": {"hub_user": None, "hub_url": None, "namespace": None, "hub_password": None},
                                   "desc": u"AppStore镜像仓库配置", "enable": True},
            "NEWBIE_GUIDE": {"value": None, "desc": u"开启/关闭新手引导", "enable": True},
            "EXPORT_APP": {"value": None, "desc": u"开启/关闭导出应用", "enable": False},
            "CLOUD_MARKET": {"value": None, "desc": u"开启/关闭云应用市场", "enable": True},
            "OBJECT_STORAGE":  {"value": {"provider": "", "endpoint": "", "access_key": "",
                                          "secret_key": "", "bucket_name": "", },
                                "desc": u"云端备份使用的对象存储信息", "enable": False},
        }

    def get_oauth_services(self):
        rst = []
        if self.enterprise.ID != 1:
            oauth_services = OAuthServices.objects.filter(
                ~Q(oauth_type="enterprisecenter"), eid=self.enterprise.enterprise_id, is_deleted=False, enable=True)
        else:
            oauth_services = OAuthServices.objects.filter(
                eid=self.enterprise.enterprise_id, is_deleted=False, enable=True)
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

class PlatformConfigService(ConfigService):
    def __init__(self):
        super(PlatformConfigService, self).__init__()
        self.base_cfg_keys = [
            "IS_PUBLIC", "MARKET_URL", "ENTERPRISE_CENTER_OAUTH", "VERSION", "LOGO"
        ]
        self.base_cfg_keys_value = {
            "IS_PUBLIC": {"value": None, "desc": u"是否是公有", "enable": True},
            "MARKET_URL": {"value": os.getenv('GOODRAIN_APP_API', settings.APP_SERVICE_API["url"]),
                           "desc": u"商店路由", "enable": True},
            "ENTERPRISE_CENTER_OAUTH": {"value": self.get_enterprise_center_oauth(),
                                        "desc": u"enterprise center oauth 配置", "enable": True},
            "VERSION": {"value": os.getenv("RELEASE_DESC", "public-cloud"),
                        "desc": u"平台版本", "enable": True},
            "LOGO": {"value": self.get_image(), "desc": u"云帮图标", "enable": True},

        }

        self.cfg_keys = [
            "TITLE", "IS_REGIST",
            "DOCUMENT", "OFFICIAL_DEMO",
        ]
        self.cfg_keys_value = {
            "TITLE": {"value": "Rainbond-企业云应用操作系统，开发、交付云解决方案",
                      "desc": u"云帮title", "enable": True},
            "DOCUMENT": {"value": {"platform_url": "https://www.rainbond.com/", },
                         "desc": u"开启/关闭文档", "enable": True},
            "OFFICIAL_DEMO": {"value": None, "desc": u"开启/关闭官方Demo", "enable": True},
            "IS_REGIST": {"value": None, "desc": u"是否允许注册", "enable": True},
        }

    def get_enterprise_center_oauth(self):
        try:
            oauth_service = OAuthServices.objects.get(
                is_deleted=False, enable=True, oauth_type="enterprisecenter", ID=1)
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

    def get_image(self):
        identify = "clound_bang_logo"
        try:
            cbi = CloundBangImages.objects.get(identify=identify)
            logo = cbi.logo.name
        except CloundBangImages.DoesNotExist:
            logo = ""
        return logo

    def add_config_without_reload(self, key, default_value, type, desc=""):
        if not ConsoleSysConfig.objects.filter(key=key).exists():
            create_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            config = ConsoleSysConfig.objects.create(
                key=key, type=type, value=default_value, desc=desc, create_time=create_time)
            return config
        else:
            raise ConfigExistError("配置{}已存在".format(key))


platform_config_service = PlatformConfigService()
