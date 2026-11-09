"""Isolated database tests: no platform settings, credentials, cluster or snapshots."""
import copy
import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace
from django.conf import settings

settings.configure(INSTALLED_APPS=[],
                   DATABASES={"default": {
                       "ENGINE": "django.db.backends.sqlite3",
                       "NAME": ":memory:"
                   }},
                   SECRET_KEY="test-placeholder",
                   USE_TZ=True)
import django

django.setup()
from django.db import connection
from console.services.delivery_manifest import DeliveryError, baseline, compare, prepare

spec = importlib.util.spec_from_file_location("isolated_delivery_models",
                                              Path(__file__).parents[1] / "models/delivery_template.py")
models = importlib.util.module_from_spec(spec)
spec.loader.exec_module(models)
from console.services.delivery_templates import DeliveryService

USER = SimpleNamespace(user_id=1, nick_name="Publisher", enterprise_id="enterprise")
SCOPE = dict(enterprise_id="enterprise", team_name="team", region_name="region", app_id="123")
SOURCE = {
    "template_version":
    "v2",
    "governance_mode":
    "KUBERNETES_NATIVE_SERVICE",
    "apps": [{
        "service_id":
        "web",
        "service_key":
        "web",
        "service_share_uuid":
        "web+web",
        "service_cname":
        "Web",
        "service_alias":
        "web",
        "deploy_version":
        "build-1",
        "extend_method":
        "stateless",
        "service_source":
        "source_code",
        "git_url":
        "https://example.test/app.git",
        "dep_service_map_list": [],
        "port_map_list": [{
            "container_port": 80
        }],
        "service_env_map_list": [{
            "attr_name": "LOG_LEVEL",
            "attr_value": "info"
        }, {
            "attr_name": "PASSWORD",
            "attr_value": ""
        }],
        "extend_method_map": {
            "min_node": 1,
            "max_node": 3,
            "step_node": 1,
            "init_memory": 128,
            "container_cpu": 100
        }
    }]
}
PAYLOAD = {
    "template_name":
    "App",
    "version":
    "1.0.0",
    "description":
    "First",
    "service_ids": ["web"],
    "component_overrides": [{
        "service_id":
        "web",
        "service_env_map_list": [{
            "attr_name": "LOG_LEVEL",
            "attr_value": "debug"
        }, {
            "attr_name": "PASSWORD",
            "attr_value": ""
        }],
        "extend_method_map": {
            "min_node": 1,
            "max_node": 4,
            "step_node": 1,
            "init_memory": 0,
            "container_cpu": 0
        }
    }]
}


class Gateway:
    def __init__(self):
        self.calls = []
        self.fail = False

    def source(self, scope):
        return copy.deepcopy(SOURCE), "Source app"

    def dispatch(self, task, item):
        self.calls.append(item.component["deploy_version"])
        if self.fail:
            raise DeliveryError("同步失败", 502)
        return {"share_id": "remote", "event_id": "event", "image_name": "registry.test/frozen:build-1"}

    def status(self, task, item):
        return {"status": "success"}

    def export(self, task):
        return {"event_id": "export-event"}

    def export_status(self, task):
        return {"status": "success", "download_path": "/v2/app/download/package.tgz"}

    def install(self, task):
        return {"app_id": "target-app", "event_ids": ["deploy-event"], "region_name": "region"}

    def installation_status(self, task):
        return "succeeded"

    def prepare_catalog(self, task):
        task.result["market_app_id"] = "store-app"

    def publish_catalog(self, task):
        return {"catalog_id": "catalog"}


class DeliveryWorkflowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tables = [
            models.DeliveryTemplate, models.DeliveryTemplateVersion, models.DeliveryTask, models.DeliveryTaskItem,
            models.DeliveryListingRequest
        ]
        from django.db.migrations.state import ProjectState
        migration_path = Path(__file__).parents[1] / "migrations/0011_independent_delivery_templates.py"
        migration_spec = importlib.util.spec_from_file_location("isolated_delivery_migration", migration_path)
        migration_module = importlib.util.module_from_spec(migration_spec)
        migration_spec.loader.exec_module(migration_module)
        with connection.schema_editor() as editor:
            migration_module.Migration("0011_independent_delivery_templates", "console").apply(ProjectState(), editor)

    def setUp(self):
        with connection.cursor() as cursor:
            for table in reversed(self.tables):
                cursor.execute('DELETE FROM "{}"'.format(table._meta.db_table))
        self.gateway = Gateway()
        self.service = DeliveryService(models=models, gateway=self.gateway)

    def publish(self):
        job = self.service.start(USER, SCOPE, PAYLOAD, "request-1")
        self.service.advance(job.id)
        self.service.advance(job.id)
        return self.service.publish(USER, SCOPE, job.id)

    def test_independent_publish_freezes_source_and_has_no_snapshot_fields(self):
        job = self.service.start(USER, SCOPE, PAYLOAD, "request-1")
        self.assertEqual(models.DeliveryTemplateVersion.objects.count(), 0)
        self.service.advance(job.id)
        self.service.advance(job.id)
        version = self.service.publish(USER, SCOPE, job.id)
        self.assertEqual(version.manifest["apps"][0]["service_env_map_list"][0]["attr_value"], "debug")
        self.assertEqual(SOURCE["apps"][0]["service_env_map_list"][0]["attr_value"], "info")
        self.assertEqual(version.manifest["apps"][0]["cpu"], 0)
        self.assertEqual(self.gateway.calls, ["build-1"])
        self.assertEqual(version.id, self.service.publish(USER, SCOPE, job.id).id)
        self.assertFalse(any("snapshot" in field.name for model in self.tables for field in model._meta.fields))

    def test_environment_names_and_scaling_are_server_validated(self):
        invalid = copy.deepcopy(PAYLOAD)
        invalid["component_overrides"][0]["service_env_map_list"].pop()
        with self.assertRaises(DeliveryError):
            prepare(SOURCE, invalid, "template")
        invalid = copy.deepcopy(PAYLOAD)
        invalid["component_overrides"][0]["extend_method_map"]["max_node"] = 0
        with self.assertRaises(DeliveryError):
            prepare(SOURCE, invalid, "template")

    def test_source_baseline_excludes_overrides_and_detects_ports(self):
        version = self.publish()
        self.assertEqual(compare(version.source_baseline, baseline(SOURCE))["status"], "unchanged")
        changed = copy.deepcopy(SOURCE)
        changed["apps"][0]["port_map_list"][0]["container_port"] = 81
        self.assertEqual(compare(version.source_baseline, baseline(changed))["status"], "changed")

    def test_failed_sync_can_resume_without_repeating_completed_items(self):
        job = self.service.start(USER, SCOPE, PAYLOAD, "request-1")
        self.gateway.fail = True
        self.service.advance(job.id)
        job.refresh_from_db()
        self.assertEqual(job.status, "failed")
        with self.assertRaises(DeliveryError):
            self.service.publish(USER, SCOPE, job.id)
        self.gateway.fail = False
        self.service.retry(SCOPE, job.id)
        self.service.advance(job.id)
        self.service.advance(job.id)
        self.service.publish(USER, SCOPE, job.id)

    def test_scope_and_deleted_version_cannot_be_bypassed(self):
        version = self.publish()
        with self.assertRaises(DeliveryError):
            self.service.publish(USER, {**SCOPE, "team_name": "other"}, version.sync_id)
        self.service.delete(USER, SCOPE, version.id)
        version.refresh_from_db()
        self.assertIsNotNone(version.deleted_at)
        self.assertEqual(models.DeliveryTemplateVersion.objects.count(), 1)
        with self.assertRaises(DeliveryError):
            self.service.operation(USER, SCOPE, version.id, "offline", {})

    def test_export_does_not_require_listing_and_tracks_real_result(self):
        version = self.publish()
        task = self.service.operation(USER, SCOPE, version.id, "offline", {}, "export-1")
        self.service.advance(task.id)
        self.service.advance(task.id)
        task.refresh_from_db()
        self.assertEqual(task.status, "succeeded")
        self.assertEqual(models.DeliveryListingRequest.objects.count(), 0)

    def test_approval_is_separate_from_catalog_publication(self):
        version = self.publish()
        listing = self.service.listing(USER, SCOPE, version.id, {"reason": "Release", "destination": {"type": "local"}})
        self.service.review(USER, listing.id, "approved", "", admin=True)
        listing.refresh_from_db()
        self.assertEqual(listing.status, "approved")
        self.assertNotEqual(listing.publication_status, "published")
        self.service.advance(listing.publication_task_id)
        listing.refresh_from_db()
        self.assertEqual(listing.publication_status, "published")

    def test_request_deduplication_and_test_install_records_are_distinct(self):
        version = self.publish()
        data = {"target": {"team_name": "team", "region_name": "region", "app_name": "Installed"}}
        task = self.service.operation(USER, SCOPE, version.id, "test", data, "install-1")
        duplicate = self.service.operation(USER, SCOPE, version.id, "test", data, "install-1")
        self.assertEqual(task.id, duplicate.id)
        self.service.advance(task.id)
        self.service.advance(task.id)
        task.refresh_from_db()
        self.assertEqual(task.kind, "test")
        self.assertEqual(task.result["app_id"], "target-app")

    def test_cancelled_candidate_never_becomes_a_version(self):
        task = self.service.start(USER, SCOPE, PAYLOAD, "cancel-1")
        self.service.cancel(SCOPE, task.id)
        self.service.advance(task.id)
        with self.assertRaises(DeliveryError):
            self.service.publish(USER, SCOPE, task.id)
        self.assertEqual(models.DeliveryTemplateVersion.objects.count(), 0)

    def test_other_enterprise_cannot_mutate_versions(self):
        version = self.publish()
        other = SimpleNamespace(user_id=1, enterprise_id="other", nick_name="Other")
        for action in [
                lambda: self.service.delete(other, SCOPE, version.id),
                lambda: self.service.listing(other, SCOPE, version.id, {"reason": "Release"}),
                lambda: self.service.operation(other, SCOPE, version.id, "offline", {})
        ]:
            with self.assertRaises(DeliveryError):
                action()

    def test_renaming_new_version_keeps_the_template_identity(self):
        first = self.publish()
        task = self.service.start(USER, SCOPE, {**PAYLOAD, "template_name": "Renamed", "version": "1.1.0"}, "rename-1")
        self.service.advance(task.id)
        self.service.advance(task.id)
        second = self.service.publish(USER, SCOPE, task.id)
        self.assertEqual(first.template_id, second.template_id)
        self.assertEqual(models.DeliveryTemplate.objects.count(), 1)

    def test_daemonset_vm_and_zero_resources_keep_their_own_semantics(self):
        daemonset = copy.deepcopy(SOURCE)
        daemonset["apps"][0]["extend_method"] = "daemonset"
        manifest = prepare(daemonset, PAYLOAD, "template")
        self.assertNotIn("min_node", manifest["apps"][0]["extend_method_map"])
        self.assertEqual(manifest["apps"][0]["extend_method_map"]["container_cpu"], 0)
        vm = copy.deepcopy(SOURCE)
        vm["apps"][0]["extend_method"] = "vm"
        vm["apps"][0]["vm"] = {"disk_layout": []}
        payload = copy.deepcopy(PAYLOAD)
        payload["component_overrides"][0].pop("extend_method_map")
        self.assertEqual(prepare(vm, payload, "template")["apps"][0]["vm"], {"disk_layout": []})

    def test_unbuilt_selected_component_is_rejected_without_requiring_a_snapshot(self):
        source = copy.deepcopy(SOURCE)
        source["apps"][0]["delivery_available"] = False
        with self.assertRaises(DeliveryError):
            prepare(source, PAYLOAD, "template")

    def test_sensitive_changes_detected_but_values_and_transport_credentials_not_returned(self):
        from console.services.delivery_manifest import public_manifest
        changed = copy.deepcopy(SOURCE)
        changed["apps"][0]["service_env_map_list"][1]["attr_value"] = "test-placeholder"
        public = public_manifest(changed)
        self.assertEqual(public["apps"][0]["service_env_map_list"][1]["attr_value"], "")
        self.assertEqual(compare(baseline(SOURCE), baseline(changed))["status"], "changed")
        public = public_manifest({"service_image": {"hub_password": "test-placeholder"}})
        self.assertEqual(public, {})

    def test_installation_parameters_are_encrypted_and_not_exposed_as_task_data(self):
        from console.services.delivery_credentials import seal, open_environment
        environment = {"web": {"PASSWORD": "test-placeholder"}}
        encrypted = seal(environment)
        self.assertNotIn("test-placeholder", encrypted)
        self.assertEqual(open_environment(encrypted), environment)
        version = self.publish()
        task = self.service.operation(USER, SCOPE, version.id, "delivery", {"encrypted_environment": encrypted})
        self.assertNotIn("encrypted_environment", self.service.task_data(task))

    def test_review_reject_requires_reason_and_admin_flag(self):
        version = self.publish()
        listing = self.service.listing(USER, SCOPE, version.id, {"reason": "Release"})
        with self.assertRaises(DeliveryError):
            self.service.review(USER, listing.id, "approved", "", admin=False)
        with self.assertRaises(DeliveryError):
            self.service.review(USER, listing.id, "rejected", "", admin=True)
        self.service.review(USER, listing.id, "rejected", "Revise", admin=True)
        retry = self.service.listing(USER, SCOPE, version.id, {"reason": "Revised"})
        self.assertNotEqual(listing.id, retry.id)

    def test_different_destinations_have_independent_listing_requests(self):
        version = self.publish()
        first = self.service.listing(USER, SCOPE, version.id, {"reason": "Catalog", "destination": {"type": "local"}})
        second = self.service.listing(USER, SCOPE, version.id, {
            "reason": "Store",
            "destination": {
                "type": "market",
                "market_id": "store"
            }
        })
        self.assertNotEqual(first.id, second.id)

    def test_deleting_version_cancels_pending_review_but_preserves_tasks_and_audit(self):
        version = self.publish()
        listing = self.service.listing(USER, SCOPE, version.id, {"reason": "Release"})
        export = self.service.operation(USER, SCOPE, version.id, "offline", {})
        self.service.delete(USER, SCOPE, version.id)
        listing.refresh_from_db()
        export.refresh_from_db()
        self.assertEqual(listing.status, "cancelled")
        self.assertEqual(export.version_id, version.id)
        self.assertEqual(models.DeliveryListingRequest.objects.count(), 1)

    def test_http_status_read_does_not_advance_jobs_and_admin_identity_is_server_derived(self):
        import sys
        from unittest import mock
        from rest_framework.views import APIView
        from rest_framework.permissions import IsAuthenticated
        from rest_framework.test import APIRequestFactory, force_authenticate
        import types

        class Base(APIView):
            authentication_classes = []
            permission_classes = [IsAuthenticated]

            def initial(inner, request, *args, **kwargs):
                super(Base, inner).initial(request, *args, **kwargs)
                inner.user = request.user
                inner.is_enterprise_admin = False

        base = types.ModuleType("console.views.base")
        base.JWTAuthApiView = Base
        message = types.ModuleType("www.utils.return_message")
        message.general_message = lambda code, msg, show, **kwargs: {"code": code, "msg_show": show, "data": kwargs}
        with mock.patch.dict(sys.modules, {"console.views.base": base, "www.utils.return_message": message}):
            path = Path(__file__).parents[1] / "views/delivery_templates.py"
            view_spec = importlib.util.spec_from_file_location("isolated_delivery_views", path)
            views = importlib.util.module_from_spec(view_spec)
            view_spec.loader.exec_module(views)
        task = self.service.start(USER, SCOPE, PAYLOAD, "http-1")
        factory = APIRequestFactory()
        user = SimpleNamespace(**USER.__dict__, is_authenticated=True)
        request = factory.get("/sync/" + str(task.id))
        force_authenticate(request, user=user)
        with mock.patch.object(views, "DeliveryService", return_value=self.service), \
             mock.patch.object(views, "start_delivery_worker"), \
             mock.patch.object(views.DeliverySyncTaskView, "scope", return_value=SCOPE):
            response = views.DeliverySyncTaskView.as_view()(request, team_name="team", app_id="123", task_id=str(task.id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.gateway.calls, [])
        request = factory.post("/review", {"decision": "approved", "is_enterprise_admin": True}, format="json")
        force_authenticate(request, user=user)
        with mock.patch.object(views, "DeliveryService", return_value=self.service), mock.patch.object(
                views, "start_delivery_worker"):
            response = views.DeliveryReviewView.as_view()(request, enterprise_id="enterprise", request_id=str(task.id))
        self.assertEqual(response.status_code, 403)

    def test_online_catalog_waits_for_real_artifact_sync_before_publishing(self):
        version = self.publish()
        listing = self.service.listing(USER, SCOPE, version.id, {
            "reason": "Release",
            "destination": {
                "type": "market",
                "market_id": "store"
            }
        })
        self.service.review(USER, listing.id, "approved", "", admin=True)
        listing.refresh_from_db()
        self.service.advance(listing.publication_task_id)
        listing.refresh_from_db()
        self.assertEqual(listing.publication_status, "publishing")
        self.service.advance(listing.publication_task_id)
        listing.refresh_from_db()
        self.assertEqual(listing.publication_status, "published")

    def test_source_url_credentials_become_install_time_parameters(self):
        source = copy.deepcopy(SOURCE)
        source["apps"][0]["service_env_map_list"][0] = {
            "attr_name": "DATABASE_URL",
            "attr_value": "https://test-user:test-placeholder@example.test/db"
        }
        payload = copy.deepcopy(PAYLOAD)
        payload["component_overrides"][0]["service_env_map_list"][0] = {"attr_name": "DATABASE_URL", "attr_value": ""}
        manifest = prepare(source, payload, "template")
        variable = manifest["apps"][0]["service_env_map_list"][0]
        self.assertEqual(variable["attr_value"], "")
        self.assertTrue(variable["required_on_install"])

    def test_legacy_slug_cannot_produce_an_incomplete_successful_template(self):
        source = copy.deepcopy(SOURCE)
        source["apps"][0]["delivered_type"] = "slug"
        with self.assertRaisesRegex(DeliveryError, "镜像构建"):
            prepare(source, PAYLOAD, "template")

    def test_target_team_requires_create_permission_and_completed_publication(self):
        import sys
        import types
        from unittest import mock
        from console.services import delivery_access
        version = self.publish()
        target = {"team_name": "other-team", "region_name": "region", "app_name": "Installed"}
        main = types.ModuleType("www.models.main")
        main.TenantRegionInfo = mock.Mock()
        main.TenantRegionInfo.objects.filter.return_value.exists.return_value = True
        with mock.patch.dict(sys.modules, {"www.models.main": main}), \
             mock.patch.object(delivery_access, "team_access", return_value=SimpleNamespace(tenant_id="target-id")) as access:
            with self.assertRaises(DeliveryError):
                delivery_access.target_access(USER, target, SCOPE, version, "delivery")
            access.assert_called_with(USER, "other-team", 300001, admin=False)
            listing = self.service.listing(USER, SCOPE, version.id, {"reason": "Release"})
            self.service.review(USER, listing.id, "approved", "", admin=True)
            with self.assertRaises(DeliveryError):
                delivery_access.target_access(USER, target, SCOPE, version, "delivery")
            listing.refresh_from_db()
            self.service.advance(listing.publication_task_id)
            delivery_access.target_access(USER, target, SCOPE, version, "delivery")
            with self.assertRaises(DeliveryError):
                delivery_access.target_access(USER, target, SCOPE, version, "test", admin=False)

    def test_actual_artifact_gateway_copies_retained_output_without_reading_source_app(self):
        import sys
        import types
        from unittest import mock
        from console.services.delivery_gateway import DeliveryGateway
        version = self.publish()
        task = models.DeliveryTask.objects.create(template=version.template,
                                                  version=version,
                                                  kind="catalog_publish",
                                                  actor_id=USER.user_id,
                                                  actor_name=USER.nick_name,
                                                  request_key="gateway-test",
                                                  payload={"destination": {
                                                      "type": "market",
                                                      "market_id": "store"
                                                  }},
                                                  result={"market_app_id": "remote-app"})
        item = models.DeliveryTaskItem.objects.create(task=task, key="web", component=version.manifest["apps"][0])
        app = types.ModuleType("console.services.app")
        app.app_market_service = mock.Mock()
        store = types.ModuleType("console.appstore.appstore")
        store.app_store = mock.Mock()
        store.app_store.get_app_hub_info.return_value = {
            "hub_url": "registry.test",
            "hub_user": "test-user",
            "hub_password": "test-placeholder"
        }
        store.app_store.get_slug_hub_info.return_value = {}
        api = mock.Mock()
        api.share_delivery_artifact.return_value = (None, {
            "bean": {
                "share_id": "remote-job",
                "image_name": "market.test/web:1"
            }
        })
        gateway = DeliveryGateway()
        with mock.patch.dict(sys.modules, {"console.services.app": app, "console.appstore.appstore": store}), \
             mock.patch.object(gateway, "region_api", return_value=api):
            result = gateway.dispatch_catalog_artifact(task, item)
        body = api.share_delivery_artifact.call_args.args[2]
        self.assertEqual(body["source_image"], "registry.test/frozen:build-1")
        self.assertEqual(body["version"], "1.0.0")
        self.assertNotIn("hub_password", result)
        self.assertEqual(result["share_id"], "remote-job")

    def test_source_comparison_ignores_variable_order_but_preserves_resource_content(self):
        reordered = copy.deepcopy(SOURCE)
        reordered["apps"][0]["service_env_map_list"].reverse()
        self.assertEqual(compare(baseline(SOURCE), baseline(reordered))["status"], "unchanged")
        reordered["apps"][0]["extend_method_map"]["container_cpu"] = 1500
        self.assertEqual(compare(baseline(SOURCE), baseline(reordered))["status"], "changed")

    def test_retirement_before_listing_lock_does_not_create_a_pending_request(self):
        from unittest import mock
        from django.utils import timezone
        stale_version = self.publish()
        models.DeliveryTemplateVersion.objects.filter(pk=stale_version.pk).update(deleted_at=timezone.now(),
                                                                                  deleted_by="First actor")
        # Model a read completed before another transaction retired the version.
        with mock.patch.object(self.service.repo, "version", return_value=stale_version):
            with self.assertRaises(DeliveryError):
                self.service.listing(USER, SCOPE, stale_version.id, {"reason": "Release"})
        self.assertEqual(models.DeliveryListingRequest.objects.count(), 0)

    def test_concurrent_delete_preserves_the_first_retirement_actor(self):
        from unittest import mock
        from django.utils import timezone
        stale_version = self.publish()
        retired_at = timezone.now()
        models.DeliveryTemplateVersion.objects.filter(pk=stale_version.pk).update(deleted_at=retired_at,
                                                                                  deleted_by="First actor")
        with mock.patch.object(self.service.repo, "version", return_value=stale_version):
            with self.assertRaises(DeliveryError):
                self.service.delete(USER, SCOPE, stale_version.id)
        stale_version.refresh_from_db()
        self.assertEqual(stale_version.deleted_by, "First actor")
        self.assertEqual(stale_version.deleted_at, retired_at)

    def test_empty_application_source_does_not_call_a_nonempty_component_endpoint(self):
        import json
        import sys
        import types
        from unittest import mock
        from console.services.delivery_gateway import DeliveryGateway
        main = types.ModuleType("www.models.main")
        main.Tenants = mock.Mock()
        main.Tenants.objects.get.return_value = SimpleNamespace(tenant_name="team", tenant_id="tenant")
        main.ServiceGroup = mock.Mock()
        main.ServiceGroup.objects.filter.return_value.first.return_value = SimpleNamespace(
            ID=123, group_name="Empty application", governance_mode="KUBERNETES_NATIVE_SERVICE")
        main.ServiceGroupRelation = mock.Mock()
        main.ServiceGroupRelation.objects.filter.return_value.values_list.return_value = []
        shared = types.ModuleType("console.services.share_services")
        shared.share_service = mock.Mock()
        shared.share_service.query_share_service_info.return_value = []
        shared.share_service.get_group_services_used_plugins.return_value = []
        shared.share_service.get_k8s_resources.return_value = []
        shared.share_service.config_groups.return_value = []
        shared.share_service._list_http_ingresses.return_value = []
        encoder = types.ModuleType("console.services.app_import_and_export_service")
        encoder.MyEncoder = json.JSONEncoder
        gateway, api = DeliveryGateway(), mock.Mock()
        api.get_team_services_deploy_version.return_value = (None, {"list": None})
        modules = {
            "www.models.main": main,
            "console.services.share_services": shared,
            "console.services.app_import_and_export_service": encoder
        }
        with mock.patch.dict(sys.modules, modules), mock.patch.object(gateway, "region_api", return_value=api):
            manifest, name = gateway.source(SCOPE)
        self.assertEqual(manifest["apps"], [])
        self.assertEqual(name, "Empty application")
        api.get_team_services_deploy_version.assert_not_called()


if __name__ == "__main__":
    unittest.main()
