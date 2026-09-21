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


class ConfigExistError(Exception):
    pass


class IntegrityError(Exception):
    pass


class ConcurrentConfigManager(DummyQuerySet):
    def __init__(self, existing_config):
        self.existing_config = existing_config
        self.get_calls = []

    def create(self, **kwargs):
        raise IntegrityError("duplicate config key")

    def get(self, **kwargs):
        self.get_calls.append(kwargs)
        return self.existing_config


class ExistingConfigBeforeCreateManager(DummyQuerySet):
    def exists(self):
        return True

    def create(self, **kwargs):
        raise AssertionError("create must not be called for an existing config")


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


class ConfigQueryResult(list):
    def exists(self):
        return bool(self)


class ExistingConfigManager(object):
    def __init__(self, configs):
        self.configs = {config.key: config for config in configs}
        self.filter_calls = []
        self.get_calls = []

    def filter(self, **kwargs):
        self.filter_calls.append(kwargs)
        if "key__in" in kwargs:
            keys = kwargs["key__in"]
            return ConfigQueryResult(self.configs[key] for key in keys if key in self.configs)
        key = kwargs.get("key")
        return ConfigQueryResult([self.configs[key]] if key in self.configs else [])

    def get(self, **kwargs):
        self.get_calls.append(kwargs)
        return self.configs[kwargs["key"]]


class CreatingConfigManager(ExistingConfigManager):
    def __init__(self):
        super(CreatingConfigManager, self).__init__([])
        self.create_calls = []

    def create(self, **kwargs):
        self.create_calls.append(kwargs)
        config = types.SimpleNamespace(**kwargs)
        self.configs[config.key] = config
        return config


class ConfigAppearingBeforeCreateManager(ExistingConfigManager):
    def filter(self, **kwargs):
        self.filter_calls.append(kwargs)
        if "key__in" in kwargs:
            return ConfigQueryResult()
        key = kwargs.get("key")
        return ConfigQueryResult([self.configs[key]] if key in self.configs else [])

    def create(self, **kwargs):
        raise AssertionError("create must not be called after the config appears")


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
        install_stub("console.exception.exceptions", ConfigExistError=ConfigExistError)
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

    # capability_id: console.enterprise-config.concurrent-initialization
    def test_add_config_returns_existing_record_when_concurrent_create_wins(self):
        config_service = self.import_config_service_module()
        existing_config = types.SimpleNamespace(key="GLOBAL_IMAGE_REGISTRY", value=None, enable=False)
        manager = ConcurrentConfigManager(existing_config)
        config_service.ConsoleSysConfig = types.SimpleNamespace(objects=manager, DoesNotExist=LookupError)
        reload_calls = []
        config_service.custom_settings = types.SimpleNamespace(reload=lambda: reload_calls.append(True))

        config = config_service.ConfigService().add_config("GLOBAL_IMAGE_REGISTRY", None, "string")

        self.assertIs(config, existing_config)
        self.assertEqual(manager.get_calls, [{"key": "GLOBAL_IMAGE_REGISTRY"}])
        self.assertEqual(reload_calls, [])

    def test_add_config_rejects_config_existing_before_request(self):
        config_service = self.import_config_service_module()
        config_service.ConsoleSysConfig = types.SimpleNamespace(objects=ExistingConfigBeforeCreateManager())

        with self.assertRaises(ConfigExistError):
            config_service.ConfigService().add_config("GLOBAL_IMAGE_REGISTRY", None, "string")

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

    def test_initialization_loads_existing_config_keys_in_one_query(self):
        config_service = self.import_config_service_module()
        manager = ExistingConfigManager([
            types.SimpleNamespace(key="BASE_KEY", type="string", value="database-base", enable=False),
            types.SimpleNamespace(key="CONFIG_KEY", type="string", value="database-config", enable=True),
        ])
        config_service.ConsoleSysConfig = types.SimpleNamespace(objects=manager)
        service = config_service.ConfigService()
        service.base_cfg_keys = ["BASE_KEY"]
        service.base_cfg_keys_value = {
            "BASE_KEY": {
                "value": "default-base",
                "desc": "base",
                "enable": True,
            }
        }
        service.cfg_keys = ["CONFIG_KEY"]
        service.cfg_keys_value = {
            "CONFIG_KEY": {
                "value": "default-config",
                "desc": "config",
                "enable": False,
            }
        }
        service.get_custom_fields = lambda: []

        result = service.initialization_or_get_config

        self.assertEqual(result["base_key"], {"enable": False, "value": "default-base"})
        self.assertEqual(result["config_key"], {"enable": True, "value": "database-config"})
        self.assertEqual(manager.filter_calls, [{"key__in": ["BASE_KEY", "CONFIG_KEY"]}])
        self.assertEqual(manager.get_calls, [])

    def test_initialization_keeps_creating_missing_config_keys(self):
        config_service = self.import_config_service_module()
        manager = CreatingConfigManager()
        config_service.ConsoleSysConfig = types.SimpleNamespace(objects=manager)
        service = config_service.ConfigService()
        service.base_cfg_keys = ["BASE_KEY"]
        service.base_cfg_keys_value = {
            "BASE_KEY": {
                "value": "default-base",
                "desc": "base",
                "enable": True,
            }
        }
        service.cfg_keys = ["CONFIG_KEY"]
        service.cfg_keys_value = {
            "CONFIG_KEY": {
                "value": "default-config",
                "desc": "config",
                "enable": False,
            }
        }
        service.get_custom_fields = lambda: []

        result = service.initialization_or_get_config

        self.assertEqual(result["base_key"], {"enable": True, "value": "default-base"})
        self.assertEqual(result["config_key"], {"enable": False, "value": "default-config"})
        self.assertEqual([call["key"] for call in manager.create_calls], ["BASE_KEY", "CONFIG_KEY"])

    # capability_id: console.enterprise-config.concurrent-initialization
    def test_initialization_uses_config_created_after_bulk_lookup(self):
        config_service = self.import_config_service_module()
        existing_config = types.SimpleNamespace(
            key="GLOBAL_IMAGE_REGISTRY",
            type="string",
            value=None,
            enable=False,
        )
        manager = ConfigAppearingBeforeCreateManager([existing_config])
        config_service.ConsoleSysConfig = types.SimpleNamespace(objects=manager, DoesNotExist=LookupError)
        service = config_service.ConfigService()
        service.base_cfg_keys = []
        service.base_cfg_keys_value = {}
        service.cfg_keys = ["GLOBAL_IMAGE_REGISTRY"]
        service.cfg_keys_value = {
            "GLOBAL_IMAGE_REGISTRY": {
                "value": None,
                "desc": "global registry",
                "enable": False,
            }
        }
        service.get_custom_fields = lambda: []

        result = service.initialization_or_get_config

        self.assertEqual(result["global_image_registry"], {"enable": False, "value": None})
        self.assertEqual(manager.get_calls, [{"key": "GLOBAL_IMAGE_REGISTRY"}])
