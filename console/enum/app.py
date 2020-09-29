# -*- coding: utf-8 -*-
from console.enum.common import AutoNumber


class GovernanceModeEnum(AutoNumber):
    BUILD_IN_SERVICE_MESH = ()
    KUBERNETES_NATIVE_SERVICE = ()

    @classmethod
    def choices(cls):
        return [(key.value, key.name) for key in cls]
