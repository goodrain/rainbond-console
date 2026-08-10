# -*- coding: utf-8 -*-
import importlib
import sys
import types
from unittest import TestCase, mock


class DummyModel(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class PermissionQuerySet(object):
    def __init__(self, rows, manager):
        self.rows = rows
        self.manager = manager

    def values_list(self, *fields):
        return list(self.rows)

    def delete(self):
        self.manager.delete_count += 1


class PermissionManager(object):
    def __init__(self, rows):
        self.rows = rows
        self.all_count = 0
        self.delete_count = 0
        self.bulk_create_count = 0

    def all(self):
        self.all_count += 1
        return PermissionQuerySet(self.rows, self)

    def bulk_create(self, permissions):
        self.bulk_create_count += 1


def install_stub(module_name, **attrs):
    module = types.ModuleType(module_name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[module_name] = module


class PermsRepoPerformanceTests(TestCase):
    module_names = (
        "console.repositories.perm_repo",
        "console.exception.main",
        "console.models.main",
        "console.utils.perms",
        "www.models.main",
        "django.db",
        "django.db.models",
    )

    def tearDown(self):
        for module_name in self.module_names:
            sys.modules.pop(module_name, None)

    def import_perm_repo_module(self, metadata, stored_rows):
        manager = PermissionManager(stored_rows)
        perms_model = type("PermsInfo", (DummyModel,), {"objects": manager})
        install_stub("console.exception.main", ServiceHandleException=Exception)
        install_stub(
            "console.models.main",
            PermsInfo=perms_model,
            RoleInfo=DummyModel,
            RolePerms=DummyModel,
            UserRole=DummyModel,
        )
        install_stub("console.utils.perms", get_perms_metadata=lambda: list(metadata))
        install_stub("www.models.main", PermRelTenant=DummyModel, Users=DummyModel)
        install_stub("django.db", transaction=types.SimpleNamespace(atomic=lambda function: function))
        install_stub("django.db.models", Q=lambda *args, **kwargs: None, QuerySet=object)
        module = importlib.import_module("console.repositories.perm_repo")
        return module, manager

    def test_initialization_does_not_rebuild_permissions_when_only_row_order_differs(self):
        metadata = [
            ("view", "View", 100, "app", "team"),
            ("edit", "Edit", 200, "app", "team"),
        ]
        module, manager = self.import_perm_repo_module(metadata, list(reversed(metadata)))

        module.PermsRepo().initialize_permission_settings()

        self.assertEqual(manager.delete_count, 0)
        self.assertEqual(manager.bulk_create_count, 0)

    def test_successful_initialization_is_reused_within_the_process(self):
        metadata = [("view", "View", 100, "app", "team")]
        module, manager = self.import_perm_repo_module(metadata, metadata)
        repo = module.PermsRepo()

        repo.initialize_permission_settings()
        repo.initialize_permission_settings()

        self.assertEqual(manager.all_count, 1)

    def test_changed_permissions_rebuild_once_within_the_check_interval(self):
        metadata = [("view", "View", 100, "app", "team")]
        stored_rows = [("old-view", "Old View", 100, "app", "team")]
        module, manager = self.import_perm_repo_module(metadata, stored_rows)
        repo = module.PermsRepo()

        repo.initialize_permission_settings()
        repo.initialize_permission_settings()

        self.assertEqual(manager.delete_count, 1)
        self.assertEqual(manager.bulk_create_count, 1)
        self.assertEqual(manager.all_count, 1)

    def test_first_initialization_runs_even_when_monotonic_clock_is_below_interval(self):
        metadata = [("view", "View", 100, "app", "team")]
        module, manager = self.import_perm_repo_module(metadata, metadata)

        with mock.patch.object(module.time, "monotonic", return_value=10):
            module.PermsRepo().initialize_permission_settings()

        self.assertEqual(manager.all_count, 1)
