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


class ServiceHandleException(Exception):
    def __init__(self, msg="", msg_show="", status_code=500, **kwargs):
        super(ServiceHandleException, self).__init__(msg_show or msg)
        self.msg = msg
        self.msg_show = msg_show
        self.status_code = status_code


class SourceCodeType(object):
    GITLAB_MANUAL = "gitlab_manual"
    GITLAB_SELF = "gitlab_self"
    GITLAB_NEW = "gitlab_new"
    GITLAB_EXIT = "gitlab_exit"
    GITHUB = "github"
    GITLAB_DEMO = "gitlab_demo"


class RegionInvokeApi(object):
    class CallApiError(Exception):
        pass


class FirstDeployServiceStub(object):
    DEPLOY_TYPE_SOURCE_CODE = "source_code"

    def __init__(self):
        self.safe_begin_tracking = mock.Mock(return_value={"key": "first-deploy"})
        self.safe_bind_events = mock.Mock()
        self.safe_mark_failure = mock.Mock()

    def get_deploy_type(self, service_source):
        return self.DEPLOY_TYPE_SOURCE_CODE

    @staticmethod
    def build_service_app_context(app=None, component_count=1):
        context = {"component_count": component_count}
        if app is not None:
            context["app_id"] = getattr(app, "ID", "")
            context["app_name"] = getattr(app, "group_name", "")
        return context

    def reset(self):
        self.safe_begin_tracking.reset_mock(return_value=True)
        self.safe_begin_tracking.return_value = {"key": "first-deploy"}
        self.safe_bind_events.reset_mock()
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
console_app_service = Obj()
package_upload_service = Obj()
app_manage_service = Obj()
app_check_service = Obj()
arch_service = Obj()
group_service = Obj()
deploy_repo = Obj()
service_source_repo = Obj()

install_stub("console.constants", SourceCodeType=SourceCodeType)
install_stub(
    "console.exception.main",
    ServiceHandleException=ServiceHandleException,
    AbortRequest=ServiceHandleException)
install_stub("console.repositories.app", service_source_repo=service_source_repo)
install_stub("console.repositories.deploy_repo", deploy_repo=deploy_repo)
install_stub("console.services.app", app_service=console_app_service, package_upload_service=package_upload_service)
install_stub("console.services.app_actions", app_manage_service=app_manage_service)
install_stub("console.services.app_check_service", app_check_service=app_check_service)
install_stub("console.services.app_config", package=True)
install_stub("console.services.app_config.arch_service", arch_service=arch_service)
install_stub("console.services.group_service", group_service=group_service)
install_stub(
    "console.services.enterprise_first_deploy_service",
    enterprise_first_deploy_service=first_deploy_service)
install_stub("www.apiclient.regionapi", RegionInvokeApi=RegionInvokeApi)
install_stub("www.models.main", ServiceGroup=object, TenantServiceInfo=object, Tenants=object, Users=object)
install_stub("www.utils.crypt", make_uuid=lambda *args, **kwargs: "uuid-1")

from console.services.source_component_service import source_component_service  # noqa: E402
from console.services.package_component_service import package_component_service  # noqa: E402
import console.services.source_component_service as source_module  # noqa: E402
import console.services.package_component_service as package_module  # noqa: E402


