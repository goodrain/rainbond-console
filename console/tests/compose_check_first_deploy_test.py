# -*- coding: utf-8 -*-
import collections
import os
import sys
import typing
from types import ModuleType
from unittest import mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))
if not hasattr(typing, "NotRequired"):
    typing.NotRequired = typing.Optional

sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
os.environ.setdefault("DISABLE_FIRST_DEPLOY_SWEEPER", "1")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402
from django.test import SimpleTestCase  # noqa: E402

django.setup()


class Obj(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class FirstDeployServiceStub(object):
    DEPLOY_TYPE_IMAGE = "image"
    FAILURE_STAGE_BUILD = "build"

    def __init__(self):
        self.safe_begin_tracking = mock.Mock(return_value={"key": "first-deploy"})
        self.safe_mark_failure = mock.Mock()

    @staticmethod
    def build_service_app_context(app=None, component_count=1):
        context = {"component_count": component_count}
        if app is not None:
            context["app_id"] = getattr(app, "ID", "")
            context["app_name"] = getattr(app, "group_name", "")
        return context

    def reset(self):
        self.safe_begin_tracking.reset_mock()
        self.safe_begin_tracking.return_value = {"key": "first-deploy"}
        self.safe_mark_failure.reset_mock()


def install_stub(module_name, package=False, **attrs):
    module = ModuleType(module_name)
    if package:
        module.__path__ = []
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[module_name] = module
    return module


first_deploy_service = FirstDeployServiceStub()
compose_service = Obj()
app_check_service = Obj()


class RegionTenantHeaderViewStub(object):
    pass


install_stub(
    "console.exception.main",
    AccountOverdueException=type("AccountOverdueException", (Exception,), {}),
    BusinessException=type("BusinessException", (Exception,), {}),
    ResourceNotEnoughException=type("ResourceNotEnoughException", (Exception,), {}),
    ServiceHandleException=type("ServiceHandleException", (Exception,), {}))
install_stub("console.models.main", ComposeGroup=object)
install_stub("console.repositories.compose_repo", compose_repo=Obj(get_group_compose_by_compose_id=lambda *args: None))
install_stub("console.repositories.group", group_repo=Obj(get_group_by_pk=lambda *args: None))
install_stub("console.services.app_check_service", app_check_service=app_check_service)
install_stub("console.services.compose_service", compose_service=compose_service)
install_stub("console.services.enterprise_first_deploy_service", enterprise_first_deploy_service=first_deploy_service)
install_stub("console.services.group_service", group_service=Obj())
install_stub("console.services.team_services", team_services=Obj())
install_stub("console.views.base", RegionTenantHeaderView=RegionTenantHeaderViewStub)
install_stub("www.models.main", ServiceGroup=object)
install_stub(
    "www.utils.return_message",
    general_message=lambda code, msg, msg_show, **kwargs: {
        "code": code,
        "msg": msg,
        "msg_show": msg_show,
        "data": kwargs,
    })

from console.views.app_create.docker_compose import ComposeCheckView  # noqa: E402


# capability_id: console.deploy-diagnostics.v3
class ComposeCheckFirstDeployTrackingTests(SimpleTestCase):
    def setUp(self):
        first_deploy_service.reset()
        self.view = ComposeCheckView()
        self.view.tenant = Obj(tenant_name="demo-team", enterprise_id="eid-1")
        self.view.user = Obj(nick_name="tester")
        self.view.response_region = "rainbond"
        self.view.group = Obj(ID=12, group_name="compose-app")

    def test_compose_check_task_failure_records_first_deploy_failure(self):
        compose_service.check_compose = mock.Mock(return_value=(500, "compose yaml invalid", None))
        request = Obj(data={"compose_id": "compose-1"})

        response = self.view.post(request)

        self.assertEqual(response.data["code"], 500)
        first_deploy_service.safe_begin_tracking.assert_called_once()
        begin_kwargs = first_deploy_service.safe_begin_tracking.call_args[1]
        self.assertEqual(begin_kwargs["enterprise_id"], "eid-1")
        self.assertEqual(begin_kwargs["tenant_name"], "demo-team")
        self.assertEqual(begin_kwargs["region_name"], "rainbond")
        self.assertEqual(begin_kwargs["deploy_type"], "image")
        self.assertEqual(begin_kwargs["operator"], "tester")
        self.assertEqual(begin_kwargs["source_language"], "docker-compose")
        self.assertEqual(begin_kwargs["trigger"], "compose_check")
        self.assertEqual(begin_kwargs["app_context"]["compose_id"], "compose-1")
        self.assertEqual(begin_kwargs["workload_context"]["source_type"], "docker-compose")
        first_deploy_service.safe_mark_failure.assert_called_once_with(
            {"key": "first-deploy"},
            reason="compose yaml invalid",
            failure_stage="build")

    def test_compose_check_result_failure_records_first_deploy_failure(self):
        group_compose = Obj(compose_id="compose-1", create_status="checking")
        data = {
            "check_status": "failure",
            "error_infos": [{"error_info": "compose service image format invalid"}],
            "service_info": [],
        }
        compose_service.get_group_compose_by_compose_id = mock.Mock(return_value=group_compose)
        compose_service.save_compose_services = mock.Mock(return_value=(200, "success", []))
        compose_service.wrap_compose_check_info = mock.Mock(return_value={"check_status": "failure", "service_info": []})
        app_check_service.get_service_check_info = mock.Mock(return_value=(200, "success", data))
        request = Obj(GET={"check_uuid": "check-1", "compose_id": "compose-1"})

        with mock.patch("console.views.app_create.docker_compose.transaction.savepoint_commit"):
            response = self.view.get(request)

        self.assertEqual(response.data["data"]["bean"]["check_status"], "failure")
        first_deploy_service.safe_begin_tracking.assert_called_once()
        begin_kwargs = first_deploy_service.safe_begin_tracking.call_args[1]
        self.assertEqual(begin_kwargs["trigger"], "compose_check")
        self.assertEqual(begin_kwargs["app_context"]["compose_id"], "compose-1")
        self.assertEqual(begin_kwargs["workload_context"]["check_uuid"], "check-1")
        first_deploy_service.safe_mark_failure.assert_called_once_with(
            {"key": "first-deploy"},
            reason="compose service image format invalid",
            failure_stage="build")
