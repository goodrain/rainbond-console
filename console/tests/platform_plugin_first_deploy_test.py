# -*- coding: utf-8 -*-
import json
import os
import sys
from types import ModuleType
from unittest import TestCase, mock

sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")


class Obj(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class ServiceHandleException(Exception):
    def __init__(self, msg="", msg_show="", status_code=500, **kwargs):
        super(ServiceHandleException, self).__init__(msg_show or msg)
        self.msg = msg
        self.msg_show = msg_show
        self.status_code = status_code


class AppMarket(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class RegionInvokeApi(object):
    class CallApiError(Exception):
        pass


class FirstDeployServiceStub(object):
    DEPLOY_TYPE_APP_MARKET = "app_market"

    def __init__(self):
        self.safe_begin_tracking = mock.Mock(return_value={"key": "first-deploy"})
        self.safe_bind_events = mock.Mock()
        self.safe_mark_failure = mock.Mock()

    @staticmethod
    def build_market_app_context(app, market_app, app_model_key, version, market_name, install_from_cloud,
                                 app_template=None):
        context = {
            "app_id": getattr(app, "ID", ""),
            "app_name": getattr(app, "group_name", ""),
            "market_app_name": getattr(market_app, "app_name", ""),
            "app_model_key": app_model_key,
            "app_model_version": version,
            "market_name": market_name,
            "install_from_cloud": bool(install_from_cloud),
        }
        if app_template:
            context["component_count"] = len(app_template.get("apps") or [])
            if app_template.get("arch"):
                context["template_arch"] = app_template["arch"]
        return context

    @staticmethod
    def build_market_workload_context(app_template=None):
        apps = (app_template or {}).get("apps") or []
        return {"component_count": len(apps)}


def install_stub(module_name, package=False, **attrs):
    module = ModuleType(module_name)
    if package:
        module.__path__ = []
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[module_name] = module
    return module


first_deploy_service = FirstDeployServiceStub()
app_market_service = Obj()
market_app_service = Obj()
region_repo = Obj()

install_stub("console.appstore", package=True)
install_stub("console.appstore.appstore", app_store=Obj())
install_stub("console.exception.main", ServiceHandleException=ServiceHandleException)
install_stub("console.models.main", AppMarket=AppMarket)
install_stub(
    "console.repositories.app",
    PLATFORM_PLUGIN_DEFAULT_URL="https://hub.grapps.cn",
    PLATFORM_PLUGIN_MARKET_DOMAIN="enterprise",
    PLATFORM_PLUGIN_MARKET_NAME="platform-plugin",
    app_market_repo=Obj())
install_stub("console.repositories.group", group_repo=Obj(), tenant_service_group_repo=Obj())
install_stub("console.repositories.region_app", region_app_repo=Obj())
install_stub("console.repositories.region_repo", region_repo=region_repo)
install_stub("console.services.app", app_market_service=app_market_service)
install_stub("console.services.enterprise_first_deploy_service", enterprise_first_deploy_service=first_deploy_service)
install_stub("console.services.group_service", group_service=Obj())
install_stub("console.services.license", license_service=Obj())
install_stub("console.services.market_app", package=True)
install_stub("console.services.market_app.app_upgrade", AppUpgrade=object)
install_stub("console.services.market_app_service", market_app_service=market_app_service)
install_stub("console.services.region_services", region_services=Obj())
install_stub("console.services.team_services", team_services=Obj())
install_stub("console.utils.offline", is_cloud_market_disabled=lambda: False)
install_stub("www.apiclient.regionapi", RegionInvokeApi=RegionInvokeApi)
install_stub("www.models.main", ServiceGroup=object, Tenants=object)

from console.services.platform_plugin_service import platform_plugin_service  # noqa: E402
import console.services.platform_plugin_service as platform_module  # noqa: E402


class PlatformPluginFirstDeployTrackingTests(TestCase):
    def test_install_platform_plugin_reports_first_deploy_tracking(self):
        market_plugins = [{
            "plugin_id": "rainbond-agent",
            "plugin_name": "AI助手",
            "app_level": "free",
            "appKeyID": "agent-app-key",
            "latest_version": "1.0.0",
        }]
        tenant = Obj(tenant_id="team-1", tenant_name="rbd-plugins")
        region = Obj(region_name="rainbond")
        app = Obj(ID=1, group_name="AI助手")
        user = Obj(nick_name="alice")
        market_app = Obj(app_id="app-id", app_name="AI助手")
        app_template = {
            "apps": [{
                "memory": 256,
                "container_cpu": 100,
                "min_node": 1,
            }],
            "arch": "amd64",
        }
        app_version = Obj(app_template=json.dumps(app_template), update_time="", arch="amd64")
        component = Obj(component_id="service-1", service_alias="grservice1")
        component_snapshot = Obj(component=component)

        platform_plugin_service._get_license_bean = mock.Mock(
            return_value={"valid": False, "plugin_mapping": {}, "access_key": ""})
        platform_plugin_service._get_region_arches = mock.Mock(return_value={"amd64"})
        platform_plugin_service._get_market_platform_plugins = mock.Mock(return_value=(Obj(), market_plugins))
        platform_plugin_service._ensure_plugin_team = mock.Mock(return_value=tenant)
        platform_plugin_service._ensure_plugin_app = mock.Mock(return_value=app)
        region_repo.get_enterprise_region_by_region_name = mock.Mock(return_value=region)
        app_market_service.cloud_app_model_to_db_model = mock.Mock(return_value=(market_app, app_version))
        market_app_service._create_tenant_service_group = mock.Mock(return_value=Obj())
        market_app_service._extract_event_ids = mock.Mock(return_value=["event-1"])
        market_app_service._create_rbdplugin_if_needed = mock.Mock()

        app_upgrade = Obj()
        app_upgrade.install = mock.Mock(return_value=[{"event_id": "event-1"}])
        app_upgrade.new_app = Obj(components=mock.Mock(return_value=[component_snapshot]))

        with mock.patch.object(platform_module, "AppUpgrade", return_value=app_upgrade):
            platform_plugin_service.install_platform_plugin("eid", "rainbond", "rainbond-agent", user)

        first_deploy_service.safe_begin_tracking.assert_called_once()
        tracking_kwargs = first_deploy_service.safe_begin_tracking.call_args[1]
        self.assertEqual("eid", tracking_kwargs["enterprise_id"])
        self.assertEqual("rbd-plugins", tracking_kwargs["tenant_name"])
        self.assertEqual("rainbond", tracking_kwargs["region_name"])
        self.assertEqual("app_market", tracking_kwargs["deploy_type"])
        self.assertEqual("platform_plugin_install", tracking_kwargs["trigger"])
        self.assertEqual("rainbond-agent", tracking_kwargs["app_context"]["plugin_id"])
        self.assertEqual("extension", tracking_kwargs["app_context"]["install_source"])
        first_deploy_service.safe_bind_events.assert_called_once_with(
            {"key": "first-deploy"},
            ["event-1"],
            service_ids=["service-1"],
            service_alias="grservice1",
            service_aliases=[])
