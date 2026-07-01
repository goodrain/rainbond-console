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
from django.test import TestCase  # noqa: E402

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
    DEPLOY_TYPE_SOURCE_CODE = "source_code"
    DEPLOY_TYPE_APP_MARKET = "app_market"
    DEPLOY_TYPE_IMAGE = "image"

    @staticmethod
    def get_deploy_type(service_source):
        if service_source in ("source_code", "package_build"):
            return "source_code"
        if service_source == "market":
            return "app_market"
        return "image"

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
class AppBuildFirstDeployTrackingTests(TestCase):
    def test_app_build_tracks_source_image_and_package_deploy_types(self):
        from console.views.app_create.app_build import AppBuild

        cases = [
            ("source_code", "Java", "source_code"),
            ("docker_image", "docker-image", "image"),
            ("package_build", "Java", "source_code"),
        ]
        for service_source, language, expected_deploy_type in cases:
            view = AppBuild()
            view.tenant = Obj(tenant_name="demo-team", enterprise_id="eid-1")
            view.user = Obj(nick_name="tester", enterprise_id="eid-1")
            view.region = Obj(region_name="rainbond")
            view.oauth_instance = None
            view.app = Obj(ID=12, group_name="demo-app")
            view.service = Obj(
                service_id="draft-service",
                service_alias="draft-alias",
                service_region="rainbond",
                service_source=service_source,
                language=language,
                arch="amd64",
                service_cname="demo",
                create_status="checked",
                save=lambda: None,
            )
            built_service = Obj(
                service_id="svc-{}".format(service_source),
                service_alias="alias-{}".format(service_source),
                service_region="rainbond",
                service_source=service_source,
                language=language,
                arch="amd64",
                service_cname="demo",
            )
            tracker = {"key": "FIRST_DEPLOY_x", "enterprise_id": "eid-1"}
            request = Obj(data={"is_deploy": True}, META={})

            with mock.patch("console.views.app_create.app_build.app_service.create_region_service",
                            return_value=built_service), \
                    mock.patch("console.views.app_create.app_build.app_manage_service.deploy",
                               return_value=(200, "success", "event-{}".format(service_source))), \
                    mock.patch("console.views.app_create.app_build.enterprise_first_deploy_service.safe_begin_tracking",
                               return_value=tracker) as begin_tracking, \
                    mock.patch("console.views.app_create.app_build.enterprise_first_deploy_service.safe_bind_events") as bind_events:
                response = view.post(request)

            self.assertEqual(response.status_code, 200)
            begin_tracking.assert_called_once()
            begin_kwargs = begin_tracking.call_args[1]
            self.assertEqual("eid-1", begin_kwargs["enterprise_id"])
            self.assertEqual("demo-team", begin_kwargs["tenant_name"])
            self.assertEqual("rainbond", begin_kwargs["region_name"])
            self.assertEqual(expected_deploy_type, begin_kwargs["deploy_type"])
            self.assertEqual(language, begin_kwargs["source_language"])
            self.assertEqual(built_service.service_id, begin_kwargs["service_id"])
            self.assertEqual(built_service.service_alias, begin_kwargs["service_alias"])
            self.assertEqual("create_and_deploy", begin_kwargs["trigger"])
            bind_events.assert_called_once_with(tracker, ["event-{}".format(service_source)])
