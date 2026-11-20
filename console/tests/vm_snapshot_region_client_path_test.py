# -*- coding: utf-8 -*-
# capability_id: console.vm-snapshot.region-client-path-validation
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from types import SimpleNamespace
from unittest import TestCase, mock

import urllib3

from console.tests.vm_snapshot_region_client_test import ServiceHandleException, RegionInvokeApi, settings


class VMSnapshotRegionClientPathTestCase(TestCase):
    def setUp(self):
        self.observed = []
        self.response_status = 200
        self.response_body = {"bean": {"snapshot_name": "point-a", "finalized": False}}
        fixture = self

        class Handler(BaseHTTPRequestHandler):
            def handle_request(self):
                body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
                fixture.observed.append((self.command, self.path, json.loads(body) if body else None))
                data = json.dumps(fixture.response_body).encode("utf-8")
                self.send_response(fixture.response_status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            do_GET = handle_request
            do_POST = handle_request
            do_DELETE = handle_request

            def log_message(self, *_args):
                pass

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        self.thread.start()
        self.addCleanup(self.close_server)
        self.pool = urllib3.PoolManager()
        self.addCleanup(self.pool.clear)
        self.client = RegionInvokeApi()
        self.origin = "http://127.0.0.1:{}".format(self.server.server_port)
        self.access = mock.patch.object(self.client, "_RegionInvokeApi__get_region_access_info", return_value=(self.origin, ""))
        self.access_mock = self.access.start()
        self.addCleanup(self.access.stop)
        self.tenant = SimpleNamespace(region_tenant_name="fixed-team")
        patches = [
            mock.patch.object(self.client, "_RegionInvokeApi__get_tenant_region_info", return_value=self.tenant),
            mock.patch.object(self.client, "get_client", return_value=self.pool),
            mock.patch.dict(settings.MODULES, {"RegionToken": False}),
            mock.patch("www.apiclient.regionapibaseclient.region_repo.get_region_by_region_name",
                       return_value=SimpleNamespace(region_name="local")),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def close_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.assertFalse(self.thread.is_alive())

    def test_invalid_snapshot_names_never_reach_real_http_transport(self):
        names = (None, "", ".", "..", "../point", "point/..", "point/a", "point\\a", "%2e%2e", "%252e%252e",
                 "point?delete", "point#delete", "point\n", "point\r\n", " point", "point ", "UPPER", "point_a",
                 "-point", "point-", ".point", "point.", "point..a", "a.-b", "a-.b", "快照", "a" * 254,
                 42, True, b"point-a", [], {})
        for name in names:
            calls = [lambda: self.client.get_vm_snapshot("local", "console-team", "component", name),
                     lambda: self.client.delete_vm_snapshot("local", "console-team", "component", name,
                                                            {"operation_id": "op-a"})]
            calls.extend(lambda action=action: self.client.vm_snapshot_action("local", "console-team", "component", name,
                                                                              action, {"operation_id": "op-a"})
                         for action in ("halt", "create", "resume", "finalize", "cancel", "delete"))
            for invoke in calls:
                with self.subTest(name=name, entry=invoke):
                    with self.assertRaises(ServiceHandleException) as raised:
                        invoke()
                    self.assertEqual(raised.exception.status_code, 400)
                    self.assertEqual(raised.exception.msg, "invalid VM snapshot name")
                    self.assertEqual(self.observed, [])
        self.access_mock.assert_not_called()

    def test_backend_valid_names_keep_exact_real_request_paths(self):
        for name in ("point-a", "point.a-1", "0", "a" * 253):
            with self.subTest(name=name):
                response, _body = self.client.get_vm_snapshot("local", "console-team", "component", name)
                self.assertEqual(response.status, 200)
                self.assertEqual(self.observed[-1],
                                 ("GET", "/v2/tenants/fixed-team/services/component/vm-snapshots/" + name, None))
        payload = {"operation_id": "op-a", "request_id": "ack-a", "core_hash": "a" * 64}
        for action in ("halt", "create", "resume", "finalize", "cancel", "delete"):
            self.client.vm_snapshot_action("local", "console-team", "component", "point.a-1", action, payload)
            self.assertEqual(self.observed[-1],
                             ("POST", "/v2/tenants/fixed-team/services/component/vm-snapshots/point.a-1/" + action, payload))

    def test_empty_and_dot_scope_segments_never_reach_real_http_transport(self):
        for invalid in (None, "", ".", ".."):
            for field in ("tenant", "service"):
                self.tenant.region_tenant_name = invalid if field == "tenant" else "fixed-team"
                service = invalid if field == "service" else "component"
                calls = [lambda: self.client.list_vm_snapshots("local", "console-team", service),
                         lambda: self.client.prepare_vm_snapshot("local", "console-team", service, {"name": "point-a"}),
                         lambda: self.client.get_vm_snapshot("local", "console-team", service, "point-a"),
                         lambda: self.client.delete_vm_snapshot("local", "console-team", service, "point-a", {}),
                         lambda: self.client.vm_snapshot_action("local", "console-team", service, "point-a", "halt", {})]
                for invoke in calls:
                    with self.subTest(field=field, value=invalid):
                        with self.assertRaises(ServiceHandleException) as raised:
                            invoke()
                        self.assertEqual(raised.exception.status_code, 400)
                        self.assertEqual(self.observed, [])

    def test_real_409_keeps_error_and_real_202_delete_remains_pending(self):
        self.response_status = 409
        self.response_body = {
            "msg": "vm_restore_conflict", "bean": {"error": {"code": "vm_restore_conflict", "retryable": False}}
        }
        response, body = self.client.get_vm_snapshot("local", "console-team", "component", "point-a")
        self.assertEqual(response.status, 409)
        self.assertEqual(body, self.response_body)
        self.response_status = 202
        self.response_body = {"bean": {"finalized": True, "phase": "deleting"}}
        payload = {"operation_id": "op-a"}
        response, body = self.client.delete_vm_snapshot("local", "console-team", "component", "point-a", payload)
        self.assertEqual(response.status, 202)
        self.assertEqual(body, self.response_body)
        self.assertEqual(self.observed[-1],
                         ("DELETE", "/v2/tenants/fixed-team/services/component/vm-snapshots/point-a", payload))
