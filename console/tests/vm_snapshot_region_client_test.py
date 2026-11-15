# -*- coding: utf-8 -*-
# capability_id: console.vm-snapshot.region-client
import json
import os
from types import SimpleNamespace
from unittest import TestCase, mock

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.test_settings")

import django  # noqa: E402
from django.conf import settings  # noqa: E402

django.setup()

from console.exception.main import ServiceHandleException  # noqa: E402
from www.apiclient.regionapi import RegionInvokeApi  # noqa: E402


class VMSnapshotRegionClientTestCase(TestCase):
    def setUp(self):
        self.client = RegionInvokeApi()
        self.access = mock.patch.object(self.client,
                                        "_RegionInvokeApi__get_region_access_info",
                                        return_value=("https://region.invalid", mock.sentinel.server_authority))
        self.tenant = mock.patch.object(self.client,
                                        "_RegionInvokeApi__get_tenant_region_info",
                                        return_value=SimpleNamespace(region_tenant_name="region-team"))
        self.access_mock = self.access.start()
        self.tenant.start()
        self.addCleanup(self.access.stop)
        self.addCleanup(self.tenant.stop)

    def response(self, status=202, **overrides):
        bean = {"operation_id": "op-a", "snapshot_name": "point-a", "finalized": False}
        bean.update(overrides)
        return status, json.dumps({"bean": bean}).encode("utf-8")

    def test_prepare_preserves_accepted_response_and_exact_request(self):
        payload = {"name": "point-a", "request_id": "op-a", "manifest_id": "manifest-a", "power_after": "previous"}
        with mock.patch.object(self.client, "_request", return_value=self.response()) as request:
            response, body = self.client.prepare_vm_snapshot("region", "console-team", "gr-app", payload)
        self.assertEqual(response.status, 202)
        self.assertFalse(body["bean"]["finalized"])
        self.assertEqual(body["bean"]["operation_id"], "op-a")
        self.assertEqual(request.call_args.args,
                         ("https://region.invalid/v2/tenants/region-team/services/gr-app/vm-snapshots", "POST"))
        self.assertEqual(json.loads(request.call_args.kwargs["body"]), payload)
        self.assertEqual(request.call_args.kwargs["timeout"], 15)
        self.assertEqual(request.call_args.kwargs["retries"], 0)

    def test_list_encodes_path_segments_and_get_preserves_valid_name(self):
        with mock.patch.object(self.client, "_request", return_value=self.response(200)) as request:
            self.client.list_vm_snapshots("region", "console-team", "gr/app", page=2, page_size=15)
            self.assertEqual(
                request.call_args.args,
                ("https://region.invalid/v2/tenants/region-team/services/gr%2Fapp/vm-snapshots?page=2&page_size=15", "GET"))
            self.client.get_vm_snapshot("region", "console-team", "gr-app", "point.a")
            self.assertEqual(request.call_args.args,
                             ("https://region.invalid/v2/tenants/region-team/services/gr-app/vm-snapshots/point.a", "GET"))

    def test_actions_keep_durable_proof_and_pending_bean(self):
        payload = {
            "operation_id": "op-a",
            "core_hash": "a" * 64,
            "request_id": "resume-a",
            "manifest_document_hash": "b" * 64,
            "native_proof_hash": "c" * 64,
            "ack_kind": "ready"
        }
        with mock.patch.object(self.client, "_request", return_value=self.response(202, phase="resuming")) as request:
            for action in ("halt", "create", "resume", "finalize", "cancel", "delete"):
                result, body = self.client.vm_snapshot_action("region", "console-team", "gr-app", "point-a", action, payload)
                self.assertEqual(result.status, 202)
                self.assertEqual(body["bean"]["phase"], "resuming")
                self.assertTrue(request.call_args.args[0].endswith("/point-a/" + action))
                self.assertEqual(request.call_args.args[1], "POST")
                self.assertEqual(json.loads(request.call_args.kwargs["body"]), payload)

    def test_delete_uses_body_and_keeps_pending_even_if_creation_finalized(self):
        payload = {"operation_id": "op-a", "request_id": "delete-a", "core_hash": "a" * 64}
        with mock.patch.object(self.client, "_request", return_value=self.response(202, finalized=True,
                                                                                   phase="deleting")) as request:
            response, body = self.client.delete_vm_snapshot("region", "console-team", "gr-app", "point-a", payload)
        self.assertEqual(response.status, 202)
        self.assertEqual(body["bean"]["phase"], "deleting")
        self.assertTrue(request.call_args.args[0].endswith("/point-a"))
        self.assertEqual(request.call_args.args[1], "DELETE")
        self.assertEqual(json.loads(request.call_args.kwargs["body"]), payload)

    def test_invalid_action_and_pagination_do_not_start_a_region_request(self):
        with mock.patch.object(self.client, "_request") as request:
            for action in ("../start", "restart", "", "DELETE"):
                with self.assertRaises(ServiceHandleException):
                    self.client.vm_snapshot_action("region", "console-team", "gr-app", "point-a", action, {})
            for page, size in ((0, 20), (1, 101), (True, 20), (1, False)):
                with self.assertRaises(ServiceHandleException):
                    self.client.list_vm_snapshots("region", "console-team", "gr-app", page=page, page_size=size)
            request.assert_not_called()
            self.access_mock.assert_not_called()

    def test_dependency_errors_preserve_status_and_do_not_become_success(self):
        error = {"msg": "vm_snapshot_dependency_unavailable", "bean": {"error": {"retryable": True}}}
        with mock.patch.object(self.client, "_request", return_value=(503, json.dumps(error).encode("utf-8"))):
            response, body = self.client.get_vm_snapshot("region", "console-team", "gr-app", "point-a")
        self.assertEqual(response.status, 503)
        self.assertEqual(body, error)

    def test_snapshot_requests_do_not_mutate_shared_default_headers(self):
        before = dict(self.client.default_headers)
        with mock.patch.object(self.client, "_request", return_value=self.response(200)):
            self.client.get_vm_snapshot("region", "console-team", "gr-app", "point-a")
        self.assertEqual(self.client.default_headers, before)

    def test_each_snapshot_call_uses_its_server_owned_authority(self):
        self.client.default_headers["Authorization"] = mock.sentinel.unrelated_authority
        with mock.patch.dict(settings.MODULES, {"RegionToken": True}), \
                mock.patch.object(self.client, "_request", return_value=self.response(200)) as request:
            self.client.get_vm_snapshot("region", "console-team", "gr-app", "point-a")
        headers = request.call_args.kwargs["headers"]
        self.assertIs(headers["Authorization"], mock.sentinel.server_authority)
        self.assertIsNot(headers, self.client.default_headers)
        self.assertIs(self.client.default_headers["Authorization"], mock.sentinel.unrelated_authority)

    def test_existing_create_call_retains_response_and_body_contract(self):
        payload = {"name": "legacy-point"}
        with mock.patch.object(self.client, "_set_headers"), \
                mock.patch.object(self.client, "_request", return_value=self.response()) as request:
            response, body = self.client.create_vm_snapshot("region", "console-team", "gr-app", payload)
        self.assertEqual(response.status, 202)
        self.assertEqual(json.loads(request.call_args.kwargs["body"]), payload)
        self.assertEqual(body["bean"]["snapshot_name"], "point-a")
