# -*- coding: utf-8 -*-
import collections
import os
import sys
import typing
from types import ModuleType
from unittest import mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))
if not hasattr(typing, "NotRequired"):
    typing.NotRequired = typing.Optional

sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
openapi_client_module = ModuleType("openapi_client")
openapi_client_module.MarketOpenapiApi = type("MarketOpenapiApi", (), {})
openapi_client_module.ApiClient = type(
    "ApiClient", (), {
        "__init__": lambda self, configuration=None: None
    })
sys.modules.setdefault("openapi_client", openapi_client_module)
openapi_client_configuration = ModuleType("openapi_client.configuration")
openapi_client_configuration.Configuration = type(
    "Configuration", (), {"__init__": lambda self: None})
sys.modules.setdefault("openapi_client.configuration",
                       openapi_client_configuration)
openapi_client_rest = ModuleType("openapi_client.rest")
openapi_client_rest.ApiException = type("ApiException", (Exception, ), {})
sys.modules.setdefault("openapi_client.rest", openapi_client_rest)
market_openapi_api = ModuleType("openapi_client.api.market_openapi_api")
market_openapi_api.MarketOpenapiApi = type("MarketOpenapiApi", (), {})
sys.modules.setdefault("openapi_client.api.market_openapi_api",
                       market_openapi_api)
os.environ.setdefault("DISABLE_FIRST_DEPLOY_SWEEPER", "1")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402
from django.test import SimpleTestCase  # noqa: E402

sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "src",
                     "openapi-client")))
django.setup()


