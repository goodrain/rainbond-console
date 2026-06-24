# -*- coding: utf8 -*-
from typing import Dict, List, Tuple

from django.db.models import QuerySet

from www.models.main import ConsoleConfig


class CustomConfigsReporsitory(object):
    @staticmethod
    def bulk_create(configs: List[ConsoleConfig]) -> None:
        ConsoleConfig.objects.bulk_create(configs)

    @staticmethod
    def list() -> QuerySet:
        return ConsoleConfig.objects.filter(user_nick_name="").values()

    @staticmethod
    def list_by_user_nick_name(user_nick_name: str) -> QuerySet:
        return ConsoleConfig.objects.filter(user_nick_name=user_nick_name).values()

    @staticmethod
    def delete(keys: List[str]) -> Tuple[int, Dict[str, int]]:
        return ConsoleConfig.objects.filter(key__in=keys).delete()


custom_configs_repo = CustomConfigsReporsitory()
