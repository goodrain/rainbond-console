# -*- coding: utf-8 -*-
from console.enum.common import AutoNumber


class GovernanceModeEnum(AutoNumber):
    BUILD_IN_SERVICE_MESH = ()
    KUBERNETES_NATIVE_SERVICE = ()
    ISTIO_SERVICE_MESH = ()

    @classmethod
    def choices(cls):
        return [(key.value, key.name) for key in cls]

    @classmethod
    def names(cls):
        return [key.name for key in cls]


class AppType(AutoNumber):
    rainbond = ()
    helm = ()
