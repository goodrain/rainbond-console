# -*- coding: utf-8 -*-

from enum import Enum


class ActionType(Enum):
    BUILD = "build"
    UPDATE = "update"
    NOTHING = "nothing"
