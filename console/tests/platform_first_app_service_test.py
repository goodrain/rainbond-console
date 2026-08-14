# -*- coding: utf-8 -*-
import importlib.util
from pathlib import Path
import sys
from types import ModuleType
from unittest import TestCase, mock


class DoesNotExist(Exception):
    pass


class ConfigRecord(object):
    def __init__(self, manager, **kwargs):
        self._manager = manager
        self.save_count = 0
        self.__dict__.update(kwargs)

    def save(self, update_fields=None):
        self.save_count += 1


class ConfigManager(object):
    def __init__(self, records=None):
        self.records = list(records or [])
        for record in self.records:
            record._manager = self
        self.get_or_create_calls = []

    def matching(self, kwargs):
        return [record for record in self.records
                if all(getattr(record, key) == value for key, value in kwargs.items())]

    def get(self, **kwargs):
        records = self.matching(kwargs)
        if not records:
            raise DoesNotExist()
        return records[0]

    def get_or_create(self, defaults=None, **kwargs):
        self.get_or_create_calls.append((kwargs, defaults))
        try:
            return self.get(**kwargs), False
        except DoesNotExist:
            values = dict(defaults or {})
            values.update(kwargs)
            record = ConfigRecord(self, **values)
            self.records.append(record)
            return record, True


class ComponentManager(object):
    def __init__(self, exists):
        self._exists = exists

    def exists(self):
        return self._exists


class ConsoleSysConfigStub(object):
    DoesNotExist = DoesNotExist
    objects = None


class TenantServiceInfoStub(object):
    objects = None


def install_stub(module_name, **attrs):
    module = ModuleType(module_name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[module_name] = module


def load_platform_first_app_module():
    module_names = ("django.db", "console.models.main", "www.models.main")
    original_modules = {name: sys.modules.get(name) for name in module_names}
    install_stub("django.db")
    install_stub("console.models.main", ConsoleSysConfig=ConsoleSysConfigStub)
    install_stub("www.models.main", TenantServiceInfo=TenantServiceInfoStub)
    try:
        module_path = Path(__file__).parents[1] / "services" / "platform_first_app_service.py"
        spec = importlib.util.spec_from_file_location("_platform_first_app_service_test_target", module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except FileNotFoundError:
        return None
    finally:
        for name, original in original_modules.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original


platform_first_app_module = load_platform_first_app_module()


class PlatformFirstAppServiceTests(TestCase):
    def setUp(self):
        self.assertIsNotNone(
            platform_first_app_module,
            "console.services.platform_first_app_service must be implemented",
        )

    def configure(self, component_exists=False, records=None):
        manager = ConfigManager(records)
        platform_first_app_module.ConsoleSysConfig.objects = manager
        platform_first_app_module.TenantServiceInfo.objects = ComponentManager(component_exists)
        return manager, platform_first_app_module.PlatformFirstAppService()

    def test_missing_field_on_empty_platform_initializes_false(self):
        manager, service = self.configure(component_exists=False)

        self.assertFalse(service.is_deployed())
        self.assertEqual(1, len(manager.records))
        self.assertEqual("FIRST_APP_DEPLOYED", manager.records[0].key)
        self.assertEqual("", manager.records[0].enterprise_id)
        self.assertEqual("bool", manager.records[0].type)
        self.assertEqual("0", manager.records[0].value)
        self.assertTrue(manager.records[0].enable)

    def test_missing_field_on_legacy_platform_with_component_initializes_true(self):
        manager, service = self.configure(component_exists=True)

        self.assertTrue(service.is_deployed())
        self.assertEqual("1", manager.records[0].value)

    def test_existing_zero_and_one_values_are_parsed_as_booleans(self):
        for value, expected in (("0", False), ("1", True)):
            with self.subTest(value=value):
                record = ConfigRecord(
                    None,
                    key="FIRST_APP_DEPLOYED",
                    enterprise_id="",
                    type="bool",
                    value=value,
                    enable=True,
                )
                manager, service = self.configure(records=[record])

                self.assertEqual(expected, service.is_deployed())
                self.assertEqual([], manager.get_or_create_calls)

    def test_mark_deployed_is_idempotent(self):
        record = ConfigRecord(
            None,
            key="FIRST_APP_DEPLOYED",
            enterprise_id="",
            type="bool",
            value="0",
            enable=True,
        )
        manager, service = self.configure(records=[record])

        service.mark_deployed()
        service.mark_deployed()

        self.assertEqual(1, len(manager.records))
        self.assertEqual("1", record.value)
        self.assertEqual(1, record.save_count)

    def test_only_running_status_marks_the_first_app_as_deployed(self):
        _, service = self.configure()

        self.assertTrue(service.is_running_status({"status": "running"}))
        for status in ("starting", "waiting", "succeeded", "closed", "unKnow", None):
            with self.subTest(status=status):
                self.assertFalse(service.is_running_status({"status": status}))

    def test_safe_mark_if_running_only_marks_running_status(self):
        _, service = self.configure()
        service.mark_deployed = mock.Mock()

        service.safe_mark_if_running({"status": "starting"})
        service.safe_mark_if_running({"status": "running"})

        service.mark_deployed.assert_called_once_with()

    def test_safe_mark_if_running_does_not_break_status_queries_on_database_error(self):
        _, service = self.configure()
        service.mark_deployed = mock.Mock(side_effect=RuntimeError("database unavailable"))

        service.safe_mark_if_running({"status": "running"})

        service.mark_deployed.assert_called_once_with()

    def test_app_status_marks_after_kubeblocks_status_override(self):
        source = (Path(__file__).parents[1] / "views" / "app_overview.py").read_text()

        override_position = source.index("status_map = kubeblocks_status")
        mark_position = source.index("platform_first_app_service.safe_mark_if_running(status_map)")

        self.assertGreater(mark_position, override_position)

    def test_config_info_sets_platform_state_after_enterprise_config_merge(self):
        source = (Path(__file__).parents[1] / "views" / "logos.py").read_text()

        merge_position = source.index("data.update(ent_config)")
        state_position = source.index('data["first_app_deployed"] = platform_first_app_service.is_deployed()')

        self.assertGreater(state_position, merge_position)
