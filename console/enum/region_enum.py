# -*- coding: utf-8 -*-
from enum import IntEnum


class RegionStatusEnum(IntEnum):
    NOTREADY = 0
    ONLINE = 1
    OFFLINE = 2
    MAINTAIN = 3

    @classmethod
    def names(self):
        names = [name for name, item in list(self.__members__.items())]
        return names

    @classmethod
    def to_dict(self):
        d = {name: item.value for name, item in list(self.__members__.items())}
        return d
