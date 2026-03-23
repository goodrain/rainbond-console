import importlib
import sys
import types
from unittest import TestCase
from unittest.mock import MagicMock


class TenantServiceVolumeStub(object):
    SHARE = "share-file"
    LOCAL = "local"
    TMPFS = "memoryfs"
    CONFIGFILE = "config-file"
    objects = MagicMock()


class DummyModel(object):
    objects = MagicMock()


def install_stub(module_name, **attrs):
    module = types.ModuleType(module_name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[module_name] = module


class TenantServiceVolumnRepositoryTests(TestCase):
    def tearDown(self):
        for module_name in (
            "console.repositories.app_config",
            "console.exception.main",
            "console.utils.shortcuts",
            "www.db.base",
            "www.models.main",
            "www.models.service_publish",
        ):
            sys.modules.pop(module_name, None)

    def import_repository_module(self):
        install_stub("console.exception.main", AbortRequest=Exception)
        install_stub("console.utils.shortcuts", get_object_or_404=lambda *args, **kwargs: None)
        install_stub("www.db.base", BaseConnection=object)
        install_stub(
            "www.models.service_publish",
            ServiceExtendMethod=DummyModel,
        )
        install_stub(
            "www.models.main",
            GatewayCustomConfiguration=DummyModel,
            ServiceDomain=DummyModel,
            ServiceDomainCertificate=DummyModel,
            ServiceTcpDomain=DummyModel,
            TenantServiceAuth=DummyModel,
            TenantServiceConfigurationFile=DummyModel,
            TenantServiceEnv=DummyModel,
            TenantServiceEnvVar=DummyModel,
            TenantServiceMountRelation=DummyModel,
            TenantServiceRelation=DummyModel,
            TenantServicesPort=DummyModel,
            TenantServiceVolume=TenantServiceVolumeStub,
            ThirdPartyServiceEndpoints=DummyModel,
        )
        return importlib.import_module("console.repositories.app_config")

    def test_list_custom_volumes_treats_local_path_as_builtin_volume_type(self):
        repository_module = self.import_repository_module()
        filtered_queryset = MagicMock()
        repository_module.TenantServiceVolume.objects.filter.return_value = filtered_queryset

        repository_module.TenantServiceVolumnRepository().list_custom_volumes(["service-id"])

        filtered_queryset.exclude.assert_called_once_with(volume_type__in=[
            TenantServiceVolumeStub.CONFIGFILE,
            TenantServiceVolumeStub.SHARE,
            TenantServiceVolumeStub.LOCAL,
            TenantServiceVolumeStub.TMPFS,
            "local-path",
        ])
