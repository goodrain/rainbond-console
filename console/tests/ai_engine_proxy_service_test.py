# -*- coding: utf-8 -*-
import importlib.util
import json
import sys
import types
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock

REPO_ROOT = Path(__file__).resolve().parents[2]


class ServiceHandleException(Exception):

    def __init__(self, msg, msg_show=None, status_code=400, **kwargs):
        super(ServiceHandleException, self).__init__(msg)
        self.msg = msg
        self.msg_show = msg_show or msg
        self.status_code = status_code


class HttpResponse(object):

    def __init__(self, body="", status=200):
        self.content = body.encode("utf-8")
        self.status_code = status


class Response(object):

    def __init__(self, data, status=200):
        self.data = data
        self.status_code = status


def _install_module(name, **attrs):
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


def _load_module(name, relative_path):
    spec = importlib.util.spec_from_file_location(
        name, str(REPO_ROOT / relative_path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class AIEngineProxyContractTests(TestCase):
    module_names = (
        "console.exception.main",
        "openapi.services.ai_engine_proxy_service",
        "openapi.views.ai_engine_proxy",
        "rest_framework.permissions",
        "rest_framework.request",
        "rest_framework.response",
        "rest_framework.views",
        "www.apiclient.regionapi",
    )

    def setUp(self):
        self.region_api = Mock()
        _install_module("console.exception.main",
                        ServiceHandleException=ServiceHandleException)
        _install_module("www.apiclient.regionapi",
                        RegionInvokeApi=Mock(return_value=self.region_api))
        _install_module("rest_framework.permissions", AllowAny=object)
        _install_module("rest_framework.request", Request=object)
        _install_module("rest_framework.response", Response=Response)
        _install_module("rest_framework.views", APIView=object)
        self.service_module = _load_module(
            "openapi.services.ai_engine_proxy_service",
            "openapi/services/ai_engine_proxy_service.py",
        )
        self.view_module = _load_module(
            "openapi.views.ai_engine_proxy",
            "openapi/views/ai_engine_proxy.py",
        )
        self.service = self.service_module.AIEngineProxyService()
        self.request = Mock(method="POST")

    def tearDown(self):
        for module_name in self.module_names:
            sys.modules.pop(module_name, None)

    def test_proxy_request_disables_region_api_retries(self):
        expected_response = HttpResponse(status=200)
        self.region_api.proxy.return_value = expected_response

        response = self.service.proxy_request(
            self.request,
            "region-1",
            "v1/chat/completions",
            "trace_id=1",
        )

        self.assertIs(response, expected_response)
        self.region_api.proxy.assert_called_once_with(
            self.request,
            "/v2/platform/backend/plugins/rainbond-ai-engine/v1/chat/completions?trace_id=1",
            "region-1",
            requests_args={"retries": False},
        )

    def test_proxy_request_keeps_default_retry_behavior_for_get(self):
        get_request = Mock(method="GET")
        expected_response = HttpResponse(status=200)
        self.region_api.proxy.return_value = expected_response

        response = self.service.proxy_request(get_request, "region-1",
                                              "v1/models")

        self.assertIs(response, expected_response)
        self.region_api.proxy.assert_called_once_with(
            get_request,
            "/v2/platform/backend/plugins/rainbond-ai-engine/v1/models",
            "region-1",
        )

    def test_proxy_request_normalizes_plugin_transport_502(self):
        self.region_api.proxy.return_value = HttpResponse(
            json.dumps({
                "code": 502,
                "msg": "plugin backend unavailable: EOF",
                "plugin": "rainbond-ai-engine",
            }),
            status=502,
        )

        with self.assertRaises(ServiceHandleException) as context:
            self.service.proxy_request(self.request, "region-1",
                                       "v1/chat/completions")

        self.assertEqual(context.exception.status_code, 502)
        self.assertEqual(context.exception.msg,
                         "upstream ai-engine proxy failed")

    def test_proxy_request_preserves_model_originated_502(self):
        model_response = HttpResponse(
            json.dumps({
                "error": {
                    "message": "model is overloaded",
                    "type": "server_error",
                }
            }),
            status=502,
        )
        self.region_api.proxy.return_value = model_response

        response = self.service.proxy_request(self.request, "region-1",
                                              "v1/chat/completions")

        self.assertIs(response, model_response)

    def test_proxy_request_preserves_similar_502_from_another_plugin(self):
        other_plugin_response = HttpResponse(
            json.dumps({
                "code": 502,
                "msg": "plugin backend unavailable: EOF",
                "plugin": "another-plugin",
            }),
            status=502,
        )
        self.region_api.proxy.return_value = other_plugin_response

        response = self.service.proxy_request(self.request, "region-1",
                                              "v1/chat/completions")

        self.assertIs(response, other_plugin_response)

    def test_generated_5xx_error_uses_server_error_type(self):
        response = self.view_module.build_openai_error_response(
            "upstream ai-engine proxy failed", 502)

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.data["error"]["type"], "server_error")
