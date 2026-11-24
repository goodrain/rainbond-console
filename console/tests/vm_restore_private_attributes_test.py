# -*- coding: utf-8 -*-
"""Public HTTP and real ORM boundaries for VM restore control attributes."""
# capability_id: console.vm-restore.private-attributes
import collections
import collections.abc
import json
import os
import sys
from types import ModuleType, SimpleNamespace
from unittest import TestCase, mock

import yaml

for compatibility_name in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, compatibility_name):
        setattr(collections, compatibility_name, getattr(collections.abc, compatibility_name))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.test_settings")

sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

# The generated market client is an optional checkout, as in existing tests.
if "openapi_client" not in sys.modules:
    client_module = ModuleType("openapi_client")
    configuration_module = ModuleType("openapi_client.configuration")
    rest_module = ModuleType("openapi_client.rest")

    class _Configuration:
        def __init__(self):
            self.client_side_validation = False
            self.host = ""
            self.api_key = {}

    class _ApiException(Exception):
        status = 500
        body = ""

    setattr(client_module, "ApiClient", object)
    setattr(client_module, "MarketOpenapiApi", object)
    setattr(configuration_module, "Configuration", _Configuration)
    setattr(rest_module, "ApiException", _ApiException)
    sys.modules["openapi_client"] = client_module
    sys.modules["openapi_client.configuration"] = configuration_module
    sys.modules["openapi_client.rest"] = rest_module

import django  # noqa: E402

django.setup()

from django.db import IntegrityError, connections  # noqa: E402
from rest_framework.test import APIRequestFactory  # noqa: E402

from console.exception.main import ServiceHandleException  # noqa: E402
from console.models.main import ComponentK8sAttributes  # noqa: E402
from console.repositories.k8s_attribute import k8s_attribute_repo  # noqa: E402
from console.services.k8s_attribute import k8s_attribute_service  # noqa: E402
from console.views.app_config.base import AppBaseView  # noqa: E402
from console.views.k8s_attribute import ComponentK8sAttributeListView, ComponentK8sAttributeView  # noqa: E402
from www.models.main import TenantServiceInfo  # noqa: E402

PRIVATE_NAMES = (
    "vm_restore_state",
    "vm_restore_receipt_op-a",
    "vm_volume_bindings",
    "vm_restore_manifest_snapshot-a",
    "vm_restore_operation_op-a",
    "vm_restore_active_operation",
    " VM_RESTORE_STATE ",
    "VM_VOLUME_BINDINGS",
    "vm_restore_future_key",
)


