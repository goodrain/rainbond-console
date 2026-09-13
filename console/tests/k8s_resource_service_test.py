# -*- coding: utf-8 -*-
import json
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

    def test_preview_normalizes_empty_go_arrays_for_resource_and_application(self):
        from console.services.group_service import group_service

        config_map = Obj(ID=11,
                         name="settings",
                         kind="ConfigMap",
                         state=1,
                         content="apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: settings\n")
        tenant = Obj(enterprise_id="eid", tenant_name="team")
        for payload in ('{"bean":{"has_crd":false,"requires_cascade":false,"crds":null}}',
                        '{"bean":{"has_crd":false,"requires_cascade":false}}',
                        '{"bean":{"has_crd":false,"requires_cascade":false,"crds":[]}}'):
            for caller in ("resource", "application"):
                with self.subTest(payload=payload, caller=caller), \
                        mock.patch.object(self.service, "_get_owned_resources", return_value=[config_map]), \
                        mock.patch.object(self.service, "get_app_id_and_namespace", return_value=("team-a", "region-app-a")), \
                        mock.patch.object(resource_module, "k8s_resource_service", self.service), \
                        mock.patch.object(resource_module.region_api, "preview_delete_app_resources",
                                          return_value=(Obj(status=200), json.loads(payload))):
                    if caller == "application":
                        result = group_service._preview_app_k8s_deletion(tenant, "region-a", "42", [config_map])
                    else:
                        result = self.service.preview_delete_k8s_resources("eid", "team", "42", "region-a", [11])
                    self.assertEqual(result["crds"], [])
                    self.assertFalse(result["requires_cascade"])

    def test_empty_crd_names_do_not_bypass_cascade_permissions(self):
        for payload in ('{"requires_cascade":true,"crds":null}', '{"requires_cascade":true}',
                        '{"requires_cascade":true,"crds":[]}'):
            for admin, cascade, status in ((False, True, 403), (True, False, 409)):
                impact = json.loads(payload)
                with self.subTest(payload=payload, admin=admin, cascade=cascade), \
                        mock.patch.object(self.service, "_get_owned_resources", return_value=[self.resource]), \
                        mock.patch.object(self.service, "get_app_id_and_namespace", return_value=("team-a", "region-app-a")), \
                        mock.patch.object(self.service, "preview_delete_k8s_resources", return_value=impact), \
                        mock.patch.object(resource_module.region_api, "batch_delete_app_resources") as delete_region, \
                        mock.patch.object(resource_module.k8s_resources_repo, "delete_by_ids") as delete_rows:
                    with self.assertRaises(ServiceHandleException) as raised:
                        self.service.batch_delete_k8s_resource("eid",
                                                               "team",
                                                               "42",
                                                               "region-a", [11],
                                                               cascade_crd=cascade,
                                                               is_enterprise_admin=admin)
                    self.assertEqual(raised.exception.status_code, status)
                    delete_region.assert_not_called()
                    delete_rows.assert_not_called()

    def test_batch_delete_normalizes_empty_go_arrays_without_inventing_confirmed_ids(self):
        cases = [
            ('{"bean":{"status":"completed","deleted_client_ids":null,"cascaded_crds":null}}', []),
            ('{"bean":{"status":"completed"}}', []),
            ('{"bean":{"status":"completed","deleted_client_ids":[],"cascaded_crds":[]}}', []),
            ('{"bean":{"status":"completed","deleted_client_ids":["11"],"cascaded_crds":null}}', [11]),
        ]
        for payload, expected_ids in cases:
            with self.subTest(payload=payload), \
                    mock.patch.object(self.service, "_get_owned_resources", return_value=[self.resource]), \
                    mock.patch.object(self.service, "get_app_id_and_namespace", return_value=("team-a", "region-app-a")), \
                    mock.patch.object(self.service, "preview_delete_k8s_resources", return_value={"requires_cascade": False}), \
                    mock.patch.object(resource_module.region_api, "batch_delete_app_resources",
                                      return_value=(Obj(status=200), json.loads(payload))), \
                    mock.patch.object(resource_module.k8s_resources_repo, "delete_by_ids") as delete_rows, \
                    mock.patch.object(self.service, "_delete_cascaded_cr_metadata") as delete_cascaded:
                result = self.service.batch_delete_k8s_resource("eid", "team", "42", "region-a", [11])
                self.assertEqual(result["deleted_client_ids"], [str(item) for item in expected_ids])
                self.assertEqual(result["cascaded_crds"], [])
                if expected_ids:
                    delete_rows.assert_called_once_with(expected_ids)
                else:
                    delete_rows.assert_not_called()
                delete_cascaded.assert_called_once_with("region-a", [])

    def test_incomplete_or_failed_region_delete_preserves_metadata(self):
        error = ServiceHandleException(msg="region unavailable", status_code=503)
        for scenario in ("incomplete", "region error"):
            with self.subTest(scenario=scenario), \
                    mock.patch.object(self.service, "_get_owned_resources", return_value=[self.resource]), \
                    mock.patch.object(self.service, "get_app_id_and_namespace", return_value=("team-a", "region-app-a")), \
                    mock.patch.object(self.service, "preview_delete_k8s_resources", return_value={"requires_cascade": False}), \
                    mock.patch.object(resource_module.region_api, "batch_delete_app_resources",
                                      side_effect=error if scenario == "region error" else None,
                                      return_value=(Obj(status=200), json.loads(
                                          '{"bean":{"status":"pending","deleted_client_ids":null,"cascaded_crds":null}}'))), \
                    mock.patch.object(resource_module.k8s_resources_repo, "delete_by_ids") as delete_rows, \
                    mock.patch.object(self.service, "_delete_cascaded_cr_metadata") as delete_cascaded:
                with self.assertRaises(ServiceHandleException) as raised:
                    self.service.batch_delete_k8s_resource("eid", "team", "42", "region-a", [11])
                if scenario == "region error":
                    self.assertIs(raised.exception, error)
                else:
                    self.assertEqual(raised.exception.status_code, 502)
                delete_rows.assert_not_called()
                delete_cascaded.assert_not_called()

    def test_reconcile_normalizes_empty_go_arrays_and_preserves_unknown_resources(self):
        cases = (
            ('{"bean":{"missing_client_ids":null,"unknown":null}}', [], []),
            ('{"bean":{}}', [], []),
            ('{"bean":{"missing_client_ids":[],"unknown":[]}}', [], []),
            ('{"bean":{"missing_client_ids":["11"],"unknown":null}}', [11], []),
            ('{"bean":{"missing_client_ids":null,"unknown":[{"client_id":"11","error":"forbidden"}]}}', [], [{
                "client_id":
                "11",
                "error":
                "forbidden"
            }]),
        )
        for payload, expected_ids, unknown in cases:
            with self.subTest(payload=payload), \
                    mock.patch.object(resource_module.k8s_resources_repo, "list_available_resources",
                                      return_value=[self.resource]), \
                    mock.patch.object(self.service, "get_app_id_and_namespace", return_value=("team-a", "region-app-a")), \
                    mock.patch.object(resource_module.region_api, "reconcile_app_resources",
                                      return_value=(Obj(status=200), json.loads(payload))), \
                    mock.patch.object(resource_module.k8s_resources_repo, "delete_by_ids") as delete_rows:
                result = self.service.reconcile_k8s_resources("eid", "team", "42", "region-a")
                self.assertEqual(result["missing_client_ids"], [str(item) for item in expected_ids])
                self.assertEqual(result["unknown"], unknown)
                if expected_ids:
                    delete_rows.assert_called_once_with(expected_ids)
                else:
                    delete_rows.assert_not_called()

    def test_non_admin_cannot_confirm_cross_application_cascade(self):
        impact = {
            "requires_cascade": True,
            "crds": [{"name": "widgets.example.com"}],
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
                                  "batch_delete_app_resources") as delete_region:
            with self.assertRaises(ServiceHandleException) as raised:
                self.service.batch_delete_k8s_resource("eid",
                                                       "team",
                                                       "42",
                                                       "region-a", [11],
                                                       cascade_crd=True,
                                                       is_enterprise_admin=False)

        self.assertEqual(raised.exception.status_code, 403)
        self.assertIn("widgets.example.com", raised.exception.msg_show)
        self.assertEqual(raised.exception.bean, impact)
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

    def test_action_routes_resolve_outside_resource_names(self):
        from django.urls import resolve
        from console.views import k8s_resource as view_module

        preview = resolve("/console/teams/team/groups/42/k8s-resources/actions/deletion-impact")
        reconcile = resolve("/console/teams/team/groups/42/k8s-resources/actions/reconcile")

        self.assertIs(preview.func.view_class, view_module.AppK8sResourceDeletionImpactView)
        self.assertIs(reconcile.func.view_class, view_module.AppK8sResourceReconcileView)

    def _dispatch_resource_request(self, suffix, method, data, permissions):
        from django.urls import resolve
        from rest_framework.test import APIRequestFactory
        from console.views.base import ApplicationView

        path = "/console/teams/team/groups/42/k8s-resources/" + suffix
        match = resolve(path)
        request = getattr(APIRequestFactory(), method)(path, data, format="json")

        def initial(view, request, *args, **kwargs):
            self._configure_view(view)
            view.user_perms = permissions
            view.check_perms(request, *args, **kwargs)

        with mock.patch.object(ApplicationView, "initial", initial):
            return match.func(request, **match.kwargs)

    def test_resource_names_matching_legacy_actions_keep_resource_methods(self):
        from django.urls import resolve
        from console.views import k8s_resource as view_module

        for name in ("deletion-impact", "reconcile", "ordinary-resource"):
            for method, permission, service_method, result in (("get", 340001, "get_k8s_resource", {
                    "content": "live-yaml"
            }), ("put", 340003, "update_k8s_resource", 2), ("delete", 340004, "delete_k8s_resource", {
                    "status": "completed"
            })):
                with self.subTest(name=name, method=method):
                    match = resolve("/console/teams/team/groups/42/k8s-resources/" + name)
                    self.assertEqual(match.kwargs.get("name"), name)
                    self.assertEqual(match.kwargs["__message"][method]["perms"], [permission])
                    self.assertIs(getattr(match.func.view_class, method), getattr(view_module.AppK8ResourceView, method))
                    data = {"id": "11", "resource_yaml": "updated-yaml", "cascade_crd": True}
                    with mock.patch.object(view_module.k8s_resource_service, service_method, return_value=result) as service:
                        response = self._dispatch_resource_request(name, method, data, [permission])
                    self.assertEqual(response.status_code, 200)
                    if method == "put":
                        service.assert_called_once_with("eid", "team", "42", "updated-yaml", "region-a", name, "11")
                    elif method == "delete":
                        service.assert_called_once_with("eid",
                                                        "team",
                                                        "42",
                                                        "region-a",
                                                        name,
                                                        "11",
                                                        cascade_crd=True,
                                                        is_enterprise_admin=True)
                    else:
                        service.assert_called_once_with("eid", "team", "42", "region-a", name, "11")

    def test_new_and_legacy_action_posts_keep_action_permissions(self):
        from django.urls import resolve
        from console.views import k8s_resource as view_module

        for action, permission, view_class, service_method in (("deletion-impact", 340004,
                                                                view_module.AppK8sResourceDeletionImpactView,
                                                                "preview_delete_k8s_resources"),
                                                               ("reconcile", 340001, view_module.AppK8sResourceReconcileView,
                                                                "reconcile_k8s_resources")):
            for prefix in ("actions/", ""):
                suffix = prefix + action
                with self.subTest(path=suffix):
                    match = resolve("/console/teams/team/groups/42/k8s-resources/" + suffix)
                    self.assertEqual(match.kwargs["__message"]["post"]["perms"], [permission])
                    self.assertIs(match.func.view_class.post, view_class.post)
                    result = {"has_crd": True} if action == "deletion-impact" else {"missing_client_ids": ["11"]}
                    with mock.patch.object(view_module.k8s_resource_service, service_method, return_value=result) as service:
                        response = self._dispatch_resource_request(suffix, "post", {"ids": [11]}, [permission])
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.data["data"]["bean"], result)
                    expected_args = ("eid", "team", "42", "region-a")
                    if action == "deletion-impact":
                        expected_args += ([11], )
                    service.assert_called_once_with(*expected_args)

    def test_action_and_named_resource_routes_reject_missing_method_permission(self):
        from console.views import k8s_resource as view_module

        routes = [(name, method) for name in ("deletion-impact", "reconcile", "ordinary-resource")
                  for method in ("get", "put", "delete")]
        routes += [(prefix + action, "post") for prefix in ("actions/", "") for action in ("deletion-impact", "reconcile")]
        for suffix, method in routes:
            with self.subTest(path=suffix, method=method), \
                    mock.patch.object(view_module, "k8s_resource_service") as service:
                response = self._dispatch_resource_request(suffix, method, {"id": "11", "ids": [11]}, [])
                self.assertEqual(response.status_code, 403)
                self.assertEqual(service.mock_calls, [])
