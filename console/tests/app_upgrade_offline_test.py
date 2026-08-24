# -*- coding: utf-8 -*-
import collections
import os
import sys
from types import ModuleType
from unittest import TestCase
from unittest.mock import patch

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
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
    configuration_module.Configuration = _DummyConfiguration
    rest_module.ApiException = _DummyApiException

    sys.modules["openapi_client"] = openapi_client_module
    sys.modules["openapi_client.configuration"] = configuration_module
    sys.modules["openapi_client.rest"] = rest_module

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402
from django.test import RequestFactory  # noqa: E402

django.setup()

from console.services.upgrade_services import UpgradeService  # noqa: E402
from console.views import app_upgrade as app_upgrade_view  # noqa: E402


class Obj(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class AppUpgradeOfflineTests(TestCase):
    # capability_id: console.app-upgrade.local-offline-detail
    def test_offline_upgrade_info_view_calculates_local_details(self):
        view = app_upgrade_view.AppUpgradeInfoView()
        view.tenant = Obj(tenant_id="tenant-1")
        view.region = Obj(region_name="rainbond")
        view.user = Obj(enterprise_id="enterprise-1")
        view.app = Obj(app_id="app-1")
        app_changes = {"upgrade_info": {"snapshot-template": {"version": "1.0.3"}}}
        changes = [{"type": "env", "name": "LOG_LEVEL"}]

        with patch.dict(os.environ, {
            "DISABLE_DEFAULT_APP_MARKET": "true",
            "DISABLE_CLOUD_MARKET": "",
        }, clear=False), \
                patch.object(app_upgrade_view.upgrade_service, "get_property_changes",
                             return_value=(app_changes, changes)) as get_property_changes:
            response = view.get(RequestFactory().get("/upgrade-info", {
                "upgrade_group_id": 7,
                "version": "1.0.3",
            }), "app-1")

        get_property_changes.assert_called_once_with(view.tenant, view.region, view.user, view.app, 7, "1.0.3")
        self.assertEqual(app_changes, response.data["data"]["bean"])
        self.assertEqual(changes, response.data["data"]["list"])

    # capability_id: console.app-upgrade.remote-offline-market-guard
    def test_remote_upgrade_details_skip_market_lookup_when_offline(self):
        service = UpgradeService()
        component_group = Obj(group_key="cloud-template")
        source = Obj(
            is_install_from_cloud=lambda: True,
            get_market_name=lambda: "goodrain",
        )
        tenant = Obj(enterprise_id="enterprise-1")
        region = Obj(region_name="rainbond")
        user = Obj(enterprise_id="enterprise-1")
        app = Obj(app_id="app-1")

        with patch("console.services.upgrade_services.tenant_service_group_repo.get_component_group",
                   return_value=component_group), \
                patch.object(service, "_app_template_source", return_value=source), \
                patch.object(service, "_app_template") as app_template, \
                patch("console.services.upgrade_services.AppUpgrade") as app_upgrade, \
                patch("console.services.upgrade_services.is_cloud_market_disabled",
                      return_value=True, create=True):
            result = service.get_property_changes(tenant, region, user, app, "7", "1.0.3")

        self.assertEqual(({"upgrade_info": {}}, []), result)
        app_template.assert_not_called()
        app_upgrade.assert_not_called()

    def test_local_upgrade_details_still_load_template_when_offline(self):
        service = UpgradeService()
        component_group = Obj(group_key="snapshot-template")
        source = Obj(
            is_install_from_cloud=lambda: False,
            get_market_name=lambda: None,
        )
        tenant = Obj(enterprise_id="enterprise-1")
        region = Obj(region_name="rainbond")
        user = Obj(enterprise_id="enterprise-1")
        app = Obj(app_id="app-1")
        app_template = {"apps": []}
        app_upgrade_result = Obj(
            app_property_changes={"upgrade_info": {
                "snapshot-template": {}
            }},
            changes=lambda: [{
                "type": "port"
            }],
        )

        with patch("console.services.upgrade_services.tenant_service_group_repo.get_component_group",
                   return_value=component_group), \
                patch.object(service, "_app_template_source", return_value=source), \
                patch.object(service, "_app_template", return_value=app_template) as load_template, \
                patch("console.services.upgrade_services.AppUpgrade", return_value=app_upgrade_result) as app_upgrade, \
                patch("console.services.upgrade_services.is_cloud_market_disabled",
                      return_value=True, create=True):
            result = service.get_property_changes(tenant, region, user, app, "7", "1.0.3")

        load_template.assert_called_once_with("enterprise-1", "snapshot-template", "1.0.3", source)
        app_upgrade.assert_called_once()
        self.assertEqual((app_upgrade_result.app_property_changes, [{"type": "port"}]), result)
