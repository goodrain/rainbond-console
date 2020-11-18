# -*- coding: utf-8 -*-
from enum import IntEnum


class EnterpriseRolesEnum(IntEnum):
    admin = 0
    app_store = 1

    def names(self):
        return [name for name, item in self.__members__.items()]

    def to_dict(self):
        return {name: item.value for name, item in self.__members__.items()}
