# -*- coding: utf8 -*-
import datetime

from cadmin.models import ConsoleSysConfig


class ConfigService(object):
    def check_regist_status(self):
        register_config = ConsoleSysConfig.objects.filter(key='REGISTER_STATUS')
        if not register_status:
            config_key = "REGISTER_STATUS"
            config_value = "yes"
            config_type = "string"
            config_desc = "开启/关闭注册"
            create_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            register_config = ConsoleSysConfig.objects.create(key=config_key, type=config_type, value=config_value, desc=config_desc,
                                            create_time=create_time)
        return register_config


config_service_path = ConfigService()