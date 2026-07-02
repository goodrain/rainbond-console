# -*- coding: utf-8 -*-
import os
import sys
import typing
from types import ModuleType
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
openapi_client_module = ModuleType("openapi_client")
openapi_client_module.MarketOpenapiApi = type("MarketOpenapiApi", (), {})
openapi_client_module.ApiClient = type("ApiClient", (), {"__init__": lambda self, configuration=None: None})
sys.modules.setdefault("openapi_client", openapi_client_module)
openapi_client_configuration = ModuleType("openapi_client.configuration")
openapi_client_configuration.Configuration = type("Configuration", (), {"__init__": lambda self: None})
sys.modules.setdefault("openapi_client.configuration", openapi_client_configuration)
openapi_client_rest = ModuleType("openapi_client.rest")
openapi_client_rest.ApiException = type("ApiException", (Exception,), {})
sys.modules.setdefault("openapi_client.rest", openapi_client_rest)
market_openapi_api = ModuleType("openapi_client.api.market_openapi_api")
market_openapi_api.MarketOpenapiApi = type("MarketOpenapiApi", (), {})
sys.modules.setdefault("openapi_client.api.market_openapi_api", market_openapi_api)
regionapi_module = ModuleType("www.apiclient.regionapi")
regionapi_module.RegionInvokeApi = lambda *args, **kwargs: object()
sys.modules.setdefault("www.apiclient.regionapi", regionapi_module)
if not hasattr(typing, "NotRequired"):
    try:
        from typing_extensions import NotRequired
        typing.NotRequired = NotRequired
    except ImportError:
        typing.NotRequired = lambda item: item
if not hasattr(typing, "TypedDict"):
    try:
        from typing_extensions import TypedDict
        typing.TypedDict = TypedDict
    except ImportError:
        typing.TypedDict = dict

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402
from django.test import SimpleTestCase  # noqa: E402

django.setup()

from django.db import models  # noqa: E402
from django.db.models.query import QuerySet  # noqa: E402

if not hasattr(QuerySet, "__class_getitem__"):
    QuerySet.__class_getitem__ = classmethod(lambda cls, item: cls)

if sys.version_info < (3, 7):
    class _SubscriptableQuerySetMeta(type(QuerySet)):
        def __getitem__(cls, item):
            return cls

    class SubscriptableQuerySet(QuerySet, metaclass=_SubscriptableQuerySetMeta):
        pass

    models.QuerySet = SubscriptableQuerySet


