# -*- coding: utf-8 -*-
import json
import sys
from contextlib import ExitStack
from types import ModuleType, SimpleNamespace
from unittest import mock

if "openapi_client" not in sys.modules:
    openapi_client_module = ModuleType("openapi_client")
    configuration_module = ModuleType("openapi_client.configuration")
    rest_module = ModuleType("openapi_client.rest")

    class _Configuration(object):
        def __init__(self):
            self.host = ""
            self.api_key = {}

    configuration_module.Configuration = _Configuration
    rest_module.ApiException = type("ApiException", (Exception, ), {})
    openapi_client_module.ApiClient = object
    openapi_client_module.MarketOpenapiApi = object
    openapi_client_module.configuration = configuration_module
    openapi_client_module.rest = rest_module
    sys.modules["openapi_client"] = openapi_client_module
    sys.modules["openapi_client.configuration"] = configuration_module
    sys.modules["openapi_client.rest"] = rest_module

from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from console.views.platform_resources.cluster import (
    PersistentVolumeDetailView,
    PersistentVolumesView,
    PlatformResourceDetailView,
    PlatformResourcesView,
    PlatformResourceTypesView,
    StorageClassDetailView,
    StorageClassesView,
    StorageConfigView,
)


class PlatformResourcesAuthorizationTests(SimpleTestCase):
    _METHOD_CASES = (
        ("platform resource types get", PlatformResourceTypesView, "get", False),
        ("platform resources get", PlatformResourcesView, "get", False),
        ("platform resources post", PlatformResourcesView, "post", False),
        ("platform resource detail get", PlatformResourceDetailView, "get", True),
        ("platform resource detail put", PlatformResourceDetailView, "put", True),
        ("platform resource detail delete", PlatformResourceDetailView, "delete", True),
        ("storage classes get", StorageClassesView, "get", False),
        ("storage classes post", StorageClassesView, "post", False),
        ("storage class detail delete", StorageClassDetailView, "delete", True),
        ("persistent volumes get", PersistentVolumesView, "get", False),
        ("persistent volumes post", PersistentVolumesView, "post", False),
        ("persistent volume detail delete", PersistentVolumeDetailView, "delete", True),
        ("storage config get", StorageConfigView, "get", False),
        ("storage config put", StorageConfigView, "put", False),
    )

    def setUp(self):
        self.factory = APIRequestFactory()

    def _user(self, enterprise_id="eid"):
        return SimpleNamespace(
            user_id=1,
            nick_name="user",
            enterprise_id=enterprise_id,
            is_authenticated=True,
        )

    def _request(self, method):
        path = "/console/enterprise/eid/platform/regions/region/platform-resources"
        if method in ("post", "put"):
            return getattr(self.factory, method)(
                path,
                data=json.dumps({"default_storage_class": "standard"}),
                content_type="application/json",
            )
        return getattr(self.factory, method)(path)

    def _dispatch(self,
                  view_class,
                  method,
                  is_admin,
                  eid="eid",
                  region_binding=mock.sentinel.region_binding,
                  include_name=False):
        request = self._request(method)
        force_authenticate(request, user=self._user())

        with ExitStack() as stack:
            enterprise_filter = stack.enter_context(mock.patch("console.views.base.TenantEnterprise.objects.filter"))
            stack.enter_context(mock.patch("console.views.base.enterprise_user_perm_repo.is_admin", return_value=is_admin))
            stack.enter_context(mock.patch("console.views.base.user_services.list_roles", return_value=[]))
            stack.enter_context(mock.patch("console.views.base.perms.list_enterprise_perm_codes_by_roles", return_value=[]))
            region_lookup = stack.enter_context(
                mock.patch(
                    "console.repositories.region_repo.region_repo.get_enterprise_region_by_region_name",
                    return_value=region_binding,
                ))
            region_api = stack.enter_context(mock.patch("console.views.platform_resources.cluster.region_api"))
            console_config = stack.enter_context(mock.patch("console.views.platform_resources.cluster.ConsoleSysConfig"))

            enterprise_filter.return_value.first.return_value = SimpleNamespace(enterprise_id="eid")
            region_api.get_cluster_resource.return_value = (200, {"bean": {}})
            region_api.post_cluster_resource.return_value = (200, {"bean": {}})
            region_api.put_cluster_resource.return_value = (200, {"bean": {}})
            console_config.objects.filter.return_value.first.return_value = None

            kwargs = {"eid": eid, "region": "region"}
            if include_name:
                kwargs["name"] = "resource-name"
            response = view_class.as_view()(request, **kwargs)

        return response, region_api, region_lookup

    def test_non_admin_cannot_call_any_platform_resource_method(self):
        for label, view_class, method, include_name in self._METHOD_CASES:
            with self.subTest(endpoint=label):
                response, region_api, region_lookup = self._dispatch(
                    view_class,
                    method,
                    is_admin=False,
                    include_name=include_name,
                )

                self.assertEqual(response.status_code, 403)
                self.assertEqual(region_api.mock_calls, [])
                region_lookup.assert_not_called()

    def test_admin_cannot_use_another_enterprise_id(self):
        response, region_api, region_lookup = self._dispatch(
            PlatformResourceTypesView,
            "get",
            is_admin=True,
            eid="another-enterprise",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(region_api.mock_calls, [])
        region_lookup.assert_not_called()

    def test_admin_cannot_use_a_region_not_bound_to_the_enterprise(self):
        response, region_api, region_lookup = self._dispatch(
            PlatformResourceTypesView,
            "get",
            is_admin=True,
            region_binding=None,
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(region_api.mock_calls, [])
        region_lookup.assert_called_once_with("eid", "region")

    def test_admin_can_access_a_region_bound_to_the_enterprise(self):
        response, region_api, region_lookup = self._dispatch(
            PlatformResourceTypesView,
            "get",
            is_admin=True,
        )

        self.assertEqual(response.status_code, 200)
        region_lookup.assert_called_once_with("eid", "region")
        region_api.get_cluster_resource.assert_called_once_with("region", "platform-resources/types")
