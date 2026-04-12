# -*- coding: utf-8 -*-
import collections
import os
import sys
from types import ModuleType
from urllib.parse import parse_qs, urlsplit
from unittest import TestCase, mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from console.services.gray_release_service import GrayReleaseService  # noqa: E402


class Obj(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class GrayReleaseRouteUpdateTests(TestCase):
    # capability_id: console.gray-release.update-route-query-params
    def test_update_apisix_route_weights_keeps_service_alias_and_original_route_port_consistent(self):
        service = GrayReleaseService()
        team = Obj(tenant_id="tenant-id", tenant_name="demo-team", namespace="demo-ns")
        app = Obj(ID="internal-app-id", app_id="region-app-id")
        domain = {
            "name": "123test.rainbond.cnp-ps-s-testsvc",
            "match": {
                "hosts": ["test.rainbond.cn"],
                "paths": ["/*"],
            },
            "rules": [],
            "plugins": [],
            "authentication": {},
            "websocket": False,
        }
        original_service = Obj(service_id="origin-svc-id", service_alias="test", service_cname="test")
        new_service = Obj(service_id="gray-svc-id", service_alias="test-2033", service_cname="test")
        new_port = Obj(k8s_service_name="test-2033", container_port=8080)
        original_route_port = Obj(k8s_service_name="test", container_port=80)
        port_filters = [
            mock.Mock(first=mock.Mock(return_value=new_port)),
            mock.Mock(first=mock.Mock(return_value=None)),
            mock.Mock(first=mock.Mock(return_value=original_route_port)),
        ]

        with mock.patch("www.apiclient.regionapi.RegionInvokeApi") as region_api_class, \
                mock.patch("www.models.main.TenantServicesPort.objects.filter", side_effect=port_filters):
            region_api = region_api_class.return_value

            service._update_apisix_route_weights(
                team,
                "demo-region",
                app,
                domain,
                original_service,
                new_service,
                50,
                50,
                False,
            )

        call = region_api.api_gateway_post_proxy.call_args
        path = call[0][2]
        query = parse_qs(urlsplit(path).query)
        self.assertEqual(query.get("service_alias"), ["test"])
        self.assertEqual(query.get("port"), ["80"])
        self.assertEqual(call[1]["service_alias"], "test")
        self.assertEqual(call[1]["port"], "80")
