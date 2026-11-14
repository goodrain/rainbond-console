# -*- coding: utf-8 -*-
# capability_id: console.vm-snapshot.read-api
import copy
import importlib.util
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from types import ModuleType, SimpleNamespace
from unittest import TestCase, mock

import django
import urllib3
from django.urls import resolve
from django.utils.translation import override
from rest_framework.test import APIRequestFactory, force_authenticate

django.setup()

# The optional generated market SDK is absent in local test dependencies. This
# import-only stand-in is never called; AppBaseView/auth and RegionInvokeApi stay real.
if "openapi_client" not in sys.modules and importlib.util.find_spec("openapi_client") is None:
    market = ModuleType("openapi_client")
    configuration = ModuleType("openapi_client.configuration")
    rest = ModuleType("openapi_client.rest")
    setattr(configuration, "Configuration", lambda: SimpleNamespace(client_side_validation=False, host="", api_key={}))
    setattr(market, "ApiClient", mock.Mock())
    setattr(market, "MarketOpenapiApi", mock.Mock())
    setattr(rest, "ApiException", type("ApiException", (Exception, ), {}))
    sys.modules.update({"openapi_client": market, "openapi_client.configuration": configuration, "openapi_client.rest": rest})

from console.services.vm_snapshot_read import vm_snapshot_read_service  # noqa: E402
from console.views.vm_snapshot import VMSnapshotListView, VMSnapshotDetailView  # noqa: E402
from www.apiclient.regionapi import RegionInvokeApi  # noqa: E402


def snapshot():
    return {
        "snapshot_name": "point-a",
        "description": "Before upgrade",
        "phase": "creating",
        "ready_to_use": False,
        "consistency": "offline",
        "manifest_acked": False,
        "finalized": False,
        "cancelled": False,
        "deleted": False,
        "coverage": {
            "complete": False,
            "expected_writable_disks": 1,
            "included_disks": 0,
            "missing_disk_keys": ["root"],
            "excluded_read_only": []
        },
        "disks": [],
        "operation_id": "internal-op",
        "core_hash": "internal-hash",
        "source_vm_uid": "internal-uid",
        "snapshot_resources": [{
            "name": "physical-resource"
        }],
        "native_proof_hash": "private-proof",
        "receipt": {
            "initialization": "private-material"
        }
    }


