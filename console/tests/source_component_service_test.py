# -*- coding: utf-8 -*-
import collections
import os
import sys
import typing
from types import ModuleType
from unittest.mock import patch

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))
if not hasattr(typing, "NotRequired"):
    typing.NotRequired = typing.Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
if "openapi_client" not in sys.modules:
    openapi_client_module = ModuleType("openapi_client")
    configuration_module = ModuleType("openapi_client.configuration")
    rest_module = ModuleType("openapi_client.rest")

    class _Configuration(object):
        def __init__(self):
            self.host = ""
            self.api_key = {}

    configuration_module.Configuration = _Configuration
    rest_module.ApiException = type("ApiException", (Exception,), {})
    openapi_client_module.ApiClient = object
    openapi_client_module.MarketOpenapiApi = object
    openapi_client_module.configuration = configuration_module
    openapi_client_module.rest = rest_module
    sys.modules["openapi_client"] = openapi_client_module
    sys.modules["openapi_client.configuration"] = configuration_module
    sys.modules["openapi_client.rest"] = rest_module

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django
from django.test import SimpleTestCase

django.setup()

from django.db.models.query import QuerySet

if not hasattr(QuerySet, "__class_getitem__"):
    QuerySet.__class_getitem__ = classmethod(lambda cls, item: cls)

from console.exception.main import ServiceHandleException


