# -*- coding: utf-8 -*-
import json
from types import SimpleNamespace
from unittest import mock

from django.test import SimpleTestCase, override_settings

from console.exception.main import ServiceHandleException
from www.apiclient.regionapi import RegionInvokeApi


class AIEnginePlatformClientTests(SimpleTestCase):
    # capability_id: console.ai-engine.platform-secret-client
    def setUp(self):
        self.api = RegionInvokeApi()
        self.value = "a" * 64
        self.region = SimpleNamespace(region_name="r", enterprise_id="e", url="https://region.example", token="Token fixture")
        self.config = SimpleNamespace(verify_ssl=False, cert_file="client.pem", key_file="client.key")
        self.response = mock.Mock(status=200)
        self.response.read.return_value = json.dumps({"bean": {"token": self.value}}).encode()
        self.client = mock.Mock()
        self.client.request.return_value = self.response
        for target, value in (("get_region_info", self.region), ("get_enterprise_region_info", self.region),
                              ("_RegionInvokeApi__get_region_access_info_by_enterprise_id", (self.region.url, "Token fixture")),
                              ("_RegionInvokeApi__get_tenant_region_info",
                               SimpleNamespace(region_tenant_name="mapped-team",
                                               region_tenant_id="mapped-id")), ("create_client", self.client)):
            patcher = mock.patch.object(self.api, target, return_value=value)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = mock.patch("www.apiclient.regionapi.Configuration", return_value=self.config)
        patcher.start()
        self.addCleanup(patcher.stop)

    @override_settings(MODULES={"RegionToken": False})
    def test_bootstrap_supports_tokenless_mtls_and_verifies_peer(self):
        self.region.token = None
        self.api._RegionInvokeApi__get_region_access_info_by_enterprise_id.return_value = (self.region.url, None)
        with mock.patch.dict("os.environ", {"REGION_TOKEN": ""}):
            self.assertEqual(self.api.bootstrap_ai_engine_platform_token("e", "r"), self.value)
        self.assertTrue(self.config.verify_ssl)
        args, options = self.client.request.call_args
        self.assertEqual(args, ("POST", self.region.url + "/v2/platform/plugins/rainbond-ai-engine/platform-token"))
        self.assertNotIn("Authorization", options["headers"])
        self.assertIs(options["retries"], False)
        self.assertIs(options["redirect"], False)
        self.response.read.assert_called_once_with(4097)
        self.assertTrue(self.response.enforce_content_length)
        self.client.clear.assert_called_once_with()

    def test_bootstrap_uses_existing_token_fallback_and_never_accepts_foreign_region(self):
        self.region.token = None
        self.api._RegionInvokeApi__get_region_access_info_by_enterprise_id.return_value = (self.region.url, None)
        with mock.patch.dict("os.environ", {"REGION_TOKEN": "Token fixture-fallback"}):
            self.assertEqual(self.api.bootstrap_ai_engine_platform_token("e", "r"), self.value)
        self.assertEqual(self.client.request.call_args.kwargs["headers"]["Authorization"], "Token fixture-fallback")
        self.api.get_enterprise_region_info.return_value = None
        self.client.request.reset_mock()
        with self.assertRaises(ServiceHandleException):
            self.api.bootstrap_ai_engine_platform_token("foreign", "r")
        self.client.request.assert_not_called()

    def test_bootstrap_rejects_http_missing_identity_and_malformed_or_oversized_results_without_echo(self):
        for value in ("", "B" * 64, "x" * 63, "fixture-sensitive-body"):
            self.response.read.return_value = json.dumps({"bean": {"token": value}}).encode()
            with self.assertRaises(ServiceHandleException) as caught:
                self.api.bootstrap_ai_engine_platform_token("e", "r")
            if value:
                self.assertNotIn(value, str(caught.exception))
            self.assertEqual(caught.exception.status_code, 503)
        self.response.read.return_value = b"x" * 4097
        with self.assertRaises(ServiceHandleException):
            self.api.bootstrap_ai_engine_platform_token("e", "r")
        self.region.url = "http://region.example"
        self.region.token = None
        self.api._RegionInvokeApi__get_region_access_info_by_enterprise_id.return_value = (self.region.url, None)
        self.client.request.reset_mock()
        with self.assertRaises(ServiceHandleException):
            self.api.bootstrap_ai_engine_platform_token("e", "r")
        self.client.request.assert_not_called()
        self.region.url = "https://region.example"
        self.api._RegionInvokeApi__get_region_access_info_by_enterprise_id.return_value = (self.region.url, None)
        self.config.cert_file = self.config.key_file = None
        with mock.patch.dict("os.environ", {"REGION_TOKEN": ""}), self.assertRaises(ServiceHandleException):
            self.api.bootstrap_ai_engine_platform_token("e", "r")
        self.client.request.assert_not_called()

    def test_existing_env_api_writes_use_verified_private_channel_and_fixed_env(self):
        for create, method in ((True, "POST"), (False, "PUT")):
            self.response.read.return_value = b"{}"
            self.api.set_ai_engine_platform_env("e", "r", "team-a", "backend", self.value, create=create)
            args, options = self.client.request.call_args
            self.assertEqual(args, (method, self.region.url + "/v2/tenants/mapped-team/services/backend/env"))
            body = json.loads(options["body"])
            self.assertEqual(body["env_name"], "AI_ENGINE_PLATFORM_TOKEN")
            self.assertEqual(body["env_value"], self.value)
            self.assertEqual(body["tenant_id"], "mapped-id")
            self.assertEqual(body["scope"], "inner")
            self.assertTrue(body["is_change"])
            self.assertTrue(self.config.verify_ssl)

    def test_env_writer_rejects_path_escape_and_never_echoes_region_errors(self):
        with self.assertRaises(ServiceHandleException):
            self.api.set_ai_engine_platform_env("e", "r", "team-a", "../other", self.value)
        self.client.request.assert_not_called()
        self.response.status = 503
        self.response.read.return_value = json.dumps({"msg": "fixture-sensitive-body", "bean": {"token": self.value}}).encode()
        with self.assertRaises(ServiceHandleException) as caught:
            self.api.set_ai_engine_platform_env("e", "r", "team-a", "backend", self.value)
        self.assertNotIn("fixture-sensitive-body", str(caught.exception))
        self.assertNotIn(self.value, str(caught.exception))

    def test_partial_create_can_be_reconciled_without_replaying_the_create(self):
        exists = mock.Mock(status=409)
        exists.read.return_value = b'{"msg":"record already exist"}'
        updated = mock.Mock(status=200)
        updated.read.return_value = b"{}"
        self.client.request.side_effect = [exists, updated]
        self.api.set_ai_engine_platform_env("e", "r", "team-a", "backend", self.value, create=True)
        self.assertEqual([call.args[0] for call in self.client.request.call_args_list], ["POST", "PUT"])
        for response in (exists, updated):
            response.close.assert_called_once_with()
            response.release_conn.assert_called_once_with()
