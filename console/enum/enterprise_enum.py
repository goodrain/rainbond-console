# -*- coding: utf-8 -*-
from enum import IntEnum


class EnterpriseRolesEnum(IntEnum):
    admin = 0
    app_store = 1

    @classmethod
    def names(cls):
        return [name for name, item in list(cls.__members__.items())]

    @classmethod
    def to_dict(cls):
        return {name: item.value for name, item in list(cls.__members__.items())}
