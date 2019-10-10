# -*- coding: utf-8 -*-
import base64
import json
import logging
from datetime import datetime

from console.exception.exceptions import ConfigExistError
from console.models.main import CloundBangImages
from console.models.main import ConsoleSysConfig
from console.repositories.config_repo import cfg_repo
from console.services.enterprise_services import enterprise_services
from goodrain_web.custom_config import custom_config as custom_settings
from www.models.main import TenantEnterprise

logger = logging.getLogger("default")


class ConfigService(object):
    def __init__(self):
        # TODO: use enum
        self.base_cfg_keys = ["REGION_SERVICE_API", "TITLE",
                              "REGISTER_STATUS", "RAINBOND_VERSION", "LOGO"]
        self.feature_cfg_keys = ["GITHUB", "GITLAB", "APPSTORE_IMAGE_HUB"]
        self.update_or_create_funcs = {
            "LOGO": self._update_or_create_logo,
            "ENTERPRISE_ALIAS": self._update_entalias,
        }

    def list_by_keys(self, keys):
        cfgs = cfg_repo.list_by_keys(keys)
        res = {}
        for item in cfgs:
            try:
                value = json.loads(item.value)
            except ValueError:
                value = item.value
            if item.key.upper() == "LOGO":
                try:
                    value = self.image_to_base64(value)
                except IOError as e:
                    logger.exception(e)
                    value = "image: {}; not found.".format(value)
            res[item.key] = value
        return res

    def delete_by_key(self, key):
        key = key.upper()
        cfg_repo.delete_by_key(key)
        custom_settings.reload()

    def update_or_create(self, eid, data):
        for k, v in data.iteritems():
            k = k.upper()
            func = self.update_or_create_funcs.get(k, None)
            if func is None:
                # common way
                if isinstance(v, (dict, list)):
                    value = json.dumps(v)
                    cfg_repo.update_or_create_by_key(k, str(value))
                else:
                    cfg_repo.update_or_create_by_key(k, v)
            elif k == "ENTERPRISE_ALIAS":
                func(eid, v)
            else:
                # special way
                func(k, v)
        custom_settings.reload()

    @staticmethod
    def image_to_base64(image_path):
        """
        raise IOError
        """
        suffix = image_path.split('.')[-1]
        with open(image_path, "rb") as f:
            data = f.read()
            data = "data:image/{};base64,{}".format(suffix, base64.b64encode(data))
            return data

    def _update_or_create_logo(self, key, value):
        identify = "clound_bang_logo"
        try:
            cbi = CloundBangImages.objects.get(identify=identify)
            cbi.logo = value
            cbi.save()
        except CloundBangImages.DoesNotExist:
            cbi = CloundBangImages(
                identify=identify,
                logo=value,
                create_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            )
            cbi.save()
        cfg_repo.update_or_create_by_key(key, value)

    def _update_entalias(self, eid, alias):
        ent = enterprise_services.get_enterprise_by_id(eid)
        if ent is None:
            raise TenantEnterprise.DoesNotExist()
        ent.enterprise_alias = alias
        ent.save()

    def add_config(self, key, default_value, type, desc=""):
        if not ConsoleSysConfig.objects.filter(key=key).exists():
            create_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            config = ConsoleSysConfig.objects.create(
                key=key, type=type, value=default_value, desc=desc, create_time=create_time)
            custom_settings.reload()
            return config
        else:
            raise ConfigExistError("配置{}已存在".format(key))

    def add_config_without_reload(self, key, default_value, type, desc=""):
        if not ConsoleSysConfig.objects.filter(key=key).exists():
            create_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            config = ConsoleSysConfig.objects.create(
                key=key, type=type, value=default_value, desc=desc, create_time=create_time)
            return config
        else:
            raise ConfigExistError("配置{}已存在".format(key))

    def update_config(self, key, value):
        ConsoleSysConfig.objects.filter(key=key).update(value=value)
        # 更新配置
        custom_settings.reload()

    def get_by_key(self, key):
        cfg = cfg_repo.get_by_key(key)
        return cfg.value

    def get_image(self):
        identify = "clound_bang_logo"
        try:
            cbi = CloundBangImages.objects.get(identify=identify)
            logo = cbi.logo.name
        except CloundBangImages.DoesNotExist as e:
            logger.error(e)
            logo = ""
        return logo

    def get_config_by_key(self, key):
        if ConsoleSysConfig.objects.filter(key=key).exists():
            console_sys_config = ConsoleSysConfig.objects.get(key=key)
            return console_sys_config.value
        else:
            return None

    def get_regist_status(self):
        is_regist = self.get_config_by_key("REGISTER_STATUS")
        if not is_regist:
            config = self.add_config(key="REGISTER_STATUS", default_value="yes", type="string", desc="开启/关闭注册")
            return config.value
        else:
            return is_regist

    def get_github_config(self):
        github_config = self.get_config_by_key("GITHUB")
        if not github_config:
            github_config = "{}"
        github_dict = json.loads(github_config)
        if github_dict:
            csc = ConsoleSysConfig.objects.get(key="GITHUB")
            github_dict["enable"] = csc.enable
        else:
            github_dict["enable"] = False
        return github_dict

    def get_gitlab_config(self):
        gitlab_config = self.get_config_by_key("GITLAB")
        if not gitlab_config:
            gitlab_config = "{}"
        gitlab_dict_all = json.loads(gitlab_config)
        gitlab_dict = dict()
        if gitlab_dict_all:
            csc = ConsoleSysConfig.objects.get(key="GITLAB")
            gitlab_dict["enable"] = csc.enable
            gitlab_dict["admin_email"] = gitlab_dict_all["admin_email"]
            gitlab_dict["apitype"] = gitlab_dict_all["apitype"]
            gitlab_dict["hook_url"] = gitlab_dict_all["hook_url"]
            gitlab_dict["url"] = gitlab_dict_all["url"]
        else:
            gitlab_dict["enable"] = False
        return gitlab_dict


config_service = ConfigService()
