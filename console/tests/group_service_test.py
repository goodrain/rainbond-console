# -*- coding: utf-8 -*-
import os
import sys
from contextlib import ExitStack
from types import ModuleType
from unittest import TestCase, mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from console.services import group_service as group_service_module  # noqa: E402
from console.services.group_service import group_service  # noqa: E402
from www.apiclient.regionapi import RegionInvokeApi  # noqa: E402


class Obj(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


# capability_id: console.app.delete
class GroupServiceDeleteAppTestCase(TestCase):
    def test_delete_app_cleans_hidden_template_records(self):
        relation = mock.Mock(app_model_id="hidden-template-id")

        with mock.patch.object(group_service_module.group_repo, "delete_group_by_pk") as delete_group_mock, \
                mock.patch.object(group_service_module.upgrade_repo,
                                  "delete_app_record_by_group_id") as delete_upgrade_mock, \
                mock.patch.object(group_service_module.region_app_repo,
                                  "get_region_app_id",
                                  return_value="region-app-id") as get_region_app_id_mock, \
                mock.patch.object(group_service_module.migrate_repo,
                                  "get_by_original_group_id",
                                  return_value=None) as get_migrate_mock, \
                mock.patch.object(group_service_module.region_api, "delete_app") as delete_region_app_mock, \
                mock.patch("console.services.app_version_service.app_version_service.get_hidden_template",
                           return_value=(relation, None)) as get_hidden_template_mock, \
                mock.patch("console.services.app_version_service.rainbond_app_repo.delete_app_version_by_id"
                           ) as delete_app_version_mock, \
                mock.patch("console.services.app_version_service.rainbond_app_repo.delete_app_by_id"
                           ) as delete_hidden_app_mock, \
                mock.patch("console.services.app_version_service.app_version_template_relation_repo.delete_by_group_id",
                           create=True) as delete_relation_mock:
            group_service._delete_app("demo-team", "demo-region", 42)

        delete_group_mock.assert_called_once_with(42)
        delete_upgrade_mock.assert_called_once_with(42)
        get_hidden_template_mock.assert_called_once_with(42)
        delete_app_version_mock.assert_called_once_with("hidden-template-id")
        delete_hidden_app_mock.assert_called_once_with("hidden-template-id")
        delete_relation_mock.assert_called_once_with(42)
        get_region_app_id_mock.assert_called_once_with("demo-region", 42)
        get_migrate_mock.assert_called_once_with(42)
        delete_region_app_mock.assert_called_once_with(
            "demo-region", "demo-team", "region-app-id", {"etcd_keys": []}
        )


class GroupServiceAppStatusAggregationTests(TestCase):
    # capability_id: console.app-status.aggregate-rainbond-components
    def test_get_app_status_uses_component_aggregation_for_rainbond_apps(self):
        tenant = Obj(tenant_name="demo-team", enterprise_id="eid-1")
        component_relations = [Obj(service_id="svc-1"), Obj(service_id="svc-2")]
        components = [Obj(service_id="svc-1"), Obj(service_id="svc-2")]

        with mock.patch.object(group_service_module.region_app_repo, "get_region_app_id", return_value="region-app-1"), \
                mock.patch.object(group_service_module.region_api, "get_app_status", return_value={"status": "RUNNING"}), \
                mock.patch.object(group_service_module.group_repo, "get_group_by_id", return_value=Obj(app_type="rainbond")), \
                mock.patch.object(group_service_module.group_service_relation_repo,
                                  "get_services_by_group",
                                  return_value=component_relations), \
                mock.patch.object(group_service_module.service_repo,
                                  "get_services_by_service_ids",
                                  return_value=components), \
                mock.patch.object(group_service_module.base_service,
                                  "status_multi_service",
                                  return_value=[
                                      {"service_id": "svc-1", "status": "running"},
                                      {"service_id": "svc-2", "status": "abnormal"},
                                  ]):
            status = group_service.get_app_status(tenant, "demo-region", 42)

        self.assertEqual(status["status"], "PARTIAL_ABNORMAL")

    # capability_id: console.app-status.list-closed-with-undeploy-components
    def test_add_component_status_to_apps_marks_closed_when_components_are_closed_or_undeploy(self):
        apps = [Obj(ID=42, app_type="rainbond")]
        services = [Obj(service_id="svc-1", group_id=42), Obj(service_id="svc-2", group_id=42)]
        service_status = {
            "svc-1": {"status": "closed"},
            "svc-2": {"status": "undeploy"},
        }

        result = group_service._add_component_status_to_apps(
            apps,
            services,
            service_status,
            {42: {"status": "RUNNING", "memory": 0, "cpu": 0}},
        )

        self.assertEqual(result[42]["status"], "CLOSED")


class GroupServiceAppDetailPodCountTests(TestCase):

    def _get_app_detail(self, component_ids, pod_nums, dynamic_pods=None):
        app = Obj(
            ID=42,
            group_name="demo-app",
            app_type="rainbond",
            logo="",
            k8s_app="demo-app",
            username="owner",
            to_dict=lambda: {},
        )
        tenant = Obj(tenant_id="tenant-id", tenant_name="tenant-name", namespace="tenant-ns")
        region = Obj(region_name="rainbond")
        components = [Obj(service_id=component_id) for component_id in component_ids]
        services = [Obj(service_id=component_id, arch="amd64") for component_id in component_ids]
        resource_query = mock.Mock()
        resource_query.count.return_value = 0
        principal = Obj(get_name=lambda: "Owner", email="owner@example.com")

        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(group_service_module.group_repo, "get_group_by_pk", return_value=app))
            stack.enter_context(mock.patch.object(group_service, "sync_app_services", return_value="region-app-id"))
            stack.enter_context(
                mock.patch.object(group_service_module.group_service_relation_repo,
                                  "count_service_by_app_id",
                                  return_value=len(component_ids)))
            stack.enter_context(mock.patch.object(group_service_module.share_repo, "count_by_app_id", return_value=0))
            stack.enter_context(
                mock.patch.object(group_service_module.k8s_resources_repo, "list_by_app_id", return_value=resource_query))
            stack.enter_context(mock.patch.object(group_service_module.region_api, "get_api_gateway", return_value={"list": []}))
            stack.enter_context(
                mock.patch.object(group_service_module.app_config_group_service, "count_by_app_id", return_value=0))
            stack.enter_context(
                mock.patch.object(
                    group_service_module.group_service_relation_repo,
                    "get_services_by_group",
                    return_value=components))
            stack.enter_context(
                mock.patch.object(group_service_module.service_repo, "get_services_by_service_ids", return_value=services))
            get_pod_nums = stack.enter_context(
                mock.patch.object(
                    group_service_module.region_api,
                    "get_services_pod_nums",
                    return_value=pod_nums))
            get_dynamic_pods = stack.enter_context(
                mock.patch.object(
                    group_service_module.region_api,
                    "get_dynamic_services_pods",
                    return_value=dynamic_pods))
            stack.enter_context(
                mock.patch.object(group_service_module.user_repo, "get_user_by_username", return_value=principal))
            stack.enter_context(
                mock.patch.object(group_service_module.compose_repo, "get_group_compose_by_group_id", return_value=None))
            result = group_service.get_app_detail(tenant, region, 42)

        return result, get_pod_nums, get_dynamic_pods

    def test_lightweight_pod_counts_disable_edit_without_loading_pod_details(self):
        result, get_pod_nums, get_dynamic_pods = self._get_app_detail(
            ["service-a", "service-b"], {
                "service-a": 0,
                "service-b": 2
            })

        self.assertFalse(result["can_edit"])
        get_pod_nums.assert_called_once_with("rainbond", "tenant-name", ["service-a", "service-b"])
        get_dynamic_pods.assert_not_called()

    def test_lightweight_pod_counts_keep_edit_enabled_when_all_components_are_stopped(self):
        result, get_pod_nums, get_dynamic_pods = self._get_app_detail(
            ["service-a", "service-b"], {
                "service-a": 0,
                "service-b": 0
            })

        self.assertTrue(result["can_edit"])
        get_pod_nums.assert_called_once()
        get_dynamic_pods.assert_not_called()

    def test_unavailable_lightweight_endpoint_falls_back_to_pod_details(self):
        result, get_pod_nums, get_dynamic_pods = self._get_app_detail(
            ["service-a"], None, {"list": [{"service_id": "service-a"}]})

        self.assertFalse(result["can_edit"])
        get_pod_nums.assert_called_once_with("rainbond", "tenant-name", ["service-a"])
        get_dynamic_pods.assert_called_once_with("rainbond", "tenant-name", ["service-a"])

    def test_empty_application_skips_both_pod_region_requests(self):
        result, get_pod_nums, get_dynamic_pods = self._get_app_detail([], None)

        self.assertTrue(result["can_edit"])
        get_pod_nums.assert_not_called()
        get_dynamic_pods.assert_not_called()


