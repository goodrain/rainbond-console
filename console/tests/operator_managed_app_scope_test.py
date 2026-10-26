# -*- coding: utf-8 -*-
"""Real ORM and DRF coverage for operator-managed application ownership."""
import importlib
import os
from types import SimpleNamespace
from unittest import TestCase, mock

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.test_settings")

import django  # noqa: E402

django.setup()

from django.db import OperationalError, connections  # noqa: E402
from django.test.utils import CaptureQueriesContext  # noqa: E402
from django.utils import timezone  # noqa: E402
from rest_framework.test import APIRequestFactory  # noqa: E402

from console.exception.main import ServiceHandleException  # noqa: E402
from console.services.group_service import group_service  # noqa: E402
from console.views.base import RegionTenantHeaderView  # noqa: E402
from console.views.public_areas import GroupOperatorManagedView  # noqa: E402
from www.apiclient.regionapibaseclient import RegionApiBaseHttpClient  # noqa: E402
from www.models.main import RegionApp, ServiceGroup, ServiceGroupRelation, TenantServiceInfo  # noqa: E402

group_module = importlib.import_module("console.services.group_service")


# capability_id: console.operator-managed.scoped-application-lookup
class OperatorManagedAppScopeTestCase(TestCase):
    def setUp(self):
        self.alias = "operator_managed_app_scope"
        connections.databases[self.alias] = {
            "ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:",
            "ATOMIC_REQUESTS": False, "AUTOCOMMIT": True, "CONN_MAX_AGE": 0,
            "CONN_HEALTH_CHECKS": False, "OPTIONS": {}, "TIME_ZONE": None,
            "USER": "", "PASSWORD": "", "HOST": "", "PORT": "", "TEST": {},
        }
        self.database = connections[self.alias]
        models = (ServiceGroup, RegionApp, ServiceGroupRelation, TenantServiceInfo)
        with self.database.schema_editor() as schema:
            for model in models:
                schema.create_model(model)
        self.addCleanup(self.close_database)
        for model in models:
            patcher = mock.patch.object(model, "objects", model.objects.db_manager(self.alias))
            patcher.start()
            self.addCleanup(patcher.stop)
        self.tenant = SimpleNamespace(tenant_id="team-a", tenant_name="team-a", namespace="namespace-a")
        self.region_name = "region-a"
        self.factory = APIRequestFactory()

    def close_database(self):
        self.database.close()
        del connections[self.alias]
        connections.databases.pop(self.alias, None)

    def app(self, tenant_id="team-a", region_name="region-a", app_type="rainbond"):
        return ServiceGroup.objects.create(
            tenant_id=tenant_id, region_name=region_name, app_type=app_type,
            group_name="operator-app", create_time=timezone.now(), update_time=timezone.now())

    def mapping(self, app_id, region_name="region-a"):
        return RegionApp.objects.create(region_name=region_name, app_id=app_id, region_app_id="region-{}".format(app_id))

    def component(self, app, name, extend_method="stateless_multiple", service_source="docker_run"):
        component = TenantServiceInfo.objects.create(
            tenant_id=app.tenant_id, service_id="{}-{}".format(app.ID, name), service_alias="{}-{}".format(app.ID, name),
            service_region=app.region_name, service_key="fixture", k8s_component_name=name,
            extend_method=extend_method, service_source=service_source)
        ServiceGroupRelation.objects.create(
            tenant_id=app.tenant_id, region_name=app.region_name, group_id=app.ID, service_id=component.service_id)
        return component

    def call(self, group_id=None):
        query = {} if group_id is None else {"group_id": group_id}
        request = self.factory.get("/console/teams/team-a/operator-managed", query)
        tenant, region_name = self.tenant, self.region_name

        def initial(view, _request, *args, **kwargs):
            # Inject an already authenticated scope; retain real DRF dispatch,
            # exception conversion, service and repositories below this seam.
            view.tenant = tenant
            view.region_name = region_name

        with mock.patch.object(RegionTenantHeaderView, "initial", initial):
            return GroupOperatorManagedView.as_view()(request, team_name=tenant.tenant_name)

    def assert_missing(self, app_id):
        with mock.patch.object(group_module.base_service, "get_watch_managed") as downstream:
            response = self.call(str(app_id))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["code"], 404)
        self.assertEqual(response.data["msg_show"], "应用不存在")
        downstream.assert_not_called()

    def assert_unmapped(self, app_id):
        with mock.patch.object(group_module.base_service, "get_watch_managed") as downstream:
            response = self.call(str(app_id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["code"], 200)
        self.assertEqual(response.data["data"]["list"], {"service": [], "config_map": [], "secret": []})
        downstream.assert_not_called()

    def test_empty_application_keeps_empty_success_without_queries(self):
        for app_id in (None, ""):
            with self.subTest(app_id=app_id), \
                    mock.patch.object(group_module.base_service, "get_watch_managed") as downstream, \
                    CaptureQueriesContext(self.database) as queries:
                response = self.call(app_id)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data["data"]["list"], {"service": [], "config_map": [], "secret": []})
                self.assertEqual(len(queries), 0)
                downstream.assert_not_called()

    def test_service_preserves_legacy_falsy_empty_input(self):
        for app_id in (None, "", 0, False):
            with self.subTest(app_id=app_id), \
                    mock.patch.object(group_module.base_service, "get_watch_managed") as downstream, \
                    CaptureQueriesContext(self.database) as queries:
                data = group_service.get_watch_managed_data(self.tenant, self.region_name, app_id)
                self.assertEqual(data, {"service": [], "config_map": [], "secret": []})
                self.assertEqual(len(queries), 0)
                downstream.assert_not_called()

    def test_missing_console_application_returns_404(self):
        self.assert_missing(999999999)

    def test_deleted_console_application_with_residual_mapping_returns_404(self):
        app = self.app()
        self.mapping(app.ID)
        ServiceGroup.objects.filter(pk=app.ID)._raw_delete(self.alias)
        self.assert_missing(app.ID)

    def test_existing_console_application_without_mapping_returns_empty_success(self):
        app = self.app()
        self.assert_unmapped(app.ID)

    def test_app_from_other_tenant_or_region_is_not_read(self):
        for tenant_id, region_name in (("team-b", "region-a"), ("team-a", "region-b")):
            with self.subTest(tenant_id=tenant_id, region_name=region_name):
                app = self.app(tenant_id=tenant_id, region_name=region_name)
                # A mapping in the requested region alone is insufficient.
                self.mapping(app.ID)
                self.assert_missing(app.ID)

    def test_mapping_from_other_region_does_not_match(self):
        app = self.app()
        self.mapping(app.ID, region_name="region-b")
        self.assert_unmapped(app.ID)

    def test_mapping_initialization_window_recovers_without_hiding_the_application(self):
        app = self.app()
        with mock.patch.object(group_module.base_service, "get_watch_managed", return_value={"services": [
                {"name": "external", "ip": "10.0.0.12", "port": "8080"}]}) as downstream:
            before = self.call(str(app.ID))
            self.assertEqual(before.status_code, 200)
            self.assertEqual(before.data["data"]["list"], {"service": [], "config_map": [], "secret": []})
            downstream.assert_not_called()
            mapping = self.mapping(app.ID)
            after = self.call(str(app.ID))
            self.assertEqual(after.status_code, 200)
            self.assertEqual(after.data["data"]["list"], {"service": [
                {"name": "external-svc", "static": True, "address": ["10.0.0.12:8080"]}]})
            downstream.assert_called_once_with("region-a", "team-a", mapping.region_app_id)

    def test_invalid_nonempty_id_returns_400_without_downstream_or_queries(self):
        for app_id in ("not-a-number", "1.5", "-1", "0", "true", " "):
            with self.subTest(app_id=app_id), \
                    mock.patch.object(group_module.base_service, "get_watch_managed") as downstream, \
                    CaptureQueriesContext(self.database) as queries:
                response = self.call(app_id)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.data["code"], 400)
                self.assertEqual(response.data["msg_show"], "应用ID不合法")
                self.assertEqual(len(queries), 0)
                downstream.assert_not_called()

    def test_service_rejects_invalid_nonempty_types_without_queries(self):
        for app_id in (True, 1.5, [1], {"id": 1}):
            with self.subTest(app_id=app_id), \
                    mock.patch.object(group_module.base_service, "get_watch_managed") as downstream, \
                    CaptureQueriesContext(self.database) as queries:
                with self.assertRaises(ServiceHandleException) as raised:
                    group_service.get_watch_managed_data(self.tenant, self.region_name, app_id)
                self.assertEqual(raised.exception.status_code, 400)
                self.assertEqual(len(queries), 0)
                downstream.assert_not_called()

    def test_valid_rainbond_and_helm_output_and_kubeblocks_filters_are_unchanged(self):
        for app_type in ("rainbond", "helm"):
            with self.subTest(app_type=app_type):
                app = self.app(app_type=app_type)
                mapping = self.mapping(app.ID)
                self.component(app, "already-svc")
                self.component(app, "kb-extend", extend_method="kubeblocks_component")
                self.component(app, "kb-source", service_source="kubeblocks")
                watched = {"services": [
                    {"name": "already", "ip": "10.0.0.1", "port": "80"},
                    {"name": "kb-extend", "ip": "None", "port": "3306"},
                    {"name": "kb-source", "ip": "None", "port": "6379"},
                    {"name": "external", "ip": "10.0.0.12", "port": "8080,9090"},
                    {"name": "headless", "ip": "None", "port": "5432"},
                ], "config_map": [{"name": "unused-config"}], "secret": [{"name": "unused-reference"}]}
                with mock.patch.object(group_module.base_service, "get_watch_managed", return_value=watched) as downstream, \
                        CaptureQueriesContext(self.database) as queries:
                    response = self.call(str(app.ID))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data["data"]["list"], {"service": [
                    {"name": "external-svc", "static": True, "address": ["10.0.0.12:8080", "10.0.0.12:9090"]},
                    {"name": "headless-svc", "static": False, "namespace": "namespace-a", "service": "headless", "port": "5432"},
                ]})
                downstream.assert_called_once_with("region-a", "team-a", mapping.region_app_id)
                sql = [item["sql"] for item in queries]
                self.assertEqual(sum('FROM "service_group" ' in statement for statement in sql), 1)
                self.assertEqual(sum('FROM "region_app" ' in statement for statement in sql), 1)

    def test_valid_service_integer_application_id_is_supported(self):
        app = self.app()
        mapping = self.mapping(app.ID)
        with mock.patch.object(group_module.base_service, "get_watch_managed", return_value={}) as downstream:
            self.assertEqual(group_service.get_watch_managed_data(self.tenant, "region-a", app.ID), {"service": []})
        downstream.assert_called_once_with("region-a", "team-a", mapping.region_app_id)

    def test_downstream_service_failures_keep_their_status(self):
        app = self.app()
        self.mapping(app.ID)
        for status in (502, 503):
            error = ServiceHandleException(msg="region unavailable", msg_show="数据中心暂不可用", status_code=status)
            with self.subTest(status=status), \
                    mock.patch.object(group_module.base_service, "get_watch_managed", side_effect=error):
                response = self.call(str(app.ID))
                self.assertEqual(response.status_code, status)
                self.assertEqual(response.data["msg_show"], "数据中心暂不可用")

    def test_database_and_unexpected_mapping_errors_are_not_converted_to_404(self):
        app = self.app()
        database_error = OperationalError("database unavailable")
        with mock.patch.object(group_module.group_repo, "get_group_by_pk", side_effect=database_error), \
                mock.patch.object(group_module.base_service, "get_watch_managed") as downstream:
            with self.assertRaises(OperationalError):
                group_service.get_watch_managed_data(self.tenant, "region-a", app.ID)
            downstream.assert_not_called()
        mapping_error = RegionApp.MultipleObjectsReturned
        with mock.patch.object(group_module.region_app_repo, "get_region_app_id", side_effect=mapping_error), \
                mock.patch.object(group_module.base_service, "get_watch_managed") as downstream:
            with self.assertRaises(RegionApp.MultipleObjectsReturned):
                group_service.get_watch_managed_data(self.tenant, "region-a", app.ID)
            downstream.assert_not_called()

    def test_existing_transport_wrapper_degradation_is_not_changed_to_404(self):
        app = self.app()
        self.mapping(app.ID)
        service_module = importlib.import_module("console.services.service_services")
        error = RegionApiBaseHttpClient.CallApiError(
            "region", "/fixture/operator-managed", "GET", SimpleNamespace(status=503), {})
        with mock.patch.object(service_module.region_api, "watch_operator_managed", side_effect=error):
            response = self.call(str(app.ID))
        # This pre-existing wrapper returns {} on upstream errors. This change
        # only fixes local existence/ownership checks; it does not relabel that
        # established degradation as an application-not-found response.
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["list"], {"service": []})
