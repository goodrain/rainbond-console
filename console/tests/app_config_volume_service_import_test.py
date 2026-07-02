# -*- coding: utf-8 -*-
import importlib
import sys
import types
from types import SimpleNamespace
from unittest import TestCase


class AppConfigVolumeServiceImportTests(TestCase):

    def setUp(self):
        self._original_modules = {}

    def tearDown(self):
        for module_name, original in self._original_modules.items():
            if original is None:
                sys.modules.pop(module_name, None)
            else:
                sys.modules[module_name] = original

    def install_stub(self, module_name, **attrs):
        if module_name not in self._original_modules:
            self._original_modules[module_name] = sys.modules.get(module_name)
        module = types.ModuleType(module_name)
        for key, value in attrs.items():
            setattr(module, key, value)
        sys.modules[module_name] = module
        return module

    def forget_module(self, module_name):
        if module_name not in self._original_modules:
            self._original_modules[module_name] = sys.modules.get(module_name)
        sys.modules.pop(module_name, None)

    def install_app_config_init_stubs(self):
        class DummyService(object):
            pass

        self.install_stub("console.services.app_config.app_relation_service",
                          AppServiceRelationService=DummyService)
        self.install_stub("console.services.app_config.deploy_type_service",
                          DeployTypeService=DummyService)
        self.install_stub("console.services.app_config.domain_service", DomainService=DummyService)
        self.install_stub(
            "console.services.app_config.env_service",
            AppEnvService=DummyService,
            AppEnvVarService=DummyService,
        )
        self.install_stub("console.services.app_config.extend_service", AppExtendService=DummyService)
        self.install_stub("console.services.app_config.label_service", LabelService=DummyService)
        self.install_stub("console.services.app_config.mnt_service", AppMntService=DummyService)
        self.install_stub(
            "console.services.app_config.port_service",
            AppPortService=DummyService,
            EndpointService=DummyService,
        )
        self.install_stub("console.services.app_config.probe_service", ProbeService=DummyService)
        self.install_stub("console.services.app_config.service_monitor",
                          ComponentServiceMonitor=DummyService)

    def install_volume_service_dependency_stubs(self):
        class ServiceHandleException(Exception):
            pass

        class RegionInvokeApi(object):
            class CallApiError(Exception):
                status = 500

        class DummyModel(object):
            pass

        self.install_stub(
            "console.constants",
            AppConstants=object,
            ServiceLanguageConstants=object,
        )
        self.install_stub(
            "console.enum.component_enum",
            ComponentType=SimpleNamespace(vm=SimpleNamespace(value="vm")),
        )
        self.install_stub(
            "console.exception.main",
            ErrVolumePath=Exception,
            ServiceHandleException=ServiceHandleException,
        )
        self.install_stub(
            "console.models.main",
            ConsoleSysConfig=SimpleNamespace(objects=SimpleNamespace()),
        )
        self.install_stub("console.repositories.app", service_repo=object())
        self.install_stub("console.repositories.app_config", mnt_repo=object(), volume_repo=object())
        self.install_stub("console.services.exception", ErrVolumeTypeDoNotAllowMultiNode=Exception)
        self.install_stub("console.utils.urlutil", is_path_legal=lambda path: True)
        self.install_stub("www.apiclient.regionapi", RegionInvokeApi=RegionInvokeApi)
        self.install_stub(
            "www.models.main",
            TenantServiceInfo=DummyModel,
            Tenants=DummyModel,
            TenantServiceVolume=DummyModel,
        )
        self.install_stub("www.utils.crypt", make_uuid=lambda: "uuid")

    # capability_id: console.app-config.volume-service-module-export
    def test_volume_service_module_exports_package_singleton(self):
        self.forget_module("console.services.app_config")
        self.forget_module("console.services.app_config.volume_service")
        self.install_app_config_init_stubs()
        self.install_volume_service_dependency_stubs()

        package = importlib.import_module("console.services.app_config")
        module = importlib.import_module("console.services.app_config.volume_service")

        self.assertTrue(
            hasattr(module, "volume_service"),
            "volume_service.py must export volume_service for direct imports",
        )
        self.assertIs(module.volume_service, package.volume_service)
        self.assertIsInstance(module.volume_service, module.AppVolumeService)
