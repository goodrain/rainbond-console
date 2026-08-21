# -*- coding: utf-8 -*-
import collections
import os
import sys
from types import ModuleType
from unittest import TestCase, mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
if "openapi_client" not in sys.modules:
    openapi_client_module = ModuleType("openapi_client")
    openapi_client_module.ApiClient = object
    openapi_client_module.MarketOpenapiApi = object
    configuration_module = ModuleType("openapi_client.configuration")
    configuration_module.Configuration = type("Configuration", (), {})
    rest_module = ModuleType("openapi_client.rest")
    rest_module.ApiException = type("ApiException", (Exception, ), {})
    sys.modules["openapi_client"] = openapi_client_module
    sys.modules["openapi_client.configuration"] = configuration_module
    sys.modules["openapi_client.rest"] = rest_module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from console.exception.main import ServiceHandleException  # noqa: E402
from console.services.rbd_plugin_sync_service import RBDPluginSyncService  # noqa: E402


class Obj(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class RBDPluginSyncServiceTests(TestCase):
    def setUp(self):
        self.service = RBDPluginSyncService()
        self.tenant = Obj(
            tenant_id="team-1",
            enterprise_id="enterprise-1",
            namespace="rbd-plugins",
        )
        self.region = Obj(region_name="rainbond")
        self.template = {
            "apps": [
                {
                    "service_cname": "ui",
                    "port_map_list": [
                        {
                            "container_port": 8080,
                            "protocol": "http"
                        },
                    ],
                },
                {
                    "service_cname": "api",
                    "port_map_list": [
                        {
                            "container_port": 8787,
                            "protocol": "http"
                        },
                    ],
                },
            ],
            "platform_plugin": {
                "is_platform_plugin": True,
                "plugin_id": "rainbond-agent",
                "plugin_name": "AI助手",
                "plugin_type": "JSInject",
                "frontend_component": "ui",
                "entry_path": "/static/main.js",
                "inject_position": ["Platform"],
                "menu_title": "AI助手",
                "route_path": "/plugins/rainbond-agent",
            },
        }
        self.ui = Obj(service_id="svc-ui", service_cname="ui")
        self.api = Obj(service_id="svc-api", service_cname="api")
        self.ui_http = Obj(
            protocol="http",
            container_port=8080,
            k8s_service_name="ui-service",
        )
        self.api_http = Obj(
            protocol="HTTP",
            container_port=8787,
            k8s_service_name="api-service",
        )

    def _patch_desired_state(self, components=None, ports=None, dependencies=None, region_app_id="region-app-1"):
        components = [self.ui, self.api] if components is None else components
        ports = {
            "svc-ui": [self.ui_http],
            "svc-api": [self.api_http],
        } if ports is None else ports
        dependencies = [Obj(dep_service_id="svc-api")] if dependencies is None else dependencies

        relation_filter = mock.patch("console.services.rbd_plugin_sync_service.ServiceGroupRelation.objects.filter")
        component_filter = mock.patch("console.services.rbd_plugin_sync_service.TenantServiceInfo.objects.filter",
                                      return_value=components)
        port_lookup = mock.patch("console.services.rbd_plugin_sync_service.port_repo.get_service_ports",
                                 side_effect=lambda tenant_id, service_id: ports.get(service_id, []))
        dependency_lookup = mock.patch("console.services.rbd_plugin_sync_service.dep_relation_repo.get_service_dependencies",
                                       return_value=dependencies)
        region_app_lookup = mock.patch("console.services.rbd_plugin_sync_service.region_app_repo.get_region_app_id",
                                       return_value=region_app_id)
        region_apply = mock.patch("console.services.rbd_plugin_sync_service.region_api.create_rbdplugin")
        return relation_filter, component_filter, port_lookup, dependency_lookup, region_app_lookup, region_apply

    def test_non_platform_template_is_skipped_without_region_call(self):
        with mock.patch("console.services.rbd_plugin_sync_service.region_api.create_rbdplugin") as region_apply:
            result = self.service.reconcile(self.tenant, self.region, {"apps": []}, 23)

        self.assertEqual({"status": "skipped", "reason": "not_platform_plugin"}, result)
        region_apply.assert_not_called()

    def test_reconcile_scopes_components_and_selects_only_http_ports(self):
        mysql_port = Obj(protocol="stream", container_port=3306, k8s_service_name="mysql-service")
        tcp_port = Obj(protocol="tcp", container_port=9000, k8s_service_name="tcp-service")
        patches = self._patch_desired_state(ports={
            "svc-ui": [mysql_port, self.ui_http],
            "svc-api": [tcp_port, self.api_http],
        })

        with patches[0] as relation_filter, patches[1] as component_filter, patches[2], patches[3], \
                patches[4], patches[5] as region_apply:
            relation_filter.return_value.values_list.return_value = ["svc-ui", "svc-api"]
            result = self.service.reconcile(self.tenant, self.region, self.template, 23)

        relation_filter.assert_called_once_with(tenant_id="team-1", region_name="rainbond", group_id=23)
        component_filter.assert_called_once_with(
            tenant_id="team-1",
            service_region="rainbond",
            service_id__in=["svc-ui", "svc-api"],
        )
        payload = region_apply.call_args.args[2]
        self.assertEqual("ui-service.rbd-plugins.svc.cluster.local:8080/static/main.js", payload["frontend_service"])
        self.assertEqual("api-service.rbd-plugins.svc.cluster.local:8787", payload["backend_service"])
        self.assertEqual("region-app-1", payload["app_id"])
        self.assertEqual("reconciled", result["status"])

    def test_multiple_frontend_http_ports_use_unique_template_port(self):
        metrics_port = Obj(protocol="http", container_port=9090, k8s_service_name="metrics-service")
        patches = self._patch_desired_state(ports={
            "svc-ui": [metrics_port, self.ui_http],
            "svc-api": [self.api_http],
        })

        with patches[0] as relation_filter, patches[1], patches[2], patches[3], patches[4], patches[5] as region_apply:
            relation_filter.return_value.values_list.return_value = ["svc-ui", "svc-api"]
            self.service.reconcile(self.tenant, self.region, self.template, 23)

        self.assertIn(":8080/static/main.js", region_apply.call_args.args[2]["frontend_service"])

    def test_port_map_list_takes_precedence_over_legacy_ports(self):
        template = dict(self.template)
        template["apps"] = [
            {
                "service_cname": "ui",
                "port_map_list": [{
                    "container_port": 8080
                }],
                "ports": [{
                    "container_port": 9090
                }],
            },
            self.template["apps"][1],
        ]
        metrics_port = Obj(protocol="http", container_port=9090, k8s_service_name="metrics-service")
        patches = self._patch_desired_state(ports={
            "svc-ui": [self.ui_http, metrics_port],
            "svc-api": [self.api_http],
        })

        with patches[0] as relation_filter, patches[1], patches[2], patches[3], patches[4], patches[5] as region_apply:
            relation_filter.return_value.values_list.return_value = ["svc-ui", "svc-api"]
            self.service.reconcile(self.tenant, self.region, template, 23)

        self.assertIn(":8080/static/main.js", region_apply.call_args.args[2]["frontend_service"])

    def test_multiple_frontend_http_ports_without_unique_template_match_fail(self):
        ambiguous_template = dict(self.template)
        ambiguous_template["apps"] = [
            {
                "service_cname": "ui",
                "port_map_list": [{
                    "container_port": 8080
                }, {
                    "container_port": 9090
                }]
            },
            self.template["apps"][1],
        ]
        metrics_port = Obj(protocol="http", container_port=9090, k8s_service_name="metrics-service")
        patches = self._patch_desired_state(ports={
            "svc-ui": [self.ui_http, metrics_port],
            "svc-api": [self.api_http],
        })

        with patches[0] as relation_filter, patches[1], patches[2], patches[3], patches[4], patches[5] as region_apply:
            relation_filter.return_value.values_list.return_value = ["svc-ui", "svc-api"]
            with self.assertRaises(ServiceHandleException) as context:
                self.service.reconcile(self.tenant, self.region, ambiguous_template, 23)

        self.assertEqual("resolve_frontend_http_port", context.exception.bean["phase"])
        region_apply.assert_not_called()

    def test_missing_frontend_component_fails_without_cross_app_fallback(self):
        other_app_ui = Obj(service_id="other-ui", service_cname="ui")
        patches = self._patch_desired_state(components=[self.api])

        with patches[0] as relation_filter, patches[1] as component_filter, patches[2], patches[3], \
                patches[4], patches[5] as region_apply:
            relation_filter.return_value.values_list.return_value = ["svc-api"]
            with self.assertRaises(ServiceHandleException) as context:
                self.service.reconcile(self.tenant, self.region, self.template, 23)

        self.assertEqual("resolve_frontend_component", context.exception.bean["phase"])
        self.assertNotIn(other_app_ui.service_id, component_filter.call_args.kwargs["service_id__in"])
        region_apply.assert_not_called()

    def test_frontend_without_http_port_fails_in_fixed_phase(self):
        mysql_port = Obj(protocol="stream", container_port=3306, k8s_service_name="mysql-service")
        patches = self._patch_desired_state(ports={
            "svc-ui": [mysql_port],
            "svc-api": [self.api_http],
        })

        with patches[0] as relation_filter, patches[1], patches[2], patches[3], patches[4], patches[5] as region_apply:
            relation_filter.return_value.values_list.return_value = ["svc-ui", "svc-api"]
            with self.assertRaises(ServiceHandleException) as context:
                self.service.reconcile(self.tenant, self.region, self.template, 23)

        self.assertEqual("resolve_frontend_http_port", context.exception.bean["phase"])
        region_apply.assert_not_called()

    def test_ambiguous_http_backend_dependencies_fail_without_region_call(self):
        worker = Obj(service_id="svc-worker", service_cname="worker")
        worker_http = Obj(protocol="http", container_port=9090, k8s_service_name="worker-service")
        patches = self._patch_desired_state(
            components=[self.ui, self.api, worker],
            ports={
                "svc-ui": [self.ui_http],
                "svc-api": [self.api_http],
                "svc-worker": [worker_http],
            },
            dependencies=[Obj(dep_service_id="svc-api"), Obj(dep_service_id="svc-worker")],
        )

        with patches[0] as relation_filter, patches[1], patches[2], patches[3], patches[4], patches[5] as region_apply:
            relation_filter.return_value.values_list.return_value = ["svc-ui", "svc-api", "svc-worker"]
            with self.assertRaises(ServiceHandleException) as context:
                self.service.reconcile(self.tenant, self.region, self.template, 23)

        self.assertEqual("rbd_plugin_sync_failed", context.exception.msg)
        self.assertEqual("resolve_backend_component", context.exception.bean["phase"])
        self.assertTrue(context.exception.bean["operation_committed"])
        region_apply.assert_not_called()

    def test_backend_with_ambiguous_http_ports_fails_without_region_call(self):
        ambiguous_template = dict(self.template)
        ambiguous_template["apps"] = [
            self.template["apps"][0],
            {
                "service_cname": "api",
                "port_map_list": [{
                    "container_port": 8787
                }, {
                    "container_port": 9090
                }]
            },
        ]
        metrics_port = Obj(protocol="http", container_port=9090, k8s_service_name="api-metrics")
        patches = self._patch_desired_state(ports={
            "svc-ui": [self.ui_http],
            "svc-api": [self.api_http, metrics_port],
        })

        with patches[0] as relation_filter, patches[1], patches[2], patches[3], patches[4], patches[5] as region_apply:
            relation_filter.return_value.values_list.return_value = ["svc-ui", "svc-api"]
            with self.assertRaises(ServiceHandleException) as context:
                self.service.reconcile(self.tenant, self.region, ambiguous_template, 23)

        self.assertEqual("resolve_backend_http_port", context.exception.bean["phase"])
        region_apply.assert_not_called()

    def test_backend_multiple_http_ports_use_unique_port_map_list_match(self):
        metrics_port = Obj(protocol="http", container_port=9090, k8s_service_name="api-metrics")
        patches = self._patch_desired_state(ports={
            "svc-ui": [self.ui_http],
            "svc-api": [metrics_port, self.api_http],
        })

        with patches[0] as relation_filter, patches[1], patches[2], patches[3], patches[4], patches[5] as region_apply:
            relation_filter.return_value.values_list.return_value = ["svc-ui", "svc-api"]
            self.service.reconcile(self.tenant, self.region, self.template, 23)

        self.assertEqual(
            "api-service.rbd-plugins.svc.cluster.local:8787",
            region_apply.call_args.args[2]["backend_service"],
        )

    def test_multi_component_plugin_without_dependencies_does_not_reuse_frontend(self):
        patches = self._patch_desired_state(dependencies=[])

        with patches[0] as relation_filter, patches[1], patches[2], patches[3], patches[4], patches[5] as region_apply:
            relation_filter.return_value.values_list.return_value = ["svc-ui", "svc-api"]
            with self.assertRaises(ServiceHandleException) as context:
                self.service.reconcile(self.tenant, self.region, self.template, 23)

        self.assertEqual("resolve_backend_component", context.exception.bean["phase"])
        region_apply.assert_not_called()

    def test_single_component_plugin_without_dependencies_reuses_frontend(self):
        single_template = dict(self.template)
        single_template["apps"] = [self.template["apps"][0]]
        patches = self._patch_desired_state(
            components=[self.ui],
            ports={"svc-ui": [self.ui_http]},
            dependencies=[],
        )

        with patches[0] as relation_filter, patches[1], patches[2], patches[3], patches[4], patches[5] as region_apply:
            relation_filter.return_value.values_list.return_value = ["svc-ui"]
            result = self.service.reconcile(self.tenant, self.region, single_template, 23)

        payload = region_apply.call_args.args[2]
        self.assertEqual("reconciled", result["status"])
        self.assertEqual("ui-service.rbd-plugins.svc.cluster.local:8080", payload["backend_service"])

    def test_missing_region_app_id_reports_redacted_phase(self):
        patches = self._patch_desired_state(region_app_id="")

        with patches[0] as relation_filter, patches[1], patches[2], patches[3], patches[4], patches[5] as region_apply:
            relation_filter.return_value.values_list.return_value = ["svc-ui", "svc-api"]
            with self.assertRaises(ServiceHandleException) as context:
                self.service.reconcile(self.tenant, self.region, self.template, 23)

        self.assertEqual(502, context.exception.status_code)
        self.assertEqual("resolve_region_app_id", context.exception.bean["phase"])
        self.assertEqual("rainbond-agent", context.exception.bean["plugin_id"])
        self.assertNotIn("apps", context.exception.bean)
        region_apply.assert_not_called()

    def test_missing_enterprise_id_fails_before_region_request(self):
        tenant = Obj(
            tenant_id="team-1",
            enterprise_id=None,
            namespace="rbd-plugins",
        )
        patches = self._patch_desired_state()

        with patches[0] as relation_filter, patches[1], patches[2], patches[3], patches[4], patches[5] as region_apply:
            relation_filter.return_value.values_list.return_value = ["svc-ui", "svc-api"]
            with self.assertRaises(ServiceHandleException) as context:
                self.service.reconcile(tenant, self.region, self.template, 23)

        self.assertEqual("rbd_plugin_sync_failed", context.exception.msg)
        self.assertEqual("validate_template", context.exception.bean["phase"])
        region_apply.assert_not_called()

    def test_region_failure_is_wrapped_without_exposing_exception_text(self):
        patches = self._patch_desired_state()

        with self.assertLogs("default", level="WARNING") as captured:
            with patches[0] as relation_filter, patches[1], patches[2], patches[3], patches[4], \
                    patches[5] as region_apply:
                relation_filter.return_value.values_list.return_value = ["svc-ui", "svc-api"]
                region_apply.side_effect = RuntimeError("Authorization: secret-token")
                with self.assertRaises(ServiceHandleException) as context:
                    self.service.reconcile(self.tenant, self.region, self.template, 23)

        self.assertEqual("apply_region_rbdplugin", context.exception.bean["phase"])
        self.assertNotIn("secret-token", str(context.exception.bean))
        self.assertNotIn("secret-token", context.exception.msg_show)
        logs = "\n".join(captured.output)
        self.assertIn("error_type=RuntimeError", logs)
        self.assertIn("region_name=rainbond", logs)
        self.assertIn("target_service=ui-service.rbd-plugins.svc.cluster.local:8080/static/main.js", logs)
        self.assertNotIn("secret-token", logs)

    def test_required_platform_plugin_fields_must_be_nonempty_strings(self):
        invalid_values = {
            "plugin_id": {
                "secret": "plugin-secret"
            },
            "plugin_type": ["JSInject"],
            "frontend_component": 123,
            "entry_path": {
                "secret": "entry-secret"
            },
        }

        for field, invalid_value in invalid_values.items():
            with self.subTest(field=field):
                template = dict(self.template)
                platform_plugin = dict(self.template["platform_plugin"])
                platform_plugin[field] = invalid_value
                template["platform_plugin"] = platform_plugin
                with self.assertLogs("default", level="WARNING") as captured:
                    with mock.patch("console.services.rbd_plugin_sync_service.region_api.create_rbdplugin") as region_apply:
                        with self.assertRaises(ServiceHandleException) as context:
                            self.service.reconcile(self.tenant, self.region, template, 23)

                self.assertEqual("rbd_plugin_sync_failed", context.exception.msg)
                self.assertEqual("validate_template", context.exception.bean["phase"])
                self.assertNotIn("secret", "\n".join(captured.output))
                region_apply.assert_not_called()

    def test_inject_position_must_be_a_sequence_of_strings(self):
        for invalid_value in ("Platform", {"position": "Platform"}, 123, None, ["Platform", 7]):
            with self.subTest(invalid_value=invalid_value):
                template = dict(self.template)
                platform_plugin = dict(self.template["platform_plugin"])
                platform_plugin["inject_position"] = invalid_value
                template["platform_plugin"] = platform_plugin
                with mock.patch("console.services.rbd_plugin_sync_service.region_api.create_rbdplugin") as region_apply:
                    with self.assertRaises(ServiceHandleException) as context:
                        self.service.reconcile(self.tenant, self.region, template, 23)

                self.assertEqual("validate_template", context.exception.bean["phase"])
                region_apply.assert_not_called()

    def test_unexpected_normalization_error_is_wrapped_without_sensitive_details(self):
        patches = self._patch_desired_state()

        with self.assertLogs("default", level="WARNING") as captured:
            with patches[0] as relation_filter, patches[1], patches[2], patches[3], patches[4], \
                    patches[5] as region_apply, \
                    mock.patch(
                        "console.services.rbd_plugin_sync_service.share_service.normalize_platform_plugin_positions",
                        side_effect=RuntimeError("credential=normalization-secret"),
                    ):
                relation_filter.return_value.values_list.return_value = ["svc-ui", "svc-api"]
                with self.assertRaises(ServiceHandleException) as context:
                    self.service.reconcile(self.tenant, self.region, self.template, 23)

        self.assertEqual("rbd_plugin_sync_failed", context.exception.msg)
        self.assertEqual("validate_template", context.exception.bean["phase"])
        logs = "\n".join(captured.output)
        self.assertIn("error_type=RuntimeError", logs)
        self.assertNotIn("normalization-secret", logs)
        region_apply.assert_not_called()

    def test_downstream_service_exception_is_wrapped_without_sensitive_details(self):
        patches = self._patch_desired_state()
        downstream_error = ServiceHandleException(
            msg="Authorization: downstream-secret",
            msg_show="credential downstream-secret",
            status_code=409,
            bean={"token": "downstream-secret"},
        )

        with self.assertLogs("default", level="WARNING") as captured:
            with patches[0] as relation_filter, patches[1], patches[2], patches[3], patches[4], \
                    patches[5] as region_apply, \
                    mock.patch(
                        "console.services.rbd_plugin_sync_service.share_service.normalize_platform_plugin_positions",
                        side_effect=downstream_error,
                    ):
                relation_filter.return_value.values_list.return_value = ["svc-ui", "svc-api"]
                with self.assertRaises(ServiceHandleException) as context:
                    self.service.reconcile(self.tenant, self.region, self.template, 23)

        self.assertIsNot(downstream_error, context.exception)
        self.assertEqual(502, context.exception.status_code)
        self.assertEqual("rbd_plugin_sync_failed", context.exception.msg)
        self.assertEqual("validate_template", context.exception.bean["phase"])
        self.assertNotIn("downstream-secret", str(context.exception.bean))
        self.assertNotIn("downstream-secret", context.exception.msg_show)
        logs = "\n".join(captured.output)
        self.assertIn("error_type=ServiceHandleException", logs)
        self.assertNotIn("downstream-secret", logs)
        region_apply.assert_not_called()

    def test_repeated_reconcile_emits_identical_desired_payload(self):
        patches = self._patch_desired_state()

        with patches[0] as relation_filter, patches[1], patches[2], patches[3], patches[4], patches[5] as region_apply:
            relation_filter.return_value.values_list.return_value = ["svc-ui", "svc-api"]
            self.service.reconcile(self.tenant, self.region, self.template, 23)
            self.service.reconcile(self.tenant, self.region, self.template, 23)

        self.assertEqual(2, region_apply.call_count)
        first_payload = region_apply.call_args_list[0].args[2]
        second_payload = region_apply.call_args_list[1].args[2]
        self.assertEqual(first_payload, second_payload)
        self.assertEqual("rainbond-agent", first_payload["plugin_id"])
