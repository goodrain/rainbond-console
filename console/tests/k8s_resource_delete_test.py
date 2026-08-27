# -*- coding: utf-8 -*-
# capability_id: console.k8s-resource.delete-lifecycle
import collections
import importlib
import os
import sys
import typing
from types import ModuleType
from unittest import mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))
if not hasattr(typing, "NotRequired"):
    try:
        from typing_extensions import NotRequired
        typing.NotRequired = NotRequired
    except ImportError:
        typing.NotRequired = lambda item: item

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402
from django.test import SimpleTestCase  # noqa: E402

django.setup()


class Obj(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class K8sResourceDeleteLifecycleTests(SimpleTestCase):
    def test_delete_acceptance_marks_local_resource_and_backfills_region_id(self):
        from console.services.k8s_resource import ComponentK8sResourceService

        service = ComponentK8sResourceService()
        resource = Obj(
            ID=11,
            app_id="console-app",
            name="demo-config",
            kind="ConfigMap",
            content="apiVersion: v1\nkind: ConfigMap",
            state=1,
            region_resource_id=None,
            delete_status=0,
        )
        region_status = {
            "resource_id": 41,
            "name": "demo-config",
            "kind": "ConfigMap",
            "delete_status": 1,
            "delete_error": "",
            "delete_generation": 3,
        }

        with mock.patch.object(service, "get_app_id_and_namespace", return_value=("demo-ns", "region-app")), \
                mock.patch("console.services.k8s_resource.k8s_resources_repo.get_by_id", return_value=resource), \
                mock.patch("console.services.k8s_resource.region_api.delete_app_resource",
                           return_value=(Obj(status=202), {"bean": [region_status]})) as delete_region, \
                mock.patch("console.services.k8s_resource.k8s_resources_repo.delete_by_id") as delete_local, \
                mock.patch.object(service, "_record_delete_acceptance") as record_acceptance:
            statuses = service.delete_k8s_resource(
                "enterprise-1", "team-a", "console-app", "region-a", "demo-config", 11)

        self.assertEqual([region_status], statuses)
        self.assertNotIn("resource_id", delete_region.call_args[0][2])
        self.assertEqual("region-app", delete_region.call_args[0][2]["app_id"])
        record_acceptance.assert_called_once_with([resource], [region_status])
        delete_local.assert_not_called()

    def test_reconciliation_removes_only_region_confirmed_deleted_records(self):
        from console.services.k8s_resource import ComponentK8sResourceService

        service = ComponentK8sResourceService()
        failed = Obj(ID=11, name="failed", kind="ConfigMap", region_resource_id=41, delete_status=1)
        completed = Obj(ID=12, name="completed", kind="Secret", region_resource_id=42, delete_status=1)
        region_status = {
            "resource_id": 41,
            "name": "failed",
            "kind": "ConfigMap",
            "delete_status": 2,
            "delete_error": "finalizer is still present",
            "delete_generation": 3,
        }

        with mock.patch.object(service, "get_app_id_and_namespace", return_value=("demo-ns", "region-app")), \
                mock.patch("console.services.k8s_resource.k8s_resources_repo.list_deleting_by_app_id",
                           return_value=[failed, completed]), \
                mock.patch("console.services.k8s_resource.region_api.get_app_resource_delete_status",
                           return_value=(Obj(status=200), {"list": [region_status]})), \
                mock.patch.object(service, "_record_delete_reconciliation") as record_reconciliation:
            service.reconcile_delete_statuses("enterprise-1", "team-a", "console-app", "region-a")

        record_reconciliation.assert_called_once_with([failed, completed], [region_status])

    def test_reconciliation_keeps_local_records_when_region_status_lookup_fails(self):
        from console.services.k8s_resource import ComponentK8sResourceService

        service = ComponentK8sResourceService()
        resource = Obj(ID=11, name="demo", kind="ConfigMap", region_resource_id=41, delete_status=1)

        with mock.patch.object(service, "get_app_id_and_namespace", return_value=("demo-ns", "region-app")), \
                mock.patch("console.services.k8s_resource.k8s_resources_repo.list_deleting_by_app_id",
                           return_value=[resource]), \
                mock.patch("console.services.k8s_resource.region_api.get_app_resource_delete_status",
                           side_effect=RuntimeError("region unavailable")), \
                mock.patch.object(service, "_record_delete_reconciliation") as record_reconciliation:
            service.reconcile_delete_statuses("enterprise-1", "team-a", "console-app", "region-a")

        record_reconciliation.assert_not_called()

    def test_local_lifecycle_updates_only_remove_resources_absent_by_region_id(self):
        from console.services.k8s_resource import ComponentK8sResourceService

        service = ComponentK8sResourceService()
        failed = Obj(ID=11, name="failed", kind="ConfigMap", region_resource_id=41, delete_status=1)
        completed = Obj(ID=12, name="completed", kind="Secret", region_resource_id=42, delete_status=1)
        region_status = {
            "resource_id": 41,
            "name": "failed",
            "kind": "ConfigMap",
            "delete_status": 2,
            "delete_error": "finalizer is still present",
            "delete_generation": 3,
        }

        with mock.patch("console.services.k8s_resource.k8s_resources_repo.update_delete_lifecycle") as update_local, \
                mock.patch("console.services.k8s_resource.k8s_resources_repo.delete_by_id") as delete_local:
            service._record_delete_reconciliation.__wrapped__(service, [failed, completed], [region_status])

        update_local.assert_called_once_with(11, region_status)
        delete_local.assert_called_once_with(12)

    def test_local_acceptance_records_region_id_and_deleting_state(self):
        from console.services.k8s_resource import ComponentK8sResourceService

        service = ComponentK8sResourceService()
        resource = Obj(ID=11, name="demo-config", kind="ConfigMap", region_resource_id=None)
        region_status = {
            "resource_id": 41,
            "name": "demo-config",
            "kind": "ConfigMap",
            "delete_status": 1,
            "delete_error": "",
            "delete_generation": 3,
        }

        with mock.patch("console.services.k8s_resource.k8s_resources_repo.update_delete_lifecycle") as update_local:
            service._record_delete_acceptance.__wrapped__(service, [resource], [region_status])

        update_local.assert_called_once_with(11, region_status, accepted=True)

    def test_resource_list_serializes_integer_delete_status_for_ui(self):
        from console.services.k8s_resource import ComponentK8sResourceService

        resource = {"ID": 11, "delete_status": 2, "name": "demo-config"}
        deleting_resource = {"ID": 12, "delete_status": 1, "name": "pending-config"}

        displayed = ComponentK8sResourceService._serialize_delete_status(resource)
        deleting_displayed = ComponentK8sResourceService._serialize_delete_status(deleting_resource)

        self.assertEqual("DELETE_FAILED", displayed["delete_status"])
        self.assertEqual("DELETING", deleting_displayed["delete_status"])
        self.assertEqual(2, resource["delete_status"])

    def test_region_resource_creation_persists_returned_region_id(self):
        from console.services.region_resource_processing import RegionResource

        region_resource = RegionResource()
        region_item = {
            "ID": 55,
            "name": "demo-config",
            "kind": "ConfigMap",
            "content": "apiVersion: v1",
            "state": 1,
            "error_overview": "",
        }
        with mock.patch("console.services.region_resource_processing.k8s_resources_repo.bulk_create") as bulk_create:
            region_resource.create_k8s_resources([region_item], "console-app")

        created = bulk_create.call_args[0][0][0]
        self.assertEqual(55, created.region_resource_id)

    def test_market_sync_copies_region_resource_id_before_console_save(self):
        from console.services.market_app.market_app import MarketApp

        market_app = MarketApp.__new__(MarketApp)
        market_app.tenant_name = "team-a"
        market_app.region_name = "region-a"
        market_app.app = Obj(app_id="console-app")
        resource = Obj(
            name="demo-config",
            kind="ConfigMap",
            content="apiVersion: v1",
            state=1,
            error_overview="",
            region_resource_id=None,
            delete_status=0,
        )
        app = Obj(tenant=Obj(namespace="demo-ns"), k8s_resources=[resource])
        status = {
            "ID": 55,
            "name": "demo-config",
            "kind": "ConfigMap",
            "content": "apiVersion: v1",
            "state": 1,
            "error_overview": "",
        }

        with mock.patch("console.services.market_app.market_app.region_app_repo.get_region_app_id",
                        return_value="region-app"), \
                mock.patch("console.services.market_app.market_app.region_api.sync_k8s_resources",
                           return_value=(Obj(status=200), {"list": [status]})):
            market_app._sync_app_k8s_resources(app)

        self.assertEqual(55, resource.region_resource_id)

    def test_migration_adds_independent_delete_lifecycle_fields(self):
        migration = importlib.import_module("console.migrations.0010_k8sresource_delete_status")
        field_names = set()
        for operation in migration.Migration.operations:
            if getattr(operation, "model_name", None) == "k8sresource":
                field_names.add(getattr(operation, "name", None))

        self.assertTrue({
            "delete_status",
            "delete_error",
            "delete_started_at",
            "delete_generation",
            "region_resource_id",
        }.issubset(field_names))