class Obj(object):

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class ExtendedDeployDiagnosticsEntrypointTests(SimpleTestCase):

    def test_k8s_resource_create_tracks_and_marks_success_without_deploy_event(
            self):
        from console.views import k8s_resource as k8s_resource_view

        view = k8s_resource_view.AppK8sResourceListView()
        view.enterprise = Obj(enterprise_id="eid-1")
        view.tenant_name = "demo-team"
        view.tenant = Obj(tenant_name="demo-team", enterprise_id="eid-1")
        view.user = Obj(nick_name="tester")
        view.app_id = 12
        view.app = Obj(ID=12, group_name="demo-app")
        view.region_name = "rainbond"
        request = Obj(data={
            "resource_yaml":
            "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: demo"
        },
                      method="POST")
        tracker = {"key": "tracker"}

        with mock.patch.object(k8s_resource_view.k8s_resource_service, "create_k8s_resource") as create_resource, \
                mock.patch.object(k8s_resource_view.enterprise_first_deploy_service,
                                  "safe_begin_deploy_tracking", return_value=tracker) as begin_tracking, \
                mock.patch.object(k8s_resource_view.enterprise_first_deploy_service,
                                  "safe_mark_success") as mark_success:
            response = view.post(request)

        self.assertEqual(response.status_code, 200)
        create_resource.assert_called_once()
        begin_tracking.assert_called_once()
        begin_kwargs = begin_tracking.call_args[1]
        self.assertEqual(begin_kwargs["deploy_type"], "k8s_resource")
        self.assertEqual(begin_kwargs["trigger"], "k8s_resource_create")
        self.assertEqual(begin_kwargs["app_context"]["app_id"], 12)
        self.assertEqual(begin_kwargs["workload_context"]["source_type"],
                         "k8s_resource")
        mark_success.assert_called_once_with(tracker)

    def test_yaml_import_tracks_batch_deploy_events(self):
        from console.services import yaml_k8s_resource as yaml_module

        service = yaml_module.YamlK8SResource()
        tenant = Obj(tenant_id="tenant-1",
                     tenant_name="demo-team",
                     namespace="demo-ns",
                     enterprise_id="eid-1")
        region = Obj(region_id="region-id", region_name="rainbond")
        user = Obj(user_id=7, nick_name="tester")
        app = Obj(app_id=12,
                  region_app_id="region-app-12",
                  group_name="demo-app")
        deployed_services = [
            Obj(service_id="svc-1",
                service_alias="grsvc1",
                _last_deploy_event_id="event-1"),
            Obj(service_id="svc-2",
                service_alias="grsvc2",
                _last_deploy_event_id="event-2"),
        ]
        imported = {
            "k8s_resources": [{
                "kind": "Deployment"
            }],
            "component": [{
                "name": "api"
            }],
        }
        tracker = {"key": "tracker"}

        with mock.patch.object(yaml_module.RegionApp.objects, "filter", return_value=[app]), \
                mock.patch.object(yaml_module.region_api, "yaml_resource_import",
                                  return_value=(Obj(status=200), {"bean": imported})), \
                mock.patch.object(yaml_module.region_resource, "create_k8s_resources"), \
                mock.patch.object(yaml_module.region_resource, "create_components",
                                  return_value=["svc-1", "svc-2"]), \
                mock.patch.object(yaml_module.app_manage_service, "batch_action",
                                  return_value=(200, "success", deployed_services)), \
                mock.patch.object(yaml_module.enterprise_first_deploy_service,
                                  "safe_begin_deploy_tracking", return_value=tracker) as begin_tracking, \
                mock.patch.object(yaml_module.enterprise_first_deploy_service,
                                  "safe_bind_events") as bind_events:
            result = service.yaml_k8s_resource_import("upload-event", 12,
                                                      tenant, tenant.namespace,
                                                      region, "eid-1", user)

        self.assertEqual(result, imported)
        begin_tracking.assert_called_once()
        begin_kwargs = begin_tracking.call_args[1]
        self.assertEqual(begin_kwargs["deploy_type"], "yaml")
        self.assertEqual(begin_kwargs["trigger"], "yaml_import")
        self.assertEqual(begin_kwargs["workload_context"]["event_id"],
                         "upload-event")
        bind_events.assert_called_once_with(
            tracker, ["event-1", "event-2"],
            service_ids=["svc-1", "svc-2"],
            service_aliases=["grsvc1", "grsvc2"])

    def test_yaml_import_marks_failure_when_batch_deploy_service_result_fails(
            self):
        from console.services import yaml_k8s_resource as yaml_module

        service = yaml_module.YamlK8SResource()
        tenant = Obj(tenant_id="tenant-1",
                     tenant_name="demo-team",
                     namespace="demo-ns",
                     enterprise_id="eid-1")
        region = Obj(region_id="region-id", region_name="rainbond")
        user = Obj(user_id=7, nick_name="tester")
        app = Obj(app_id=12,
                  region_app_id="region-app-12",
                  group_name="demo-app")
        deployed_services = [
            Obj(service_id="svc-1",
                service_alias="grsvc1",
                service_cname="api",
                _last_deploy_result={
                    "code": 500,
                    "msg": "builder failed",
                })
        ]
        imported = {
            "k8s_resources": [{
                "kind": "Deployment"
            }],
            "component": [{
                "name": "api"
            }],
        }
        tracker = {"key": "tracker"}

        with mock.patch.object(yaml_module.RegionApp.objects, "filter", return_value=[app]), \
                mock.patch.object(yaml_module.region_api, "yaml_resource_import",
                                  return_value=(Obj(status=200), {"bean": imported})), \
                mock.patch.object(yaml_module.region_resource, "create_k8s_resources"), \
                mock.patch.object(yaml_module.region_resource, "create_components", return_value=["svc-1"]), \
                mock.patch.object(yaml_module.app_manage_service, "batch_action",
                                  return_value=(200, "success", deployed_services)), \
                mock.patch.object(yaml_module.enterprise_first_deploy_service,
                                  "safe_begin_deploy_tracking", return_value=tracker), \
                mock.patch.object(yaml_module.enterprise_first_deploy_service,
                                  "safe_mark_failure") as mark_failure, \
                mock.patch.object(yaml_module.enterprise_first_deploy_service,
                                  "safe_bind_events") as bind_events:
            result = service.yaml_k8s_resource_import("upload-event", 12,
                                                      tenant, tenant.namespace,
                                                      region, "eid-1", user)

        self.assertEqual(result, imported)
        mark_failure.assert_called_once_with(tracker,
                                             reason="api: builder failed",
                                             failure_stage="build")
        bind_events.assert_not_called()

    def test_upload_helm_chart_import_tracks_batch_deploy_events(self):
        from console.services import helm_app_yaml as helm_module

        service = helm_module.HelmAppService()
        tenant = Obj(tenant_id="tenant-1",
                     tenant_name="demo-team",
                     namespace="demo-ns",
                     enterprise_id="eid-1")
        user = Obj(user_id=7, nick_name="tester")
        app = Obj(app_id=12,
                  region_app_id="region-app-12",
                  group_name="demo-app")
        deployed_services = [
            Obj(service_id="svc-1",
                service_alias="grsvc1",
                _last_deploy_event_id="event-1")
        ]
        imported = {
            "k8s_resources": [{
                "kind": "Deployment"
            }],
            "component": [{
                "name": "api"
            }],
        }
        tracker = {"key": "tracker"}

        with mock.patch.object(helm_module.region_app_repo, "get_region_app_id", return_value="region-app-12"), \
                mock.patch.object(helm_module.RegionApp.objects, "filter", return_value=[app]), \
                mock.patch.object(helm_module.region_api, "import_upload_chart_resource",
                                  return_value=(Obj(status=200), {"bean": imported})), \
                mock.patch.object(helm_module.region_resource, "create_k8s_resources"), \
                mock.patch.object(helm_module.region_resource, "create_components", return_value=["svc-1"]), \
                mock.patch.object(helm_module.app_manage_service, "batch_action",
                                  return_value=(200, "success", deployed_services)), \
                mock.patch.object(helm_module.enterprise_first_deploy_service,
                                  "safe_begin_deploy_tracking", return_value=tracker) as begin_tracking, \
                mock.patch.object(helm_module.enterprise_first_deploy_service,
                                  "safe_bind_events") as bind_events:
            result = service.import_upload_chart_resource(
                "rainbond", tenant, 12, {
                    "chart": "bitnami/mysql",
                    "version": "8.0.30",
                    "values": {
                        "password": "plain-secret"
                    }
                }, user)

        self.assertEqual(result, imported)
        begin_tracking.assert_called_once()
        begin_kwargs = begin_tracking.call_args[1]
        self.assertEqual(begin_kwargs["deploy_type"], "helm")
        self.assertEqual(begin_kwargs["trigger"], "helm_upload_chart_import")
        self.assertEqual(begin_kwargs["workload_context"]["source_type"],
                         "helm")
        self.assertNotIn("plain-secret", str(begin_kwargs["workload_context"]))
        bind_events.assert_called_once_with(tracker, ["event-1"],
                                            service_ids=["svc-1"],
                                            service_aliases=["grsvc1"])

    def test_upload_helm_chart_import_marks_failure_when_batch_deploy_service_result_fails(
            self):
        from console.services import helm_app_yaml as helm_module

        service = helm_module.HelmAppService()
        tenant = Obj(tenant_id="tenant-1",
                     tenant_name="demo-team",
                     namespace="demo-ns",
                     enterprise_id="eid-1")
        user = Obj(user_id=7, nick_name="tester")
        app = Obj(app_id=12,
                  region_app_id="region-app-12",
                  group_name="demo-app")
        deployed_services = [
            Obj(service_id="svc-1",
                service_alias="grsvc1",
                service_cname="api",
                _last_deploy_result={
                    "code": 500,
                    "msg": "builder failed",
                })
        ]
        imported = {
            "k8s_resources": [{
                "kind": "Deployment"
            }],
            "component": [{
                "name": "api"
            }],
        }
        tracker = {"key": "tracker"}

        with mock.patch.object(helm_module.region_app_repo, "get_region_app_id", return_value="region-app-12"), \
                mock.patch.object(helm_module.RegionApp.objects, "filter", return_value=[app]), \
                mock.patch.object(helm_module.region_api, "import_upload_chart_resource",
                                  return_value=(Obj(status=200), {"bean": imported})), \
                mock.patch.object(helm_module.region_resource, "create_k8s_resources"), \
                mock.patch.object(helm_module.region_resource, "create_components", return_value=["svc-1"]), \
                mock.patch.object(helm_module.app_manage_service, "batch_action",
                                  return_value=(200, "success", deployed_services)), \
                mock.patch.object(helm_module.enterprise_first_deploy_service,
                                  "safe_begin_deploy_tracking", return_value=tracker), \
                mock.patch.object(helm_module.enterprise_first_deploy_service,
                                  "safe_mark_failure") as mark_failure, \
                mock.patch.object(helm_module.enterprise_first_deploy_service,
                                  "safe_bind_events") as bind_events:
            result = service.import_upload_chart_resource(
                "rainbond", tenant, 12, {
                    "chart": "bitnami/mysql",
                    "version": "8.0.30",
                }, user)

        self.assertEqual(result, imported)
        mark_failure.assert_called_once_with(tracker,
                                             reason="api: builder failed",
                                             failure_stage="build")
        bind_events.assert_not_called()

    def test_vm_create_tracks_and_marks_success_without_deploy_event(self):
        from console.views.app_create import vm_run as vm_run_view

        view = vm_run_view.VMRunCreateView()
        view.tenant = Obj(tenant_id="tenant-1",
                          tenant_name="demo-team",
                          namespace="demo-ns",
                          enterprise_id="eid-1")
        view.user = Obj(user_id=7, nick_name="tester")
        view.response_region = "rainbond"
        new_service = Obj(
            service_id="svc-vm",
            service_alias="grvm",
            service_region="rainbond",
            service_source="vm_run",
            language="",
            arch="amd64",
            to_dict=lambda: {"service_id": "svc-vm"},
        )
        request = Obj(data={
            "group_id": 12,
            "service_cname": "vm-demo",
            "k8s_component_name": "vm-demo",
            "arch": "amd64",
            "image_name": "ubuntu",
            "asset_id": 9,
        },
                      META={})
        asset = Obj(ID=9,
                    image_url="demo/vm-runtime",
                    source_uri="",
                    os_name="Ubuntu",
                    source_type="upload")
        tracker = {"key": "tracker"}

        with mock.patch.object(vm_run_view.app_service, "is_k8s_component_name_duplicate", return_value=False), \
                mock.patch.object(vm_run_view.vms, "ensure_vm_platform_running"), \
                mock.patch.object(vm_run_view.vms, "validate_vm_runtime_config"), \
                mock.patch.object(vm_run_view.vm_repo, "get_vm_image_instance_by_id", return_value=asset), \
                mock.patch.object(vm_run_view.vms, "is_vm_asset_ready", return_value=True), \
                mock.patch.object(vm_run_view.vms, "infer_vm_boot_source_format", return_value="qcow2"), \
                mock.patch.object(vm_run_view.vms, "resolve_vm_boot_source",
                                  return_value={"image": "demo/vm-runtime", "vm_url": ""}), \
                mock.patch.object(vm_run_view.vms, "resolve_vm_boot_mode", return_value="uefi"), \
                mock.patch.object(vm_run_view.app_service, "create_vm_run_app",
                                  return_value=(200, "success", new_service)), \
                mock.patch.object(vm_run_view.vms, "build_initial_vm_disk_layout", return_value=[]), \
                mock.patch.object(vm_run_view.vms, "save_vm_runtime_config"), \
                mock.patch.object(vm_run_view.vms, "build_vm_create_disk_imports", return_value=[]), \
                mock.patch.object(vm_run_view.group_service, "add_service_to_group", return_value=(200, "success")), \
                mock.patch.object(vm_run_view.enterprise_first_deploy_service,
                                  "safe_begin_deploy_tracking", return_value=tracker) as begin_tracking, \
                mock.patch.object(vm_run_view.enterprise_first_deploy_service,
                                  "safe_bind_events") as bind_events:
            response = view.post(request)

        self.assertEqual(response.status_code, 200)
        begin_tracking.assert_called_once()
        begin_kwargs = begin_tracking.call_args[1]
        self.assertEqual(begin_kwargs["deploy_type"], "virtual_machine")
        self.assertEqual(begin_kwargs["trigger"], "vm_create")
        self.assertEqual(begin_kwargs["workload_context"]["source_type"],
                         "virtual_machine")
        self.assertNotIn("demo/vm-runtime",
                         str(begin_kwargs["workload_context"]))
        bind_events.assert_called_once_with(tracker, [],
                                            service_ids=["svc-vm"],
                                            service_aliases=["grvm"])
