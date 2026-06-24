import importlib.util
import sys
import types
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock


def install_stub(module_name, **attrs):
    module = types.ModuleType(module_name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[module_name] = module
    return module


def atomic(func=None):
    if func is None:
        return lambda wrapped: wrapped
    return func


class AbortRequest(Exception):
    def __init__(self, msg, msg_show=None, status_code=400, error_code=None, **kwargs):
        super(AbortRequest, self).__init__(msg)
        self.msg = msg
        self.msg_show = msg_show or msg
        self.status_code = status_code
        self.error_code = error_code or status_code


class ServiceHandleException(AbortRequest):
    pass


class PortServiceDeleteTests(TestCase):
    def tearDown(self):
        for module_name in (
            "console.constants",
            "console.enum.app",
            "console.exception.bcode",
            "console.exception.main",
            "console.models.main",
            "console.repositories.app",
            "console.repositories.app_config",
            "console.repositories.group",
            "console.repositories.probe_repo",
            "console.repositories.region_app",
            "console.repositories.region_repo",
            "console.services.app_config",
            "console.services.app_config.domain_service",
            "console.services.app_config.env_service",
            "console.services.app_config.port_service",
            "console.services.app_config.probe_service",
            "console.services.plugin",
            "console.services.region_services",
            "django.db",
            "validators",
            "www.apiclient.regionapi",
            "www.apiclient.regionapibaseclient",
            "www.models.main",
            "www.utils.crypt",
        ):
            sys.modules.pop(module_name, None)

    def import_port_service_module(self):
        repo_root = Path(__file__).resolve().parents[2]
        app_config_package = types.ModuleType("console.services.app_config")
        app_config_package.__path__ = [str(repo_root / "console" / "services" / "app_config")]
        sys.modules["console.services.app_config"] = app_config_package

        install_stub("django.db", transaction=types.SimpleNamespace(atomic=atomic))
        install_stub("validators", ipv4=lambda value: False, ipv6=lambda value: False, domain=lambda value: True)
        install_stub("console.constants", ServicePortConstants=types.SimpleNamespace())
        install_stub("console.enum.app", GovernanceModeEnum=types.SimpleNamespace(
            BUILD_IN_SERVICE_MESH=types.SimpleNamespace(name="BUILD_IN_SERVICE_MESH")))
        install_stub("console.exception.bcode", ErrComponentPortExists=Exception("port exists"),
                     ErrK8sServiceNameExists=Exception("k8s service name exists"))
        install_stub("console.exception.main", AbortRequest=AbortRequest, CheckThirdpartEndpointFailed=AbortRequest,
                     ServiceHandleException=ServiceHandleException)
        install_stub("console.repositories.app", service_repo=MagicMock())
        install_stub("console.repositories.app_config", domain_repo=MagicMock(), env_var_repo=MagicMock(),
                     port_repo=MagicMock(), service_endpoints_repo=MagicMock(), tcp_domain=MagicMock())
        install_stub("console.repositories.group", group_repo=MagicMock())
        install_stub("console.repositories.probe_repo", probe_repo=MagicMock())
        install_stub("console.repositories.region_app", region_app_repo=MagicMock())
        install_stub("console.repositories.region_repo", region_repo=MagicMock())
        install_stub("console.services.app_config.domain_service", domain_service=MagicMock())
        install_stub("console.services.app_config.env_service", AppEnvVarService=MagicMock)
        install_stub("console.services.app_config.probe_service", ProbeService=MagicMock)
        install_stub("console.services.plugin", app_plugin_service=MagicMock())
        install_stub("console.services.region_services", region_services=MagicMock())
        install_stub("console.models.main", TenantServiceInfo=object, RegionConfig=object)
        install_stub("www.models.main", ServiceGroup=object, TenantServiceEnvVar=object, TenantServicesPort=object, Tenants=object)
        install_stub("www.apiclient.regionapi", RegionInvokeApi=MagicMock)
        install_stub("www.apiclient.regionapibaseclient",
                     RegionApiBaseHttpClient=types.SimpleNamespace(CallApiError=Exception))
        install_stub("www.utils.crypt", make_uuid=lambda value: "uuid-" + str(value))

        module_path = repo_root / "console" / "services" / "app_config" / "port_service.py"
        spec = importlib.util.spec_from_file_location("console.services.app_config.port_service", str(module_path))
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module

    def configure_delete_dependencies(self, module, port):
        module.port_repo.get_service_port_by_port.return_value = port
        module.probe_repo.get_service_probe.return_value.filter.return_value.first.return_value = None
        module.env_var_service = MagicMock()
        module.domain_service = MagicMock()

    def configure_manage_port_dependencies(self, module, port):
        region = types.SimpleNamespace(region_id="region-1", httpdomain="apps.example.com")
        app = types.SimpleNamespace(
            app_id=7,
            governance_mode="KUBERNETES_NATIVE_SERVICE",
        )
        module.region_repo.get_region_by_region_name.return_value = region
        module.port_repo.get_service_port_by_port.return_value = port
        module.domain_repo.get_service_domain_by_container_port.return_value = []
        module.region_api.api_gateway_bind_http_domain.return_value = None
        module.region_api.api_gateway_get_proxy.return_value = {"list": ["svc.apps.example.com"]}
        module.group_repo.get_by_service_id.return_value = app
        module.env_var_service.add_service_env_var.return_value = (200, "success", None)
        module.env_var_service.delete_env_by_container_port.return_value = None
        return app

    # capability_id: console.component.port-toggle-events
    def test_open_outer_port_synchronizes_region_component_event(self):
        module = self.import_port_service_module()
        tenant = types.SimpleNamespace(tenant_id="tenant-1", tenant_name="default", enterprise_id="enterprise-1")
        service = types.SimpleNamespace(
            service_id="component-1",
            tenant_id="tenant-1",
            service_region="region-1",
            service_alias="gr2dc0bf",
            service_cname="nginx",
            service_key="nginx",
            service_source="source",
            create_status="complete",
        )
        port = types.SimpleNamespace(
            container_port=80,
            protocol="http",
            port_alias="http",
            is_inner_service=True,
            is_outer_service=False,
            k8s_service_name="gr2dc0bf",
            save=MagicMock(),
        )
        app = self.configure_manage_port_dependencies(module, port)

        module.AppPortService().manage_port(
            tenant, service, "region-1", 80, "open_outer", "http", "SVC80", user_name="alice", app=app)

        module.region_api.manage_outer_port.assert_called_once_with(
            "region-1",
            "default",
            "gr2dc0bf",
            80,
            {"operation": "open", "enterprise_id": "enterprise-1", "operator": "alice"},
        )

    # capability_id: console.component.port-toggle-events
    def test_close_outer_port_synchronizes_region_component_event(self):
        module = self.import_port_service_module()
        tenant = types.SimpleNamespace(tenant_id="tenant-1", tenant_name="default", enterprise_id="enterprise-1")
        service = types.SimpleNamespace(
            service_id="component-1",
            tenant_id="tenant-1",
            service_region="region-1",
            service_alias="gr2dc0bf",
            service_cname="nginx",
            service_key="nginx",
            service_source="source",
            create_status="complete",
        )
        port = types.SimpleNamespace(
            container_port=80,
            protocol="http",
            port_alias="http",
            is_inner_service=True,
            is_outer_service=True,
            k8s_service_name="gr2dc0bf",
            save=MagicMock(),
        )
        app = self.configure_manage_port_dependencies(module, port)

        module.AppPortService().manage_port(
            tenant, service, "region-1", 80, "close_outer", "http", "SVC80", user_name="alice", app=app)

        module.region_api.manage_outer_port.assert_called_once_with(
            "region-1",
            "default",
            "gr2dc0bf",
            80,
            {"operation": "close", "enterprise_id": "enterprise-1", "operator": "alice"},
        )

    # capability_id: console.component.port-toggle-events
    def test_inner_port_toggle_keeps_region_component_event_path(self):
        module = self.import_port_service_module()
        tenant = types.SimpleNamespace(tenant_id="tenant-1", tenant_name="default", enterprise_id="enterprise-1")
        service = types.SimpleNamespace(
            service_id="component-1",
            tenant_id="tenant-1",
            service_region="region-1",
            service_alias="gr2dc0bf",
            service_cname="nginx",
            service_key="nginx",
            create_status="complete",
        )
        port = types.SimpleNamespace(
            container_port=80,
            protocol="http",
            port_alias="http",
            is_inner_service=False,
            is_outer_service=False,
            k8s_service_name="gr2dc0bf",
            save=MagicMock(),
        )
        app = self.configure_manage_port_dependencies(module, port)

        module.AppPortService().manage_port(
            tenant, service, "region-1", 80, "open_inner", "http", "SVC80", user_name="alice", app=app)
        module.AppPortService().manage_port(
            tenant, service, "region-1", 80, "close_inner", "http", "SVC80", user_name="alice", app=app)

        self.assertEqual(module.region_api.manage_inner_port.call_count, 2)
        module.region_api.manage_inner_port.assert_any_call(
            "region-1",
            "default",
            "gr2dc0bf",
            80,
            {"operation": "open", "enterprise_id": "enterprise-1", "operator": "alice"},
        )
        module.region_api.manage_inner_port.assert_any_call(
            "region-1",
            "default",
            "gr2dc0bf",
            80,
            {"operation": "close", "enterprise_id": "enterprise-1", "operator": "alice"},
        )

    def test_delete_closed_port_ignores_inactive_custom_http_domains(self):
        module = self.import_port_service_module()
        tenant = types.SimpleNamespace(tenant_id="tenant-1", tenant_name="default", enterprise_id="enterprise-1")
        service = types.SimpleNamespace(
            service_id="component-1",
            service_region="region-1",
            service_alias="gr2dc0bf",
            create_status="complete",
        )
        port = types.SimpleNamespace(is_inner_service=False, is_outer_service=False)
        inactive_custom_domain = types.SimpleNamespace(type=1, is_outer_service=False)
        module.domain_repo.get_service_domain_by_container_port.return_value = [inactive_custom_domain]
        self.configure_delete_dependencies(module, port)

        deleted_port = module.AppPortService().delete_port_by_container_port(tenant, service, 80, "alice")

        self.assertIs(deleted_port, port)
        module.region_api.delete_service_port.assert_called_once()
        module.port_repo.delete_serivce_port_by_port.assert_called_once_with("tenant-1", "component-1", 80)
        module.domain_service.delete_by_port.assert_called_once_with("component-1", 80)

    def test_delete_closed_port_rejects_active_custom_http_domains(self):
        module = self.import_port_service_module()
        tenant = types.SimpleNamespace(tenant_id="tenant-1", tenant_name="default", enterprise_id="enterprise-1")
        service = types.SimpleNamespace(service_id="component-1", service_region="region-1", service_alias="gr2dc0bf")
        port = types.SimpleNamespace(is_inner_service=False, is_outer_service=False)
        active_custom_domain = types.SimpleNamespace(type=1, is_outer_service=True)
        module.domain_repo.get_service_domain_by_container_port.return_value = [active_custom_domain]
        self.configure_delete_dependencies(module, port)

        with self.assertRaises(AbortRequest) as ctx:
            module.AppPortService().delete_port_by_container_port(tenant, service, 80, "alice")

        self.assertEqual(ctx.exception.status_code, 412)
