# -*- coding: utf-8 -*-
import os
import sys
from types import ModuleType
from unittest import TestCase, mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
openapi_client_module = ModuleType("openapi_client")
openapi_client_module.MarketOpenapiApi = type("MarketOpenapiApi", (), {})
openapi_client_module.ApiClient = type("ApiClient", (), {"__init__": lambda self, configuration=None: None})
sys.modules.setdefault("openapi_client", openapi_client_module)
openapi_client_configuration = ModuleType("openapi_client.configuration")
openapi_client_configuration.Configuration = type("Configuration", (), {"__init__": lambda self: None})
sys.modules.setdefault("openapi_client.configuration", openapi_client_configuration)
openapi_client_rest = ModuleType("openapi_client.rest")
openapi_client_rest.ApiException = type("ApiException", (Exception, ), {})
sys.modules.setdefault("openapi_client.rest", openapi_client_rest)
market_openapi_api = ModuleType("openapi_client.api.market_openapi_api")
market_openapi_api.MarketOpenapiApi = type("MarketOpenapiApi", (), {})
sys.modules.setdefault("openapi_client.api.market_openapi_api", market_openapi_api)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from console.exception.main import ServiceHandleException  # noqa: E402
from console.services import k8s_resource as resource_module  # noqa: E402
from console.services.k8s_resource import ComponentK8sResourceService  # noqa: E402


