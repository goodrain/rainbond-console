# -*- coding: utf8 -*-
from www.models.main import ConsoleConfig


class CustomConfigsReporsitory(object):
    @staticmethod
    def bulk_create(configs):
        ConsoleConfig.objects.bulk_create(configs)

    @staticmethod
    def list():
        return ConsoleConfig.objects.filter().values()

    @staticmethod
    def delete(keys):
        return ConsoleConfig.objects.filter(key__in=keys).delete()


custom_configs_repo = CustomConfigsReporsitory()
