"""Keep delivery SQLite settings isolated from the rest of the Django suite."""
import subprocess
import os
import sys
import unittest
from pathlib import Path


class DeliveryWorkflowTest(unittest.TestCase):
    def test_closing_snapshot_draft_never_runs_market_version_cleanup(self):
        from types import SimpleNamespace
        from unittest import mock
        from console.views import service_share as module
        view = module.ServiceShareDeleteView()
        draft = SimpleNamespace(app_id="snapshot-hidden", group_id=42, scope="", share_version=None, is_success=False, step=1)
        relation = SimpleNamespace(app_model_id="snapshot-hidden", template_type="application_version")
        with mock.patch.object(module.share_service, "get_service_share_record_by_ID", return_value=draft), mock.patch.object(
                module.app_version_service, "get_relation", return_value=relation), mock.patch.object(
                    module.share_service,
                    "get_app_version_by_app_id",
                    side_effect=AssertionError(
                        "Snapshot drafts must not query market versions")) as versions, mock.patch.object(
                            module.share_service, "delete_record") as close:
            result = view.delete(SimpleNamespace(), "source", "7")
        self.assertEqual(result.status_code, 200)
        versions.assert_not_called()
        close.assert_called_once_with(draft)

    def test_component_list_returns_cpu_memory_and_replica_configuration_without_changing_aggregate_memory(self):
        import uuid
        from django.db import transaction
        from django.utils import timezone
        from www.models.main import ServiceGroup, ServiceGroupRelation, TenantServiceInfo
        from console.services.service_services import base_service
        with transaction.atomic():
            tenant_id = uuid.uuid4().hex
            app = ServiceGroup.objects.create(tenant_id=tenant_id,
                                              group_name="Runtime test",
                                              region_name="test-region",
                                              create_time=timezone.now(),
                                              update_time=timezone.now())
            component = TenantServiceInfo.objects.create(tenant_id=tenant_id,
                                                         service_id=uuid.uuid4().hex,
                                                         service_alias="runtime-test",
                                                         service_cname="Runtime test",
                                                         service_region="test-region",
                                                         min_cpu=750,
                                                         min_memory=256,
                                                         min_node=2,
                                                         create_time=timezone.now(),
                                                         update_time=timezone.now())
            ServiceGroupRelation.objects.create(tenant_id=tenant_id,
                                                region_name="test-region",
                                                group_id=app.ID,
                                                service_id=component.service_id)
            rows = base_service.get_group_services_list(tenant_id, "test-region", str(app.ID))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].get("container_cpu"), 750)
            self.assertEqual(rows[0].get("container_memory"), 256)
            self.assertEqual(rows[0].get("current_node"), 2)
            self.assertEqual(rows[0]["min_memory"], 512)
            transaction.set_rollback(True)

    def test_delivery_detail_reports_missing_source_application_without_removing_the_asset(self):
        import uuid
        from types import SimpleNamespace
        from django.db import transaction
        from django.utils import timezone
        from www.models.main import ServiceGroup, Tenants
        from console.models.delivery_template import DeliveryTemplate
        from console.services.delivery_templates import DeliveryService
        from console.views.delivery_templates import DevelopmentDeliveriesView
        with transaction.atomic():
            team = Tenants.objects.create(tenant_id=uuid.uuid4().hex,
                                          tenant_name="runtime-" + uuid.uuid4().hex[:12],
                                          enterprise_id="runtime-test",
                                          tenant_alias="Runtime test")
            app = ServiceGroup.objects.create(tenant_id=team.tenant_id,
                                              group_name="Runtime test",
                                              region_name="test-region",
                                              create_time=timezone.now(),
                                              update_time=timezone.now())
            profile = DeliveryTemplate.objects.create(enterprise_id="runtime-test",
                                                      team_name=team.tenant_name,
                                                      region_name="test-region",
                                                      app_id=str(app.ID),
                                                      name="Template",
                                                      app_name="Runtime test")
            view = DevelopmentDeliveriesView()
            view.user = SimpleNamespace(enterprise_id="runtime-test")
            view.is_enterprise_admin = True
            view.delivery = DeliveryService()
            view.reply = lambda bean: bean
            request = SimpleNamespace(GET={"group_id": str(profile.id)})
            self.assertTrue(view.get(request, "runtime-test")["source_app_exists"])
            app.delete()
            self.assertFalse(view.get(request, "runtime-test")["source_app_exists"])
            self.assertTrue(DeliveryTemplate.objects.filter(pk=profile.pk).exists())
            transaction.set_rollback(True)

    @unittest.skipUnless(os.environ.get("RAINBOND_TEST_MYSQL_SOCKET"), "Requires an isolated MySQL test socket")
    def test_mysql_mixed_collations_preserve_catalog_visibility(self):
        from django.db import connections
        from console.models.main import RainbondCenterApp, RainbondCenterAppVersion
        from console.models.delivery_template import (DeliveryTemplate, DeliveryTemplateVersion, DeliveryListingRequest,
                                                      DeliveryTask)
        from console.services.delivery_catalog import visible_catalog_apps, visible_catalog_versions
        import tempfile
        socket = Path(os.environ["RAINBOND_TEST_MYSQL_SOCKET"]).resolve()
        self.assertTrue(socket.parent.name.startswith("rainbond-collation-"))
        self.assertIn(socket.parent.parent, (Path("/tmp").resolve(), Path(tempfile.gettempdir()).resolve()))
        alias = "catalog_collation_mysql"
        connections.databases[alias] = {
            **connections.databases["default"], "ENGINE": "django.db.backends.mysql",
            "NAME": "rainbond_collation_regression", "HOST": str(socket), "USER": "root",
            "OPTIONS": {"charset": "utf8mb4"}, "AUTOCOMMIT": True
        }
        connection = connections[alias]
        tables = [DeliveryTemplate, DeliveryTemplateVersion, DeliveryTask, DeliveryListingRequest,
                  RainbondCenterApp, RainbondCenterAppVersion]
        created = []
        try:
            with connection.schema_editor() as editor:
                for model in tables:
                    editor.create_model(model)
                    created.append(model)
            with connection.cursor() as cursor:
                for model in (RainbondCenterApp, RainbondCenterAppVersion):
                    cursor.execute("ALTER TABLE " + connection.ops.quote_name(model._meta.db_table) +
                                   " CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            profile = DeliveryTemplate.objects.using(alias).create(
                enterprise_id="collation-test", team_name="source", region_name="region", app_id="42",
                name="Template", app_name="Application")
            RainbondCenterApp.objects.using(alias).create(
                app_id=profile.id.hex, enterprise_id="collation-test", app_name="Template", scope="enterprise")
            version = DeliveryTemplateVersion.objects.using(alias).create(
                template=profile, version="1.0.0", creator_id=1, creator_name="Tester", manifest={},
                source_baseline={}, digest="test")
            RainbondCenterAppVersion.objects.using(alias).create(
                app_id=profile.id.hex, version="1.0.0", record_id=0, share_user=1, share_team="source", is_complete=True)
            row = DeliveryListingRequest.objects.using(alias).create(
                version=version, reason="Publish", applicant_id=1, applicant_name="Tester", status="approved",
                publication_status="published", destination={"type": "local"})
            apps = visible_catalog_apps(RainbondCenterApp.objects.using(alias).all())
            versions = visible_catalog_versions(RainbondCenterAppVersion.objects.using(alias).all())
            self.assertEqual(apps.count(), 1)
            self.assertEqual(versions.count(), 1)
            import uuid
            legacy_id = uuid.uuid4().hex
            RainbondCenterApp.objects.using(alias).create(
                app_id=legacy_id, enterprise_id="collation-test", app_name="Legacy template", scope="enterprise")
            RainbondCenterAppVersion.objects.using(alias).create(
                app_id=legacy_id, version="0.1.0", record_id=0, share_user=1, share_team="source", is_complete=True)
            self.assertEqual(apps.count(), 2)
            self.assertEqual(versions.count(), 2)
            row.publication_status = "unlisted"
            row.save(using=alias)
            self.assertEqual(apps.count(), 1)
            self.assertEqual(versions.count(), 1)
            row.publication_status = "published"
            row.save(using=alias)
            self.assertEqual(apps.count(), 2)
            self.assertEqual(versions.count(), 2)
        finally:
            with connection.schema_editor() as editor:
                for model in reversed(created):
                    editor.delete_model(model)
            connection.close()
            del connections[alias]
            connections.databases.pop(alias, None)

    def test_unlisted_delivery_catalog_versions_are_hidden_but_legacy_templates_and_other_versions_remain_visible(self):
        from django.db import transaction
        from console.models.main import RainbondCenterApp, RainbondCenterAppVersion
        from console.models.delivery_template import DeliveryTemplate, DeliveryTemplateVersion, DeliveryListingRequest
        from console.services.delivery_catalog import visible_catalog_apps, visible_catalog_versions, catalog_version_available
        import uuid
        with transaction.atomic():
            profile = DeliveryTemplate.objects.create(enterprise_id="test-visibility",
                                                      team_name="source",
                                                      region_name="region",
                                                      app_id="42",
                                                      name="Template",
                                                      app_name="App")
            app = RainbondCenterApp.objects.create(app_id=profile.id.hex,
                                                   enterprise_id="test-visibility",
                                                   app_name="Template",
                                                   scope="enterprise",
                                                   is_version=True)
            first = DeliveryTemplateVersion.objects.create(template=profile,
                                                           version="1.0.0",
                                                           creator_id=1,
                                                           creator_name="User",
                                                           manifest={},
                                                           source_baseline={},
                                                           digest="test")
            listing = DeliveryListingRequest.objects.create(version=first,
                                                            reason="Publish",
                                                            applicant_id=1,
                                                            applicant_name="User",
                                                            status="approved",
                                                            publication_status="published",
                                                            destination={"type": "local"})
            catalog = RainbondCenterAppVersion.objects.create(app_id=profile.id.hex,
                                                              version="1.0.0",
                                                              record_id=0,
                                                              share_user=1,
                                                              share_team="source",
                                                              is_complete=True)
            legacy = RainbondCenterAppVersion.objects.create(app_id=uuid.uuid4().hex,
                                                             version="0.1.0",
                                                             record_id=0,
                                                             share_user=1,
                                                             share_team="source",
                                                             is_complete=True)
            self.assertTrue(visible_catalog_versions(RainbondCenterAppVersion.objects.filter(pk=catalog.pk)).exists())
            listing.publication_status = "unlisted"
            listing.save()
            self.assertFalse(visible_catalog_versions(RainbondCenterAppVersion.objects.filter(pk=catalog.pk)).exists())
            self.assertFalse(visible_catalog_apps(RainbondCenterApp.objects.filter(pk=app.pk)).exists())
            DeliveryListingRequest.objects.create(version=first,
                                                  reason="Sync",
                                                  applicant_id=1,
                                                  applicant_name="User",
                                                  status="not_required",
                                                  publication_status="published",
                                                  destination={
                                                      "type": "market",
                                                      "market_id": "store"
                                                  })
            self.assertFalse(visible_catalog_apps(RainbondCenterApp.objects.filter(pk=app.pk)).exists())
            self.assertFalse(catalog_version_available(profile.id.hex, "1.0.0"))
            self.assertTrue(catalog_version_available(legacy.app_id, "0.1.0"))
            self.assertTrue(visible_catalog_versions(RainbondCenterAppVersion.objects.filter(pk=legacy.pk)).exists())
            second = DeliveryTemplateVersion.objects.create(template=profile,
                                                            version="2.0.0",
                                                            creator_id=1,
                                                            creator_name="User",
                                                            manifest={},
                                                            source_baseline={},
                                                            digest="test")
            DeliveryListingRequest.objects.create(version=second,
                                                  reason="Publish",
                                                  applicant_id=1,
                                                  applicant_name="User",
                                                  status="approved",
                                                  publication_status="published",
                                                  destination={"type": "local"})
            self.assertTrue(visible_catalog_apps(RainbondCenterApp.objects.filter(pk=app.pk)).exists())
            self.assertFalse(visible_catalog_versions(RainbondCenterAppVersion.objects.filter(pk=catalog.pk)).exists())
            listing.publication_status = "published"
            listing.save()
            self.assertTrue(visible_catalog_versions(RainbondCenterAppVersion.objects.filter(pk=catalog.pk)).exists())
            transaction.set_rollback(True)

    def test_listing_withdrawal_endpoint_requires_application_write_scope_and_exact_version(self):
        from types import SimpleNamespace
        from unittest import mock
        from console.views.delivery_templates import DeliveryListingWithdrawalView
        view = DeliveryListingWithdrawalView()
        view.user = SimpleNamespace(user_id=1)
        view.scope = mock.Mock(return_value={"app_id": "42"})
        view.delivery = mock.Mock()
        view.reply = lambda bean: bean
        request = SimpleNamespace(data={"action": "cancel"})
        view.post(request, "source", "42", "version-1", "request-1")
        view.scope.assert_called_once_with(request, "source", "42", write=True)
        view.delivery.withdraw_listing.assert_called_once_with(view.user, {"app_id": "42"}, "version-1", "request-1", "cancel")

    def test_private_delivery_source_appears_in_the_existing_upgrade_list_without_a_market_copy(self):
        from datetime import datetime
        from types import SimpleNamespace
        from unittest import mock
        from console.services import market_app_service as module
        key = "112530304174481d91398b63d845401e"
        model = SimpleNamespace(app_name="Private delivery", create_user=1, create_team="source",
                                app_id=key, pic="", source="local", describe="Private application",
                                is_official=False, details="Introduction")
        tenant = SimpleNamespace(enterprise_id="enterprise", tenant_id="tenant", tenant_name="source")
        source = mock.Mock(team_id="tenant")
        source.is_install_from_cloud.return_value = False
        source.get_market_name.return_value = None
        source.get_template_update_time.return_value = None
        versions = [SimpleNamespace(version=version, update_time=datetime(2026, 11, 12))
                    for version in ("2.0.0", "1.0.0")]
        with mock.patch.object(module, "delivery_upgrade_source") as delivery, \
                mock.patch.object(module.rainbond_app_repo, "get_rainbond_app_and_version") as catalog, \
                mock.patch.object(module.upgrade_service, "get_app_not_upgrade_record",
                                  return_value=SimpleNamespace(ID=0, status=0)):
            delivery.model.return_value = model
            delivery.version_options.return_value = versions
            rows = list(module.market_app_service.yield_app_info({key + "-73": {
                "version": "1.0.0", "component_source": source}}, tenant, "42"))
        self.assertEqual(rows[0]["group_name"], "Private delivery")
        self.assertEqual(rows[0]["current_version"], "1.0.0")
        self.assertEqual(rows[0]["upgrade_versions"], {"2.0.0"})
        catalog.assert_not_called()
        delivery.version_options.assert_called_once_with("enterprise", key, "source")

    def test_upgrade_comparison_loads_the_frozen_private_version_for_the_target_team(self):
        from unittest import mock
        from console.services import upgrade_services as module
        manifest = {"group_version": "2.0.0", "apps": [{"service_id": "frozen-component"}]}
        source = mock.Mock(team_id="tenant")
        source.is_install_from_cloud.return_value = False
        with mock.patch.object(module, "delivery_upgrade_source") as delivery, \
                mock.patch.object(module, "target_team_name", return_value="source"), \
                mock.patch.object(module.rainbond_app_repo, "get_rainbond_app_and_version") as catalog:
            delivery.template.return_value = mock.Mock()
            delivery.manifest.return_value = manifest
            result = module.UpgradeService._app_template("enterprise", "private-key", "2.0.0", source)
        self.assertIs(result, manifest)
        delivery.manifest.assert_called_once_with("enterprise", "private-key", "2.0.0", "source")
        catalog.assert_not_called()

    def test_online_publish_retry_uses_source_permission_but_local_retry_requires_admin(self):
        from contextlib import nullcontext
        from types import SimpleNamespace
        from unittest import mock
        from console.views.delivery_templates import DeliveryTaskRetryView
        from console.services.delivery_manifest import DeliveryError
        view = DeliveryTaskRetryView()
        view.user, view.is_enterprise_admin = SimpleNamespace(enterprise_id="enterprise"), False
        view.admin = mock.Mock(side_effect=DeliveryError("仅管理员", 403))
        task = mock.Mock(status="failed",
                         kind="catalog_publish",
                         version=SimpleNamespace(deleted_at=None),
                         template=SimpleNamespace(team_name="source", app_id="11"),
                         payload={"destination": {
                             "type": "market",
                             "market_id": "store"
                         }})
        view.delivery = mock.Mock()
        selected = view.delivery.m.DeliveryTask.objects.select_for_update.return_value.select_related.return_value
        selected.filter.return_value.first.return_value = task
        view.delivery.task_data.return_value = {"id": "task", "status": "queued"}
        with mock.patch("django.db.transaction.atomic", return_value=nullcontext()), \
                mock.patch("console.views.delivery_templates.team_access") as access:
            response = view.post(SimpleNamespace(), "task")
            self.assertEqual(response.status_code, 202)
            access.assert_called_once_with(view.user, "source", 310001, "11", False)
            view.admin.assert_not_called()
            task.status = "failed"
            task.payload = {"destination": {"type": "local"}}
            with self.assertRaises(DeliveryError):
                view.post(SimpleNamespace(), "task")
            view.admin.assert_called_once_with("enterprise")

    def test_upgrade_availability_checks_source_access_and_uses_target_gateway(self):
        from types import SimpleNamespace
        from unittest import mock
        from console.views.delivery_templates import DeliveryTaskUpgradeView
        from console.services.delivery_manifest import DeliveryError
        view = DeliveryTaskUpgradeView()
        view.user = SimpleNamespace(enterprise_id="enterprise")
        view.is_enterprise_admin = False
        task = SimpleNamespace(template=SimpleNamespace(team_name="source-team", app_id="11"))
        view.delivery = mock.Mock()
        view.delivery.m.DeliveryTask.objects.select_related.return_value.filter.return_value.first.return_value = task
        view.delivery.gateway.upgrade_info.return_value = {"available": False}
        with mock.patch("console.views.delivery_templates.team_access") as permission:
            response = view.get(SimpleNamespace(), "task-id")
            permission.assert_called_once_with(view.user, "source-team", 300002, "11", False)
            view.delivery.gateway.upgrade_info.assert_called_once_with(task, view.user, False)
            self.assertEqual(response.status_code, 200)
            permission.side_effect = DeliveryError("无权访问", 403)
            view.delivery.gateway.upgrade_info.reset_mock()
            with self.assertRaises(DeliveryError):
                view.get(SimpleNamespace(), "task-id")
            view.delivery.gateway.upgrade_info.assert_not_called()

    def test_independent_delivery_workflow(self):
        result = subprocess.run([sys.executable, "-m", "console.tests.isolated_delivery_workflow"],
                                cwd=Path(__file__).parents[2],
                                capture_output=True,
                                text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_existing_app_model_endpoints_accept_delivery_source(self):
        from types import SimpleNamespace
        from unittest import mock
        from rest_framework.response import Response
        from console.views.center_pool.apps import CenterAppCLView, CenterAppUDView
        request = SimpleNamespace(META={},
                                  data={"delivery_source": {
                                      "team_name": "team",
                                      "region_name": "region",
                                      "app_id": "123"
                                  }})
        with mock.patch("console.views.center_pool.apps.save_delivery_profile", return_value=Response({"ok": True})) as save:
            create_view = CenterAppCLView()
            create_view.post(request, "enterprise")
            save.assert_called_once_with(create_view, request, "enterprise")
            save.reset_mock()
            edit_view = CenterAppUDView()
            edit_view.put(request, "enterprise", "template-id")
            save.assert_called_once_with(edit_view, request, "enterprise", "template-id")

    def test_existing_catalog_creation_without_source_uses_original_service(self):
        from types import SimpleNamespace
        from unittest import mock
        from console.views.center_pool.apps import CenterAppCLView
        request = SimpleNamespace(META={}, data={"name": "CatalogTemplate", "scope": "team", "create_team": "team"})
        view = CenterAppCLView()
        view.user = SimpleNamespace(enterprise_id="enterprise")
        with mock.patch("console.views.center_pool.apps.save_delivery_profile") as delivery, \
             mock.patch("console.views.center_pool.apps.market_app_service") as market, \
             mock.patch("console.views.center_pool.apps.app_tag_repo") as tags, \
             mock.patch("console.views.center_pool.apps.operation_log_service"):
            tags.get_tags.return_value = []
            market.json_rainbond_app.return_value = "{}"
            response = view.post(request, "enterprise")
        self.assertEqual(response.status_code, 200)
        market.create_rainbond_app.assert_called_once()
        delivery.assert_not_called()
