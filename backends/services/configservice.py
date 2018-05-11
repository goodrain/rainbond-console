# -*- coding: utf8 -*-

import datetime
import json
import logging

from backends.models.main import CloundBangImages
from backends.services.exceptions import *
from cadmin.models import ConsoleSysConfig
from www.utils.license import LICENSE
from goodrain_web.custom_config import custom_config as custom_settings
logger = logging.getLogger("default")


class ConfigService(object):
    def get_image(self):
        identify = "clound_bang_logo"
        try:
            cbi = CloundBangImages.objects.get(identify=identify)
            logo = cbi.logo.name
        except CloundBangImages.DoesNotExist as e:
            logo = "/static/www/images/yunbanglogo.png"
        return logo

    def upload_image(self, request):
        rt_url = None
        logo = request.FILES["logo"]
        # 1M 大小
        if logo.size > 1048576:
            raise ParamsError("图片大小不能超过1M")
        identify = "clound_bang_logo"
        create_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        count = CloundBangImages.objects.filter(identify=identify).count()
        if count > 1:
            CloundBangImages.objects.filter(identify=identify).delete()
            count = 0
        if count == 0:
            cbi = CloundBangImages.objects.create(identify=identify, logo=logo, create_time=create_time)
            rt_url = cbi.logo.name
        else:
            cbi = CloundBangImages.objects.get(identify=identify)
            cbi.logo = logo
            cbi.save()
            rt_url = cbi.logo.name

        logo_conf = self.get_config_by_key("LOGO")
        if logo_conf:
            self.update_config("LOGO",rt_url)
        else:
            self.add_config("LOGO", rt_url, "string", "云帮LOGO")
        return rt_url

    def get_config_by_key(self, key):
        if ConsoleSysConfig.objects.filter(key=key).exists():
            console_sys_config = ConsoleSysConfig.objects.get(key=key)
            return console_sys_config.value
        else:
            return None

    def add_config(self, key, default_value, type, desc=""):
        if not ConsoleSysConfig.objects.filter(key=key).exists():
            create_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            config = ConsoleSysConfig.objects.create(key=key,
                                                     type=type,
                                                     value=default_value,
                                                     desc=desc,
                                                     create_time=create_time)
            custom_settings.reload()
            return config
        else:
            raise ConfigExistError("配置{}已存在".format(key))

    def update_config(self, key, value):
        ConsoleSysConfig.objects.filter(key=key).update(value=value)
        # 更新配置
        custom_settings.reload()

    def get_safety_config(self):
        registerable = self.get_config_by_key("REGISTERABLE")
        if not registerable:
            config = self.add_config("REGISTERABLE", 1, "bool", "云帮可否注册")
            registerable = config.value

        tenant_createable = self.get_config_by_key("TENANT_CREATEABLE")
        if not tenant_createable:
            config = self.add_config("TENANT_CREATEABLE", 1, "bool", "云帮可否注册")
            tenant_createable = config.value

        max_num = LICENSE.get_authorization_tenant_number()

        tenant_num = self.get_config_by_key("TENANT_NUM")
        if not tenant_num:
            config = self.add_config("TENANT_NUM", max_num, "int", "最大团队个数")
            tenant_num = config.value
        config_map = {}
        config_map["registerable"] = registerable
        config_map["tenant_createable"] = tenant_createable
        config_map["tenant_num"] = tenant_num

        return config_map

    def update_registerable_config(self, action):
        if action == "open":
            self.update_config("REGISTERABLE", 1)
        else:
            self.update_config("REGISTERABLE", 0)

    def update_tenant_config(self, action, tenant_num):
        if not action:
            raise ParamsError("参数错误")
        if action == "set-num" and not tenant_num:
            raise ParamsError("参数错误")
        if action == "open":
            self.update_config("TENANT_CREATEABLE", 1)
        elif action == "close":
            self.update_config("TENANT_CREATEABLE", 0)
        elif action == "set-num":
            max_num = LICENSE.get_authorization_tenant_number()
            if int(tenant_num) > int(max_num):
                raise TenantOverFlowError("租户数量超出最大值")
            self.update_config("TENANT_NUM", tenant_num)

    def get_license_info(self):
        license_info = LICENSE.license_info
        module_list = license_info.get("module_list",[])
        tranf_module_list = []
        if "all" in module_list:
            tranf_module_list.append("全部功能")
        else:
            tranf_module_list.append("基础功能")
        license_info["module_list"] = tranf_module_list

        return license_info

    def update_license_info(self, new_license):

        if LICENSE.validation(new_license):
            # self.update_config("LICENSE", new_license)
            LICENSE.set_license(new_license)
        else:
            raise ParamsError("无效的license")

    def get_github_config(self):
        github_config = self.get_config_by_key("GITHUB_SERVICE_API")
        if not github_config:
            github_config = "{}"
        github_dict = json.loads(github_config)
        if github_dict:
            csc = ConsoleSysConfig.objects.get(key="GITHUB_SERVICE_API")
            github_dict["enable"] = csc.enable
        else:
            github_dict["enable"] = False
        return github_dict

    def add_github_config(self, redirect_uri, client_secret, client_id):
        value_map = {}
        value_map["redirect_uri"] = redirect_uri
        value_map["client_secret"] = client_secret
        value_map["client_id"] = client_id
        value = json.dumps(value_map)
        self.add_config("GITHUB_SERVICE_API", value, "json", "github配置")

    def update_github_config(self, redirect_uri, client_secret, client_id):
        value_map = {}
        value_map["redirect_uri"] = redirect_uri
        value_map["client_secret"] = client_secret
        value_map["client_id"] = client_id
        value = json.dumps(value_map)
        self.update_config("GITHUB_SERVICE_API", value)

    def get_gitlab_config(self):
        gitlab_config = self.get_config_by_key("GITLAB_SERVICE_API")
        if not gitlab_config:
            gitlab_config = "{}"
        gitlab_dict_all = json.loads(gitlab_config)
        gitlab_dict = dict()
        if gitlab_dict_all:
            csc = ConsoleSysConfig.objects.get(key="GITLAB_SERVICE_API")
            gitlab_dict["enable"] = csc.enable
            gitlab_dict["admin_email"] = gitlab_dict_all["admin_email"]
            gitlab_dict["apitype"] = gitlab_dict_all["apitype"]
            gitlab_dict["hook_url"] = gitlab_dict_all["hook_url"]
            gitlab_dict["url"] = gitlab_dict_all["url"]
        else:
            gitlab_dict["enable"] = False
        return gitlab_dict

    def add_gitlab_config(self, url, admin_user, admin_password, admin_email, hook_url='', ):
        value_map = {}
        value_map["url"] = url
        value_map["apitype"] = "gitlab service"
        value_map["admin_user"] = admin_user
        value_map["admin_password"] = admin_password
        value_map["hook_url"] = hook_url
        value_map["admin_email"] = admin_email

        value = json.dumps(value_map)
        self.add_config("GITLAB_SERVICE_API", value, "json", "github配置")

    def update_gitlab_config(self, url, admin_user, admin_password, admin_email, hook_url='', ):
        value_map = {}
        value_map["url"] = url
        value_map["apitype"] = "gitlab service"
        value_map["admin_user"] = admin_user
        value_map["admin_password"] = admin_password
        value_map["hook_url"] = hook_url
        value_map["admin_email"] = admin_email
        value = json.dumps(value_map)
        self.update_config("GITLAB_SERVICE_API", value)

    def get_image_hub_config(self):
        image_hub_config = self.get_config_by_key("APPSTORE_IMAGE_HUB")
        if not image_hub_config:
            image_hub_config = "{}"
        hubconfig_all = json.loads(image_hub_config)
        hub_config_dict = dict()
        if hubconfig_all:
            csc = ConsoleSysConfig.objects.get(key="APPSTORE_IMAGE_HUB")
            hub_config_dict.update(hubconfig_all)
            hub_config_dict["enable"] = csc.enable
        else:
            hub_config_dict["enable"] = False
        return hub_config_dict

    def add_image_hub_config(self, hub_url, namespace, hub_user, hub_password):
        value_map = dict()
        value_map["hub_url"] = hub_url
        value_map["namespace"] = namespace
        value_map["hub_user"] = hub_user
        value_map["hub_password"] = hub_password

        value = json.dumps(value_map)
        self.add_config("APPSTORE_IMAGE_HUB", value, "json", "云市仓库配置")

    def update_image_hub_config(self, hub_url, namespace, hub_user, hub_password):
        value_map = dict()
        value_map["hub_url"] = hub_url
        value_map["namespace"] = namespace
        value_map["hub_user"] = hub_user
        value_map["hub_password"] = hub_password

        value = json.dumps(value_map)
        self.update_config("APPSTORE_IMAGE_HUB", value)

    def get_ftp_config(self):
        ftp_config = self.get_config_by_key("APPSTORE_SLUG_PATH")
        if not ftp_config:
            ftp_config = "{}"
        ftpconfig_all = json.loads(ftp_config)
        ftp_config_dict = dict()
        if ftpconfig_all:
            csc = ConsoleSysConfig.objects.get(key="APPSTORE_SLUG_PATH")
            ftp_config_dict.update(ftpconfig_all)
            ftp_config_dict["enable"] = csc.enable
        else:
            ftp_config_dict["enable"] = False
        return ftp_config_dict

    def add_ftp_config(self, ftp_host, ftp_port, namespace, ftp_username, ftp_password):
        value_map = dict()
        value_map["ftp_host"] = ftp_host
        value_map["ftp_port"] = ftp_port
        value_map["namespace"] = namespace
        value_map["ftp_username"] = ftp_username
        value_map["ftp_password"] = ftp_password

        value = json.dumps(value_map)
        self.add_config("APPSTORE_SLUG_PATH", value, "json", "仓库FTP配置")

    def update_ftp_config(self, ftp_host, ftp_port, namespace, ftp_username, ftp_password):
        value_map = dict()
        value_map["ftp_host"] = ftp_host
        value_map["ftp_port"] = ftp_port
        value_map["namespace"] = namespace
        value_map["ftp_username"] = ftp_username
        value_map["ftp_password"] = ftp_password

        value = json.dumps(value_map)
        self.update_config("APPSTORE_SLUG_PATH", value)


    def manage_code_conf(self, action, type):
        if action not in ("open", "close",):
            raise ParamsError("操作参数错误")
        if type not in ("github", "gitlab","ftpconf","hubconf"):
            raise ParamsError("操作参数错误")
        if action == "open":
            if type == "github":
                ConsoleSysConfig.objects.filter(key="GITHUB_SERVICE_API").update(enable=True)
            elif type == "gitlab":
                ConsoleSysConfig.objects.filter(key="GITLAB_SERVICE_API").update(enable=True)
            elif type == "hubconf":
                ConsoleSysConfig.objects.filter(key="APPSTORE_IMAGE_HUB").update(enable=True)
            elif type == "ftpconf":
                ConsoleSysConfig.objects.filter(key="APPSTORE_SLUG_PATH").update(enable=True)
        else:
            if type == "github":
                ConsoleSysConfig.objects.filter(key="GITHUB_SERVICE_API").update(enable=False)
            elif type == "gitlab":
                ConsoleSysConfig.objects.filter(key="GITLAB_SERVICE_API").update(enable=False)
            elif type == "hubconf":
                ConsoleSysConfig.objects.filter(key="APPSTORE_IMAGE_HUB").update(enable=False)
            elif type == "ftpconf":
                ConsoleSysConfig.objects.filter(key="APPSTORE_SLUG_PATH").update(enable=False)
        custom_settings.reload()
config_service = ConfigService()