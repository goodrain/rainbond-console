# -*- coding: utf-8 -*-
import os
import sys
import collections
import collections.abc
from types import ModuleType
from unittest import TestCase
from unittest.mock import patch

try:
    from _pytest.fixtures import FixtureRequest, SubRequest

    if not hasattr(FixtureRequest, "funcargnames"):
        FixtureRequest.funcargnames = property(lambda self: self.fixturenames)
    if not hasattr(SubRequest, "funcargnames"):
        SubRequest.funcargnames = property(lambda self: self.fixturenames)
except Exception:
    pass

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

sys.path.insert(
    0,
    os.path.abspath(os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "src",
        "openapi-client",
    )),
)
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
if "openapi_client" not in sys.modules:
    openapi_client_module = ModuleType("openapi_client")
    configuration_module = ModuleType("openapi_client.configuration")
    rest_module = ModuleType("openapi_client.rest")

    class _DummyConfiguration(object):
        def __init__(self):
            self.client_side_validation = False
            self.host = ""
            self.api_key = {}

    class _DummyApiException(Exception):
        status = 500
        body = ""

    openapi_client_module.ApiClient = object
    openapi_client_module.MarketOpenapiApi = object
    openapi_client_module.V1AppModelCreateRequest = dict
    openapi_client_module.V1CreateAppPaaSVersionRequest = dict
    openapi_client_module.configuration = configuration_module
    openapi_client_module.rest = rest_module
    configuration_module.Configuration = _DummyConfiguration
    rest_module.ApiException = _DummyApiException
    sys.modules["openapi_client"] = openapi_client_module
    sys.modules["openapi_client.configuration"] = configuration_module
    sys.modules["openapi_client.rest"] = rest_module

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from console.exception.main import ServiceHandleException  # noqa: E402


class Obj(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


# capability_id: console.groupcopy.package-build-guard
class GroupAppCopyServiceTests(TestCase):

    @patch(
        "console.services.groupcopy_service.app_service.create_service_alias",
        return_value="alias-new")
    @patch(
        "console.services.groupcopy_service.groupapp_backup_service."
        "get_group_app_metadata")
    def test_get_modify_group_metadata_rejects_package_build(
            self, mock_get_metadata, _):
        from console.services.groupcopy_service import groupapp_copy_service

        mock_get_metadata.return_value = (
            0,
            {
                "compose_group_info": None,
                "group_info": {},
                "plugin_info": {},
                "app_config_group_info": [],
                "service_group_relation": [{"service_id": "svc-pkg"}],
                "apps": [
                    {
                        "service_base": {
                            "service_id": "svc-pkg",
                            "service_source": "package_build",
                            "service_cname": "uploaded-jar",
                            "k8s_component_name": "uploaded-jar",
                        },
                        "service_relation": [],
                        "service_mnts": [],
                        "service_plugin_config": [],
                    }
                ],
                "compose_service_relation": None,
            },
        )

        with self.assertRaises(ServiceHandleException) as ctx:
            groupapp_copy_service.get_modify_group_metadata(
                Obj(tenant_id="team-old"),
                "rainbond",
                Obj(tenant_id="team-new"),
                "rainbond",
                1,
                ["svc-pkg"],
                {},
            )

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("package_build", ctx.exception.msg)
        self.assertIn("uploaded-jar", ctx.exception.msg_show)

    @patch(
        "console.services.groupcopy_service.app_service.create_service_alias",
        return_value="alias-new")
    @patch(
        "console.services.groupcopy_service.groupapp_backup_service."
        "get_group_app_metadata")
    def test_get_modify_group_metadata_allows_source_code(
            self, mock_get_metadata, _):
        from console.services.groupcopy_service import groupapp_copy_service

        mock_get_metadata.return_value = (
            64,
            {
                "compose_group_info": None,
                "group_info": {},
                "plugin_info": {},
                "app_config_group_info": [],
                "service_group_relation": [{"service_id": "svc-code"}],
                "apps": [
                    {
                        "service_base": {
                            "service_id": "svc-code",
                            "service_source": "source_code",
                            "service_cname": "source-code",
                            "k8s_component_name": "source-code",
                        },
                        "service_relation": [],
                        "service_mnts": [],
                        "service_plugin_config": [],
                    }
                ],
                "compose_service_relation": None,
            },
        )

        metadata, change_services_map = (
            groupapp_copy_service.get_modify_group_metadata(
                Obj(tenant_id="team-old"),
                "rainbond",
                Obj(tenant_id="team-new"),
                "rainbond",
                1,
                ["svc-code"],
                {},
            )
        )

        self.assertEqual(
            metadata["apps"][0]["service_base"]["service_id"], "svc-code")
        self.assertIn("svc-code", change_services_map)
