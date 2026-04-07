import importlib
import sys
import types
from unittest import TestCase


class DummyQuerySet(object):
    def filter(self, *args, **kwargs):
        return self

    def exists(self):
        return False

    def count(self):
        return 0

    def __or__(self, other):
        return self

    def __iter__(self):
        return iter([])


class DummyModel(object):
    objects = DummyQuerySet()


class ConfigKey(object):
    def __init__(self, name):
        self.name = name


def install_stub(module_name, **attrs):
    module = types.ModuleType(module_name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[module_name] = module


class EnterpriseConfigServiceTests(TestCase):
    def tearDown(self):
        for module_name in (
            "console.services.config_service",
            "console.exception.exceptions",
            "console.models.main",
            "console.repositories.oauth_repo",
            "console.repositories.user_repo",
            "console.services.enterprise_services",
            "console.utils.oauth.oauth_types",
            "console.enum.system_config",
            "goodrain_web.custom_config",
            "django.conf",
            "django.db.models",
        ):
            sys.modules.pop(module_name, None)

    def import_config_service_module(self):
        install_stub("console.exception.exceptions", ConfigExistError=Exception)
        install_stub("console.models.main", ConsoleSysConfig=DummyModel, OAuthServices=DummyModel)
        install_stub(
            "console.repositories.oauth_repo",
            oauth_user_repo=types.SimpleNamespace(get_by_oauths_user_id=lambda *args, **kwargs: []),
        )
        install_stub("console.repositories.user_repo", user_repo=object())
        install_stub(
            "console.services.enterprise_services",
            enterprise_services=types.SimpleNamespace(
                get_enterprise_by_enterprise_id=lambda enterprise_id: types.SimpleNamespace(enterprise_id=enterprise_id)
            ),
        )
        install_stub(
            "console.utils.oauth.oauth_types",
            NoSupportOAuthType=Exception,
            get_oauth_instance=lambda *args, **kwargs: types.SimpleNamespace(get_authorize_url=lambda: ""),
        )
        install_stub(
            "console.enum.system_config",
            ConfigKeyEnum=types.SimpleNamespace(
                SECURITY_RESTRICTIONS=ConfigKey("SECURITY_RESTRICTIONS"),
                ENTERPRISE_EDITION=ConfigKey("ENTERPRISE_EDITION"),
            ),
        )
        install_stub(
            "goodrain_web.custom_config",
            custom_config=types.SimpleNamespace(reload=lambda: None),
        )
        install_stub("django.conf", settings=types.SimpleNamespace())
        install_stub("django.db.models", Q=lambda *args, **kwargs: None)
        return importlib.import_module("console.services.config_service")

    # capability_id: console.enterprise-config.user-context
    def test_enterprise_config_service_defaults_user_id_to_none(self):
        config_service = self.import_config_service_module()

        service = config_service.EnterpriseConfigService("enterprise-id")

        self.assertEqual(service.enterprise_id, "enterprise-id")
        self.assertIsNone(service.user_id)

    # capability_id: console.enterprise-config.user-context
    def test_enterprise_config_service_keeps_explicit_user_id(self):
        config_service = self.import_config_service_module()

        service = config_service.EnterpriseConfigService("enterprise-id", "user-id")

        self.assertEqual(service.user_id, "user-id")
