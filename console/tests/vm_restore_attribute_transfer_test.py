# -*- coding: utf-8 -*-
"""Exercise existing template, market, backup and Region sync entry points."""
# capability_id: console.vm-restore.attribute-transfer
import copy
import importlib
import io
import json
import logging
from contextlib import ExitStack
from types import SimpleNamespace
from unittest import TestCase, mock

# Reuse optional generated-client compatibility setup used by the HTTP suite.
from console.tests import vm_restore_private_attributes_test as bootstrap  # noqa: F401
from console.models.main import ComponentK8sAttributes, RainbondCenterAppVersion
from console.services.app import app_service
from console.services.app_check_service import AppCheckService
from console.services.app_import_and_export_service import export_service
from console.services.app_version_service import AppVersionService
from console.services.backup_service import groupapp_backup_service
from console.services.market_app.app_restore import AppRestore
from console.services.market_app.component import Component
from console.services.market_app.market_app import MarketApp
from console.services.market_app.new_components import NewComponents
from console.services.share_services import share_service
from console.services.vm_login_security import filter_vm_login_transfer_attributes
from console.views import app_version as version_views
from console.views.base import ApplicationView
from www.models.main import TenantServiceInfo


class VMRestoreAttributeTransferTestCase(TestCase):
    def setUp(self):
        self.service = TenantServiceInfo(tenant_id="tenant-a",
                                         service_id="service-a",
                                         service_alias="service-a",
                                         service_region="region-a",
                                         service_key="fixture",
                                         k8s_component_name="service-a",
                                         extend_method="stateless_multiple")
        self.tenant = SimpleNamespace(tenant_id="tenant-a", tenant_name="team-a")
        self.attrs = [
            ComponentK8sAttributes(ID=index + 1,
                                   tenant_id="tenant-a",
                                   component_id="service-a",
                                   name=name,
                                   save_type="string",
                                   attribute_value=value) for index, (name, value) in enumerate((
                                       ("vm_restore_state", "control-sentinel"),
                                       ("vm_restore_operation_op-a", "control-sentinel"),
                                       ("vm_restore_manifest_snapshot-a", "control-sentinel"),
                                       ("vm_volume_bindings", "control-sentinel"),
                                       ("labels", "public-sentinel"),
                                       ("vm_disk_layout", "[]"),
                                   ))
        ]
        self.dictionaries = [attr.to_dict() for attr in self.attrs]

    def component(self, attrs=None):
        return Component(self.service,
                         None, [], [], [], [], [],
                         None, [], [], [],
                         support_labels=[],
                         k8s_attributes=self.attrs if attrs is None else attrs)

    def assert_public(self, attrs):
        names = [attr.get("name") if isinstance(attr, dict) else attr.name for attr in attrs]
        self.assertEqual(names, ["labels", "vm_disk_layout"])
        self.assertNotIn("control-sentinel", str(attrs))

    def test_shared_transfer_pipeline_filters_model_and_dict_forms(self):
        self.assert_public(filter_vm_login_transfer_attributes(self.attrs))
        self.assert_public(filter_vm_login_transfer_attributes(self.dictionaries))

    def test_template_installer_and_upgrade_ignore_source_private_state(self):
        installer = NewComponents.__new__(NewComponents)
        attrs = installer._template_to_k8s_attributes(self.service, self.dictionaries, {})
        self.assert_public(attrs)
        self.assertTrue(all(attr.pk is None for attr in attrs))
        self.assertTrue(all(attr.component_id == "service-a" and attr.tenant_id == "tenant-a" for attr in attrs))
        cpt = self.component([])
        cpt._update_component_k8s_attributes({"add": self.dictionaries})
        self.assert_public(cpt.k8s_attributes)

    def test_market_sync_payload_and_publish_do_not_export_private_records(self):
        market = MarketApp.__new__(MarketApp)
        market.labels = {}
        app = SimpleNamespace(components=lambda: [self.component()])
        with mock.patch.object(market, "_create_plugin_body", return_value={}), \
                mock.patch("console.services.market_app.market_app.domain_repo.list_all_certificate", return_value=[]):
            body = market._create_component_body(app)
        self.assert_public(body[0]["component_k8s_attributes"])
        with mock.patch("console.services.share_services.k8s_attribute_repo.list_by_component_ids", return_value=self.attrs):
            exported = share_service.list_component_k8s_attributes(["service-a"])
        self.assert_public(exported["service-a"])
        self.assertTrue(all("ID" not in item for item in exported["service-a"]))

    def test_version_normalization_and_image_rewrite_both_strip_private_records(self):
        component = {"component_k8s_attributes": self.dictionaries, "image": "fixture/image"}
        normalized = AppVersionService._normalize_template_images({"apps": [component]})
        self.assert_public(normalized["apps"][0]["component_k8s_attributes"])
        rewritten = AppVersionService._rewrite_component_image_to_upstream(component)
        self.assert_public(rewritten["component_k8s_attributes"])
        unchanged_image = AppVersionService._rewrite_component_image_to_upstream(
            {"component_k8s_attributes": self.dictionaries})
        self.assert_public(unchanged_image["component_k8s_attributes"])
        self.assertEqual(len(component["component_k8s_attributes"]), len(self.attrs))

    def test_legacy_snapshot_restore_rebuilds_only_public_attrs_with_live_target_identity(self):
        restore = AppRestore.__new__(AppRestore)
        restore.support_labels = []
        restore.tenant = self.tenant
        restore.region_name = "region-a"
        snap = {
            key: []
            for key in ("service_env_vars", "service_ports", "service_volumes", "service_config_file", "service_probes",
                        "service_monitors", "component_graphs", "service_labels")
        }
        snap["service_base"] = self.service.to_dict()
        snap["component_k8s_attributes"] = [
            dict(attr, tenant_id="tenant-b", component_id="service-b") for attr in self.dictionaries
        ]
        with mock.patch.object(TenantServiceInfo.objects, "get", return_value=self.service):
            cpt = restore._create_component(snap, {})
        self.assert_public(cpt.k8s_attributes)
        self.assertTrue(all(attr.pk is None for attr in cpt.k8s_attributes))
        self.assertTrue(all(attr.component_id == "service-a" and attr.tenant_id == "tenant-a" for attr in cpt.k8s_attributes))

    def test_backup_exports_exclude_restore_controls(self):
        module = importlib.import_module("console.services.backup_service")
        repo_names = ("service_label_repo", "domain_repo", "configuration_repo", "tcp_domain", "probe_repo",
                      "service_source_repo", "auth_repo", "env_var_repo", "compile_env_repo", "extend_repo", "mnt_repo",
                      "volume_repo", "port_repo", "dep_relation_repo", "service_monitor_repo", "component_graph_repo",
                      "app_plugin_relation_repo", "service_plugin_config_repo", "service_endpoints_repo")
        with ExitStack() as stack:
            for name in repo_names:
                repository = stack.enter_context(mock.patch.object(module, name))
                for method in ("get_service_labels", "get_service_domains", "list_by_rule_ids", "get_service_tcpdomains",
                               "get_service_probe", "get_service_auth", "get_service_env", "get_service_mnts",
                               "get_service_volumes_with_config_file", "get_service_config_files", "get_service_ports",
                               "get_service_dependencies", "get_component_service_monitors", "list",
                               "get_service_plugin_relation_by_service_id", "get_service_plugin_all_config",
                               "get_service_endpoints_by_service_id"):
                    getattr(repository, method).return_value = []
                for method in ("get_service_source", "get_service_compile_env", "get_extend_method_by_service"):
                    getattr(repository, method).return_value = None
            stack.enter_context(mock.patch.object(module.k8s_attribute_repo, "get_by_component_id", return_value=self.attrs))
            body, _ = groupapp_backup_service.get_service_details(self.tenant, self.service)
        self.assert_public(body["component_k8s_attributes"])

    def test_region_payload_and_fallback_sync_do_not_send_or_log_private_records(self):
        module = importlib.import_module("console.services.app")
        rows = mock.MagicMock()
        rows.__iter__.side_effect = lambda: iter(self.attrs)
        rows.count.return_value = len(self.attrs)
        logger = logging.getLogger("default")
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        previous_level = logger.level
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        try:
            with mock.patch.object(module.k8s_attribute_repo, "get_by_component_id", return_value=rows), \
                    mock.patch.object(module, "region_api") as region:
                payload = app_service._AppService__get_component_k8s_attributes_payload(self.service)
                self.assert_public(payload)
                app_service._AppService__sync_k8s_attributes_to_region(self.tenant, self.service)
                self.assertEqual([call.args[-1]["name"] for call in region.create_component_k8s_attribute.call_args_list],
                                 ["labels", "vm_disk_layout"])
        finally:
            logger.removeHandler(handler)
            logger.setLevel(previous_level)
        self.assertNotIn("control-sentinel", stream.getvalue())

    def test_compose_writer_rejects_private_control_before_value_logging(self):
        module = importlib.import_module("console.services.app_check_service")
        with mock.patch.object(module.logger, "info") as info, \
                mock.patch.object(module.k8s_attribute_repo, "create") as create, \
                self.assertRaises(bootstrap.ServiceHandleException) as caught:
            AppCheckService()._AppCheckService__save_k8s_attribute(self.tenant, self.service, "vm_restore_state",
                                                                   "control-sentinel")
        self.assertEqual(caught.exception.status_code, 403)
        info.assert_not_called()
        create.assert_not_called()

    def test_original_component_builder_omits_controls_before_same_component_overwrite(self):
        module = importlib.import_module("console.services.market_app.original_app")
        original = module.OriginalApp.__new__(module.OriginalApp)
        original.support_labels = []
        with ExitStack() as stack:
            stack.enter_context(
                mock.patch.object(module.group_service, "list_components_by_upgrade_group_id", return_value=[self.service]))
            stack.enter_context(mock.patch.object(original, "_list_http_rules", return_value={}))
            stack.enter_context(mock.patch.object(original, "_list_tcp_rules", return_value={}))
            for name, method in (("env_var_repo", "get_service_env"), ("port_repo", "get_service_ports"),
                                 ("volume_repo", "get_service_volumes_with_config_file"), ("volume_repo",
                                                                                           "get_service_config_files"),
                                 ("probe_repo", "list_probes"), ("service_monitor_repo", "list_by_service_ids"),
                                 ("component_graph_repo", "list"), ("app_plugin_relation_repo", "list_by_component_ids")):
                stack.enter_context(mock.patch.object(getattr(module, name), method, return_value=[]))
            stack.enter_context(mock.patch.object(module.service_source_repo, "get_service_source", return_value=None))
            stack.enter_context(mock.patch.object(module.k8s_attribute_repo, "get_by_component_id", return_value=self.attrs))
            components = original._create_components(1, 1)
        self.assert_public(components[0].k8s_attributes)

    def test_snapshot_import_missing_live_target_is_conflict_before_constructing_attributes(self):
        restore = AppRestore.__new__(AppRestore)
        restore.support_labels = []
        restore.tenant = self.tenant
        restore.region_name = "region-a"
        snap = {
            key: []
            for key in ("service_env_vars", "service_ports", "service_volumes", "service_config_file", "service_probes",
                        "service_monitors", "component_graphs", "service_labels", "component_k8s_attributes")
        }
        snap["service_base"] = self.service.to_dict()
        snap["component_k8s_attributes"] = self.dictionaries
        with mock.patch.object(TenantServiceInfo.objects, "get", side_effect=TenantServiceInfo.DoesNotExist), \
                self.assertRaises(bootstrap.ServiceHandleException) as caught:
            restore._create_component(snap, {})
        self.assertEqual(caught.exception.status_code, 409)


