"""Keep delivery SQLite settings isolated from the rest of the Django suite."""
import subprocess
import sys
import unittest
from pathlib import Path


class DeliveryWorkflowTest(unittest.TestCase):
    def test_snapshot_source_is_scoped_to_the_same_team_application_and_snapshot_type(self):
        from types import SimpleNamespace
        from unittest import mock
        from console.models import main as models
        from www.models import main as legacy
        from console.services.delivery_gateway import DeliveryGateway
        from console.services.delivery_manifest import DeliveryError
        scope = dict(enterprise_id='enterprise', team_name='source', region_name='region', app_id='42')
        gateway = DeliveryGateway()
        with mock.patch.object(legacy, 'Tenants') as tenants, mock.patch.object(legacy, 'ServiceGroup') as apps, \
                mock.patch.object(models, 'AppVersionTemplateRelation') as relations, \
                mock.patch.object(models, 'RainbondCenterAppVersion') as versions:
            tenants.objects.filter.return_value.first.return_value = SimpleNamespace(tenant_id='tenant')
            apps.objects.filter.return_value.first.return_value = SimpleNamespace(ID=42, group_name='Source')
            relations.objects.filter.return_value.first.return_value = SimpleNamespace(app_model_id='hidden-model')
            versions.objects.filter.return_value.first.return_value = SimpleNamespace(
                ID=51, version='0.0.3', app_template='{"apps": []}')
            source, name = gateway.snapshot_source(scope, '51')
            self.assertEqual(name, 'Source')
            self.assertEqual(source['source_snapshot']['version'], '0.0.3')
            tenants.objects.filter.assert_called_once_with(tenant_name='source', enterprise_id='enterprise')
            apps.objects.filter.assert_called_once_with(ID='42', tenant_id='tenant', region_name='region')
            relations.objects.filter.assert_called_once_with(
                group_id=42, tenant_id='tenant', template_type='application_version')
            versions.objects.filter.assert_called_once_with(
                ID='51', app_id='hidden-model', template_type='application_version')
            versions.objects.filter.return_value.first.return_value = None
            with self.assertRaises(DeliveryError) as failure:
                gateway.snapshot_source(scope, '52')
            self.assertEqual(failure.exception.status, 404)
            for invalid in ('', None, [], True, 'runtime'):
                with self.assertRaises(DeliveryError):
                    gateway.snapshot_source(scope, invalid)
            apps.objects.filter.return_value.first.return_value = None
            with self.assertRaises(DeliveryError):
                gateway.snapshot_source(scope, '51')

    def test_snapshot_source_endpoint_reuses_application_scope_and_masks_private_defaults(self):
        from types import SimpleNamespace
        from unittest import mock
        from console.views.delivery_templates import DeliverySourceView
        view = DeliverySourceView()
        scope = dict(enterprise_id='enterprise', team_name='source', region_name='region', app_id='42')
        view.scope = mock.Mock(return_value=scope)
        view.reply = lambda bean: bean
        view.delivery = mock.Mock()
        view.delivery.gateway.snapshot_source.return_value = ({
            'source_snapshot': {'version_id': '51', 'version': '0.0.3'},
            'apps': [{'service_env_map_list': [{'attr_name': 'PASSWORD', 'attr_value': '$SAVED_DEFAULT'}]}]
        }, 'Source')
        request = SimpleNamespace(GET={'snapshot_id': '51'})
        result = view.get(request, 'source', '42')
        view.scope.assert_called_once_with(request, 'source', '42')
        view.delivery.gateway.snapshot_source.assert_called_once_with(scope, '51')
        view.delivery.gateway.source.assert_not_called()
        self.assertEqual(result['apps'][0]['service_env_map_list'][0]['attr_value'], '')

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