class RegionApiPodCountTests(TestCase):

    def test_get_services_pod_nums_uses_lightweight_endpoint_and_short_timeout(self):
        client = RegionInvokeApi()
        tenant_region = Obj(region_tenant_name="region-tenant")

        with mock.patch.object(
                client,
                "_RegionInvokeApi__get_region_access_info",
                return_value=("http://region.example", "token")), mock.patch.object(
                    client,
                    "_RegionInvokeApi__get_tenant_region_info",
                    return_value=tenant_region), mock.patch.object(client, "_set_headers"), mock.patch.object(
                        client,
                        "_get",
                        return_value=({"status": 200}, {"bean": {
                            "service-a": 2
                        }})) as request_get:
            result = client.get_services_pod_nums("rainbond", "tenant-name", ["service-a"])

        self.assertEqual(result, {"service-a": 2})
        request_get.assert_called_once_with(
            "http://region.example/v2/tenants/region-tenant/pod_nums?service_ids=service-a",
            client.default_headers,
            region="rainbond",
            timeout=3,
        )

    def test_get_services_pod_nums_returns_none_when_endpoint_is_unavailable(self):
        client = RegionInvokeApi()
        tenant_region = Obj(region_tenant_name="region-tenant")

        with mock.patch.object(
                client,
                "_RegionInvokeApi__get_region_access_info",
                return_value=("http://region.example", "token")), mock.patch.object(
                    client,
                    "_RegionInvokeApi__get_tenant_region_info",
                    return_value=tenant_region), mock.patch.object(client, "_set_headers"), mock.patch.object(
                        client, "_get", return_value=({"status": 404}, {"msg": "not found"})):
            result = client.get_services_pod_nums("rainbond", "tenant-name", ["service-a"])

        self.assertIsNone(result)


