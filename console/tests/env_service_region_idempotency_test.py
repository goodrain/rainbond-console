# capability_id: console.port-inner.env-sync-idempotent
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


class EnvAlreadyExist(Exception):
    pass


class InvalidEnvName(Exception):
    pass


class ServiceHandleException(Exception):
    pass


class DummyCallApiError(Exception):
    def __init__(self, apitype, url, method, res, body, describe=None):
        self.message = {
            "apitype": apitype,
            "url": url,
            "method": method,
            "httpcode": res.status,
            "body": body,
        }
        self.apitype = apitype
        self.url = url
        self.method = method
        self.body = body
        self.status = res.status


class EnvServiceRegionIdempotencyTests(TestCase):
    def tearDown(self):
        for module_name in (
            "console.exception.main",
            "console.repositories.app_config",
            "console.services.app_config.env_service",
            "django.db.transaction",
            "www.models.main",
            "www.apiclient.regionapi",
            "www.apiclient.regionapibaseclient",
        ):
            sys.modules.pop(module_name, None)

    def import_env_service_module(self):
        repo_root = Path(__file__).resolve().parents[2]

        install_stub("django.db.transaction", atomic=atomic)
        install_stub(
            "console.exception.main",
            EnvAlreadyExist=EnvAlreadyExist,
            InvalidEnvName=InvalidEnvName,
            ServiceHandleException=ServiceHandleException,
        )
        install_stub(
            "console.repositories.app_config",
            compile_env_repo=MagicMock(),
            dep_relation_repo=MagicMock(),
            env_var_repo=MagicMock(),
        )
        install_stub("www.models.main", TenantServicesPort=object, TenantServiceEnvVar=object)
        install_stub("www.apiclient.regionapi", RegionInvokeApi=MagicMock)
        install_stub(
            "www.apiclient.regionapibaseclient",
            RegionApiBaseHttpClient=types.SimpleNamespace(CallApiError=DummyCallApiError),
        )

        module_path = repo_root / "console" / "services" / "app_config" / "env_service.py"
        spec = importlib.util.spec_from_file_location("console.services.app_config.env_service", str(module_path))
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module

    def test_add_service_env_var_updates_region_when_env_already_exists(self):
        module = self.import_env_service_module()
        tenant = types.SimpleNamespace(tenant_id="tenant-id", tenant_name="tenant-name", enterprise_id="enterprise-id")
        service = types.SimpleNamespace(
            tenant_id="tenant-id",
            service_id="service-id",
            service_region="region-name",
            service_alias="service-alias",
            create_status="complete",
        )
        repo = module.env_var_repo
        repo.get_service_env_by_attr_name.return_value = None
        created_env = object()
        repo.add_service_env.return_value = created_env
        region_error = DummyCallApiError(
            "region api",
            "http://region/v2/tenants/tenant-name/services/service-alias/env",
            "POST",
            types.SimpleNamespace(status=400),
            {"msg": "record already exist"},
        )
        module.region_api.add_service_env.side_effect = region_error

        code, msg, env = module.AppEnvVarService().add_service_env_var(
            tenant,
            service,
            3389,
            "连接地址",
            "GRBD3CDA3389_HOST",
            "grbd3cda-3389",
            False,
            scope="outer",
            user_name="tester",
        )

        self.assertEqual(200, code)
        self.assertEqual("success", msg)
        self.assertIs(env, created_env)
        module.region_api.update_service_env.assert_called_once_with(
            "region-name",
            "tenant-name",
            "service-alias",
            {
                "old_env_name": "GRBD3CDA3389_HOST",
                "env_name": "GRBD3CDA3389_HOST",
                "env_value": "grbd3cda-3389",
                "scope": "outer",
                "operator": "tester",
            },
        )
        repo.add_service_env.assert_called_once_with(
            tenant_id="tenant-id",
            service_id="service-id",
            container_port=3389,
            name="连接地址",
            attr_name="GRBD3CDA3389_HOST",
            attr_value="grbd3cda-3389",
            is_change=False,
            scope="outer",
        )

    def test_add_service_env_var_retries_add_when_region_update_reports_record_not_found(self):
        module = self.import_env_service_module()
        tenant = types.SimpleNamespace(tenant_id="tenant-id", tenant_name="tenant-name", enterprise_id="enterprise-id")
        service = types.SimpleNamespace(
            tenant_id="tenant-id",
            service_id="service-id",
            service_region="region-name",
            service_alias="service-alias",
            create_status="complete",
        )
        repo = module.env_var_repo
        repo.get_service_env_by_attr_name.return_value = None
        created_env = object()
        repo.add_service_env.return_value = created_env
        add_conflict = DummyCallApiError(
            "region api",
            "http://region/v2/tenants/tenant-name/services/service-alias/env",
            "POST",
            types.SimpleNamespace(status=400),
            {"msg": "record already exist"},
        )
        update_missing = DummyCallApiError(
            "region api",
            "http://region/v2/tenants/tenant-name/services/service-alias/env",
            "PUT",
            types.SimpleNamespace(status=500),
            {"msg": "update env error, record not found"},
        )
        module.region_api.add_service_env.side_effect = [add_conflict, None]
        module.region_api.update_service_env.side_effect = update_missing

        code, msg, env = module.AppEnvVarService().add_service_env_var(
            tenant,
            service,
            3389,
            "端口",
            "GRBD3CDA3389_PORT",
            "3389",
            False,
            scope="outer",
            user_name="tester",
        )

        self.assertEqual(200, code)
        self.assertEqual("success", msg)
        self.assertIs(env, created_env)
        self.assertEqual(module.region_api.add_service_env.call_count, 2)
        module.region_api.update_service_env.assert_called_once_with(
            "region-name",
            "tenant-name",
            "service-alias",
            {
                "old_env_name": "GRBD3CDA3389_PORT",
                "env_name": "GRBD3CDA3389_PORT",
                "env_value": "3389",
                "scope": "outer",
                "operator": "tester",
            },
        )