class Obj(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


# capability_id: console.component.create-from-source
# capability_id: console.deploy-diagnostics.source-check
class SourceComponentServiceTests(SimpleTestCase):

    # capability_id: console.source-component.auto-create-flow
    @patch("console.services.source_component_service.deploy_repo.create_deploy_relation_by_service_id")
    @patch("console.services.source_component_service.app_manage_service.deploy")
    @patch("console.services.source_component_service.arch_service.update_affinity_by_arch")
    @patch("console.services.source_component_service.console_app_service.create_region_service")
    @patch("console.services.source_component_service.app_manage_service.change_lang_and_package_tool")
    @patch("console.services.source_component_service.app_check_service.save_service_check_info")
    @patch("console.services.source_component_service.region_api.get_service_check_info")
    @patch("console.services.source_component_service.app_check_service.check_service")
    @patch("console.services.source_component_service.group_service.add_service_to_group")
    @patch("console.services.source_component_service.console_app_service.create_service_source_info")
    @patch("console.services.source_component_service.console_app_service.create_source_code_app")
    @patch("console.services.source_component_service.console_app_service.is_k8s_component_name_duplicate")
    # capability_id: console.source-component.auto-create-flow
    def test_auto_create_component_runs_full_source_flow(
            self,
            mock_name_duplicate,
            mock_create_source,
            mock_create_source_info,
            mock_add_to_group,
            mock_check_service,
            mock_get_check_info,
            mock_save_check_info,
            mock_change_lang_and_package_tool,
            mock_create_region_service,
            mock_update_affinity,
            mock_deploy,
            mock_create_deploy_relation,
    ):
        from console.services.source_component_service import source_component_service

        user = Obj(user_id=1, pk=1, nick_name="admin")
        team = Obj(tenant_id="team-1", tenant_name="demo-team", enterprise_id="eid-1")
        app = Obj(ID=12, region_name="rainbond", group_name="demo-app")
        service = Obj(
            service_id="svc-1",
            service_alias="alias-1",
            service_cname="component-1",
            service_region="rainbond",
            service_source="source_code",
            create_status="creating",
            arch="amd64",
            check_uuid="chk-1",
            check_event_id="evt-check-1",
        )
        service.to_dict = lambda: {"service_id": "svc-1", "service_alias": "alias-1"}
        service.save = lambda: None
        built_service = Obj(service_id="svc-1", create_status="complete", arch="amd64")

        mock_name_duplicate.return_value = False
        mock_create_source.return_value = (200, "success", service)
        mock_add_to_group.return_value = (200, "success")
        mock_check_service.return_value = (200, "success", {"check_uuid": "chk-1"})
        mock_get_check_info.return_value = (
            None,
            {"bean": {"check_status": "success", "error_infos": [], "service_info": [{
                "language": "static",
                "runtime_info": {
                    "framework": {"name": "other-static"},
                    "build_config": {"output_dir": "dist", "build_command": "npm run build", "start_command": ""},
                    "package_manager": {"name": "npm"},
                    "config_files": {"has_npmrc": False, "has_yarnrc": False},
                    "language_version": "20.20.0",
                }
            }]}}
        )
        mock_create_region_service.return_value = built_service
        mock_change_lang_and_package_tool.return_value = (200, "success")
        mock_deploy.return_value = (200, "success", "evt-1")

        def save_check_info(team_obj, app_id, service_obj, data):
            service_obj.create_status = "checked"

        mock_save_check_info.side_effect = save_check_info

        result = source_component_service.auto_create_component(
            team=team,
            app=app,
            user=user,
            service_cname="component-1",
            code_from="gitlab_manual",
            git_url="https://git.example.com/demo.git",
            code_version="v1.0.0",
            version_type="tag",
            subdirectories="services/api",
            username="git-user",
            password="git-pass",
            k8s_component_name="component-1",
        )

        self.assertEqual(result["service_id"], "svc-1")
        self.assertTrue(result["built"])
        self.assertEqual(result["git_url"], "https://git.example.com/demo.git?dir=services/api")
        self.assertEqual(result["code_version"], "tag:v1.0.0")
        self.assertEqual(result["server_type"], "git")
        mock_create_source.assert_called_once()
        create_args = mock_create_source.call_args[0]
        self.assertEqual(create_args[5], "https://git.example.com/demo.git?dir=services/api")
        self.assertEqual(create_args[7], "tag:v1.0.0")
        self.assertEqual(create_args[8], "git")
        mock_create_source_info.assert_called_once_with(team, service, "git-user", "git-pass")
        mock_add_to_group.assert_called_once_with(team, "rainbond", 12, "svc-1")
        mock_check_service.assert_called_once()
        mock_change_lang_and_package_tool.assert_called_once()
        mock_create_region_service.assert_called_once_with(team, service, "admin")
        mock_update_affinity.assert_called_once()
        mock_deploy.assert_called_once_with(team, built_service, user)
        mock_create_deploy_relation.assert_called_once_with(service_id="svc-1")

    # capability_id: console.source-component.detect-server-type
    # capability_id: console.source-component.detect-server-type
    def test_infer_server_type_supports_git_svn_and_oss(self):
        from console.services.source_component_service import source_component_service

        self.assertEqual(source_component_service.infer_server_type("https://git.example.com/demo.git"), "git")
        self.assertEqual(source_component_service.infer_server_type("svn://repo.example.com/project/trunk"), "svn")
        self.assertEqual(source_component_service.infer_server_type("oss://bucket/path/app.tar.gz"), "oss")

    # capability_id: console.source-component.invalid-server-type
    def test_infer_server_type_rejects_unknown_server_type(self):
        from console.services.source_component_service import source_component_service

        with self.assertRaises(ServiceHandleException) as context:
            source_component_service.infer_server_type("https://git.example.com/demo.git", "ftp")

        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(context.exception.msg_show, "参数server_type无效")

    # capability_id: console.source-component.normalize-code-source
    # capability_id: console.source-component.normalize-code-source
    def test_normalize_code_from_maps_generic_git_to_gitlab_manual(self):
        from console.services.source_component_service import source_component_service

        self.assertEqual(
            source_component_service.normalize_code_from("git", "https://gitee.com/rainbond/demo-2048.git"),
            "gitlab_manual",
        )
        self.assertEqual(
            source_component_service.normalize_code_from("git", "https://github.com/openai/openai-python.git"),
            "github",
        )
        self.assertEqual(
            source_component_service.normalize_code_from(
                "git",
                "https://ghfast.top/https://github.com/openai/openai-python.git",
            ),
            "gitlab_manual",
        )
        self.assertEqual(
            source_component_service.normalize_code_from("gitlab_manual", "https://gitee.com/rainbond/demo-2048.git"),
            "gitlab_manual",
        )

    # capability_id: console.source-component.normalize-git-url
    def test_normalize_git_url_appends_subdirectory_once(self):
        from console.services.source_component_service import source_component_service

        self.assertEqual(
            source_component_service.normalize_git_url("https://git.example.com/demo.git", "services/api"),
            "https://git.example.com/demo.git?dir=services/api",
        )
        self.assertEqual(
            source_component_service.normalize_git_url(
                "https://git.example.com/demo.git?dir=services/api", "services/api"
            ),
            "https://git.example.com/demo.git?dir=services/api",
        )

    # capability_id: console.source-component.normalize-code-version
    def test_normalize_code_version_handles_tag_and_oss(self):
        from console.services.source_component_service import source_component_service

        self.assertEqual(
            source_component_service.normalize_code_version("v1.0.0", "tag", "git"),
            "tag:v1.0.0",
        )
        self.assertEqual(
            source_component_service.normalize_code_version("master", "branch", "git"),
            "master",
        )
        self.assertEqual(
            source_component_service.normalize_code_version("v1.0.0", "tag", "oss"),
            "",
        )

    # capability_id: console.source-component.duplicate-name-guard
    @patch("console.services.source_component_service.console_app_service.is_k8s_component_name_duplicate", return_value=True)
    def test_auto_create_component_rejects_duplicate_k8s_component_name(self, mock_name_duplicate):
        from console.services.source_component_service import source_component_service

        user = Obj(user_id=1, pk=1, nick_name="admin")
        team = Obj(tenant_id="team-1", tenant_name="demo-team", enterprise_id="eid-1")
        app = Obj(ID=12, region_name="rainbond", group_name="demo-app")

        with self.assertRaises(ServiceHandleException) as context:
            source_component_service.auto_create_component(
                team=team,
                app=app,
                user=user,
                service_cname="component-1",
                code_from="gitlab_manual",
                git_url="https://git.example.com/demo.git",
                k8s_component_name="component-1",
            )

        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(context.exception.msg_show, "组件英文名称已存在")
        mock_name_duplicate.assert_called_once_with(12, "component-1")

    @patch("console.services.source_component_service.console_app_service.create_source_code_app")
    @patch("console.services.source_component_service.group_service.add_service_to_group")
    @patch("console.services.source_component_service.app_check_service.check_service")
    @patch("console.services.source_component_service.region_api.get_service_check_info")
    # capability_id: console.source-component.check-failure
    def test_auto_create_component_raises_on_check_failure(
            self, mock_get_check_info, mock_check_service, mock_add_to_group,
            mock_create_source):
        from console.services.source_component_service import source_component_service

        user = Obj(user_id=1, pk=1, nick_name="admin")
        team = Obj(tenant_id="team-1", tenant_name="demo-team", enterprise_id="eid-1")
        app = Obj(ID=12, region_name="rainbond", group_name="demo-app")
        service = Obj(
            service_id="svc-1",
            service_alias="alias-1",
            service_cname="component-1",
            service_region="rainbond",
            service_source="source_code",
            create_status="creating",
            arch="amd64",
            check_uuid="chk-1",
        )
        service.to_dict = lambda: {"service_id": "svc-1"}
        service.save = lambda: None

        mock_create_source.return_value = (200, "success", service)
        mock_add_to_group.return_value = (200, "success")
        mock_check_service.return_value = (200, "success", {"check_uuid": "chk-1"})
        mock_get_check_info.return_value = (
            None,
            {"bean": {"check_status": "failure", "error_infos": [{"error_info": "bad repo"}], "service_info": []}},
        )

        with patch.object(source_component_service, "_report_source_check_failure") as mock_report_check_failure:
            with self.assertRaises(ServiceHandleException) as context:
                source_component_service.auto_create_component(
                    team=team,
                    app=app,
                    user=user,
                    service_cname="component-1",
                    code_from="gitlab_manual",
                    git_url="https://git.example.com/demo.git",
                )

        self.assertIn("bad repo", context.exception.msg_show)
        mock_report_check_failure.assert_called_once()
        report_args = mock_report_check_failure.call_args[0]
        self.assertEqual(report_args[0], team)
        self.assertEqual(report_args[4], "https://git.example.com/demo.git")
        self.assertEqual(report_args[7], "chk-1")
        self.assertEqual(report_args[8], "bad repo")

    # capability_id: console.source-component.multi-service-guard
    @patch("console.services.source_component_service.console_app_service.create_source_code_app")
    @patch("console.services.source_component_service.group_service.add_service_to_group")
    @patch("console.services.source_component_service.app_check_service.check_service")
    @patch("console.services.source_component_service.region_api.get_service_check_info")
    def test_auto_create_component_rejects_multi_service_detection(
            self, mock_get_check_info, mock_check_service, mock_add_to_group, mock_create_source):
        from console.services.source_component_service import source_component_service

        user = Obj(user_id=1, pk=1, nick_name="admin")
        team = Obj(tenant_id="team-1", tenant_name="demo-team", enterprise_id="eid-1")
        app = Obj(ID=12, region_name="rainbond", group_name="demo-app")
        service = Obj(
            service_id="svc-1",
            service_alias="alias-1",
            service_cname="component-1",
            service_region="rainbond",
            service_source="source_code",
            create_status="creating",
            arch="amd64",
            check_uuid="chk-1",
        )
        service.to_dict = lambda: {"service_id": "svc-1"}
        service.save = lambda: None

        mock_create_source.return_value = (200, "success", service)
        mock_add_to_group.return_value = (200, "success")
        mock_check_service.return_value = (200, "success", {"check_uuid": "chk-1"})
        mock_get_check_info.return_value = (
            None,
            {"bean": {"check_status": "success", "error_infos": [], "service_info": [{}, {}]}},
        )

        with self.assertRaises(ServiceHandleException) as context:
            source_component_service.auto_create_component(
                team=team,
                app=app,
                user=user,
                service_cname="component-1",
                code_from="gitlab_manual",
                git_url="https://git.example.com/demo.git",
            )

        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(context.exception.msg_show, "检测到多组件源码，请使用多组件创建流程")

    # capability_id: console.source-component.check-request-failure
    @patch("console.services.source_component_service.console_app_service.create_source_code_app")
    @patch("console.services.source_component_service.group_service.add_service_to_group")
    @patch("console.services.source_component_service.app_check_service.check_service")
    def test_auto_create_component_rejects_check_request_failure(
            self, mock_check_service, mock_add_to_group, mock_create_source):
        from console.services.source_component_service import source_component_service

        user = Obj(user_id=1, pk=1, nick_name="admin")
        team = Obj(tenant_id="team-1", tenant_name="demo-team", enterprise_id="eid-1")
        app = Obj(ID=12, region_name="rainbond", group_name="demo-app")
        service = Obj(service_id="svc-1", service_alias="alias-1", service_cname="component-1", service_region="rainbond")
        service.to_dict = lambda: {"service_id": "svc-1"}
        service.save = lambda: None

        mock_create_source.return_value = (200, "success", service)
        mock_add_to_group.return_value = (200, "success")
        mock_check_service.return_value = (500, "check request failed", {})

        with self.assertRaises(ServiceHandleException) as context:
            source_component_service.auto_create_component(
                team=team,
                app=app,
                user=user,
                service_cname="component-1",
                code_from="gitlab_manual",
                git_url="https://git.example.com/demo.git",
            )

        self.assertEqual(context.exception.status_code, 500)
        self.assertEqual(context.exception.msg_show, "check request failed")

    # capability_id: console.source-component.deploy-failure
    @patch("console.services.source_component_service.app_manage_service.deploy")
    @patch("console.services.source_component_service.arch_service.update_affinity_by_arch")
    @patch("console.services.source_component_service.console_app_service.create_region_service")
    @patch("console.services.source_component_service.region_api.get_service_check_info")
    @patch("console.services.source_component_service.app_check_service.check_service")
    @patch("console.services.source_component_service.group_service.add_service_to_group")
    @patch("console.services.source_component_service.console_app_service.create_source_code_app")
    def test_auto_create_component_rejects_deploy_failure(
            self,
            mock_create_source,
            mock_add_to_group,
            mock_check_service,
            mock_get_check_info,
            mock_create_region_service,
            mock_update_affinity,
            mock_deploy,
    ):
        from console.services.source_component_service import source_component_service

        user = Obj(user_id=1, pk=1, nick_name="admin")
        team = Obj(tenant_id="team-1", tenant_name="demo-team", enterprise_id="eid-1")
        app = Obj(ID=12, region_name="rainbond", group_name="demo-app")
        service = Obj(service_id="svc-1", service_alias="alias-1", service_cname="component-1", service_region="rainbond", arch="amd64")
        service.to_dict = lambda: {"service_id": "svc-1"}
        service.save = lambda: None
        built_service = Obj(service_id="svc-1", create_status="building", arch="amd64")

        mock_create_source.return_value = (200, "success", service)
        mock_add_to_group.return_value = (200, "success")
        mock_check_service.return_value = (200, "success", {"check_uuid": "chk-1"})
        mock_get_check_info.return_value = (None, {"bean": {"check_status": "success", "error_infos": [], "service_info": []}})
        mock_create_region_service.return_value = built_service
        mock_deploy.return_value = (500, "deploy failed", None)

        with self.assertRaises(ServiceHandleException) as context:
            source_component_service.auto_create_component(
                team=team,
                app=app,
                user=user,
                service_cname="component-1",
                code_from="gitlab_manual",
                git_url="https://git.example.com/demo.git",
            )

        self.assertEqual(context.exception.status_code, 500)
        self.assertEqual(context.exception.msg_show, "deploy failed")

    # capability_id: console.source-component.check-poll-success
    def test_wait_for_check_result_retries_until_success(self):
        from console.services.source_component_service import source_component_service, region_api

        team = Obj(tenant_name="demo-team")
        responses = [
            (None, {"bean": {"check_status": "checking"}}),
            (None, {"bean": {"check_status": "success", "service_info": []}}),
        ]

        with patch.object(region_api, "get_service_check_info", side_effect=responses) as get_info_mock, \
                patch("console.services.source_component_service.time.sleep") as sleep_mock:
            bean = source_component_service._wait_for_check_result(
                "demo-region", team, "chk-1", max_retries=2, poll_interval=0
            )

        self.assertEqual(bean["check_status"], "success")
        self.assertEqual(get_info_mock.call_count, 2)
        sleep_mock.assert_called_once_with(0)

    # capability_id: console.source-component.check-poll-failure
    def test_wait_for_check_result_raises_with_first_error_info(self):
        from console.services.source_component_service import source_component_service, region_api

        team = Obj(tenant_name="demo-team")
        response = (None, {"bean": {"check_status": "failure", "error_infos": [{"error_info": "compile failed"}]}})

        with patch.object(region_api, "get_service_check_info", return_value=response):
            with self.assertRaises(ServiceHandleException) as context:
                source_component_service._wait_for_check_result(
                    "demo-region", team, "chk-1", max_retries=1, poll_interval=0
                )

        self.assertEqual(context.exception.status_code, 500)
        self.assertEqual(context.exception.msg_show, "compile failed")

    # capability_id: console.source-component.build-config-error
    @patch("console.services.source_component_service.app_manage_service.change_lang_and_package_tool")
    def test_apply_default_build_config_raises_when_save_fails(self, mock_change_lang):
        from console.services.source_component_service import source_component_service

        team = Obj(tenant_name="demo-team")
        component = Obj(language="", service_id="svc-1")
        service_info = {
            "language": "Node.js",
            "runtime_info": {
                "framework": {"name": "nextjs"},
                "build_config": {"output_dir": ".next", "build_command": "build", "start_command": "start"},
                "package_manager": {"name": "pnpm"},
                "config_files": {"has_npmrc": True, "has_yarnrc": False},
                "language_version": "20.20.0",
            },
        }
        mock_change_lang.return_value = (500, "save build config failed")

        with self.assertRaises(ServiceHandleException) as context:
            source_component_service.apply_default_build_config(team, component, service_info)

        self.assertEqual(context.exception.status_code, 500)
        self.assertEqual(context.exception.msg_show, "save build config failed")

    # capability_id: console.source-component.prefer-dockerfile
    @patch("console.services.source_component_service.deploy_repo.create_deploy_relation_by_service_id")
    @patch("console.services.source_component_service.app_manage_service.deploy")
    @patch("console.services.source_component_service.arch_service.update_affinity_by_arch")
    @patch("console.services.source_component_service.console_app_service.create_region_service")
    @patch("console.services.source_component_service.app_manage_service.change_lang_and_package_tool")
    @patch("console.services.source_component_service.app_check_service.save_service_check_info")
    @patch("console.services.source_component_service.region_api.get_service_check_info")
    @patch("console.services.source_component_service.app_check_service.check_service")
    @patch("console.services.source_component_service.group_service.add_service_to_group")
    @patch("console.services.source_component_service.console_app_service.create_service_source_info")
    @patch("console.services.source_component_service.console_app_service.create_source_code_app")
    @patch("console.services.source_component_service.console_app_service.is_k8s_component_name_duplicate")
    def test_auto_create_component_prefers_dockerfile_when_requested(
            self,
            mock_name_duplicate,
            mock_create_source,
            mock_create_source_info,
            mock_add_to_group,
            mock_check_service,
            mock_get_check_info,
            mock_save_check_info,
            mock_change_lang_and_package_tool,
            mock_create_region_service,
            mock_update_affinity,
            mock_deploy,
            mock_create_deploy_relation,
    ):
        from console.services.source_component_service import source_component_service

        user = Obj(user_id=1, pk=1, nick_name="admin")
        team = Obj(tenant_id="team-1", tenant_name="demo-team", enterprise_id="eid-1")
        app = Obj(ID=12, region_name="rainbond", group_name="demo-app")
        service = Obj(
            service_id="svc-1",
            service_alias="alias-1",
            service_cname="component-1",
            service_region="rainbond",
            service_source="source_code",
            create_status="creating",
            arch="amd64",
            check_uuid="chk-1",
            check_event_id="evt-check-1",
        )
        service.to_dict = lambda: {"service_id": "svc-1", "service_alias": "alias-1"}
        service.save = lambda: None
        built_service = Obj(service_id="svc-1", create_status="complete", arch="amd64")

        mock_name_duplicate.return_value = False
        mock_create_source.return_value = (200, "success", service)
        mock_add_to_group.return_value = (200, "success")
        mock_check_service.return_value = (200, "success", {"check_uuid": "chk-1"})
        mock_get_check_info.return_value = (
            None,
            {"bean": {"check_status": "success", "error_infos": [], "service_info": [{
                "language": "dockerfile,Node.js",
                "dockerfiles": ["Dockerfile"],
                "runtime_info": {
                    "framework": {"name": "nextjs"},
                    "build_config": {"output_dir": ".next", "build_command": "npm run build", "start_command": "npm run start"},
                    "package_manager": {"name": "npm"},
                    "config_files": {"has_npmrc": False, "has_yarnrc": False},
                    "language_version": "20.20.0",
                }
            }]}}
        )
        mock_create_region_service.return_value = built_service
        mock_deploy.return_value = (200, "success", "evt-1")

        def save_check_info(team_obj, app_id, service_obj, data):
            service_obj.create_status = "checked"

        mock_save_check_info.side_effect = save_check_info

        result = source_component_service.auto_create_component(
            team=team,
            app=app,
            user=user,
            service_cname="component-1",
            code_from="git",
            git_url="https://git.example.com/demo.git",
            prefer_dockerfile_when_detected=True,
        )

        self.assertTrue(result["built"])
        self.assertEqual(result["selected_language"], "dockerfile")
        self.assertEqual(result["detected_language_raw"], "dockerfile,Node.js")
        mock_change_lang_and_package_tool.assert_not_called()

    # capability_id: console.source-component.prefer-dockerfile-from-dockerfiles-flag
    @patch("console.services.source_component_service.deploy_repo.create_deploy_relation_by_service_id")
    @patch("console.services.source_component_service.app_manage_service.deploy")
    @patch("console.services.source_component_service.arch_service.update_affinity_by_arch")
    @patch("console.services.source_component_service.console_app_service.create_region_service")
    @patch("console.services.source_component_service.app_manage_service.change_lang_and_package_tool")
    @patch("console.services.source_component_service.app_check_service.save_service_check_info")
    @patch("console.services.source_component_service.region_api.get_service_check_info")
    @patch("console.services.source_component_service.app_check_service.check_service")
    @patch("console.services.source_component_service.group_service.add_service_to_group")
    @patch("console.services.source_component_service.console_app_service.create_service_source_info")
    @patch("console.services.source_component_service.console_app_service.create_source_code_app")
    @patch("console.services.source_component_service.console_app_service.is_k8s_component_name_duplicate")
    def test_auto_create_component_prefers_dockerfile_when_dockerfiles_exist(
            self,
            mock_name_duplicate,
            mock_create_source,
            mock_create_source_info,
            mock_add_to_group,
            mock_check_service,
            mock_get_check_info,
            mock_save_check_info,
            mock_change_lang_and_package_tool,
            mock_create_region_service,
            mock_update_affinity,
            mock_deploy,
            mock_create_deploy_relation,
    ):
        from console.services.source_component_service import source_component_service

        user = Obj(user_id=1, pk=1, nick_name="admin")
        team = Obj(tenant_id="team-1", tenant_name="demo-team", enterprise_id="eid-1")
        app = Obj(ID=12, region_name="rainbond", group_name="demo-app")
        service = Obj(
            service_id="svc-1",
            service_alias="alias-1",
            service_cname="component-1",
            service_region="rainbond",
            service_source="source_code",
            create_status="creating",
            arch="amd64",
            check_uuid="chk-1",
            check_event_id="evt-check-1",
        )
        service.to_dict = lambda: {"service_id": "svc-1", "service_alias": "alias-1"}
        service.save = lambda: None
        built_service = Obj(service_id="svc-1", create_status="complete", arch="amd64")

        mock_name_duplicate.return_value = False
        mock_create_source.return_value = (200, "success", service)
        mock_add_to_group.return_value = (200, "success")
        mock_check_service.return_value = (200, "success", {"check_uuid": "chk-1"})
        mock_get_check_info.return_value = (
            None,
            {"bean": {"check_status": "success", "error_infos": [], "service_info": [{
                "language": "Node.js",
                "dockerfiles": ["Dockerfile"],
                "runtime_info": {
                    "framework": {"name": "nextjs"},
                    "build_config": {"output_dir": ".next", "build_command": "npm run build", "start_command": "npm run start"},
                    "package_manager": {"name": "npm"},
                    "config_files": {"has_npmrc": False, "has_yarnrc": False},
                    "language_version": "20.20.0",
                }
            }]}}
        )
        mock_create_region_service.return_value = built_service
        mock_deploy.return_value = (200, "success", "evt-1")

        def save_check_info(team_obj, app_id, service_obj, data):
            service_obj.create_status = "checked"

        mock_save_check_info.side_effect = save_check_info

        result = source_component_service.auto_create_component(
            team=team,
            app=app,
            user=user,
            service_cname="component-1",
            code_from="git",
            git_url="https://git.example.com/demo.git",
            prefer_dockerfile_when_detected=True,
        )

        self.assertTrue(result["built"])
        self.assertEqual(result["selected_language"], "dockerfile")
        self.assertEqual(result["detected_language_raw"], "Node.js")
        mock_change_lang_and_package_tool.assert_not_called()

    # capability_id: console.source-component.check-timeout-pending
    @patch("console.services.source_component_service.group_service.add_service_to_group")
    @patch("console.services.source_component_service.app_check_service.check_service")
    @patch("console.services.source_component_service.console_app_service.create_source_code_app")
    @patch("console.services.source_component_service.console_app_service.is_k8s_component_name_duplicate")
    def test_auto_create_component_returns_pending_result_when_check_times_out(
            self,
            mock_name_duplicate,
            mock_create_source,
            mock_check_service,
            mock_add_to_group,
    ):
        from console.services.source_component_service import source_component_service

        user = Obj(user_id=1, pk=1, nick_name="admin")
        team = Obj(tenant_id="team-1", tenant_name="demo-team", enterprise_id="eid-1")
        app = Obj(ID=12, region_name="rainbond", group_name="demo-app")
        service = Obj(
            service_id="svc-1",
            service_alias="alias-1",
            service_cname="component-1",
            service_region="rainbond",
            service_source="source_code",
            create_status="checking",
            arch="amd64",
            check_uuid="chk-1",
        )
        service.to_dict = lambda: {"service_id": "svc-1", "service_alias": "alias-1"}
        service.save = lambda: None

        mock_name_duplicate.return_value = False
        mock_create_source.return_value = (200, "success", service)
        mock_add_to_group.return_value = (200, "success")
        mock_check_service.return_value = (200, "success", {"check_uuid": "chk-1"})

        with patch.object(
                source_component_service,
                "_wait_for_check_result",
                side_effect=ServiceHandleException(msg="check timeout", msg_show="代码检测超时", status_code=500),
        ):
            result = source_component_service.auto_create_component(
                team=team,
                app=app,
                user=user,
                service_cname="component-1",
                code_from="git",
                git_url="https://git.example.com/demo.git",
                is_deploy=True,
            )

        self.assertFalse(result["built"])
        self.assertEqual(result["workflow_stage"], "checking")
        self.assertEqual(result["next_action"], "rainbond_get_component_check_result")
        self.assertEqual(result["check_uuid"], "chk-1")
        self.assertEqual(result["service_id"], "svc-1")

    # capability_id: console.source-component.check-timeout-pending
    @patch("console.services.source_component_service.service_source_repo.update_or_create_service_source")
    @patch("console.services.source_component_service.service_source_repo.get_service_source")
    @patch("console.services.source_component_service.group_service.add_service_to_group")
    @patch("console.services.source_component_service.app_check_service.check_service")
    @patch("console.services.source_component_service.console_app_service.create_source_code_app")
    @patch("console.services.source_component_service.console_app_service.is_k8s_component_name_duplicate")
    def test_auto_create_component_persists_dockerfile_preference_on_check_timeout(
            self,
            mock_name_duplicate,
            mock_create_source,
            mock_check_service,
            mock_add_to_group,
            mock_get_service_source,
            mock_update_service_source,
    ):
        import json

        from console.services.source_component_service import source_component_service

        user = Obj(user_id=1, pk=1, nick_name="admin")
        team = Obj(tenant_id="team-1", tenant_name="demo-team", enterprise_id="eid-1")
        app = Obj(ID=12, region_name="rainbond", group_name="demo-app")
        service = Obj(
            service_id="svc-1",
            service_alias="alias-1",
            service_cname="component-1",
            service_region="rainbond",
            service_source="source_code",
            create_status="checking",
            arch="amd64",
            check_uuid="chk-1",
        )
        service.to_dict = lambda: {"service_id": "svc-1", "service_alias": "alias-1"}
        service.save = lambda: None

        mock_name_duplicate.return_value = False
        mock_create_source.return_value = (200, "success", service)
        mock_add_to_group.return_value = (200, "success")
        mock_check_service.return_value = (200, "success", {"check_uuid": "chk-1"})
        mock_get_service_source.return_value = None

        with patch.object(
                source_component_service,
                "_wait_for_check_result",
                side_effect=ServiceHandleException(msg="check timeout", msg_show="代码检测超时", status_code=500),
        ):
            result = source_component_service.auto_create_component(
                team=team,
                app=app,
                user=user,
                service_cname="component-1",
                code_from="git",
                git_url="https://git.example.com/demo.git",
                prefer_dockerfile_when_detected=True,
            )

        self.assertFalse(result["built"])
        self.assertTrue(result["prefer_dockerfile_when_detected"])
        self.assertTrue(result["build_mode_note"])
        mock_update_service_source.assert_called_once()
        persisted = mock_update_service_source.call_args[1]
        self.assertEqual(persisted["team_id"], "team-1")
        self.assertEqual(persisted["service_id"], "svc-1")
        extend_info = json.loads(persisted["extend_info"])
        self.assertTrue(extend_info["prefer_dockerfile_when_detected"])

    # capability_id: console.source-component.check-timeout-pending
    @patch("console.services.source_component_service.service_source_repo.update_or_create_service_source")
    @patch("console.services.source_component_service.group_service.add_service_to_group")
    @patch("console.services.source_component_service.app_check_service.check_service")
    @patch("console.services.source_component_service.console_app_service.create_source_code_app")
    @patch("console.services.source_component_service.console_app_service.is_k8s_component_name_duplicate")
    def test_auto_create_component_skips_preference_persistence_when_not_requested(
            self,
            mock_name_duplicate,
            mock_create_source,
            mock_check_service,
            mock_add_to_group,
            mock_update_service_source,
    ):
        from console.services.source_component_service import source_component_service

        user = Obj(user_id=1, pk=1, nick_name="admin")
        team = Obj(tenant_id="team-1", tenant_name="demo-team", enterprise_id="eid-1")
        app = Obj(ID=12, region_name="rainbond", group_name="demo-app")
        service = Obj(
            service_id="svc-1",
            service_alias="alias-1",
            service_cname="component-1",
            service_region="rainbond",
            service_source="source_code",
            create_status="checking",
            arch="amd64",
            check_uuid="chk-1",
        )
        service.to_dict = lambda: {"service_id": "svc-1", "service_alias": "alias-1"}
        service.save = lambda: None

        mock_name_duplicate.return_value = False
        mock_create_source.return_value = (200, "success", service)
        mock_add_to_group.return_value = (200, "success")
        mock_check_service.return_value = (200, "success", {"check_uuid": "chk-1"})

        with patch.object(
                source_component_service,
                "_wait_for_check_result",
                side_effect=ServiceHandleException(msg="check timeout", msg_show="代码检测超时", status_code=500),
        ):
            result = source_component_service.auto_create_component(
                team=team,
                app=app,
                user=user,
                service_cname="component-1",
                code_from="git",
                git_url="https://git.example.com/demo.git",
            )

        self.assertFalse(result["built"])
        self.assertFalse(result["prefer_dockerfile_when_detected"])
        mock_update_service_source.assert_not_called()

    # capability_id: console.source-component.prefer-dockerfile-from-dockerfiles-flag
    @patch("console.services.source_component_service.deploy_repo.create_deploy_relation_by_service_id")
    @patch("console.services.source_component_service.app_manage_service.deploy")
    @patch("console.services.source_component_service.arch_service.update_affinity_by_arch")
    @patch("console.services.source_component_service.console_app_service.create_region_service")
    @patch("console.services.source_component_service.app_manage_service.change_lang_and_package_tool")
    @patch("console.services.source_component_service.app_check_service.save_service_check_info")
    @patch("console.services.source_component_service.region_api.get_service_check_info")
    @patch("console.services.source_component_service.app_check_service.check_service")
    @patch("console.services.source_component_service.group_service.add_service_to_group")
    @patch("console.services.source_component_service.console_app_service.create_service_source_info")
    @patch("console.services.source_component_service.console_app_service.create_source_code_app")
    @patch("console.services.source_component_service.console_app_service.is_k8s_component_name_duplicate")
    def test_auto_create_component_reports_unapplied_dockerfile_preference(
            self,
            mock_name_duplicate,
            mock_create_source,
            mock_create_source_info,
            mock_add_to_group,
            mock_check_service,
            mock_get_check_info,
            mock_save_check_info,
            mock_change_lang_and_package_tool,
            mock_create_region_service,
            mock_update_affinity,
            mock_deploy,
            mock_create_deploy_relation,
    ):
        from console.services.source_component_service import source_component_service

        user = Obj(user_id=1, pk=1, nick_name="admin")
        team = Obj(tenant_id="team-1", tenant_name="demo-team", enterprise_id="eid-1")
        app = Obj(ID=12, region_name="rainbond", group_name="demo-app")
        service = Obj(
            service_id="svc-1",
            service_alias="alias-1",
            service_cname="component-1",
            service_region="rainbond",
            service_source="source_code",
            create_status="creating",
            arch="amd64",
            check_uuid="chk-1",
            check_event_id="evt-check-1",
        )
        service.to_dict = lambda: {"service_id": "svc-1", "service_alias": "alias-1"}
        service.save = lambda: None
        built_service = Obj(service_id="svc-1", create_status="complete", arch="amd64")

        mock_name_duplicate.return_value = False
        mock_create_source.return_value = (200, "success", service)
        mock_add_to_group.return_value = (200, "success")
        mock_check_service.return_value = (200, "success", {"check_uuid": "chk-1"})
        # Detection found a CNB language but no Dockerfile at the build root,
        # so the requested Dockerfile preference cannot be applied.
        mock_get_check_info.return_value = (
            None,
            {"bean": {"check_status": "success", "error_infos": [], "service_info": [{
                "language": "Go",
            }]}}
        )
        mock_create_region_service.return_value = built_service
        mock_deploy.return_value = (200, "success", "evt-1")

        def save_check_info(team_obj, app_id, service_obj, data):
            service_obj.create_status = "checked"

        mock_save_check_info.side_effect = save_check_info

        result = source_component_service.auto_create_component(
            team=team,
            app=app,
            user=user,
            service_cname="component-1",
            code_from="git",
            git_url="https://git.example.com/demo.git",
            prefer_dockerfile_when_detected=True,
        )

        self.assertTrue(result["built"])
        self.assertEqual(result["selected_language"], "Go")
        self.assertFalse(result["dockerfile_preference_applied"])
        self.assertTrue(result["build_mode_note"])

    # capability_id: console.source-component.prefer-dockerfile-from-dockerfiles-flag
    def test_load_dockerfile_preference_reads_persisted_flag(self):
        from console.services.source_component_service import source_component_service

        team = Obj(tenant_id="team-1", tenant_name="demo-team")
        service = Obj(service_id="svc-1")

        with patch(
                "console.services.source_component_service.service_source_repo.get_service_source"
        ) as mock_get_source:
            mock_get_source.return_value = Obj(extend_info='{"prefer_dockerfile_when_detected": true}')
            self.assertTrue(source_component_service.load_dockerfile_preference(team, service))

            mock_get_source.return_value = Obj(extend_info='{"install_from_cloud": true}')
            self.assertFalse(source_component_service.load_dockerfile_preference(team, service))

            mock_get_source.return_value = Obj(extend_info="not-json")
            self.assertFalse(source_component_service.load_dockerfile_preference(team, service))

            mock_get_source.return_value = None
            self.assertFalse(source_component_service.load_dockerfile_preference(team, service))
