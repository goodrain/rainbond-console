# -*- coding: utf-8 -*-
import os
import sys
from types import ModuleType
from unittest import TestCase, mock

sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")


class Obj(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class AbortRequest(Exception):
    pass


class ServiceHandleException(Exception):
    pass


class GovernanceModeEnumStub(object):
    KUBERNETES_NATIVE_SERVICE = Obj(name="KUBERNETES_NATIVE_SERVICE")


class ComponentTypeStub(object):
    state_multiple = Obj(value="state_multiple")
    stateless_multiple = Obj(value="stateless_multiple")


class TenantServiceInfoStub(object):
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
            "market_app_id": getattr(market_app, "app_id", ""),
            "market_app_name": getattr(market_app, "app_name", ""),
            "app_model_key": app_model_key,
            "app_model_version": version,
            "market_name": market_name,
            "install_from_cloud": bool(install_from_cloud),
        }
        if app_template:
            context["component_count"] = len(app_template.get("apps") or [])
            context["template_arch"] = app_template.get("arch", "")
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

install_stub("console.appstore", package=True)
install_stub("console.appstore.appstore", AppStore=object, app_store=Obj())
install_stub("console.constants", AppConstants=Obj(MARKET="market"))
install_stub("console.enum.app", GovernanceModeEnum=GovernanceModeEnumStub)
install_stub("console.enum.component_enum", ComponentType=ComponentTypeStub)
install_stub(
    "console.exception.bcode",
    ErrAppConfigGroupExists=type("ErrAppConfigGroupExists", (Exception,), {}),
    ErrK8sServiceNameExists=type("ErrK8sServiceNameExists", (Exception,), {}))
install_stub(
    "console.exception.main",
    AbortRequest=AbortRequest,
    ErrVolumePath=type("ErrVolumePath", (Exception,), {}),
    MarketAppLost=type("MarketAppLost", (Exception,), {}),
    RbdAppNotFound=type("RbdAppNotFound", (Exception,), {}),
    ServiceHandleException=ServiceHandleException)
install_stub(
    "console.models.main",
    AppMarket=object,
    AppUpgradeRecord=object,
    RainbondCenterApp=object,
    RainbondCenterAppVersion=object,
    RegionConfig=object)
install_stub(
    "console.repositories.app",
    app_market_repo=Obj(),
    app_tag_repo=Obj(),
    service_source_repo=Obj())
install_stub(
    "console.repositories.app_config",
    env_var_repo=Obj(),
    extend_repo=Obj(),
    port_repo=Obj(),
    volume_repo=Obj(),
    dep_relation_repo=Obj())
install_stub("console.repositories.app_version_repo", app_version_template_relation_repo=Obj())
install_stub("console.repositories.base", BaseConnection=object)
install_stub("console.repositories.group", group_repo=Obj(), tenant_service_group_repo=Obj())
install_stub("console.repositories.market_app_repo", app_import_record_repo=Obj(), rainbond_app_repo=Obj())
install_stub("console.repositories.plugin", plugin_repo=Obj())
install_stub("console.repositories.plugin.plugin", plugin_version_repo=Obj())
install_stub("console.repositories.region_app", region_app_repo=Obj())
install_stub("console.repositories.service_repo", service_repo=Obj())
install_stub("console.repositories.team_repo", team_repo=Obj())
install_stub("console.services.app", app_market_service=Obj(), app_service=Obj())
install_stub("console.services.app_actions", app_manage_service=Obj())
install_stub(
    "console.services.app_config",
    package=True,
    AppMntService=lambda: Obj(),
    domain_service=Obj(),
    port_service=Obj(),
    probe_service=Obj(),
    volume_service=Obj())
install_stub("console.services.app_config.app_relation_service", AppServiceRelationService=lambda: Obj())
install_stub("console.services.app_config.component_graph", component_graph_service=Obj())
install_stub("console.services.app_config.service_monitor", service_monitor_repo=Obj())
install_stub("console.services.app_config_group", app_config_group_service=Obj())
install_stub("console.services.enterprise_first_deploy_service", enterprise_first_deploy_service=first_deploy_service)
install_stub("console.services.group_service", group_service=Obj())
install_stub("console.services.market_app", package=True)
install_stub("console.services.market_app.app_upgrade", AppUpgrade=object)
install_stub("console.services.market_app.component_group", ComponentGroup=object)
install_stub("console.services.market_app.utils",
             resolve_none_placeholders=lambda apps: None,
             collect_install_hostname_remap=lambda tenant_id, apps: {},
             apply_hostname_remap=lambda apps, remap: None)
install_stub(
    "console.services.plugin",
    app_plugin_service=Obj(),
    plugin_config_service=Obj(),
    plugin_service=Obj(),
    plugin_version_service=Obj())
