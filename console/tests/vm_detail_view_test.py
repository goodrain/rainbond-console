# -*- coding: utf-8 -*-
import collections
import os
import sys
from types import ModuleType, SimpleNamespace
from unittest import TestCase, mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
openapi_client_module = ModuleType("openapi_client")
openapi_client_module.ApiClient = lambda configuration=None: SimpleNamespace(configuration=configuration)
openapi_client_module.MarketOpenapiApi = lambda client=None: SimpleNamespace(client=client)

openapi_client_configuration = ModuleType("openapi_client.configuration")


class _OpenAPIConfiguration(object):
    def __init__(self):
        self.client_side_validation = False
        self.host = ""
        self.api_key = {}


openapi_client_configuration.Configuration = _OpenAPIConfiguration

openapi_client_rest = ModuleType("openapi_client.rest")


class _ApiException(Exception):
    def __init__(self, status=400, body=""):
        super().__init__(body)
        self.status = status
        self.body = body


openapi_client_rest.ApiException = _ApiException

sys.modules.setdefault("openapi_client", openapi_client_module)
sys.modules.setdefault("openapi_client.configuration", openapi_client_configuration)
sys.modules.setdefault("openapi_client.rest", openapi_client_rest)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402
from rest_framework.test import APIRequestFactory  # noqa: E402

django.setup()

from console.views import app_overview  # noqa: E402
from console.views.app_overview import AppDetailView  # noqa: E402


class AppVMDetailViewTests(TestCase):
    # capability_id: console.vm-overview.vnc-url-plugin-fallback

    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = AppDetailView()
        self.view.tenant = SimpleNamespace(
            tenant_id="tenant-a",
            tenant_name="demo-team",
            namespace="demo-ns",
            enterprise_id="eid-demo"
        )
        self.view.service = SimpleNamespace(
            tenant_id="tenant-a",
            service_id="service-a",
            service_alias="demo-vm",
            service_cname="demo-vm",
            k8s_component_name="demo-vm",
            service_region="demo-region",
            extend_method="vm",
            service_source="manual",
            to_dict=lambda: {"service_id": "service-a", "service_alias": "demo-vm"}
        )
        self.view.request = None

    # capability_id: console.vm-overview.vnc-url-plugin-fallback
    def test_get_builds_vm_vnc_url_from_plugin_fallback_when_query_param_missing(self):
        request = self.view.initialize_request(
            self.factory.get("/console/teams/demo-team/apps/demo-vm/detail")
        )
        self.view.request = request

        with mock.patch("console.views.app_overview.group_service.get_services_group_name",
                        return_value={"service-a": {"group_name": "demo-app", "group_id": 1, "k8s_app": "app-k8s"}}), \
                mock.patch("console.views.app_overview.volume_repo.get_service_volumes_with_config_file", return_value=[]), \
                mock.patch("console.views.app_overview.ws_service.get_event_log_ws", return_value="ws://events"), \
                mock.patch("console.views.app_overview.vms.get_vm_current_pod_ip", return_value="10.0.0.9"), \
                mock.patch("console.views.app_overview.vms.get_vm_profile", return_value={"runtime": {}}) as profile_mock, \
                mock.patch.object(app_overview, "rbd_plugin_service",
                                  SimpleNamespace(get_vm_plugin_url=mock.Mock(
                                      return_value="https://console.example.com:30001"
                                  )),
                                  create=True):
            response = self.view.get(request)

        expected = (
            "https://console.example.com:30001/vnc_lite.html?path="
            "k8s/apis/subresources.kubevirt.io/v1alpha3/namespaces/demo-ns/"
            "virtualmachineinstances/app-k8s-demo-vm/vnc"
        )
        self.assertEqual(expected, response.data["data"]["bean"]["vm_url"])
        profile_mock.assert_called_once_with(
            self.view.service,
            current_pod_ip="10.0.0.9",
            connections={
                "vnc_url": expected,
                "console_url": ""
            }
        )