class VMRestoreStoredTemplateTransferTestCase(TestCase):
    close_database = bootstrap.VMRestorePrivateAttributesTestCase.close_database

    def setUp(self):
        bootstrap.VMRestorePrivateAttributesTestCase.setUp(self)
        with self.database.schema_editor() as schema:
            schema.create_model(RainbondCenterAppVersion)
        patcher = mock.patch.object(RainbondCenterAppVersion, "objects",
                                    RainbondCenterAppVersion.objects.db_manager(self.alias))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.version_service = AppVersionService()
        self.app = SimpleNamespace(app_id="hidden-a", pic=None, describe="stored-metadata-sentinel")

    @staticmethod
    def template(public_value="public-sentinel", control_value="control-sentinel"):
        attributes = [{
            "name": name,
            "save_type": "string",
            "attribute_value": value
        } for name, value in (("vm_restore_state", control_value), ("vm_restore_future_key", control_value),
                              ("vm_volume_bİndİngs", control_value), ("labels", public_value), ("vm_disk_layout", "[]"),
                              ("vm_login_password_hash", "credential-sentinel"))]
        return {
            "group_key": "hidden-a",
            "group_version": "1.0.0",
            "snapshot_id": "snapshot-sentinel",
            "custom_metadata": {
                "marker": "metadata-sentinel"
            },
            "apps": [{
                "service_alias": "web",
                "image": "fixture/image",
                "component_k8s_attributes": attributes
            }],
            "plugins": [{
                "plugin_alias": "plugin-a",
                "component_k8s_attributes": copy.deepcopy(attributes)
            }],
        }

    def stored_version(self, template, version="1.0.0"):
        return RainbondCenterAppVersion.objects.create(app_id="hidden-a",
                                                       version=version,
                                                       version_alias="alias-sentinel",
                                                       app_version_info="info-sentinel",
                                                       record_id=1,
                                                       share_user=1,
                                                       share_team="team-a",
                                                       template_type=self.version_service.SNAPSHOT_TEMPLATE_TYPE,
                                                       app_template=json.dumps(template))

    def assert_public_template(self, template):
        for section in ("apps", "plugins"):
            names = [attribute["name"] for attribute in template[section][0]["component_k8s_attributes"]]
            self.assertEqual(names, ["labels", "vm_disk_layout", "vm_login_password_hash"])
        self.assertNotIn("control-sentinel", json.dumps(template))
        self.assertEqual(template["custom_metadata"], {"marker": "metadata-sentinel"})
        self.assertEqual(template["snapshot_id"], "snapshot-sentinel")

    def snapshot_detail(self, version):
        with mock.patch.object(self.version_service,
                               "get_hidden_template",
                               return_value=(SimpleNamespace(app_model_id="hidden-a"), None)):
            return self.version_service.get_snapshot_detail("app-a", version.pk)

    def test_stored_export_metadata_filters_apps_and_plugins_without_rewriting_storage(self):
        template = self.template()
        version = self.stored_version(template)
        original = version.app_template
        with mock.patch.object(RainbondCenterAppVersion, "save") as save:
            metadata = export_service._AppExportService__get_app_metata(self.app, version, {"image_handle": "retain"})
        save.assert_not_called()
        dto = json.loads(metadata)
        self.assert_public_template(dto)
        self.assertEqual(dto["annotations"]["version_alias"], "alias-sentinel")
        self.assertEqual(dto["annotations"]["describe"], "stored-metadata-sentinel")
        self.assertEqual(dto["helm_chart"]["image_handle"], "retain")
        version.refresh_from_db()
        self.assertEqual(version.app_template, original)

    def test_export_entrypoint_filters_stored_metadata_for_every_existing_format(self):
        version = self.stored_version(self.template())
        original = version.app_template
        module = importlib.import_module("console.services.app_import_and_export_service")
        export_region = SimpleNamespace(region_name="region-a")
        with mock.patch.object(module.rainbond_app_repo, "get_rainbond_app_and_version", return_value=(self.app, version)), \
                mock.patch.object(export_service, "select_handle_region", return_value=export_region), \
                mock.patch.object(module.app_export_record_repo, "get_export_record", return_value=None), \
                mock.patch.object(module.app_export_record_repo, "create_app_export_record") as create, \
                mock.patch.object(module, "region_api") as region:
            for export_format in ("rainbond-app", "docker-compose", "slug", "helm-chart"):
                with self.subTest(export_format=export_format):
                    result = export_service.export_app("enterprise-a", "hidden-a", version.version, export_format,
                                                       {"image_handle": "retain"})
                    self.assertIs(result, create.return_value)
                    arguments = region.export_app.call_args.args
                    self.assertEqual(arguments[:2], ("region-a", "enterprise-a"))
                    self.assertEqual(arguments[2]["format"], export_format)
                    self.assert_public_template(json.loads(arguments[2]["group_metadata"]))
        version.refresh_from_db()
        self.assertEqual(version.app_template, original)

    def test_snapshot_detail_projects_legacy_template_and_preserves_stored_content_hash(self):
        template = self.template()
        version = self.stored_version(template)
        original = version.app_template
        expected_hash = self.version_service._content_hash(template)
        with mock.patch.object(RainbondCenterAppVersion, "save") as save:
            detail = self.snapshot_detail(version)
        save.assert_not_called()
        self.assert_public_template(detail["template"])
        self.assertEqual(detail["content_hash"], expected_hash)
        self.assertNotEqual(detail["content_hash"], self.version_service._content_hash(detail["template"]))
        self.assertEqual(detail["version_alias"], "alias-sentinel")
        self.assertEqual(detail["snapshot_id"], "snapshot-sentinel")
        self.assertFalse(detail["has_previous_version"])
        version.refresh_from_db()
        self.assertEqual(version.app_template, original)

    def test_snapshot_public_diff_filters_both_stored_versions_and_keeps_public_changes(self):
        previous = self.stored_version(self.template("previous-public-sentinel", "prior-control-sentinel"), "1.0.0")
        current = self.stored_version(self.template(), "1.0.1")
        originals = {row.pk: row.app_template for row in (previous, current)}
        detail = self.snapshot_detail(current)
        self.assertNotIn("control-sentinel", json.dumps(detail))
        self.assert_public_template(detail["template"])
        self.assertEqual(detail["previous_version"], "1.0.0")
        self.assertEqual(detail["diff_summary"]["updated_components"], ["web"])
        updated = detail["component_diff_details"]["updated_components"]
        changes = next(change for change in updated[0]["other_changes"] if change["field_key"] == "component_k8s_attributes")
        self.assertEqual(sorted(attribute["name"] for attribute in changes["before"]),
                         ["labels", "vm_disk_layout", "vm_login_password_hash"])
        self.assertEqual(sorted(attribute["name"] for attribute in changes["after"]),
                         ["labels", "vm_disk_layout", "vm_login_password_hash"])
        self.assertEqual(next(attribute["attribute_value"] for attribute in changes["before"] if attribute["name"] == "labels"),
                         "previous-public-sentinel")
        self.assertEqual(next(attribute["attribute_value"] for attribute in changes["after"] if attribute["name"] == "labels"),
                         "public-sentinel")
        for row in (previous, current):
            row.refresh_from_db()
            self.assertEqual(row.app_template, originals[row.pk])

    def test_private_only_stored_changes_do_not_appear_in_public_diff(self):
        self.stored_version(self.template(control_value="prior-control-sentinel"), "1.0.0")
        current = self.stored_version(self.template(), "1.0.1")
        detail = self.snapshot_detail(current)
        self.assertFalse(detail["diff_summary"]["has_changes"])
        self.assertEqual(detail["component_diff_details"]["updated_components"], [])
        self.assert_public_template(detail["template"])