class VMSnapshotReadAPITestCase(TestCase):
    def test_identity_pending_and_unknown_remain_unready_and_keep_safe_item_codes(self):
        for code in ('vm_snapshot_identity_pending', 'vm_snapshot_identity_outcome_unknown'):
            self.collection([snapshot()])
            self.upstream_body['bean']['items'][0].update(phase='stopping', error_code=code)
            result = self.call()
            self.assertEqual(result.status_code, 200)
            item = result.data['data']['bean']['items'][0]
            self.assertEqual(item['error_code'], code)
            self.assertFalse(item['ready_to_use'])
            self.upstream_body['bean']['items'][0]['ready_to_use'] = True
            self.assertEqual(self.call().status_code, 502)

    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = SimpleNamespace(user_id=17, enterprise_id="enterprise-a", nick_name="reader", is_authenticated=True)
        self.tenant = SimpleNamespace(tenant_id="team-a", tenant_name="team-a", enterprise_id="enterprise-a", creater=99)
        self.component = SimpleNamespace(service_id="service-a",
                                         service_alias="vm-a",
                                         tenant_id="team-a",
                                         service_region="region-a",
                                         extend_method="vm")
        self.app = SimpleNamespace(ID=42, username="another-user")
        self.other_component = SimpleNamespace(**{**vars(self.component), "service_id": "service-b", "service_alias": "vm-b"})
        self.other_app = SimpleNamespace(ID=99, username="another-user")
        self.permissions = {42: [300002]}
        self.upstream_status = 200
        self.upstream_body = {"bean": snapshot()}
        self.client = RegionInvokeApi()
        self.patches = [
            mock.patch("console.views.base.Tenants.objects.get",
                       side_effect=lambda **q: self.tenant if q.get("tenant_name", q.get("tenant_id")) == "team-a" else
                       SimpleNamespace(tenant_id="team-b", tenant_name="team-b", enterprise_id="enterprise-a", creater=99)),
            mock.patch("console.views.base.TenantEnterprise.objects.filter"),
            mock.patch("console.views.base.EnterpriseUserPerm.objects.filter"),
            mock.patch("console.views.base.user_services.list_roles", return_value=[]),
            mock.patch("console.views.base.perms.list_enterprise_perm_codes_by_roles", return_value=[]),
            mock.patch("console.views.base.optimized_role_perm_repo.get_user_team_all_perms",
                       side_effect=lambda **scope: {
                           "global_perms": [],
                           "app_perms": self.permissions if scope["tenant_id"] == "team-a" else {}
                       }),
            mock.patch("console.views.base.ServiceGroup.objects.filter"),
            mock.patch("console.views.base.TenantServiceInfo.objects.filter", side_effect=self.components),
            mock.patch("console.views.app_config.base.group_service.get_service_group_info",
                       side_effect=lambda service_id: self.app if service_id == "service-a" else self.other_app),
            mock.patch("console.views.app_config.base.group_service.get_app_by_id", side_effect=self.application),
            mock.patch("console.views.base.region_repo.get_region_by_region_name",
                       side_effect=lambda name: SimpleNamespace(region_name=name)),
            mock.patch.object(vm_snapshot_read_service, "client", self.client),
            mock.patch.object(self.client,
                              "_RegionInvokeApi__get_region_access_info",
                              return_value=("https://region.invalid", "")),
            mock.patch.object(self.client,
                              "_RegionInvokeApi__get_tenant_region_info",
                              return_value=SimpleNamespace(region_tenant_name="region-team-a")),
        ]
        for patch in self.patches:
            value = patch.start()
            self.addCleanup(patch.stop)
            if patch.attribute == 'filter':
                value.return_value.first.return_value = None
                value.return_value.values_list.return_value = []
        transport = mock.patch.object(self.client, "_request", side_effect=self.transport)
        self.request = transport.start()
        self.addCleanup(transport.stop)

    def components(self, **query):
        for component in [self.component, self.other_component]:
            if query == {"service_alias": component.service_alias, "tenant_id": component.tenant_id}:
                return [component]
        return []

    def application(self, tenant, region, app_id):
        if tenant.tenant_id == self.component.tenant_id and region == self.component.service_region:
            return {42: self.app, 99: self.other_app}.get(app_id)
        return None

    def transport(self, *_args, **_kwargs):
        return self.upstream_status, json.dumps(self.upstream_body).encode()

    def call(self, detail=False, query=None, authenticated=True, method="get", name="point-a", tenant="team-a", alias="vm-a"):
        path = "/console/teams/{}/apps/{}/vm-snapshots".format(tenant, alias)
        if detail:
            path += "/" + name
        match = resolve(path)
        self.assertIs(match.func.view_class, VMSnapshotDetailView if detail else VMSnapshotListView)
        request = getattr(self.factory, method)(path, query or {"region_name": "region-a"})
        if authenticated:
            force_authenticate(request, self.user)
        return match.func(request, **match.kwargs)

    def collection(self, items=None, **overrides):
        bean = {"items": [snapshot()] if items is None else items, "page": 1, "page_size": 20, "total": 1}
        bean.update(overrides)
        self.upstream_body = {"bean": bean}

    def test_ordinary_describe_user_reads_list_through_actual_client_and_scoped_route(self):
        self.collection()
        response = self.call(query={"region_name": "region-a", "namespace": "other", "service_id": "other", "app_id": 99})
        self.assertEqual(response.status_code, 200)
        bean = response.data["data"]["bean"]
        self.assertEqual(bean["items"][0]["phase"], "creating")
        self.assertFalse(bean["items"][0]["ready_to_use"])
        self.assertEqual((bean["page"], bean["page_size"], bean["total"]), (1, 20, 1))
        self.assertEqual(
            self.request.call_args.args,
            ("https://region.invalid/v2/tenants/region-team-a/services/vm-a/vm-snapshots?page=1&page_size=20", "GET"))
        self.assertEqual(self.request.call_args.kwargs["region"], "region-a")
        self.assertNotIn("internal", json.dumps(response.data))
        self.assertNotIn("private", json.dumps(response.data))

    def test_detail_exposes_only_logical_disk_and_selected_safe_config_fields(self):
        self.upstream_body["bean"].update({
            "config": {
                "cpu_milli":
                2000,
                "memory_mib":
                2048,
                "boot_mode":
                "uefi",
                "cloud_init":
                "private",
                "disk_layout": [{
                    "volume_id": 1,
                    "canonical_name": "physical-disk",
                    "role": "root",
                    "device": "disk",
                    "bus": "virtio",
                    "boot_order": 1,
                    "read_only": False,
                    "secret": "private"
                }]
            },
            "disks": [{
                "volume_id": 1,
                "disk_key": "root",
                "role": "root",
                "read_only": False,
                "storage_class": "standard",
                "requested_bytes": 1073741824,
                "source_pvc": {
                    "name": "physical-pvc"
                },
                "volume_snapshot": {
                    "uid": "private"
                }
            }]
        })
        response = self.call(detail=True)
        self.assertEqual(response.status_code, 200)
        bean = response.data["data"]["bean"]
        self.assertEqual(bean["disks"][0]["volume_id"], 1)
        self.assertEqual(bean["config"]["cpu_milli"], 2000)
        self.assertNotIn("physical", json.dumps(response.data))
        self.assertNotIn("private", json.dumps(response.data))
        self.assertEqual(self.request.call_args.args[-1], "GET")
        self.assertTrue(self.request.call_args.args[0].endswith("/vm-snapshots/point-a"))

    def test_real_empty_list_is_success_but_missing_or_malformed_payload_is_not(self):
        self.collection([], total=0)
        self.assertEqual(self.call().data["data"]["bean"]["items"], [])
        for body in [{}, {
                "bean": {}
        }, {
                "bean": {
                    "items": []
                }
        }, {
                "bean": {
                    "items": None,
                    "page": 1,
                    "page_size": 20,
                    "total": 0
                }
        }]:
            self.upstream_body = body
            response = self.call()
            self.assertEqual(response.status_code, 502)
            self.assertEqual(response.data["data"]["bean"]["error"]["code"], "vm_snapshot_read_failed")

    def test_no_permission_cross_team_component_region_and_application_never_call_region(self):
        for case in ["no-permission", "team", "component", "region", "application"]:
            with self.subTest(case=case):
                self.permissions = {} if case == "no-permission" else {42: [300002]}
                self.request.reset_mock()
                query = {"region_name": "region-b" if case == "region" else "region-a"}
                if case == "application":
                    self.permissions = {99: [300002]}
                response = self.call(query=query,
                                     tenant="team-b" if case == "team" else "team-a",
                                     alias="vm-b" if case == "component" else "vm-a")
                self.assertIn(response.status_code, (403, 404))
                self.request.assert_not_called()

    def test_unauthenticated_and_non_vm_requests_are_rejected_before_client(self):
        self.assertIn(self.call(authenticated=False).status_code, (401, 403))
        self.request.assert_not_called()
        self.component.extend_method = "stateless"
        response = self.call()
        self.assertEqual(response.status_code, 422)
        self.request.assert_not_called()

    def test_dot_segments_and_bad_pagination_never_reach_transport(self):
        for name in [".", "..", "%2e%2e", "point_a", "UPPER"]:
            self.assertEqual(self.call(detail=True, name=name).status_code, 400)
        for query in [{"page": "0"}, {"page_size": "101"}, {"page": "x"}, {"page": "1.2"}, {"page_size": ""}]:
            self.assertEqual(self.call(query={"region_name": "region-a", **query}).status_code, 400)
        self.request.assert_not_called()

    def test_valid_name_and_pagination_are_forwarded_without_scope_override(self):
        self.collection([], page=2, page_size=15, total=0)
        self.assertEqual(self.call(query={"region_name": "region-a", "page": "2", "page_size": "15"}).status_code, 200)
        self.assertTrue(self.request.call_args.args[0].endswith("?page=2&page_size=15"))
        self.upstream_body = {"bean": snapshot()}
        self.upstream_body["bean"]["snapshot_name"] = "point.a"
        self.assertEqual(self.call(detail=True, name="point.a").status_code, 200)

    def test_real_upstream_errors_keep_status_code_retryability_and_safe_bilingual_messages(self):
        cases = [(403, "vm_snapshot_forbidden", False), (404, "vm_snapshot_not_found", False), (409, "vm_restore_busy", False),
                 (409, "vm_restore_conflict", False), (409, "vm_snapshot_pending", True),
                 (422, "vm_snapshot_storage_unsupported", False), (422, "vm_snapshot_config_unsupported", False),
                 (422, "vm_snapshot_incomplete", False), (503, "vm_snapshot_dependency_unavailable", True)]
        for status, code, retryable in cases:
            self.upstream_status = status
            self.upstream_body = {"msg": code, "bean": {"error": {"code": code, "retryable": retryable}, "receipt": "private"}}
            with override("en"):
                english = self.call(detail=True)
            with override("zh-hans"):
                chinese = self.call(detail=True)
            self.assertEqual(chinese.status_code, status)
            self.assertEqual(chinese.data["data"]["bean"], {"error": {"code": code, "retryable": retryable}})
            self.assertNotEqual(english.data["msg_show"], chinese.data["msg_show"])
            self.assertNotIn("private", json.dumps(chinese.data))
            if status == 503:
                self.assertEqual(chinese["Retry-After"], "3")

    def test_transport_failure_unknown_errors_and_accepted_get_never_become_success(self):
        for status in [202, 500, 502]:
            self.upstream_status = status
            self.upstream_body = {"msg": "private raw failure", "bean": snapshot()}
            response = self.call(detail=True)
            self.assertEqual(response.status_code, 502)
            self.assertNotIn("private", json.dumps(response.data))
        self.request.side_effect = RuntimeError("private transport detail")
        response = self.call(detail=True)
        self.assertEqual(response.status_code, 502)
        self.assertNotIn("private", json.dumps(response.data))

    def test_projection_is_fail_closed_for_malformed_detail_and_does_not_invent_ready(self):
        initial = snapshot()
        for key, invalid in [("ready_to_use", "true"), ("coverage", None), ("snapshot_name", ".."), ("phase", {
                "private": "raw"
        })]:
            self.upstream_body = {"bean": {**copy.deepcopy(initial), key: invalid}}
            self.assertEqual(self.call(detail=True).status_code, 502)
        self.upstream_body = {"bean": initial}
        self.upstream_body["bean"].update(ready_to_use=True, phase="ready", manifest_acked=False, finalized=False)
        bean = self.call(detail=True).data["data"]["bean"]
        self.assertTrue(bean["ready_to_use"])
        self.assertFalse(bean["manifest_acked"])
        self.assertFalse(bean["finalized"])

    def test_mutations_are_unavailable_and_legacy_create_client_still_preserves_body(self):
        for method in ["post", "put", "delete"]:
            self.assertIn(self.call(method=method).status_code, (403, 405))
        self.request.assert_not_called()
        self.upstream_status = 202
        self.upstream_body = {"bean": {"snapshot_name": "legacy-point"}}
        payload = {"name": "legacy-point", "description": "unchanged"}
        response, body = self.client.create_vm_snapshot("region-a", "team-a", "vm-a", payload)
        self.assertEqual(response.status, 202)
        self.assertEqual(body["bean"]["snapshot_name"], "legacy-point")
        self.assertEqual(json.loads(self.request.call_args.kwargs["body"]), payload)

    def test_malformed_nested_metadata_or_mismatched_detail_fails_closed(self):
        invalid = [
            {
                "snapshot_name": "other-point"
            },
            {
                "disks": None
            },
            {
                "error_code": {
                    "private": "raw"
                }
            },
            {
                "coverage": {
                    "complete": False,
                    "expected_writable_disks": 1,
                    "included_disks": 0,
                    "missing_disk_keys": [False],
                    "excluded_read_only": []
                }
            },
            {
                "config": {
                    "cpu_milli": -1,
                    "memory_mib": 1,
                    "boot_mode": "uefi",
                    "disk_layout": []
                }
            },
            {
                "config": {
                    "cpu_milli": 2000,
                    "memory_mib": 2048,
                    "boot_mode": "uefi",
                    "disk_layout": None
                }
            },
        ]
        for changed in invalid:
            self.upstream_body = {"bean": {**snapshot(), **changed}}
            self.assertEqual(self.call(detail=True).status_code, 502)
        self.upstream_body = {
            "bean": {
                **snapshot(), "creation_time": "2026-11-13T02:03:04Z",
                "phase": "stopping",
                "error_code": "vm_snapshot_halt_outcome_pending"
            }
        }
        response = self.call(detail=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["bean"]["error_code"], "vm_snapshot_halt_outcome_pending")

    def test_structured_dependency_failure_and_business_error_never_become_empty_success(self):
        from console.exception.main import ServiceHandleException
        self.request.side_effect = ServiceHandleException("private transport material", status_code=503)
        response = self.call(detail=True)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response["Retry-After"], "3")
        self.assertNotIn("private", json.dumps(response.data))
        self.request.side_effect = self.transport
        self.upstream_body = {"code": 403, "msg": "vm_snapshot_forbidden", "bean": snapshot()}
        self.assertEqual(self.call(detail=True).status_code, 403)
        self.collection([], total=0, page_size=19)
        self.assertEqual(self.call().status_code, 502)

    def test_view_service_and_actual_region_transport_read_a_local_http_response(self):
        fixture = self
        paths = []

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                paths.append(self.path)
                body = json.dumps(fixture.upstream_body).encode()
                self.send_response(fixture.upstream_status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_args):
                pass

        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        thread.start()
        pool = urllib3.PoolManager()
        try:
            from django.conf import settings
            from www.apiclient.regionapibaseclient import RegionApiBaseHttpClient
            real_request = RegionApiBaseHttpClient._request.__get__(self.client)
            with mock.patch.object(self.client, "_request", real_request), mock.patch.object(
                    self.client, "get_client", return_value=pool), mock.patch.dict(
                        settings.MODULES, {"RegionToken": False}), mock.patch.object(self.client,
                                                                                     "_RegionInvokeApi__get_region_access_info",
                                                                                     return_value=("http://127.0.0.1:{}".format(
                                                                                         server.server_port), "")):
                response = self.call(detail=True)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data["data"]["bean"]["snapshot_name"], "point-a")
                self.upstream_status = 503
                self.upstream_body = {
                    "msg": "vm_snapshot_dependency_unavailable",
                    "bean": {
                        "error": {
                            "code": "vm_snapshot_dependency_unavailable",
                            "retryable": True
                        }
                    }
                }
                self.assertEqual(self.call(detail=True).status_code, 503)
            self.assertEqual(paths, ["/v2/tenants/region-team-a/services/vm-a/vm-snapshots/point-a"] * 2)
        finally:
            pool.clear()
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
            self.assertFalse(thread.is_alive())

    def test_explicit_business_error_is_not_hidden_by_valid_success_dto(self):
        for detail in (False, True):
            for code, status in [("vm_restore_busy", 409), ("vm_snapshot_dependency_unavailable", 503)]:
                bean = snapshot() if detail else {"items": [], "page": 1, "page_size": 20, "total": 0}
                self.upstream_body = {"code": 200, "bean": {**bean, "error": {"code": code}}}
                response = self.call(detail=detail)
                self.assertEqual(response.status_code, status)
                self.assertEqual(response.data["data"]["bean"]["error"]["code"], code)
        for error in [None, False, 0, [], {}, {"code": ""}, {"code": "unknown"}]:
            self.upstream_body = {"bean": {**snapshot(), "error": error}}
            self.assertEqual(self.call(detail=True).status_code, 502)

    def test_present_optional_error_code_is_validated_even_when_falsey(self):
        for detail in (False, True):
            for invalid in [None, False, 0, [], {}]:
                value = {**snapshot(), "error_code": invalid}
                self.upstream_body = {
                    "bean": value
                } if detail else {
                    "bean": {
                        "items": [value],
                        "page": 1,
                        "page_size": 20,
                        "total": 1
                    }
                }
                self.assertEqual(self.call(detail=detail).status_code, 502)
            for value in [snapshot(), {**snapshot(), "error_code": ""}]:
                self.upstream_body = {
                    "bean": value
                } if detail else {
                    "bean": {
                        "items": [value],
                        "page": 1,
                        "page_size": 20,
                        "total": 1
                    }
                }
                self.assertEqual(self.call(detail=detail).status_code, 200)