# capability_id: console.operator-managed.skip-kubeblocks-services
class GroupServiceOperatorManagedTests(TestCase):
    def test_get_watch_managed_data_skips_services_backing_kubeblocks_components(self):
        tenant = Obj(tenant_name="demo-team", namespace="demo-ns")
        kubeblocks_component = Obj(
            extend_method="kubeblocks_component",
            service_source="kubeblocks",
            k8s_component_name="test-5060-mysql",
        )
        app_service_stub = ModuleType("console.services.app")
        app_service_stub.app_service = Obj(
            is_k8s_component_name_duplicate=mock.Mock(return_value=False)
        )

        with mock.patch.object(group_service_module.region_app_repo,
                               "get_region_app_id",
                               return_value="region-app-1"), \
                mock.patch.object(group_service_module.base_service,
                                  "get_watch_managed",
                                  return_value={
                                      "services": [
                                          {
                                              "name": "test-5060-mysql",
                                              "ip": "None",
                                              "port": "3306",
                                          },
                                          {
                                              "name": "external-api",
                                              "ip": "None",
                                              "port": "8080",
                                          },
                                      ]
                                  }), \
                mock.patch.object(group_service,
                                  "list_components",
                                  return_value=[kubeblocks_component]), \
                mock.patch.dict(sys.modules, {"console.services.app": app_service_stub}):
            data = group_service.get_watch_managed_data(tenant, "demo-region", 42)

        self.assertEqual(
            data,
            {
                "service": [
                    {
                        "name": "external-api-svc",
                        "static": False,
                        "namespace": "demo-ns",
                        "service": "external-api",
                        "port": "8080",
                    }
                ]
            },
        )
