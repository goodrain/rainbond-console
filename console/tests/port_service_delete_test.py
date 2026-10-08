import importlib.util
import sys
import types
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock, call


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


class RegionCallApiError(Exception):
    def __init__(self, message, status=400, body=None):
        super(RegionCallApiError, self).__init__(message)
        self.body = body or {"msg": message}
        self.status = status
        self.message = {"httpcode": status, "body": self.body}


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
            "django.db.models",
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
        install_stub("django.db.models", QuerySet=object)
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
                     RegionApiBaseHttpClient=types.SimpleNamespace(CallApiError=RegionCallApiError))
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
        region = types.SimpleNamespace(region_id="region-1", region_name="region-1", httpdomain="apps.example.com")
        app = types.SimpleNamespace(
            app_id=7,
            governance_mode="KUBERNETES_NATIVE_SERVICE",
        )
        module.region_repo.get_region_by_region_name.return_value = region
        module.port_repo.get_service_port_by_port.return_value = port
        module.domain_repo.get_service_domain_by_container_port.return_value = []
        module.region_api.api_gateway_bind_http_domain.return_value = None
        module.region_api.api_gateway_get_proxy.side_effect = lambda region, tenant, path, app: {
            "list": ["svc.apps.example.com"] if "/http/domains?" in path else []}
        module.group_repo.get_by_service_id.return_value = app
        module.env_var_service.add_service_env_var.return_value = (200, "success", None)
        module.env_var_service.delete_env_by_container_port.return_value = None
        return app

    def configure_tcp_close_dependencies(self, module, routes):
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
            container_port=8080,
            protocol="tcp",
            port_alias="tcp",
            is_inner_service=True,
            is_outer_service=True,
            k8s_service_name="gr2dc0bf",
            save=MagicMock(),
        )
        app = self.configure_manage_port_dependencies(module, port)
        module.tcp_domain.get_service_tcp_domains_by_service_id_and_port.return_value = []
        module.region_api.api_gateway_get_proxy.side_effect = lambda region, tenant, path, app: {
            "list": [{"service_name": "gr2dc0bf-" + str(port), "nodePort": port, "protocol": "TCP"}
                     for port in routes] if "/tcp/domains?" in path else []}
        return tenant, service, port, app

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

    # capability_id: console.component.tcp-port-close-release
    def test_close_tcp_port_releases_all_region_routes_before_local_mapping(self):
        module = self.import_port_service_module()
        tenant, service, _, app = self.configure_tcp_close_dependencies(module, [31000, 31001])
        operations = []
        module.region_api.delete_proxy.side_effect = lambda *args: operations.append("region-delete")
        module.tcp_domain.delete_by_component_port.side_effect = lambda *args: operations.append("local-delete")
        module.region_api.manage_outer_port.side_effect = lambda *args: operations.append("sync")
        plugin_service = sys.modules["console.services.plugin"].app_plugin_service
        plugin_service.update_config_if_have_entrance_plugin.side_effect = lambda *args: operations.append("plugin")

        result = module.AppPortService().manage_port(
            tenant, service, "region-1", 8080, "close_outer", "tcp", "SVC8080", user_name="alice", app=app)

        self.assertEqual(result[:2], (200, "操作成功"))
        region = module.region_repo.get_region_by_region_name.return_value
        module.region_api.api_gateway_get_proxy.assert_called_once_with(
            region,
            "tenant-1",
            "/api-gateway/v1/default/routes/tcp/domains?service_alias=gr2dc0bf&port=8080&details=true",
            7,
        )
        route_base = "/v2/proxy-pass/gateway/default/routes/tcp/gr2dc0bf-"
        module.region_api.delete_proxy.assert_has_calls([
            call("region-1", route_base + "31000?service_id=component-1"),
            call("region-1", route_base + "31001?service_id=component-1"),
        ])
        self.assertEqual(module.region_api.delete_proxy.call_count, 2)
        module.tcp_domain.delete_by_component_port.assert_called_once_with("component-1", 8080)
        self.assertEqual(operations, ["region-delete", "region-delete", "sync", "local-delete", "plugin"])

    # capability_id: console.component.tcp-port-close-release
    def test_close_tcp_port_with_no_region_routes_deletes_stale_local_mapping(self):
        module = self.import_port_service_module()
        tenant, service, _, app = self.configure_tcp_close_dependencies(module, [])

        result = module.AppPortService().manage_port(
            tenant, service, "region-1", 8080, "close_outer", "tcp", "SVC8080", user_name="alice", app=app)

        self.assertEqual(result[:2], (200, "操作成功"))
        module.region_api.delete_proxy.assert_not_called()
        module.tcp_domain.delete_by_component_port.assert_called_once_with("component-1", 8080)

    # capability_id: console.component.tcp-port-close-release
    def test_close_tcp_port_preserves_local_mapping_when_region_query_fails(self):
        module = self.import_port_service_module()
        tenant, service, _, app = self.configure_tcp_close_dependencies(module, [])
        module.region_api.api_gateway_get_proxy.side_effect = RuntimeError("query failed")

        with self.assertRaisesRegex(RuntimeError, "query failed"):
            module.AppPortService().manage_port(
                tenant, service, "region-1", 8080, "close_outer", "tcp", "SVC8080", user_name="alice", app=app)

        module.region_api.delete_proxy.assert_not_called()
        module.tcp_domain.delete_by_component_port.assert_not_called()
        module.region_api.manage_outer_port.assert_not_called()
        sys.modules["console.services.plugin"].app_plugin_service.update_config_if_have_entrance_plugin.assert_not_called()

    # capability_id: console.component.tcp-port-close-release
    def test_close_tcp_port_preserves_local_mapping_when_region_delete_fails(self):
        module = self.import_port_service_module()
        tenant, service, _, app = self.configure_tcp_close_dependencies(module, [31000, 31001])
        module.region_api.delete_proxy.side_effect = [None, RuntimeError("delete failed")]

        with self.assertRaisesRegex(RuntimeError, "delete failed"):
            module.AppPortService().manage_port(
                tenant, service, "region-1", 8080, "close_outer", "tcp", "SVC8080", user_name="alice", app=app)

        self.assertEqual(module.region_api.delete_proxy.call_count, 2)
        module.tcp_domain.delete_by_component_port.assert_not_called()
        module.region_api.manage_outer_port.assert_not_called()
        sys.modules["console.services.plugin"].app_plugin_service.update_config_if_have_entrance_plugin.assert_not_called()

    # capability_id: console.component.port-operation-errors
    def test_open_outer_protocol_mismatch_explains_how_to_resynchronize_inner_service(self):
        module = self.import_port_service_module()
        tenant = types.SimpleNamespace(tenant_id="tenant-1", tenant_name="default", enterprise_id="enterprise-1")
        service = types.SimpleNamespace(
            service_id="component-1",
            tenant_id="tenant-1",
            service_region="region-1",
            service_alias="gr2dc0bf",
            service_cname="sip",
            service_key="sip",
            service_source="source",
            create_status="complete",
            namespace="",
        )
        port = types.SimpleNamespace(
            container_port=5060,
            protocol="udp",
            port_alias="SIP",
            is_inner_service=True,
            is_outer_service=False,
            k8s_service_name="gr2dc0bf",
            save=MagicMock(),
        )
        app = self.configure_manage_port_dependencies(module, port)
        module.tcp_domain.get_service_tcp_domains_by_service_id_and_port.return_value = []
        module.region_api.api_gateway_bind_tcp_domain.side_effect = RegionCallApiError(
            "protocol is not supported by the component port")

        with self.assertRaises(ServiceHandleException) as ctx:
            module.AppPortService().manage_port(
                tenant, service, "region-1", 5060, "open_outer", None, "SIP", user_name="alice", app=app)

        self.assertEqual(ctx.exception.msg, "protocol is not supported by the component port")
        self.assertEqual(
            ctx.exception.msg_show,
            "组件对内服务的 5060 端口协议尚未同步为 UDP，请关闭并重新开启对内服务后，再开启对外服务",
        )
        self.assertNotIn("数据中心", ctx.exception.msg_show)

    # capability_id: console.component.port-operation-errors
    def test_port_toggle_region_errors_use_action_specific_messages(self):
        module = self.import_port_service_module()

        expectations = {
            "open_inner": "开启对内服务失败，请稍后重试；若问题持续，请查看组件事件",
            "close_inner": "关闭对内服务失败，请稍后重试；若问题持续，请查看组件事件",
            "open_outer": "开启对外服务失败，请稍后重试；若问题持续，请查看组件事件",
            "close_outer": "关闭对外服务失败，请稍后重试；若问题持续，请查看组件事件",
        }
        for action, expected in expectations.items():
            with self.subTest(action=action):
                self.assertEqual(
                    module.build_port_operation_error_msg_show(action, 8080, "tcp", {"msg": "unexpected failure"}, 500),
                    expected,
                )

    # capability_id: console.component.port-operation-errors
    def test_port_toggle_region_errors_translate_common_recovery_cases(self):
        module = self.import_port_service_module()

        self.assertEqual(
            module.build_port_operation_error_msg_show(
                "open_outer", 8080, "tcp", {"msg": "backend service is unavailable for protocol validation"}, 400),
            "组件对内服务尚未就绪，请关闭并重新开启对内服务后，再开启对外服务",
        )
        self.assertEqual(
            module.build_port_operation_error_msg_show(
                "close_inner", 8080, "tcp", {"msg": "service port record not found"}, 404),
            "组件端口 8080 不存在或已被删除，请刷新页面后重试",
        )
        self.assertEqual(
            module.build_port_operation_error_msg_show(
                "open_inner", 8080, "tcp", {"type": "connect error"}, 503),
            "集群通信异常，开启对内服务未完成，请稍后重试",
        )

    # capability_id: console.component.port-operation-errors
    def test_open_outer_http_default_route_failure_uses_user_facing_message(self):
        module = self.import_port_service_module()
        tenant = types.SimpleNamespace(tenant_id="tenant-1", tenant_name="default", enterprise_id="enterprise-1")
        service = types.SimpleNamespace(
            service_id="component-1",
            tenant_id="tenant-1",
            service_region="region-1",
            service_alias="gr2dc0bf",
            service_cname="web",
            service_key="web",
            service_source="source",
            create_status="complete",
            namespace="",
        )
        port = types.SimpleNamespace(
            container_port=80,
            protocol="http",
            port_alias="HTTP",
            is_inner_service=True,
            is_outer_service=False,
            k8s_service_name="gr2dc0bf",
            save=MagicMock(),
        )
        app = self.configure_manage_port_dependencies(module, port)
        module.region_api.api_gateway_bind_http_domain.side_effect = RuntimeError("gateway failed")

        result = module.AppPortService().manage_port(
            tenant, service, "region-1", 80, "open_outer", None, "HTTP", user_name="alice", app=app)

        self.assertEqual(result[:2], (412, "创建默认访问地址失败，请稍后重试"))
        self.assertNotIn("数据中心", result[1])

    # capability_id: console.component.port-operation-errors
    def test_port_toggle_translates_unfriendly_service_errors(self):
        module = self.import_port_service_module()
        tenant = types.SimpleNamespace(tenant_id="tenant-1", tenant_name="default", enterprise_id="enterprise-1")
        service = types.SimpleNamespace(
            service_id="component-1",
            tenant_id="tenant-1",
            service_region="region-1",
            service_alias="gr2dc0bf",
            service_key="web",
            create_status="complete",
        )
        port = types.SimpleNamespace(
            container_port=8080,
            protocol="tcp",
            port_alias="TCP",
            is_inner_service=False,
            is_outer_service=False,
            k8s_service_name="gr2dc0bf",
            save=MagicMock(),
        )
        self.configure_manage_port_dependencies(module, port)
        module.region_api.manage_inner_port.side_effect = ServiceHandleException(
            msg="update service port error", msg_show="update service port error", status_code=500)

        with self.assertRaises(ServiceHandleException) as ctx:
            module.AppPortService().manage_port(
                tenant, service, "region-1", 8080, "open_inner", None, "TCP", user_name="alice")

        self.assertEqual(ctx.exception.msg_show, "开启对内服务失败，请稍后重试；若问题持续，请查看组件事件")

    # capability_id: console.component.port-operation-errors
    def test_port_toggle_preserves_existing_actionable_service_errors(self):
        module = self.import_port_service_module()
        tenant = types.SimpleNamespace(tenant_id="tenant-1", tenant_name="default", enterprise_id="enterprise-1")
        service = types.SimpleNamespace(
            service_id="component-1",
            tenant_id="tenant-1",
            service_region="region-1",
            service_alias="gr2dc0bf",
            service_key="web",
            create_status="complete",
        )
        port = types.SimpleNamespace(
            container_port=8080,
            protocol="tcp",
            port_alias="TCP",
            is_inner_service=False,
            is_outer_service=True,
            k8s_service_name="gr2dc0bf",
            save=MagicMock(),
        )
        self.configure_manage_port_dependencies(module, port)

        with self.assertRaises(ServiceHandleException) as ctx:
            module.AppPortService().manage_port(
                tenant, service, "region-1", 8080, "close_inner", None, "TCP", user_name="alice")

        self.assertEqual(ctx.exception.msg_show, "对外服务开启中，需先关闭对外服务")

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
