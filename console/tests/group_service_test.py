# -*- coding: utf-8 -*-
import os
import sys
from types import ModuleType
from unittest import TestCase, mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from console.services import group_service as group_service_module  # noqa: E402
from console.services.group_service import group_service  # noqa: E402


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


# capability_id: console.app.delete-with-resources
class GroupServiceDeleteAppWithResourcesTestCase(TestCase):
    def test_delete_app_with_resources_deletes_components_and_attached_resources(self):
        user = Obj(user_id=1001, enterprise_id="eid-1", nick_name="admin")
        tenant = Obj(tenant_id="team-1", tenant_name="demo-team", enterprise_id="eid-1")
        app = Obj(ID=42, app_id=42, app_type="rainbond", group_name="demo-app")
        services = [Obj(service_id="svc-1"), Obj(service_id="svc-2")]
        k8s_resources = [Obj(ID=7), Obj(ID=8)]

        with mock.patch.object(group_service, "batch_delete_app_services",
                               return_value=services) as batch_delete_mock, \
                mock.patch("console.services.kubeblocks_service.kubeblocks_service.delete_kubeblocks_cluster"
                           ) as delete_kubeblocks_mock, \
                mock.patch("console.services.k8s_resource.k8s_resource_service.list_by_app_id",
                           return_value=k8s_resources) as list_k8s_mock, \
                mock.patch("console.services.k8s_resource.k8s_resource_service.batch_delete_k8s_resource"
                           ) as delete_k8s_mock, \
                mock.patch.object(group_service_module.app_config_group_service,
                                  "batch_delete_config_group") as delete_config_group_mock, \
                mock.patch.object(group_service, "delete_app_share_records") as delete_share_mock, \
                mock.patch.object(group_service, "delete_app") as delete_app_mock:
            result = group_service.delete_app_with_resources(user, tenant, "demo-region", app)

        self.assertEqual(result, services)
        batch_delete_mock.assert_called_once_with(user, "team-1", "demo-region", 42)
        delete_kubeblocks_mock.assert_called_once_with(["svc-1", "svc-2"], "demo-region")
        list_k8s_mock.assert_called_once_with("42")
        delete_k8s_mock.assert_called_once_with("eid-1", "demo-team", "42", "demo-region", [7, 8])
        delete_config_group_mock.assert_called_once_with("demo-region", "demo-team", 42)
        delete_share_mock.assert_called_once_with("demo-team", 42)
        delete_app_mock.assert_called_once_with(tenant, "demo-region", app)


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
