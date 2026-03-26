# -*- coding: utf-8 -*-
from unittest.mock import patch

from django.test import SimpleTestCase

from console.exception.main import ServiceHandleException


class Obj(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class SourceComponentServiceTests(SimpleTestCase):

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

    def test_infer_server_type_supports_git_svn_and_oss(self):
        from console.services.source_component_service import source_component_service

        self.assertEqual(source_component_service.infer_server_type("https://git.example.com/demo.git"), "git")
        self.assertEqual(source_component_service.infer_server_type("svn://repo.example.com/project/trunk"), "svn")
        self.assertEqual(source_component_service.infer_server_type("oss://bucket/path/app.tar.gz"), "oss")

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
            source_component_service.normalize_code_from("gitlab_manual", "https://gitee.com/rainbond/demo-2048.git"),
            "gitlab_manual",
        )

    @patch("console.services.source_component_service.console_app_service.create_source_code_app")
    @patch("console.services.source_component_service.group_service.add_service_to_group")
    @patch("console.services.source_component_service.app_check_service.check_service")
    @patch("console.services.source_component_service.region_api.get_service_check_info")
    def test_auto_create_component_raises_on_check_failure(
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
            {"bean": {"check_status": "failure", "error_infos": [{"error_info": "bad repo"}], "service_info": []}},
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

        self.assertIn("bad repo", context.exception.msg_show)
