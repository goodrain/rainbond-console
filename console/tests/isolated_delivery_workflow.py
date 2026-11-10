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
        "delivered_path":
        "registry.test/source:web-build-1",
        "delivered_type":
        "image",
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
        from django.db import migrations, models as fields
        legacy = migrations.Migration("catalog_note_baseline", "console")
        legacy.operations = [
            migrations.CreateModel(name="RainbondCenterAppVersion",
                                   fields=[("ID", fields.AutoField(primary_key=True)),
                                           ("app_version_info", fields.CharField(max_length=255))],
                                   options={"db_table": "rainbond_center_app_version"})
        ]
        with connection.schema_editor() as editor:
            state = legacy.apply(ProjectState(), editor)
            state = migration_module.Migration("0011_independent_delivery_templates", "console").apply(state, editor)
            next_spec = importlib.util.spec_from_file_location(
                "delivery_metadata_migration",
                Path(__file__).parents[1] / "migrations/0012_delivery_template_metadata.py")
            next_module = importlib.util.module_from_spec(next_spec)
            next_spec.loader.exec_module(next_module)
            next_module.Migration("0012_delivery_template_metadata", "console").apply(state, editor)

    def setUp(self):
        with connection.cursor() as cursor:
            for table in reversed(self.tables):
                cursor.execute('DELETE FROM "{}"'.format(table._meta.db_table))
        self.gateway = Gateway()
        self.service = DeliveryService(models=models, gateway=self.gateway)

    def create_version(self, data, request_key=None):
        if not self.service.repo.templates(SCOPE).exists():
            self.service.update_metadata(USER, SCOPE, data)
        return self.service.create(USER, SCOPE, data, request_key)

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
        self.assertEqual(listing.publication_status, "publishing")
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
        from www.utils.return_message import get_exception_message
        message = types.ModuleType("www.utils.return_message")
        message.get_exception_message = get_exception_message
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
            with self.assertRaises(DeliveryError):
                delivery_access.target_access(USER, target, SCOPE, version, "delivery")
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

    def test_direct_creation_saves_fixed_artifacts_without_a_sync_job(self):
        version = self.create_version(PAYLOAD, "direct-1")
        self.assertEqual(version.manifest["apps"][0]["share_image"], "registry.test/source:web-build-1")
        self.assertEqual(models.DeliveryTask.objects.count(), 0)
        self.assertEqual(self.gateway.calls, [])
        self.assertIsNone(version.sync_id)
        duplicate = self.create_version(PAYLOAD, "direct-1")
        self.assertEqual(duplicate.id, version.id)

    def test_long_release_notes_and_template_metadata_are_preserved(self):
        notes = "新增功能与修复记录\n" * 300
        version = self.create_version(
            {
                **PAYLOAD, "description": notes,
                "template_description": "应用用途简介",
                "logo": "/media/uploads/app.png"
            }, "metadata-1")
        self.assertEqual(version.description, notes)
        self.assertEqual(version.manifest["annotations"]["describe"], "应用用途简介")
        self.assertEqual(version.manifest["annotations"]["version_info"], notes)
        self.assertEqual(self.service.version_data(version)["logo"], "/media/uploads/app.png")

    def test_metadata_edit_does_not_rewrite_existing_version(self):
        version = self.create_version(PAYLOAD, "edit-1")
        before = copy.deepcopy(version.manifest)
        self.service.update_metadata(USER, SCOPE, {
            "template_name": "New name",
            "template_description": "New overview",
            "logo": "/media/uploads/new.png"
        })
        version.refresh_from_db()
        self.assertEqual(version.manifest, before)
        self.assertEqual(self.service.list(SCOPE)["template"]["name"], "New name")
        self.assertEqual(models.DeliveryTask.objects.count(), 0)

    def test_local_catalog_sync_starts_only_after_review(self):
        version = self.create_version(PAYLOAD, "review-sync-1")
        listing = self.service.listing(USER, SCOPE, version.id, {"reason": "Release"})
        self.assertEqual(self.gateway.calls, [])
        self.service.review(USER, listing.id, "approved", "", admin=True)
        listing.refresh_from_db()
        self.assertEqual(self.gateway.calls, [])
        self.service.advance(listing.publication_task_id)
        listing.refresh_from_db()
        self.assertEqual(listing.publication_status, "publishing")
        self.assertEqual(self.gateway.calls, ["build-1"])
        self.service.advance(listing.publication_task_id)
        listing.refresh_from_db()
        self.assertEqual(listing.publication_status, "published")

    def test_direct_version_can_install_and_export_without_listing(self):
        version = self.create_version(PAYLOAD, "private-use-1")
        install = self.service.operation(USER, SCOPE, version.id, "delivery",
                                         {"target": {
                                             "team_name": "team",
                                             "region_name": "region",
                                             "app_name": "Private"
                                         }})
        export = self.service.operation(USER, SCOPE, version.id, "offline", {"format": "docker-compose"})
        self.assertEqual(install.kind, "delivery")
        self.assertEqual(self.service.task_data(export)["export_format"], "docker-compose")
        self.assertEqual(models.DeliveryListingRequest.objects.count(), 0)
        with self.assertRaises(DeliveryError):
            self.service.operation(USER, SCOPE, version.id, "offline", {"format": "unsupported"})

    def test_export_reuses_active_format_and_retains_completed_records(self):
        version = self.create_version(PAYLOAD)
        first = self.service.operation(USER, SCOPE, version.id, "offline", {"format": "helm-chart"}, "export-one")
        second = self.service.operation(USER, SCOPE, version.id, "offline", {"format": "helm-chart"}, "export-two")
        self.assertEqual(first.id, second.id)
        different = self.service.operation(USER, SCOPE, version.id, "offline", {"format": "docker-compose"})
        self.assertNotEqual(first.id, different.id)
        self.service.advance(first.id)
        self.service.advance(first.id)
        first.refresh_from_db()
        self.assertTrue(self.service.task_data(first)["download_url"])
        next_export = self.service.operation(USER, SCOPE, version.id, "offline", {"format": "helm-chart"}, "export-three")
        self.assertNotEqual(first.id, next_export.id)
        self.assertEqual(version.tasks.filter(kind="offline").count(), 3)
        with self.assertRaises(DeliveryError):
            self.service.operation(USER, SCOPE, version.id, "offline", {"format": "docker-compose"}, "export-one")

    def test_local_catalog_gateway_publishes_copied_artifacts_and_frozen_metadata(self):
        import sys
        import types
        import json
        from unittest import mock
        from console.services.delivery_gateway import DeliveryGateway
        version = self.create_version({**PAYLOAD, "logo": "/uploads/logo.png", "template_description": "Application summary"})
        task = models.DeliveryTask.objects.create(template=version.template,
                                                  version=version,
                                                  kind="catalog_publish",
                                                  actor_id=1,
                                                  actor_name="Reviewer",
                                                  request_key="local-catalog",
                                                  payload={"destination": {
                                                      "type": "local"
                                                  }})
        models.DeliveryTaskItem.objects.create(task=task,
                                               key="web",
                                               component=version.manifest["apps"][0],
                                               result={"image_name": "catalog.test/web:1.0.0"},
                                               status="succeeded")
        main, app = types.ModuleType("console.models.main"), types.ModuleType("console.services.app")
        main.RainbondCenterApp = mock.Mock()
        main.RainbondCenterAppVersion = mock.Mock()
        app.app_market_service = mock.Mock()
        with mock.patch.dict(sys.modules, {"console.models.main": main, "console.services.app": app}):
            result = DeliveryGateway().publish_catalog(task)
        saved = main.RainbondCenterAppVersion.objects.get_or_create.call_args.kwargs["defaults"]
        manifest = json.loads(saved["app_template"])
        self.assertEqual(manifest["apps"][0]["share_image"], "catalog.test/web:1.0.0")
        self.assertEqual(result["published_manifest"]["apps"][0]["share_image"], "catalog.test/web:1.0.0")
        metadata = main.RainbondCenterApp.objects.update_or_create.call_args.kwargs["defaults"]
        self.assertEqual(metadata["pic"], "/uploads/logo.png")
        self.assertEqual(metadata["describe"], "Application summary")
        self.assertEqual(version.manifest["apps"][0]["share_image"], "registry.test/source:web-build-1")
        app.app_market_service.create_market_app_model_version.assert_not_called()

    def test_export_gateway_preserves_selected_formats_and_existing_image_references(self):
        import sys
        import types
        import json
        from unittest import mock
        from console.services.delivery_gateway import DeliveryGateway
        version = self.create_version(PAYLOAD)
        encoder = types.ModuleType("console.services.app_import_and_export_service")
        encoder.export_service = mock.Mock()
        encoder.export_service._AppExportService__normalize_export_template.side_effect = copy.deepcopy
        store = types.ModuleType("console.appstore.appstore")
        store.app_store = mock.Mock()
        store.app_store.get_app_hub_info.return_value = {}
        gateway, api = DeliveryGateway(), mock.Mock()
        with mock.patch.dict(sys.modules, {"console.services.app_import_and_export_service": encoder,
                                          "console.appstore.appstore": store}), \
             mock.patch.object(gateway, "region_api", return_value=api):
            for format_name in ("rainbond-app", "docker-compose", "helm-chart", "slug"):
                task = self.service.operation(USER, SCOPE, version.id, "offline", {"format": format_name})
                gateway.export(task)
                body = api.export_app.call_args.args[2]
                self.assertEqual(body["format"], format_name)
                manifest = json.loads(body["group_metadata"])
                self.assertEqual(manifest["apps"][0]["share_image"], "registry.test/source:web-build-1")
                self.assertEqual(manifest["helm_chart"]["image_handle"], "image_save")

    def test_install_manifest_uses_private_artifact_until_cross_team_publication(self):
        from console.services.delivery_gateway import DeliveryGateway
        version = self.create_version(PAYLOAD)
        task = self.service.operation(USER, SCOPE, version.id, "delivery",
                                      {"target": {
                                          "team_name": "team",
                                          "region_name": "region"
                                      }})
        gateway = DeliveryGateway()
        self.assertEqual(gateway.installation_manifest(task)[0]["apps"][0]["share_image"], "registry.test/source:web-build-1")
        listing = self.service.listing(USER, SCOPE, version.id, {"reason": "List"})
        listing = self.service.review(USER, listing.id, "approved", "", admin=True)
        published = copy.deepcopy(version.manifest)
        published["apps"][0]["share_image"] = "catalog.test/web:1.0.0"
        publication = listing.publication_task
        publication.result = {"published_manifest": published}
        publication.save()
        listing.publication_status = "published"
        listing.save()
        task.payload["target"]["team_name"] = "another-team"
        self.assertEqual(gateway.installation_manifest(task)[0]["apps"][0]["share_image"], "catalog.test/web:1.0.0")

    def test_market_application_metadata_is_separate_from_long_release_notes(self):
        import sys
        import types
        from unittest import mock
        from console.services.delivery_gateway import DeliveryGateway
        version = self.create_version({
            **PAYLOAD, "logo": "/uploads/logo.png",
            "template_description": "Application summary",
            "description": "Release notes\n" * 300
        })
        task = models.DeliveryTask.objects.create(template=version.template,
                                                  version=version,
                                                  kind="catalog_publish",
                                                  actor_id=1,
                                                  actor_name="Reviewer",
                                                  request_key="market-metadata",
                                                  payload={"destination": {
                                                      "type": "market",
                                                      "market_id": "store"
                                                  }})
        app, store = types.ModuleType("console.services.app"), types.ModuleType("console.appstore.appstore")
        app.app_market_service, store.app_store = mock.Mock(), mock.Mock()
        store.app_store.create_app.return_value = {"app_id": "remote-app"}
        with mock.patch.dict(sys.modules, {
                "console.services.app": app,
                "console.appstore.appstore": store,
                "console.models.delivery_template": models
        }):
            DeliveryGateway().prepare_catalog(task)
        metadata = store.app_store.create_app.call_args.args[1]
        self.assertEqual(metadata["desc"], "Application summary")
        self.assertEqual(metadata["logo"], "/uploads/logo.png")
        self.assertEqual(task.result["market_app_id"], "remote-app")

    def test_template_can_be_created_before_any_version_or_component_sync(self):
        self.service.gateway.source = lambda scope: self.fail("Metadata creation must not read component build artifacts")
        template = self.service.update_metadata(USER, SCOPE, {
            "template_name": "Team template",
            "logo": "/uploads/team.png",
            "template_description": "Purpose"
        })
        self.assertEqual(self.service.list(SCOPE)["template"]["id"], str(template.id))
        self.assertEqual(self.service.list(SCOPE)["items"], [])
        self.assertEqual(models.DeliveryTask.objects.count(), 0)

    def test_version_creation_requires_an_existing_template(self):
        with self.assertRaises(DeliveryError):
            self.service.create(USER, SCOPE, {"version": "1.0.0", "service_ids": ["web"]})
        self.assertFalse(models.DeliveryTemplate.objects.exists())

    def test_publishing_version_uses_current_metadata_without_modifying_it(self):
        template = self.service.update_metadata(USER, SCOPE, {
            "template_name": "Current template",
            "logo": "/uploads/current.png",
            "template_description": "Current description"
        })
        version = self.service.create(USER, SCOPE, {
            **PAYLOAD, "template_name": "Stale name",
            "logo": "/uploads/stale.png",
            "template_description": "Stale description"
        })
        template.refresh_from_db()
        self.assertEqual(template.name, "Current template")
        self.assertEqual(template.logo, "/uploads/current.png")
        self.assertEqual(version.manifest["group_name"], "Current template")
        self.assertEqual(version.manifest["annotations"]["describe"], "Current description")
        self.assertEqual(version.manifest["annotations"]["logo"], "/uploads/current.png")

    def test_metadata_edits_apply_to_new_versions_while_old_versions_remain_frozen(self):
        first = self.create_version(PAYLOAD)
        self.service.update_metadata(USER, SCOPE, {
            "template_name": "Updated template",
            "logo": "/uploads/updated.png",
            "template_description": "Updated purpose"
        })
        second = self.service.create(
            USER, SCOPE, {
                "version": "1.0.1",
                "description": "New release",
                "service_ids": PAYLOAD["service_ids"],
                "component_overrides": PAYLOAD["component_overrides"]
            })
        first.refresh_from_db()
        self.assertEqual(first.manifest["group_name"], PAYLOAD["template_name"])
        self.assertEqual(second.manifest["group_name"], "Updated template")
        self.assertEqual(second.manifest["annotations"]["logo"], "/uploads/updated.png")
        self.assertEqual(first.template_id, second.template_id)
        self.assertEqual(second.template.versions.count(), 2)

    def test_catalog_profile_payload_creates_and_edits_only_private_template_information(self):
        template = self.service.save_catalog_metadata(USER, SCOPE, {
            "name": "Private template",
            "pic": "/uploads/private.png",
            "describe": "Purpose"
        })
        self.assertEqual(template.logo, "/uploads/private.png")
        self.assertFalse(template.versions.exists())
        self.assertEqual(models.DeliveryTask.objects.count(), 0)
        updated = self.service.save_catalog_metadata(USER, SCOPE, {
            "name": "Updated template",
            "describe": "New purpose"
        }, template.id.hex)
        self.assertEqual(updated.id, template.id)
        self.assertEqual(updated.name, "Updated template")
        with self.assertRaises(DeliveryError):
            self.service.save_catalog_metadata(USER, SCOPE, {"name": "Wrong app"}, "0" * 32)
        with self.assertRaises(DeliveryError):
            self.service.save_catalog_metadata(USER, SCOPE, {"name": "Duplicate"})

    def test_catalog_metadata_source_requires_same_enterprise_and_application_permission(self):
        import sys
        import types
        from unittest import mock
        from console.services.delivery_access import catalog_metadata_scope
        main = types.ModuleType("www.models.main")
        main.ServiceGroup = mock.Mock()
        main.ServiceGroup.objects.filter.return_value.exists.return_value = True
        source = {"team_name": "team", "region_name": "region", "app_id": "123"}
        with mock.patch.dict(sys.modules, {"www.models.main": main}), \
             mock.patch("console.services.delivery_access.team_access") as access:
            self.assertEqual(catalog_metadata_scope(USER, "enterprise", source), SCOPE)
            access.assert_called_once_with(USER, "team", 310001, "123", False)
            with self.assertRaises(DeliveryError):
                catalog_metadata_scope(USER, "another-enterprise", source)
            main.ServiceGroup.objects.filter.return_value.exists.return_value = False
            with self.assertRaises(DeliveryError):
                catalog_metadata_scope(USER, "enterprise", source)

    def test_listing_exposes_current_profile_separately_from_the_frozen_version(self):
        version = self.create_version(PAYLOAD)
        listing = self.service.listing(USER, SCOPE, version.id, {"reason": "Review"})
        self.service.update_metadata(USER, SCOPE, {
            "template_name": "Current profile",
            "template_description": "Current purpose"
        })
        listing = models.DeliveryListingRequest.objects.select_related("version__template").get(id=listing.id)
        data = self.service.listing_data(listing)
        self.assertEqual(data["template_profile"]["name"], "Current profile")
        self.assertEqual(data["template"]["template_name"], PAYLOAD["template_name"])


if __name__ == "__main__":
    unittest.main()
