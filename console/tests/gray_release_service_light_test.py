import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from urllib.parse import parse_qs, urlsplit
from unittest import TestCase, mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "services" / "gray_release_service.py"


class ServiceHandleException(Exception):
    pass


def _package(name):
    module = ModuleType(name)
    module.__path__ = []
    return module


def _module(name, **attrs):
    module = ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    return module


def _atomic(func=None):
    if func is None:
        return _atomic
    return func


def _build_stub_modules():
    console_exception = _package("console.exception")
    console_exception_main = _module(
        "console.exception.main", ServiceHandleException=ServiceHandleException
    )
    console_exception.main = console_exception_main

    console_models = _package("console.models")
    console_models_main = _module("console.models.main", GrayReleaseStatus=object(), GrayReleaseRecord=object(), RegionConfig=object())
    console_models.main = console_models_main

    console_repositories = _package("console.repositories")
    console_repositories_app_config = _module(
        "console.repositories.app_config", domain_repo=SimpleNamespace()
    )
    console_repositories_gray_release = _module(
        "console.repositories.gray_release_repo", gray_release_repo=SimpleNamespace()
    )
    console_repositories_region_app = _module(
        "console.repositories.region_app", region_app_repo=SimpleNamespace()
    )
    console_repositories.app_config = console_repositories_app_config
    console_repositories.gray_release_repo = console_repositories_gray_release
    console_repositories.region_app = console_repositories_region_app

    console_services = _package("console.services")
    console_services_app_actions = _module(
        "console.services.app_actions", app_manage_service=SimpleNamespace()
    )
    console_services_app = _module(
        "console.services.app", app_market_service=SimpleNamespace()
    )
    console_services_group = _module(
        "console.services.group_service", group_service=SimpleNamespace()
    )
    console_services_market = _module(
        "console.services.market_app_service", market_app_service=SimpleNamespace()
    )
    console_services_app_config = _package("console.services.app_config")

    class DomainService(object):
        pass

    console_services_domain_service = _module(
        "console.services.app_config.domain_service", DomainService=DomainService
    )
    console_services.app_actions = console_services_app_actions
    console_services.app = console_services_app
    console_services.group_service = console_services_group
    console_services.market_app_service = console_services_market
    console_services.app_config = console_services_app_config
    console_services_app_config.domain_service = console_services_domain_service

    django_pkg = _package("django")
    django_db = _module(
        "django.db", transaction=SimpleNamespace(atomic=_atomic)
    )
    django_forms = _package("django.forms")
    django_forms_models = _module(
        "django.forms.models", model_to_dict=lambda value: value
    )
    django_pkg.db = django_db
    django_pkg.forms = django_forms
    django_forms.models = django_forms_models

    www_pkg = _package("www")
    www_apiclient = _package("www.apiclient")
    www_apiclient_regionapi = _module(
        "www.apiclient.regionapi", RegionInvokeApi=lambda: None
    )
    www_models = _package("www.models")
    www_models_main = _module(
        "www.models.main",
        ServiceDomain=object(),
        ServiceGroup=object(),
        Tenants=object(),
        Users=object(),
        TenantServiceInfo=object(),
        TenantServicesPort=SimpleNamespace(objects=None),
    )
    www_utils = _package("www.utils")
    www_utils_crypt = _module("www.utils.crypt", make_uuid=lambda: "uuid")
    www_pkg.apiclient = www_apiclient
    www_pkg.models = www_models
    www_pkg.utils = www_utils
    www_apiclient.regionapi = www_apiclient_regionapi
    www_models.main = www_models_main
    www_utils.crypt = www_utils_crypt

    return {
        "console.exception": console_exception,
        "console.exception.main": console_exception_main,
        "console.models": console_models,
        "console.models.main": console_models_main,
        "console.repositories": console_repositories,
        "console.repositories.app_config": console_repositories_app_config,
        "console.repositories.gray_release_repo": console_repositories_gray_release,
        "console.repositories.region_app": console_repositories_region_app,
        "console.services": console_services,
        "console.services.app_actions": console_services_app_actions,
        "console.services.app": console_services_app,
        "console.services.group_service": console_services_group,
        "console.services.market_app_service": console_services_market,
        "console.services.app_config": console_services_app_config,
        "console.services.app_config.domain_service": console_services_domain_service,
        "django": django_pkg,
        "django.db": django_db,
        "django.forms": django_forms,
        "django.forms.models": django_forms_models,
        "www": www_pkg,
        "www.apiclient": www_apiclient,
        "www.apiclient.regionapi": www_apiclient_regionapi,
        "www.models": www_models,
        "www.models.main": www_models_main,
        "www.utils": www_utils,
        "www.utils.crypt": www_utils_crypt,
    }


def _load_gray_release_service_module():
    spec = importlib.util.spec_from_file_location(
        "gray_release_service_under_test", MODULE_PATH
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class GrayReleaseRouteUpdateLightTests(TestCase):
    # capability_id: console.gray-release.update-route-query-uses-original-port
    def test_update_route_query_uses_original_service_port_when_ports_differ(self):
        stub_modules = _build_stub_modules()

        with mock.patch.dict(sys.modules, stub_modules, clear=False):
            module = _load_gray_release_service_module()
            region_api = mock.Mock()
            sys.modules["www.apiclient.regionapi"].RegionInvokeApi = mock.Mock(
                return_value=region_api
            )

            new_port = SimpleNamespace(
                k8s_service_name="test-2033", container_port=8080
            )
            original_route_port = SimpleNamespace(
                k8s_service_name="test", container_port=80
            )
            port_querysets = [
                mock.Mock(first=mock.Mock(return_value=new_port)),
                mock.Mock(first=mock.Mock(return_value=None)),
                mock.Mock(first=mock.Mock(return_value=original_route_port)),
            ]
            sys.modules["www.models.main"].TenantServicesPort = SimpleNamespace(
                objects=SimpleNamespace(filter=mock.Mock(side_effect=port_querysets))
            )

            service = module.GrayReleaseService()
            team = SimpleNamespace(
                tenant_id="tenant-id", tenant_name="demo-team", namespace="demo-ns"
            )
            app = SimpleNamespace(ID="internal-app-id", app_id="region-app-id")
            domain = {
                "name": "123test.rainbond.cnp-ps-s-testsvc",
                "match": {
                    "hosts": ["test.rainbond.cn"],
                    "paths": ["/*"],
                },
                "plugins": [],
                "authentication": {},
                "websocket": False,
            }
            original_service = SimpleNamespace(
                service_id="origin-svc-id", service_alias="test", service_cname="test"
            )
            new_service = SimpleNamespace(
                service_id="gray-svc-id",
                service_alias="test-2033",
                service_cname="test",
            )

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

        path = region_api.api_gateway_post_proxy.call_args[0][2]
        query = parse_qs(urlsplit(path).query)

        self.assertEqual(query.get("service_alias"), ["test"])
        self.assertEqual(query.get("port"), ["80"])