class Obj(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def install_stub(module_name, **attrs):
    module = ModuleType(module_name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[module_name] = module
    return module


class FirstDeployServiceStub(object):
    DEPLOY_TYPE_IMAGE = "image"

    @staticmethod
    def build_service_app_context(app=None, component_count=1):
        context = {"component_count": component_count}
        if app is not None:
            context["app_id"] = getattr(app, "ID", "")
            context["app_name"] = getattr(app, "group_name", "")
        return context

    def safe_begin_tracking(self, *args, **kwargs):
        return None

    def safe_bind_events(self, *args, **kwargs):
        return None

    def safe_mark_failure(self, *args, **kwargs):
        return None


install_stub("console.cloud.services", check_account_quota=lambda *args, **kwargs: True)
install_stub("console.repositories.deploy_repo", deploy_repo=Obj(create_deploy_relation_by_service_id=lambda **kwargs: None))
install_stub("console.services.app", app_service=Obj(create_region_service=lambda *args, **kwargs: None))
install_stub("console.services.app_actions", app_manage_service=Obj(deploy=lambda *args, **kwargs: (200, "success", "")),
             event_service=Obj(delete_service_events=lambda *args, **kwargs: None))
install_stub("console.services.app_config",
             dependency_service=Obj(delete_region_dependency=lambda *args, **kwargs: None),
             env_var_service=Obj(delete_region_env=lambda *args, **kwargs: None),
             port_service=Obj(delete_region_port=lambda *args, **kwargs: None),
             probe_service=Obj(delete_service_probe=lambda *args, **kwargs: None),
             volume_service=Obj(delete_region_volumes=lambda *args, **kwargs: None))
install_stub("console.services.app_config.arch_service",
             arch_service=Obj(update_affinity_by_arch=lambda *args, **kwargs: None))
install_stub("console.services.compose_service",
             compose_service=Obj(get_group_compose_by_compose_id=lambda *args, **kwargs: None,
                                 get_compose_services=lambda *args, **kwargs: []))
install_stub("console.services.enterprise_first_deploy_service",
             enterprise_first_deploy_service=FirstDeployServiceStub(),
             EnterpriseFirstDeployService=FirstDeployServiceStub)
install_stub("console.services.operation_log",
             operation_log_service=Obj(generate_component_comment=lambda *args, **kwargs: "",
                                       create_component_log=lambda *args, **kwargs: None),
             Operation=Obj(BUILD="build"))


class AppBaseViewStub(object):
    pass


class CloudEnterpriseCenterViewStub(object):
    pass


class RegionTenantHeaderCloudEnterpriseCenterViewStub(object):
    pass


install_stub("console.views.app_config.base", AppBaseView=AppBaseViewStub)
install_stub("console.views.base",
             CloudEnterpriseCenterView=CloudEnterpriseCenterViewStub,
             RegionTenantHeaderCloudEnterpriseCenterView=RegionTenantHeaderCloudEnterpriseCenterViewStub)


# capability_id: console.deploy-diagnostics.v3
class ComposeBuildFirstDeployTrackingTests(SimpleTestCase):
    def test_compose_build_tracks_first_deploy_and_binds_all_component_events(self):
        from console.views.app_create.app_build import ComposeBuildView

        view = ComposeBuildView()
        view.tenant = Obj(tenant_name="demo-team", enterprise_id="eid-1")
        view.user = Obj(nick_name="tester")
        view.oauth_instance = None
        view.region_name = "rainbond"
        view.region = Obj(region_name="rainbond")
        view.app = Obj(ID=12, group_name="compose-app")
        view.group = view.app

        service_a = Obj(service_id="draft-a", service_alias="draft-a", service_source="docker_compose")
        service_b = Obj(service_id="draft-b", service_alias="draft-b", service_source="docker_compose")
        built_a = Obj(
            service_id="svc-a",
            service_alias="alias-a",
            service_region="rainbond",
            service_source="docker_compose",
            language="docker-compose",
            arch="amd64",
        )
        built_b = Obj(
            service_id="svc-b",
            service_alias="alias-b",
            service_region="rainbond",
            service_source="docker_compose",
            language="docker-compose",
            arch="amd64",
        )
        tracker = {"key": "FIRST_DEPLOY_x", "enterprise_id": "eid-1"}
        request = Obj(data={"compose_id": "compose-1"}, META={})

        with mock.patch("console.views.app_create.app_build.compose_service.get_group_compose_by_compose_id",
                        return_value=Obj(create_status="checked", save=lambda: None)), \
                mock.patch("console.views.app_create.app_build.compose_service.get_compose_services",
                           return_value=[service_a, service_b]), \
                mock.patch("console.views.app_create.app_build.app_service.create_region_service",
                           side_effect=[built_a, built_b]), \
                mock.patch("console.views.app_create.app_build.app_manage_service.deploy",
                           side_effect=[(200, "success", "event-a"), (200, "success", "event-b")]), \
                mock.patch("console.views.app_create.app_build.enterprise_first_deploy_service.safe_begin_tracking",
                           return_value=tracker) as begin_tracking, \
                mock.patch("console.views.app_create.app_build.enterprise_first_deploy_service.safe_bind_events") as bind_events:
            response = view.post(request)

        self.assertEqual(response.status_code, 200)
        begin_tracking.assert_called_once()
        begin_kwargs = begin_tracking.call_args[1]
        self.assertEqual(begin_kwargs["enterprise_id"], "eid-1")
        self.assertEqual(begin_kwargs["tenant_name"], "demo-team")
        self.assertEqual(begin_kwargs["region_name"], "rainbond")
        self.assertEqual(begin_kwargs["deploy_type"], "image")
        self.assertEqual(begin_kwargs["trigger"], "compose_build")
        self.assertEqual(begin_kwargs["app_context"]["component_count"], 2)
        bind_events.assert_called_once_with(
            tracker,
            ["event-a", "event-b"],
            service_ids=["svc-a", "svc-b"],
            service_aliases=["alias-a", "alias-b"])