class AutoCreateFirstDeployTrackingTests(TestCase):
    def setUp(self):
        first_deploy_service.reset()
        console_app_service.is_k8s_component_name_duplicate = mock.Mock(return_value=False)
        console_app_service.create_service_source_info = mock.Mock()
        console_app_service.create_source_code_app = mock.Mock()
        console_app_service.create_package_upload_info = mock.Mock()
        console_app_service.create_region_service = mock.Mock()
        package_upload_service.get_upload_record = mock.Mock(return_value=Obj(create_time="2026-03-20 16:00:00"))
        package_upload_service.update_upload_record = mock.Mock()
        group_service.add_service_to_group = mock.Mock(return_value=(200, "success"))
        app_check_service.check_service = mock.Mock(return_value=(200, "success", {"check_uuid": "chk-1"}))
        app_check_service.save_service_check_info = mock.Mock()
        app_manage_service.change_lang_and_package_tool = mock.Mock(return_value=(200, "success"))
        app_manage_service.deploy = mock.Mock(return_value=(200, "success", "evt-deploy-1"))
        arch_service.update_affinity_by_arch = mock.Mock()
        deploy_repo.create_deploy_relation_by_service_id = mock.Mock()
        service_source_repo.get_service_source = mock.Mock(return_value=None)
        service_source_repo.update_or_create_service_source = mock.Mock()
        source_module.region_api.get_service_check_info = mock.Mock(return_value=(
            None,
            {"bean": {"check_status": "success", "service_info": [{"language": "Python"}], "error_infos": []}},
        ))
        package_module.region_api.get_upload_file_dir = mock.Mock(return_value=(
            None,
            {"bean": {"packages": ["demo.war"]}},
        ))

    def test_source_auto_create_deploy_tracks_first_deploy(self):
        user = Obj(user_id=1, pk=1, nick_name="admin")
        team = Obj(tenant_id="team-1", tenant_name="demo-team", enterprise_id="eid-1")
        app = Obj(ID=12, region_name="rainbond", group_name="demo-app")
        component = Obj(
            service_id="svc-source-1",
            service_alias="alias-source-1",
            service_cname="source-demo",
            service_region="rainbond",
            service_source="source_code",
            arch="amd64",
            check_uuid="chk-1")
        region_component = Obj(
            service_id="svc-source-1",
            service_alias="alias-source-1",
            service_cname="source-demo",
            service_region="rainbond",
            service_source="source_code",
            arch="amd64")
        console_app_service.create_source_code_app.return_value = (200, "success", component)
        console_app_service.create_region_service.return_value = region_component

        source_component_service.auto_create_component(
            team=team,
            app=app,
            user=user,
            service_cname="source-demo",
            code_from="gitlab_manual",
            git_url="https://git.example.com/demo.git",
            code_version="main")

        tracking_kwargs = first_deploy_service.safe_begin_tracking.call_args[1]
        self.assertEqual(tracking_kwargs["enterprise_id"], "eid-1")
        self.assertEqual(tracking_kwargs["tenant_name"], "demo-team")
        self.assertEqual(tracking_kwargs["region_name"], "rainbond")
        self.assertEqual(tracking_kwargs["deploy_type"], "source_code")
        self.assertEqual(tracking_kwargs["source_language"], "Python")
        self.assertEqual(tracking_kwargs["service_id"], "svc-source-1")
        self.assertEqual(tracking_kwargs["service_alias"], "alias-source-1")
        self.assertEqual(tracking_kwargs["trigger"], "source_auto_create")
        self.assertEqual(tracking_kwargs["app_context"], {
            "app_id": 12,
            "app_name": "demo-app",
            "component_count": 1,
        })
        first_deploy_service.safe_bind_events.assert_called_once_with(
            {"key": "first-deploy"},
            ["evt-deploy-1"],
            service_ids=["svc-source-1"],
            service_alias="alias-source-1")

    def test_package_auto_create_deploy_tracks_first_deploy(self):
        user = Obj(user_id=1, pk=1, nick_name="admin")
        team = Obj(tenant_id="team-1", tenant_name="demo-team", enterprise_id="eid-1")
        app = Obj(ID=12, region_name="rainbond", group_name="demo-app")
        component = Obj(
            service_id="svc-pkg-1",
            service_alias="alias-pkg-1",
            service_cname="package-demo",
            service_region="rainbond",
            service_source="package_build",
            arch="amd64",
            check_uuid="chk-1")
        region_component = Obj(
            service_id="svc-pkg-1",
            service_alias="alias-pkg-1",
            service_cname="package-demo",
            service_region="rainbond",
            service_source="package_build",
            arch="amd64")
        console_app_service.create_package_upload_info.return_value = component
        console_app_service.create_region_service.return_value = region_component
        with mock.patch.object(
                package_module.source_component_service,
                "_wait_for_check_result",
                return_value={
                    "check_status": "success",
                    "service_info": [{"language": "Java-war"}],
                    "error_infos": [],
                }), mock.patch.object(package_module.source_component_service, "apply_default_build_config"):
            package_component_service.auto_create_component(
                team=team,
                app=app,
                user=user,
                event_id="evt-upload-1",
                service_cname="package-demo")

        tracking_kwargs = first_deploy_service.safe_begin_tracking.call_args[1]
        self.assertEqual(tracking_kwargs["enterprise_id"], "eid-1")
        self.assertEqual(tracking_kwargs["tenant_name"], "demo-team")
        self.assertEqual(tracking_kwargs["region_name"], "rainbond")
        self.assertEqual(tracking_kwargs["deploy_type"], "source_code")
        self.assertEqual(tracking_kwargs["source_language"], "Java-war")
        self.assertEqual(tracking_kwargs["service_id"], "svc-pkg-1")
        self.assertEqual(tracking_kwargs["service_alias"], "alias-pkg-1")
        self.assertEqual(tracking_kwargs["trigger"], "package_auto_create")
        self.assertEqual(tracking_kwargs["app_context"], {
            "app_id": 12,
            "app_name": "demo-app",
            "component_count": 1,
        })
        first_deploy_service.safe_bind_events.assert_called_once_with(
            {"key": "first-deploy"},
            ["evt-deploy-1"],
            service_ids=["svc-pkg-1"],
            service_alias="alias-pkg-1")
