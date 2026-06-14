import importlib
import sys
import types
from unittest import TestCase
from unittest.mock import MagicMock


class DummyAtomic(object):
    def __call__(self, func):
        return func


class FakePaginator(object):
    def __init__(self, items, page_size):
        self.items = items
        self.count = len(items)

    def page(self, page):
        return self.items


class DummyApplicationConfigGroup(object):
    class DoesNotExist(Exception):
        pass


class DummyErrAppConfigGroupExists(Exception):
    pass


class DummyErrAppConfigGroupNotFound(Exception):
    pass


def install_stub(module_name, **attrs):
    module = types.ModuleType(module_name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[module_name] = module


class AppConfigGroupServiceWorkflowTests(TestCase):
    def tearDown(self):
        for module_name in (
            "console.services.app_config_group",
            "console.repositories.app_config_group",
            "console.repositories.app",
            "console.repositories.region_app",
            "console.models.main",
            "console.exception.bcode",
            "www.apiclient.regionapi",
            "www.utils.crypt",
            "django.db",
            "django.core.paginator",
        ):
            sys.modules.pop(module_name, None)

    def import_service_module(self):
        self.app_config_group_repo = MagicMock()
        self.app_config_group_service_repo = MagicMock()
        self.app_config_group_item_repo = MagicMock()
        self.service_repo = MagicMock()
        self.region_app_repo = MagicMock()
        self.region_api = MagicMock()

        install_stub(
            "console.repositories.app_config_group",
            app_config_group_repo=self.app_config_group_repo,
            app_config_group_service_repo=self.app_config_group_service_repo,
            app_config_group_item_repo=self.app_config_group_item_repo,
        )
        install_stub("console.repositories.app", service_repo=self.service_repo)
        install_stub("console.repositories.region_app", region_app_repo=self.region_app_repo)
        install_stub("console.models.main", ApplicationConfigGroup=DummyApplicationConfigGroup, ConfigGroupItem=object, ConfigGroupService=object)
        install_stub(
            "console.exception.bcode",
            ErrAppConfigGroupExists=DummyErrAppConfigGroupExists,
            ErrAppConfigGroupNotFound=DummyErrAppConfigGroupNotFound,
        )
        install_stub("www.apiclient.regionapi", RegionInvokeApi=lambda: self.region_api)
        install_stub("www.utils.crypt", make_uuid=lambda: "config-group-id")
        install_stub("django.db", transaction=types.SimpleNamespace(atomic=DummyAtomic()))
        install_stub("django.core.paginator", Paginator=FakePaginator)

        service_module = importlib.import_module("console.services.app_config_group")
        service_module.app_config_group_repo = self.app_config_group_repo
        service_module.app_config_group_service_repo = self.app_config_group_service_repo
        service_module.app_config_group_item_repo = self.app_config_group_item_repo
        service_module.service_repo = self.service_repo
        service_module.region_app_repo = self.region_app_repo
        service_module.region_api = self.region_api
        return service_module

    # capability_id: console.app-config-group.create
    def test_create_config_group_creates_remote_and_local_records(self):
        service_module = self.import_service_module()
        cgroup = types.SimpleNamespace(config_group_id="config-group-id", region_name="demo-region", config_group_name="demo")
        self.app_config_group_repo.get.side_effect = service_module.ApplicationConfigGroup.DoesNotExist()
        self.app_config_group_repo.create.return_value = cgroup
        self.region_app_repo.get_region_app_id.return_value = "region-app-id"
        service_module.create_items_and_services = MagicMock()
        service_module.app_config_group_service.get_config_group = MagicMock(return_value={"config_group_name": "demo"})

        result = service_module.app_config_group_service.create_config_group(
            12,
            "demo",
            [{"item_key": "KEY", "item_value": "VALUE"}],
            "env",
            True,
            ["svc-1"],
            "demo-region",
            "demo-team",
        )

        self.assertEqual(result["config_group_name"], "demo")
        self.app_config_group_repo.create.assert_called_once()
        service_module.create_items_and_services.assert_called_once_with(cgroup, [{"item_key": "KEY", "item_value": "VALUE"}], ["svc-1"])
        self.region_api.create_app_config_group.assert_called_once()

    # capability_id: console.app-config-group.update
    def test_update_config_group_updates_remote_and_local_records(self):
        service_module = self.import_service_module()
        cgroup = types.SimpleNamespace(config_group_id="config-group-id", region_name="demo-region", config_group_name="demo")
        self.app_config_group_repo.get.return_value = cgroup
        self.region_app_repo.get_region_app_id.return_value = "region-app-id"
        service_module.create_items_and_services = MagicMock()
        service_module.app_config_group_service.get_config_group = MagicMock(return_value={"config_group_name": "demo", "enable": False})

        result = service_module.app_config_group_service.update_config_group(
            "demo-region",
            12,
            "demo",
            [{"item_key": "KEY", "item_value": "NEW"}],
            False,
            ["svc-1"],
            "demo-team",
        )

        self.assertEqual(result["config_group_name"], "demo")
        self.app_config_group_repo.update.assert_called_once()
        self.app_config_group_item_repo.delete.assert_called_once_with("config-group-id")
        self.app_config_group_service_repo.delete.assert_called_once_with("config-group-id")
        service_module.create_items_and_services.assert_called_once_with(cgroup, [{"item_key": "KEY", "item_value": "NEW"}], ["svc-1"])
        self.region_api.update_app_config_group.assert_called_once()

    # capability_id: console.app-config-group.delete
    def test_delete_config_group_deletes_remote_and_local_records(self):
        service_module = self.import_service_module()
        cgroup = types.SimpleNamespace(config_group_id="config-group-id", region_name="demo-region", config_group_name="demo")
        self.app_config_group_repo.get.return_value = cgroup
        self.region_app_repo.get_region_app_id.return_value = "region-app-id"

        service_module.app_config_group_service.delete_config_group("demo-region", "demo-team", 12, "demo")

        self.region_api.delete_app_config_group.assert_called_once_with("demo-region", "demo-team", "region-app-id", "demo")
        self.app_config_group_item_repo.delete.assert_called_once_with("config-group-id")
        self.app_config_group_service_repo.delete.assert_called_once_with("config-group-id")
        self.app_config_group_repo.delete.assert_called_once_with("demo-region", 12, "demo")

    # capability_id: console.app-config-group.get
    def test_get_config_group_returns_built_response(self):
        service_module = self.import_service_module()
        cgroup = types.SimpleNamespace(config_group_id="config-group-id")
        self.app_config_group_repo.get.return_value = cgroup
        service_module.build_response = MagicMock(return_value={"config_group_name": "demo", "services_num": 1})

        result = service_module.app_config_group_service.get_config_group("demo-region", 12, "demo")

        self.assertEqual(result["config_group_name"], "demo")
        service_module.build_response.assert_called_once_with(cgroup)

    # capability_id: console.app-config-group.list
    def test_list_config_groups_returns_items_and_total(self):
        service_module = self.import_service_module()
        cgroup = types.SimpleNamespace(config_group_id="config-group-id")

        class FakeQuerySet(list):
            def filter(self, **kwargs):
                return self

        self.app_config_group_repo.list.return_value = FakeQuerySet([cgroup])
        service_module.build_response = MagicMock(return_value={"config_group_name": "demo"})

        items, total = service_module.app_config_group_service.list_config_groups("demo-region", 12, 1, 10)

        self.assertEqual(total, 1)
        self.assertEqual(items, [{"config_group_name": "demo"}])