class Obj(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


# capability_id: console.k8s-resource.crd-cascade-delete
class K8sResourceDeletionServiceTest(TestCase):
    def setUp(self):
        self.service = ComponentK8sResourceService()
        self.resource = Obj(
            ID=11,
            app_id="42",
            name="widgets.example.com",
            kind="CustomResourceDefinition",
            content=("apiVersion: apiextensions.k8s.io/v1\nkind: CustomResourceDefinition\n"
                     "metadata:\n  name: widgets.example.com\n"),
            state=1)

    def test_preview_scopes_ids_to_current_application(self):
        impact = {
            "has_crd": True,
            "requires_cascade": True,
            "other_app_count": 1,
            "crds": [{"affected_region_app_ids": ["region-app-b"]}]
        }
        with mock.patch.object(resource_module.k8s_resources_repo,
                               "list_by_app_id_and_ids",
                               return_value=[self.resource]) as list_resources, \
                mock.patch.object(self.service,
                                  "get_app_id_and_namespace",
                                  return_value=("team-a", "region-app-a")), \
                mock.patch.object(resource_module.region_api,
                                  "preview_delete_app_resources",
                                  return_value=(Obj(status=200), {"bean": impact})) as preview:
            result = self.service.preview_delete_k8s_resources("eid", "team", "42", "region-a", [11])

        self.assertNotIn("affected_region_app_ids", result["crds"][0])
        list_resources.assert_called_once_with("42", [11])
        payload = preview.call_args[0][2]
        self.assertEqual(payload["app_id"], "region-app-a")
        self.assertEqual(payload["k8s_resources"][0]["client_id"], "11")

    def test_non_admin_cannot_confirm_cross_application_cascade(self):
        impact = {"requires_cascade": True}
        with mock.patch.object(self.service,
                               "preview_delete_k8s_resources",
                               return_value=impact), \
                mock.patch.object(self.service,
                                  "_get_owned_resources",
                                  return_value=[self.resource]), \
                mock.patch.object(self.service,
                                  "get_app_id_and_namespace",
                                  return_value=("team-a", "region-app-a")), \
                mock.patch.object(resource_module.region_api,
                                  "batch_delete_app_resources") as delete_region:
            with self.assertRaises(ServiceHandleException) as raised:
                self.service.batch_delete_k8s_resource("eid",
                                                       "team",
                                                       "42",
                                                       "region-a", [11],
                                                       cascade_crd=True,
                                                       is_enterprise_admin=False)

        self.assertEqual(raised.exception.status_code, 403)
        delete_region.assert_not_called()

    def test_successful_cascade_deletes_selected_and_cross_app_metadata(self):
        impact = {"requires_cascade": True}
        result = {
            "status": "completed",
            "deleted_client_ids": ["11"],
            "cascaded_crds": [{
                "group": "example.com",
                "kind": "Widget"
            }],
        }
        with mock.patch.object(self.service,
                               "preview_delete_k8s_resources",
                               return_value=impact), \
                mock.patch.object(self.service,
                                  "_get_owned_resources",
                                  return_value=[self.resource]), \
                mock.patch.object(self.service,
                                  "get_app_id_and_namespace",
                                  return_value=("team-a", "region-app-a")), \
                mock.patch.object(resource_module.region_api,
                                  "batch_delete_app_resources",
                                  return_value=(Obj(status=200), {"bean": result})), \
                mock.patch.object(resource_module.k8s_resources_repo,
                                  "delete_by_ids") as delete_selected, \
                mock.patch.object(self.service,
                                  "_delete_cascaded_cr_metadata") as delete_cascaded:
            actual = self.service.batch_delete_k8s_resource("eid",
                                                            "team",
                                                            "42",
                                                            "region-a", [11],
                                                            cascade_crd=True,
                                                            is_enterprise_admin=True)

        self.assertEqual(actual, result)
        delete_selected.assert_called_once_with([11])
        delete_cascaded.assert_called_once_with("region-a", result["cascaded_crds"])

    def test_cascade_metadata_cleanup_matches_region_group_and_kind(self):
        matching = Obj(ID=21, kind="Widget", content="apiVersion: example.com/v1\nkind: Widget\nmetadata:\n  name: matching\n")
        other_group = Obj(ID=22,
                          kind="Widget",
                          content="apiVersion: other.example.com/v1\nkind: Widget\nmetadata:\n  name: other\n")
        malformed = Obj(ID=23, kind="Widget", content=": invalid")
        with mock.patch.object(resource_module.region_app_repo,
                               "list_by_region",
                               return_value=[Obj(app_id=42), Obj(app_id=43)]), \
                mock.patch.object(resource_module.k8s_resources_repo,
                                  "list_by_app_ids_and_kind",
                                  return_value=[matching, other_group, malformed]) as candidates, \
                mock.patch.object(resource_module.k8s_resources_repo,
                                  "delete_by_ids") as delete_rows:
            self.service._delete_cascaded_cr_metadata("region-a", [{"group": "example.com", "kind": "Widget"}])

        candidates.assert_called_once_with([42, 43], "Widget")
        delete_rows.assert_called_once_with([21])

    def test_reconcile_deletes_missing_and_preserves_unknown(self):
        present = Obj(ID=31, name="present", kind="Widget", content=self.resource.content, state=1)
        unknown = Obj(ID=32, name="unknown", kind="Widget", content=self.resource.content, state=1)
        reconcile_result = {
            "missing_client_ids": ["31"],
            "unknown": [{
                "client_id": "32",
                "error": "forbidden"
            }],
        }
        with mock.patch.object(resource_module.k8s_resources_repo,
                               "list_available_resources",
                               return_value=[present, unknown]), \
                mock.patch.object(self.service,
                                  "get_app_id_and_namespace",
                                  return_value=("team-a", "region-app-a")), \
                mock.patch.object(resource_module.region_api,
                                  "reconcile_app_resources",
                                  return_value=(Obj(status=200), {"bean": reconcile_result})), \
                mock.patch.object(resource_module.k8s_resources_repo,
                                  "delete_by_ids") as delete_rows:
            actual = self.service.reconcile_k8s_resources("eid", "team", "42", "region-a")

        self.assertEqual(actual, reconcile_result)
        delete_rows.assert_called_once_with([31])

    def test_get_resource_scopes_metadata_lookup_to_current_application(self):
        live = {"content": "live-yaml"}
        with mock.patch.object(self.service,
                               "get_app_id_and_namespace",
                               return_value=("team-a", "region-app-a")), \
                mock.patch.object(resource_module.k8s_resources_repo,
                                  "get_by_app_id_and_id",
                                  return_value=self.resource) as get_resource, \
                mock.patch.object(resource_module.region_api,
                                  "get_app_resource",
                                  return_value=(Obj(status=200), {"bean": live})), \
                mock.patch.object(resource_module.k8s_resources_repo, "update") as update:
            result = self.service.get_k8s_resource("eid", "team", "42", "region-a",
                                                   "widgets.example.com", "11")

        self.assertEqual(result, live)
        get_resource.assert_called_once_with("42", "11")
        update.assert_called_once_with("42", "widgets.example.com", "CustomResourceDefinition", content="live-yaml")

    def test_update_resource_scopes_metadata_lookup_to_current_application(self):
        updated = {"content": "updated", "error_overview": "success", "state": 2}
        with mock.patch.object(self.service,
                               "get_app_id_and_namespace",
                               return_value=("team-a", "region-app-a")), \
                mock.patch.object(resource_module.k8s_resources_repo,
                                  "get_by_app_id_and_id",
                                  return_value=self.resource) as get_resource, \
                mock.patch.object(resource_module.region_api,
                                  "update_app_resource",
                                  return_value=(Obj(status=200), {"bean": updated})), \
                mock.patch.object(resource_module.k8s_resources_repo, "update") as update:
            state = self.service.update_k8s_resource("eid", "team", "42", "new-yaml", "region-a",
                                                     "widgets.example.com", "11")

        self.assertEqual(state, 2)
        get_resource.assert_called_once_with("42", "11")
        update.assert_called_once_with("42", "widgets.example.com", "CustomResourceDefinition", **updated)

    def test_owned_resource_validation_rejects_foreign_ids(self):
        with mock.patch.object(resource_module.k8s_resources_repo,
                               "list_by_app_id_and_ids",
                               return_value=[self.resource]):
            with self.assertRaises(ServiceHandleException) as raised:
                self.service._get_owned_resources("42", [11, 99])

        self.assertEqual(raised.exception.status_code, 404)

    def test_reconcile_skips_region_call_for_empty_application(self):
        with mock.patch.object(resource_module.k8s_resources_repo,
                               "list_available_resources",
                               return_value=[]), \
                mock.patch.object(resource_module.region_api, "reconcile_app_resources") as reconcile:
            result = self.service.reconcile_k8s_resources("eid", "team", "42", "region-a")

        self.assertEqual(result, {"missing_client_ids": [], "unknown": []})
        reconcile.assert_not_called()


# capability_id: console.k8s-resource.reconcile-endpoint
class K8sResourceViewTest(TestCase):
    @staticmethod
    def _configure_view(view):
        view.enterprise = Obj(enterprise_id="eid")
        view.tenant_name = "team"
        view.app_id = 42
        view.region_name = "region-a"
        view.is_enterprise_admin = True
        return view

    def test_deletion_impact_view_returns_preview(self):
        from console.views import k8s_resource as view_module

        view = self._configure_view(view_module.AppK8sResourceDeletionImpactView())
        request = Obj(data={"ids": [11]})
        impact = {"has_crd": True}
        with mock.patch.object(view_module.k8s_resource_service, "preview_delete_k8s_resources",
                               return_value=impact) as preview:
            response = view.post(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["bean"], impact)
        preview.assert_called_once_with("eid", "team", "42", "region-a", [11])

    def test_batch_delete_passes_admin_and_cascade_confirmation(self):
        from console.views import k8s_resource as view_module

        view = self._configure_view(view_module.AppK8sResourceListView())
        request = Obj(data={"ids": [11], "cascade_crd": True})
        result = {"status": "completed"}
        with mock.patch.object(view_module.k8s_resource_service, "batch_delete_k8s_resource", return_value=result) as delete:
            response = view.delete(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["bean"], result)
        delete.assert_called_once_with("eid", "team", "42", "region-a", [11], cascade_crd=True, is_enterprise_admin=True)

    def test_reconcile_view_returns_result(self):
        from console.views import k8s_resource as view_module

        view = self._configure_view(view_module.AppK8sResourceReconcileView())
        request = Obj(data={})
        result = {"missing_client_ids": ["11"], "unknown": []}
        with mock.patch.object(view_module.k8s_resource_service, "reconcile_k8s_resources", return_value=result) as reconcile:
            response = view.post(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["bean"], result)
        reconcile.assert_called_once_with("eid", "team", "42", "region-a")

    def test_fixed_action_routes_resolve_before_resource_name(self):
        from django.urls import resolve
        from console.views import k8s_resource as view_module

        preview = resolve("/console/teams/team/groups/42/k8s-resources/deletion-impact")
        reconcile = resolve("/console/teams/team/groups/42/k8s-resources/reconcile")

        self.assertIs(preview.func.view_class, view_module.AppK8sResourceDeletionImpactView)
        self.assertIs(reconcile.func.view_class, view_module.AppK8sResourceReconcileView)
