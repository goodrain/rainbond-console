# -*- coding: utf-8 -*-
from www.models.main import ConsoleConfig
from console.repositories.custom_configs import custom_configs_repo


class CustomConfigsService(object):
    @staticmethod
    def bulk_create_or_update(configs):
        create_config_models = []
        update_config_models = []
        old_configs = custom_configs_repo.list()
        exist_configs = {cfg["key"]: cfg["value"] for cfg in old_configs}
        for config in configs:
            if not config.get("key"):
                continue
            if not exist_configs.get(config["key"]):
                c_config_model = ConsoleConfig(key=config["key"], value=config.get("value", ""))
                create_config_models.append(c_config_model)
                continue
            u_config_model = ConsoleConfig(key=config["key"], value=config.get("value", ""))
            update_config_models.append(u_config_model)
        delete_keys = [ucm.key for ucm in update_config_models]
        custom_configs_repo.delete(delete_keys)
        create_config_models.extend(update_config_models)
        return custom_configs_repo.bulk_create(create_config_models)

    @staticmethod
    def list():
        return custom_configs_repo.list()


custom_configs_service = CustomConfigsService()
