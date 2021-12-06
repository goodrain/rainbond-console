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

    @classmethod
    def use_k8s_service_name_governance_modes(cls):
        return [cls.KUBERNETES_NATIVE_SERVICE.name, cls.ISTIO_SERVICE_MESH.name]


class AppType(AutoNumber):
    rainbond = ()
    helm = ()