class VMRestorePrivateAttributesTestCase(TestCase):
    def setUp(self):
        self.alias = "vm_restore_private_attributes"
        connections.databases[self.alias] = {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
            "ATOMIC_REQUESTS": False,
            "AUTOCOMMIT": True,
            "CONN_MAX_AGE": 0,
            "CONN_HEALTH_CHECKS": False,
            "OPTIONS": {},
            "TIME_ZONE": None,
            "USER": "",
            "PASSWORD": "",
            "HOST": "",
            "PORT": "",
            "TEST": {},
        }
        self.database = connections[self.alias]
        with self.database.schema_editor() as schema:
            schema.create_model(TenantServiceInfo)
            schema.create_model(ComponentK8sAttributes)
        self.addCleanup(self.close_database)
        for model in (TenantServiceInfo, ComponentK8sAttributes):
            patcher = mock.patch.object(model, "objects", model.objects.db_manager(self.alias))
            patcher.start()
            self.addCleanup(patcher.stop)
        self.service = TenantServiceInfo.objects.create(tenant_id="tenant-a",
                                                        service_id="service-a",
                                                        service_alias="service-a",
                                                        service_region="region-a",
                                                        service_key="fixture")
        self.tenant = SimpleNamespace(tenant_id="tenant-a", tenant_name="team-a")
        self.factory = APIRequestFactory()
        self.region_patcher = mock.patch("console.services.k8s_attribute.region_api")
        self.region = self.region_patcher.start()
        self.addCleanup(self.region_patcher.stop)

    def close_database(self):
        self.database.close()
        del connections[self.alias]
        connections.databases.pop(self.alias, None)

    def attr(self, name, value="control-sentinel", **kwargs):
        fields = dict(tenant_id="tenant-a", component_id="service-a", name=name, save_type="string", attribute_value=value)
        fields.update(kwargs)
        return ComponentK8sAttributes.objects.create(**fields)

    def snapshot(self):
        return list(ComponentK8sAttributes.objects.order_by("pk").values())

    def call(self, method, name=None, attribute=None):
        view_class = ComponentK8sAttributeView if name is not None else ComponentK8sAttributeListView
        path = "/console/teams/team-a/components/service-a/k8s-attributes"
        path += "/" + name if name is not None else ""
        request = getattr(self.factory, method)(path, {"attribute": attribute or {}}, format="json")
        tenant, service = self.tenant, self.service

        def initial(view, _request, *args, **kwargs):
            # Only authentication/scope lookup is injected. Real DRF dispatch,
            # HTTP exception conversion, service and ORM stay in the request.
            view.tenant, view.service = tenant, service
            view.region_name = "region-a"
            view.user = SimpleNamespace(nick_name="operator")

        kwargs = {"tenantName": "team-a", "serviceAlias": "service-a"}
        if name is not None:
            kwargs["name"] = name
        with mock.patch.object(AppBaseView, "initial", initial):
            return view_class.as_view()(request, **kwargs)

    def test_private_crud_is_http_403_and_leaves_orm_and_region_unchanged(self):
        for name in PRIVATE_NAMES:
            self.attr(name)
        before = self.snapshot()
        for name in PRIVATE_NAMES:
            for method in ("get", "put", "delete", "post"):
                with self.subTest(name=name, method=method):
                    response = self.call(method, None if method == "post" else name, {
                        "name": name,
                        "save_type": "string",
                        "attribute_value": "replacement-sentinel"
                    })
                    self.assertEqual(response.status_code, 403)
                    self.assertNotIn("control-sentinel", str(response.data))
                    self.assertEqual(self.snapshot(), before)
        self.assertFalse(self.region.mock_calls)

    def test_public_list_hides_private_rows_but_internal_repository_keeps_them(self):
        for name in PRIVATE_NAMES:
            self.attr(name)
        self.attr("labels", "public-sentinel")
        response = self.call("get")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["name"] for item in response.data["data"]["list"]], ["labels"])
        self.assertNotIn("control-sentinel", str(response.data))
        self.assertEqual(k8s_attribute_repo.get_by_component_id("service-a").count(), len(PRIVATE_NAMES) + 1)
        self.assertEqual(k8s_attribute_repo.get_by_component_id_name("service-a", "vm_restore_state").count(), 1)

    def test_public_crud_whitelists_input_and_preserves_ordinary_and_vm_configuration(self):
        private = self.attr("vm_restore_state")
        for name in ("labels", "vm_disk_layout", "vm_restoreish", "nodeSelector"):
            response = self.call("post",
                                 attribute={
                                     "ID": private.pk,
                                     "pk": private.pk,
                                     "tenant_id": "tenant-b",
                                     "component_id": "service-b",
                                     "name": name,
                                     "save_type": "string",
                                     "attribute_value": "public-sentinel"
                                 })
            self.assertEqual(response.status_code, 200)
            row = ComponentK8sAttributes.objects.get(name=name)
            self.assertNotEqual(row.pk, private.pk)
            self.assertEqual((row.tenant_id, row.component_id), ("tenant-a", "service-a"))
            response = self.call("put", name, {"name": name, "save_type": "string", "attribute_value": "updated-sentinel"})
            self.assertEqual(response.status_code, 200)
            row.refresh_from_db()
            self.assertEqual(row.attribute_value, "updated-sentinel")
            self.assertEqual(self.call("get", name).status_code, 200)
            self.assertEqual(self.call("delete", name).status_code, 200)
        private.refresh_from_db()
        self.assertEqual(private.attribute_value, "control-sentinel")

    def test_overwrite_preserves_private_rows_rescopes_and_discards_supplied_primary_keys(self):
        private = self.attr("vm_restore_state")
        self.attr("labels", "old-sentinel")
        before_private = ComponentK8sAttributes.objects.filter(pk=private.pk).values().get()
        incoming = ComponentK8sAttributes(ID=private.pk,
                                          tenant_id="tenant-b",
                                          component_id="service-a",
                                          name="labels",
                                          save_type="string",
                                          attribute_value="new-sentinel")
        k8s_attribute_repo.overwrite_by_component_ids(["service-a"], [incoming])
        self.assertEqual(ComponentK8sAttributes.objects.filter(pk=private.pk).values().get(), before_private)
        row = ComponentK8sAttributes.objects.get(name="labels")
        self.assertEqual((row.tenant_id, row.component_id, row.attribute_value), ("tenant-a", "service-a", "new-sentinel"))
        self.assertNotEqual(row.pk, private.pk)
        k8s_attribute_repo.overwrite_by_component_ids(["service-a"], [])
        self.assertEqual(self.snapshot(), [before_private])

    def test_overwrite_rejects_private_batch_and_foreign_component_before_mutation(self):
        self.attr("vm_restore_state")
        self.attr("labels")
        before = self.snapshot()
        for name, component_id in (("vm_restore_state", "service-a"), ("labels", "service-b")):
            incoming = ComponentK8sAttributes(tenant_id="tenant-a",
                                              component_id=component_id,
                                              name=name,
                                              save_type="string",
                                              attribute_value="replacement-sentinel")
            with self.subTest(name=name), self.assertRaises(ServiceHandleException) as caught:
                k8s_attribute_repo.overwrite_by_component_ids(["service-a"], [incoming])
            self.assertEqual(caught.exception.status_code, 403)
            self.assertEqual(self.snapshot(), before)

    def test_bulk_create_does_not_allow_private_name_or_primary_key_injection(self):
        private = self.attr("vm_restore_state")
        before = self.snapshot()
        for name in PRIVATE_NAMES:
            incoming = ComponentK8sAttributes(tenant_id="tenant-a",
                                              component_id="service-a",
                                              name=name,
                                              save_type="string",
                                              attribute_value="replacement-sentinel")
            with self.subTest(name=name), self.assertRaises(ServiceHandleException):
                k8s_attribute_repo.bulk_create([incoming])
            self.assertEqual(self.snapshot(), before)
        rows = k8s_attribute_repo.bulk_create([
            ComponentK8sAttributes(ID=private.pk,
                                   tenant_id="tenant-b",
                                   component_id="service-a",
                                   name="labels",
                                   save_type="string",
                                   attribute_value="public-sentinel")
        ])
        self.assertNotEqual(rows[0].pk, private.pk)
        self.assertEqual(rows[0].tenant_id, "tenant-a")
        private.refresh_from_db()
        self.assertEqual(private.attribute_value, "control-sentinel")

    def test_overwrite_detects_existing_wrong_tenant_and_missing_live_service(self):
        self.attr("vm_restore_state", tenant_id="tenant-b")
        before = self.snapshot()
        for ids in (["service-a"], ["missing-service"]):
            with self.subTest(ids=ids), self.assertRaises(ServiceHandleException) as caught:
                k8s_attribute_repo.overwrite_by_component_ids(ids, [])
            self.assertEqual(caught.exception.status_code, 409)
            self.assertEqual(self.snapshot(), before)

    def test_public_name_collision_cannot_read_update_or_delete_an_internal_row(self):
        private = self.attr("vm_restore_state")
        # Emulate a MySQL accent/case-insensitive lookup returning a protected
        # row for a superficially public name. PK writes must use exact matches.
        with mock.patch.object(k8s_attribute_repo,
                               "get_by_component_id_name",
                               return_value=ComponentK8sAttributes.objects.filter(pk=private.pk)):
            found = k8s_attribute_service.get_by_component_ids_and_name("service-a", "vm_réstoré_state")
            self.assertEqual(list(found), [])
            self.assertEqual(k8s_attribute_repo.update("service-a", "vm_réstoré_state", attribute_value="changed"), 0)
            self.assertEqual(k8s_attribute_repo.delete("service-a", "vm_réstoré_state")[0], 0)
        private.refresh_from_db()
        self.assertEqual(private.attribute_value, "control-sentinel")

    def test_region_reserved_unicode_alias_is_forbidden_through_http(self):
        for name in ("vm_volume_bİndİngs", " VM_VOLUME_BİNDİNGS "):
            with self.subTest(name=name):
                self.attr(name)
                before = self.snapshot()
                statuses = {}
                for method in ("get", "put", "delete", "post"):
                    response = self.call(method, None if method == "post" else name, {
                        "name": name,
                        "save_type": "string",
                        "attribute_value": "replacement-sentinel"
                    })
                    statuses[method] = response.status_code
                    self.assertNotIn("control-sentinel", str(response.data))
                self.assertEqual(statuses, {method: 403 for method in statuses})
                self.assertEqual(self.snapshot(), before)
        self.assertFalse(self.region.mock_calls)

    def test_region_reserved_unicode_alias_is_hidden_and_preserved(self):
        for name in ("vm_volume_bİndİngs", " VM_VOLUME_BİNDİNGS "):
            self.attr(name)
        before = self.snapshot()
        self.attr("labels", "public-sentinel")
        listed = self.call("get").data["data"]["list"]
        k8s_attribute_repo.overwrite_by_component_ids(["service-a"], [])
        self.assertEqual([row["name"] for row in listed], ["labels"])
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(k8s_attribute_repo.get_by_component_id("service-a").count(), 2)
        for name in (row["name"] for row in before):
            incoming = ComponentK8sAttributes(component_id="service-a",
                                              tenant_id="tenant-a",
                                              name=name,
                                              save_type="string",
                                              attribute_value="replacement-sentinel")
            for operation in (k8s_attribute_repo.bulk_create,
                              lambda rows: k8s_attribute_repo.overwrite_by_component_ids(["service-a"], rows)):
                with self.subTest(name=name), self.assertRaises(ServiceHandleException) as caught:
                    operation([incoming])
                self.assertEqual(caught.exception.status_code, 403)
                self.assertEqual(self.snapshot(), before)

    def test_missing_json_value_retains_public_default_on_create_and_update(self):
        response = self.call("post", attribute={"name": "labels", "save_type": "json"})
        self.assertEqual(response.status_code, 200)
        row = ComponentK8sAttributes.objects.get(name="labels")
        self.assertEqual(json.loads(row.attribute_value), {})
        row.attribute_value = '{"old": "sentinel"}'
        row.save()
        response = self.call("put", "labels", {"name": "labels", "save_type": "json"})
        self.assertEqual(response.status_code, 200)
        row.refresh_from_db()
        self.assertEqual(json.loads(row.attribute_value), {})

    def test_missing_sequence_value_retains_public_create_success(self):
        for name in ("args", "cmd"):
            with self.subTest(name=name):
                response = self.call("post", attribute={"name": name, "save_type": "yaml"})
                self.assertEqual(response.status_code, 200)
                row = ComponentK8sAttributes.objects.get(name=name)
                self.assertEqual(row.save_type, "yaml")
                self.assertEqual(yaml.safe_load(row.attribute_value), [])

    def test_missing_sequence_value_retains_public_update_success(self):
        for name in ("args", "cmd"):
            with self.subTest(name=name):
                row = self.attr(name, "- before-sentinel\n")
                response = self.call("put", name, {"name": name, "save_type": "yaml"})
                self.assertEqual(response.status_code, 200)
                row.refresh_from_db()
                self.assertEqual(row.save_type, "yaml")
                self.assertEqual(yaml.safe_load(row.attribute_value), [])

    def test_python_only_strip_controls_do_not_expand_region_reservations(self):
        names = [control + "vm_volume_bindings" + control for control in ("\x1c", "\x1d", "\x1e", "\x1f")]
        for name in names:
            with self.subTest(name=repr(name)):
                response = self.call("post", attribute={"name": name, "save_type": "string", "attribute_value": "public"})
                self.assertEqual(response.status_code, 200)
        listed = self.call("get").data["data"]["list"]
        self.assertEqual([row["name"] for row in listed], names)

    def test_unicode_nearby_names_remain_public_without_transliteration(self):
        names = ("vm_volume_bındıngs", "vm_volume_bi\u0307ndi\u0307ngs", "vm_volume_bİndİngs_backup", "vm_reſtore_state",
                 "vm_restore", "vm_restoreish", "vm_restore-state", "vm_disk_layout", "vm_volume_bindings_backup")
        for name in names:
            with self.subTest(name=name):
                response = self.call("post", attribute={"name": name, "save_type": "string", "attribute_value": "public"})
                self.assertEqual(response.status_code, 200)
        listed = self.call("get").data["data"]["list"]
        self.assertEqual([row["name"] for row in listed], list(names))

    def test_overwrite_real_insert_failure_rolls_back_public_delete(self):
        self.attr("labels", "old-sentinel")
        self.attr("vm_restore_state")
        before = self.snapshot()
        incoming = ComponentK8sAttributes(component_id="service-a",
                                          tenant_id="wrong",
                                          name=None,
                                          save_type="string",
                                          attribute_value="invalid")
        with self.assertRaises(IntegrityError):
            k8s_attribute_repo.overwrite_by_component_ids(["service-a"], [incoming])
        self.assertEqual(self.snapshot(), before)

    def test_bulk_create_real_insert_failure_is_atomic(self):
        before = self.snapshot()
        attrs = [
            ComponentK8sAttributes(component_id="service-a",
                                   tenant_id="wrong",
                                   name=name,
                                   save_type="string",
                                   attribute_value="new-sentinel") for name in ("labels", None)
        ]
        with self.assertRaises(IntegrityError):
            k8s_attribute_repo.bulk_create(attrs)
        self.assertEqual(self.snapshot(), before)

    def test_mixed_private_bulk_rejects_whole_batch(self):
        before = self.snapshot()
        attrs = [
            ComponentK8sAttributes(component_id="service-a",
                                   tenant_id="wrong",
                                   name=name,
                                   save_type="string",
                                   attribute_value="new-sentinel") for name in ("labels", "\tVm_ReStOrE_next\n")
        ]
        for operation in (k8s_attribute_repo.bulk_create,
                          lambda rows: k8s_attribute_repo.overwrite_by_component_ids(["service-a"], rows)):
            with self.assertRaises(ServiceHandleException) as caught:
                operation(attrs)
            self.assertEqual(caught.exception.status_code, 403)
            self.assertEqual(self.snapshot(), before)

    def test_repository_update_scope_and_identity_mutation_is_rejected(self):
        row = self.attr("labels", "old-sentinel")
        before = self.snapshot()
        for extra in ({"tenant_id": "tenant-b"}, {"ID": row.pk}, {"pk": row.pk}, {"operator": "injected"}):
            with self.subTest(extra=extra), self.assertRaises(ServiceHandleException) as caught:
                k8s_attribute_repo.update("service-a", "labels", **extra)
            self.assertEqual(caught.exception.status_code, 403)
            self.assertEqual(self.snapshot(), before)

    def test_bulk_ordinary_copies_derive_each_live_tenant(self):
        TenantServiceInfo.objects.create(tenant_id="tenant-b",
                                         service_id="service-b",
                                         service_alias="service-b",
                                         service_region="region-a",
                                         service_key="fixture")
        private = self.attr("vm_restore_state")
        attrs = [
            ComponentK8sAttributes(ID=private.pk,
                                   component_id=sid,
                                   tenant_id="injected",
                                   name="labels",
                                   save_type="json",
                                   attribute_value="{}") for sid in ("service-a", "service-b")
        ]
        created = k8s_attribute_repo.bulk_create(attrs)
        self.assertEqual([(row.component_id, row.tenant_id) for row in created], [("service-a", "tenant-a"),
                                                                                  ("service-b", "tenant-b")])
        self.assertEqual(len({private.pk} | {row.pk for row in created}), 3)
        self.assertEqual(k8s_attribute_repo.get_by_component_id("service-a").count(), 2)
        private.refresh_from_db()
        self.assertEqual(private.attribute_value, "control-sentinel")

    def test_name_collision_filters_exact_public_rows_from_mixed_results(self):
        private = self.attr("vm_restore_state")
        public = self.attr("vm_réstoré_state", "public-sentinel")
        collision = ComponentK8sAttributes.objects.filter(pk__in=[private.pk, public.pk])
        with mock.patch.object(k8s_attribute_repo, "get_by_component_id_name", return_value=collision):
            found = k8s_attribute_service.get_by_component_ids_and_name("service-a", "vm_réstoré_state")
            self.assertEqual([row.pk for row in found], [public.pk])
            self.assertEqual(k8s_attribute_repo.update("service-a", "vm_réstoré_state", attribute_value="changed"), 1)
            self.assertEqual(k8s_attribute_repo.delete("service-a", "vm_réstoré_state")[0], 1)
        private.refresh_from_db()
        self.assertEqual(private.attribute_value, "control-sentinel")
