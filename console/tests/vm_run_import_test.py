import importlib
import sys
import types
from unittest import TestCase


class VMRunImportTests(TestCase):

    def setUp(self):
        self._original_modules = {}

    def tearDown(self):
        for module_name, original in self._original_modules.items():
            if original is None:
                sys.modules.pop(module_name, None)
            else:
                sys.modules[module_name] = original
        sys.modules.pop("console.views.app_create.vm_run", None)

    def install_stub(self, module_name, **attrs):
        if module_name not in self._original_modules:
            self._original_modules[module_name] = sys.modules.get(module_name)
        module = types.ModuleType(module_name)
        for key, value in attrs.items():
            setattr(module, key, value)
        sys.modules[module_name] = module
        return module

    def test_vm_run_import_uses_package_level_volume_service_singleton(self):
        class DummyRegionTenantHeaderView(object):
            pass

        class DummyResponse(object):
            def __init__(self, data, status=None):
                self.data = data
                self.status_code = status

        def never_cache(func):
            return func

        app_config_module = self.install_stub("console.services.app_config", __path__=[], volume_service=object())
        self.install_stub("console.services.app_config.volume_service")
        self.install_stub(
            "console.exception.bcode", ErrK8sComponentNameExists=Exception, ErrVMImageNameExists=Exception)
        self.install_stub("console.exception.main", ResourceNotEnoughException=Exception)
        self.install_stub("console.repositories.virtual_machine", vm_repo=object())
        self.install_stub("console.services.app", app_service=object())
        self.install_stub("console.services.virtual_machine", vms=object())
        self.install_stub("console.views.base", RegionTenantHeaderView=DummyRegionTenantHeaderView)
        self.install_stub("console.services.group_service", group_service=object())
        self.install_stub("www.utils.return_message", general_message=lambda *args, **kwargs: {})
        self.install_stub("django.views.decorators.cache", never_cache=never_cache)
        self.install_stub("rest_framework.response", Response=DummyResponse)

        vm_run_module = importlib.import_module("console.views.app_create.vm_run")

        self.assertIs(vm_run_module.volume_service, app_config_module.volume_service)