class VMRestorePublicVersionComparisonTestCase(TestCase):
    setUp = VMRestoreStoredTemplateTransferTestCase.setUp
    close_database = VMRestoreStoredTemplateTransferTestCase.close_database
    template = staticmethod(VMRestoreStoredTemplateTransferTestCase.template)
    stored_version = VMRestoreStoredTemplateTransferTestCase.stored_version

    def call_version_view(self, view_type, method="get", version_id=None, data=None):
        tenant = self.tenant

        def initial(view, request, *args, **kwargs):
            view.tenant = tenant
            view.region = SimpleNamespace(region_name="region-a")
            view.user = SimpleNamespace(user_id=1)
            view.app = SimpleNamespace(ID=42, group_name="group-a")

        path = "/console/teams/team-a/groups/42/app-versions"
        request = getattr(self.factory, method)(path, data or {}, format="json")
        kwargs = {"group_id": "42", "tenantName": "team-a"}
        if version_id is not None:
            kwargs["version_id"] = str(version_id)
        with mock.patch.object(ApplicationView, "initial", initial), \
                mock.patch.object(version_views, "app_version_service", self.version_service), \
                mock.patch.object(
                    version_views, "app_version_auto_snapshot_service",
                    new=SimpleNamespace(status=mock.Mock(return_value={})), create=True):
            response = view_type.as_view()(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        return response.data["data"]

    def public_live_template(self, template):
        current = copy.deepcopy(template)
        for section in ("apps", "plugins"):
            current[section][0]["component_k8s_attributes"] = [
                row for row in current[section][0]["component_k8s_attributes"]
                if row["name"] in ("labels", "vm_disk_layout", "vm_login_password_hash")
            ]
        return current

    def overview(self, current):
        module = importlib.import_module("console.services.app_version_service")
        with mock.patch.object(self.version_service, "get_hidden_template",
                               return_value=(SimpleNamespace(app_model_id="hidden-a"), self.app)), \
                mock.patch.object(module.share_repo, "get_last_shared_app_version_by_group_id", return_value=None), \
                mock.patch.object(module.market_app_service, "get_market_apps_in_app", return_value=[]), \
                mock.patch.object(self.version_service, "_latest_successful_rollback_record", return_value=None), \
                mock.patch.object(self.version_service, "_build_app_template", return_value=current):
            return self.call_version_view(version_views.AppVersionOverviewView)["bean"]

    def listing_and_detail(self, current):
        with mock.patch.object(self.version_service, "get_hidden_template",
                               return_value=(SimpleNamespace(app_model_id="hidden-a"), self.app)), \
                mock.patch.object(self.version_service, "get_relation", return_value=SimpleNamespace()):
            listing = self.call_version_view(version_views.AppVersionSnapshotListView)["list"]
            detail = self.call_version_view(version_views.AppVersionSnapshotDetailView, version_id=current.pk)["bean"]
        return listing, detail

    def test_overview_http_excludes_private_stored_baseline_and_private_only_changes(self):
        stored = self.template()
        version = self.stored_version(stored)
        original = version.app_template
        current = self.public_live_template(stored)
        current_before = copy.deepcopy(current)
        overview = self.overview(current)
        self.assertNotIn("control-sentinel", json.dumps(overview))
        self.assertFalse(overview["has_changes"])
        self.assertEqual(overview["component_diff_details"]["updated_components"], [])
        self.assertEqual(current, current_before)
        version.refresh_from_db()
        self.assertEqual(version.app_template, original)

    def test_list_http_ignores_private_only_changes_and_matches_detail(self):
        previous = self.stored_version(self.template(control_value="prior-control-sentinel"), "1.0.0")
        current = self.stored_version(self.template(), "1.0.1")
        originals = {row.pk: row.app_template for row in (previous, current)}
        listing, detail = self.listing_and_detail(current)
        self.assertFalse(detail["diff_summary"]["has_changes"])
        self.assertEqual(listing[0]["diff_summary"], detail["diff_summary"])
        self.assertFalse(listing[0]["diff_summary"]["has_changes"])
        for row in (previous, current):
            row.refresh_from_db()
            self.assertEqual(row.app_template, originals[row.pk])

    def test_http_comparisons_preserve_public_values_containing_reserved_name_text(self):
        before = self.template("literal vm_restore_state before", "prior-control-sentinel")
        after = self.template("literal vm_restore_state after")
        self.stored_version(before, "1.0.0")
        current = self.stored_version(after, "1.0.1")
        live = self.public_live_template(after)
        next(row for row in live["apps"][0]["component_k8s_attributes"] if row["name"] == "labels")["attribute_value"] = \
            "literal vm_restore_state live"
        overview = self.overview(live)
        listing, detail = self.listing_and_detail(current)
        for dto in (overview, detail):
            self.assertNotIn("control-sentinel", json.dumps(dto))
        self.assertTrue(overview["has_changes"])
        self.assertIn("literal vm_restore_state live", json.dumps(overview))
        self.assertTrue(listing[0]["diff_summary"]["has_changes"])
        self.assertEqual(listing[0]["diff_summary"], detail["diff_summary"])
        changes = detail["component_diff_details"]["updated_components"][0]["other_changes"]
        attribute_change = next(change for change in changes if change["field_key"] == "component_k8s_attributes")
        for side, value in (("before", "literal vm_restore_state before"), ("after", "literal vm_restore_state after")):
            attributes = attribute_change[side]
            self.assertEqual(next(row["attribute_value"] for row in attributes if row["name"] == "labels"), value)
            self.assertEqual({row["name"] for row in attributes}, {"labels", "vm_disk_layout", "vm_login_password_hash"})

    def test_snapshot_post_ignores_private_only_changes_without_creating_a_version(self):
        stored = self.template()
        stored["source_component_groups"] = []
        version = self.stored_version(stored)
        original = version.app_template
        current = self.public_live_template(stored)
        module = importlib.import_module("console.services.app_version_service")
        with mock.patch("console.services.cleanup_coordination.protect_region_references", return_value=ExitStack()), \
                mock.patch.object(module.ServiceGroup.objects, "select_for_update"), \
                mock.patch.object(self.version_service, "get_or_create_hidden_template",
                                  return_value=(SimpleNamespace(app_model_id="hidden-a"), self.app)), \
                mock.patch.object(self.version_service, "_build_app_template", return_value=current), \
                mock.patch.object(self.version_service, "_snapshot_source_groups", return_value=[], create=True), \
                mock.patch.object(self.version_service, "_take_restore_snapshot",
                                  side_effect=AssertionError("private-only changes must not create a version")) as take:
            result = self.call_version_view(version_views.AppVersionSnapshotListView, method="post", data={"version":
                                                                                                           "1.0.1"})["bean"]
        self.assertFalse(result["created"])
        self.assertFalse(result["change_summary"]["has_changes"])
        take.assert_not_called()
        self.assertEqual(RainbondCenterAppVersion.objects.count(), 1)
        version.refresh_from_db()
        self.assertEqual(version.app_template, original)

    def test_internal_raw_comparison_and_content_hash_stay_distinct(self):
        before = self.template(control_value="prior-control-sentinel")
        after = self.template()
        originals = copy.deepcopy((before, after))
        self.assertNotEqual(self.version_service._content_hash(before), self.version_service._content_hash(after))
        self.assertEqual(self.version_service._build_rollback_component_plan(after, before)["changed"], {"web"})
        self.assertEqual((before, after), originals)

    def test_detail_http_preserves_missing_and_empty_attribute_shapes(self):
        for has_attribute_field in (False, True):
            with self.subTest(has_attribute_field=has_attribute_field):
                template = self.template()
                for section in ("apps", "plugins"):
                    if has_attribute_field:
                        template[section][0]["component_k8s_attributes"] = []
                    else:
                        del template[section][0]["component_k8s_attributes"]
                version = self.stored_version(template, "1.0.{0}".format(int(has_attribute_field)))
                _, detail = self.listing_and_detail(version)
                for section in ("apps", "plugins"):
                    component = detail["template"][section][0]
                    self.assertEqual("component_k8s_attributes" in component, has_attribute_field)
                    if has_attribute_field:
                        self.assertEqual(component["component_k8s_attributes"], [])
