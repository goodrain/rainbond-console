# -*- coding: utf-8 -*-
from www.models.main import ConsoleConfig
from console.repositories.custom_configs import custom_configs_repo


class CustomConfigsService(object):
    @staticmethod
    def bulk_create(configs):
        config_models = []
        for config in configs:
            if not config.get("key"):
                continue
            config_model = ConsoleConfig(key=config["key"], value=config.get("value", ""))
            config_models.append(config_model)
        return custom_configs_repo.bulk_create(config_models)

    @staticmethod
    def list():
        return custom_configs_repo.list()


custom_configs_service = CustomConfigsService()