install_stub("console.services.region_services", region_services=Obj())
install_stub("console.services.share_services", share_service=Obj())
install_stub("console.services.telemetry", telemetry_service=Obj(track_market_app_installed=lambda **kwargs: None))
install_stub("console.services.upgrade_services", upgrade_service=Obj())
install_stub("console.services.virtual_machine", vms=Obj(ensure_vm_platform_running=lambda *args, **kwargs: None))
install_stub("console.utils.offline", is_cloud_market_disabled=lambda: False)
install_stub("console.utils.version", compare_version=lambda *args, **kwargs: 0, sorted_versions=lambda versions: versions)
install_stub("www.apiclient.regionapi", RegionInvokeApi=lambda: Obj(get_cluster_nodes_arch=lambda *args: (None, {"list": ["amd64"]})))
install_stub(
    "www.models.main",
    TenantEnterprise=object,
    TenantEnterpriseToken=object,
    TenantServiceEnvVar=object,
    TenantServiceInfo=TenantServiceInfoStub,
    TenantServicesPort=object,
    Users=object,
    ServiceGroup=Obj(objects=Obj(first=lambda: None)),
    Tenants=Obj(objects=Obj(get=lambda **kwargs: None)),
    ServiceGroupRelation=object)
install_stub("www.models.plugin", ServicePluginConfigVar=object)
install_stub("www.tenantservice.baseservice", BaseTenantService=lambda: Obj())
install_stub("www.utils.crypt", make_uuid=lambda: "uuid")

from console.services.market_app_service import market_app_service  # noqa: E402
import console.services.market_app_service as market_module  # noqa: E402


# capability_id: console.deploy-diagnostics.v3
class MarketAppFirstDeployTrackingTests(TestCase):
    def setUp(self):
        first_deploy_service.safe_begin_tracking.reset_mock()
        first_deploy_service.safe_bind_events.reset_mock()
        first_deploy_service.safe_mark_failure.reset_mock()

    def test_install_app_reports_first_deploy_tracking_for_market_install(self):
        tenant = Obj(tenant_id="tenant-1", tenant_name="team-a", enterprise_id="eid-1")
        region = Obj(region_name="region-a")
        user = Obj(enterprise_id="eid-1", nick_name="tester")
        app = Obj(ID=7, app_id="app-7", group_name="target-app", governance_mode="KUBERNETES_NATIVE_SERVICE")
        market_app = Obj(app_id="market-app-1", app_name="Demo App", source="")
        app_template = {
            "apps": [{"service_cname": "web"}, {"service_cname": "worker"}],
            "arch": "amd64",
        }
        components = [
            Obj(component=Obj(component_id="svc-web", service_alias="alias-web")),
            Obj(component=Obj(component_id="svc-worker", service_alias="alias-worker")),
        ]
        app_upgrade = Obj(
            install=mock.Mock(return_value=[{"event_id": "event-web"}, {"event_id": "event-worker"}]),
            new_app=Obj(components=mock.Mock(return_value=components)))

        market_module.group_repo.get_group_by_id = mock.Mock(return_value=app)
        market_module.region_api.get_cluster_nodes_arch = mock.Mock(return_value=(None, {"list": ["amd64"]}))
        market_app_service.get_app_template = mock.Mock(return_value=(app_template, market_app))
        market_app_service._ensure_vm_template_allowed = mock.Mock()
        market_app_service._create_tenant_service_group = mock.Mock(return_value=Obj())
        market_app_service._create_rbdplugin_if_needed = mock.Mock()
        market_app_service._track_market_app_installed = mock.Mock()

        with mock.patch.object(market_module, "AppUpgrade", return_value=app_upgrade):
            app_name = market_app_service.install_app(
                tenant,
                region,
                user,
                "app-7",
                "market-model-key",
                "1.2.3",
                "localApplication",
                False,
                is_deploy=True)

        self.assertEqual("Demo App", app_name)
        first_deploy_service.safe_begin_tracking.assert_called_once()
        tracking_kwargs = first_deploy_service.safe_begin_tracking.call_args[1]
        self.assertEqual("eid-1", tracking_kwargs["enterprise_id"])
        self.assertEqual("team-a", tracking_kwargs["tenant_name"])
        self.assertEqual("region-a", tracking_kwargs["region_name"])
        self.assertEqual("app_market", tracking_kwargs["deploy_type"])
        self.assertEqual("tester", tracking_kwargs["operator"])
        self.assertEqual("market_install", tracking_kwargs["trigger"])
        self.assertEqual("Demo App", tracking_kwargs["app_context"]["market_app_name"])
        self.assertEqual("market-model-key", tracking_kwargs["app_context"]["app_model_key"])
        self.assertEqual(2, tracking_kwargs["app_context"]["component_count"])
        self.assertEqual({"component_count": 2}, tracking_kwargs["workload_context"])
        first_deploy_service.safe_bind_events.assert_called_once_with(
            {"key": "first-deploy"},
            ["event-web", "event-worker"],
            service_ids=["svc-web", "svc-worker"],
            service_alias="",
            service_aliases=["alias-web", "alias-worker"])
        market_app_service._track_market_app_installed.assert_called_once()
