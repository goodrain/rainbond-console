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


class IntegrityError(Exception):
    pass


class CustomFieldQuerySet(object):
    def __init__(self, configs):
        self.configs = configs

    def count(self):
        return len(self.configs)

    def __iter__(self):
        return iter(self.configs)


class CustomFieldManager(object):
    def __init__(self, configs):
        self.configs = configs

    def filter(self, **kwargs):
        configs = self.configs
        for key, value in kwargs.items():
            if key == "desc__startswith":
                configs = [config for config in configs if config.desc.startswith(value)]
            else:
                configs = [config for config in configs if getattr(config, key) == value]
        return CustomFieldQuerySet(configs)


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
            "django.db",
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
        install_stub("django.db", IntegrityError=IntegrityError)
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

    # capability_id: console.enterprise-config.custom-fields-disabled-bool
    def test_get_custom_fields_includes_disabled_bool_fields(self):
        config_service = self.import_config_service_module()
        disabled_field = types.SimpleNamespace(
            key="SHOW_AI_ASSISTANT",
            type="bool",
            value="false",
            enable=False,
            enterprise_id="enterprise-id",
            desc="自定义字段: show_ai_assistant",
        )
        config_service.ConsoleSysConfig = types.SimpleNamespace(objects=CustomFieldManager([disabled_field]))

        service = config_service.EnterpriseConfigService("enterprise-id", "user-id")

        self.assertEqual(
            service.get_custom_fields(),
            [{
                "key": "show_ai_assistant",
                "value": "false",
                "type": "bool",
                "enable": False,
            }],
        )

    # capability_id: console.enterprise-config.concurrent-initialization
    def test_add_config_returns_existing_record_when_concurrent_create_wins(self):
        config_service = self.import_config_service_module()
        existing_config = types.SimpleNamespace(key="TITLE", value="", enable=True)

        class RaceQuerySet(object):
            def exists(self):
                return False

        class RaceManager(object):
            def __init__(self):
                self.get_kwargs = None

            def filter(self, **kwargs):
                return RaceQuerySet()

            def create(self, **kwargs):
                raise IntegrityError("UNIQUE constraint failed: console_sys_config.key")

            def get(self, **kwargs):
                self.get_kwargs = kwargs
                return existing_config

        race_manager = RaceManager()

        class RaceConsoleSysConfig(object):
            objects = race_manager
            DoesNotExist = LookupError

        reload_calls = []
        config_service.ConsoleSysConfig = RaceConsoleSysConfig
        config_service.custom_settings = types.SimpleNamespace(reload=lambda: reload_calls.append(True))

        service = config_service.EnterpriseConfigService("enterprise-id", "user-id")
        config = service.add_config(key="TITLE", default_value="", type="string", enable=True, desc="title")

        self.assertIs(config, existing_config)
        self.assertEqual(race_manager.get_kwargs, {"key": "TITLE"})
        self.assertEqual(reload_calls, [])
