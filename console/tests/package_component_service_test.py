# -*- coding: utf-8 -*-
import os
import sys
from types import ModuleType
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django
from django.test import SimpleTestCase

django.setup()

from console.exception.main import ServiceHandleException


class Obj(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


# capability_id: console.component.create-from-package
class PackageComponentServiceTests(SimpleTestCase):

    # capability_id: console.package-component.replace-existing-flow
    @patch("console.services.package_component_service.deploy_repo.create_deploy_relation_by_service_id")
    @patch("console.services.package_component_service.app_manage_service.deploy")
    @patch("console.services.package_component_service.package_upload_service.update_upload_record")
    @patch("console.services.package_component_service.console_app_service.change_package_upload_info")
    @patch("console.services.package_component_service.package_upload_service.get_upload_record")
    @patch("console.services.package_component_service.PackageComponentService._get_uploaded_packages")
    def test_replace_component_reuses_service_id_and_triggers_build(
        self,
        mock_get_uploaded_packages,
        mock_get_upload_record,
        mock_change_package_info,
        mock_update_upload_record,
        mock_deploy,
        mock_create_deploy_relation,
    ):
        from console.services.package_component_service import package_component_service

        user = Obj(user_id=1, pk=1, nick_name="admin")
        team = Obj(tenant_id="team-1", tenant_name="demo-team", enterprise_id="eid-1")
        app = Obj(ID=12, region_name="rainbond", group_name="demo-app")
        service = Obj(
            service_id="svc-pkg-1",
            service_alias="alias-pkg-1",
            service_cname="demo-war",
            service_region="rainbond",
            service_source="package_build",
            server_type="pkg",
            create_status="complete",
            git_url="/grdata/package_build/components/svc-pkg-1/events/evt-old",
            code_version="2026-03-20 16:00:00",
        )
        mock_get_upload_record.return_value = Obj(create_time="2026-03-21 16:00:00",
                                                  component_id="svc-pkg-1",
                                                  status="unfinished")
        mock_get_uploaded_packages.return_value = ["demo-v2.war"]
        mock_change_package_info.return_value = 1
        mock_update_upload_record.return_value = 1
        mock_deploy.return_value = (200, "success", "evt-build-2")

        result = package_component_service.replace_component(
            team=team,
            app=app,
            service=service,
            user=user,
            event_id="evt-upload-2",
            expected_current_event_id="evt-old",
            is_deploy=True,
        )

        self.assertEqual(result["service_id"], "svc-pkg-1")
        self.assertEqual(result["previous_upload_event_id"], "evt-old")
        self.assertEqual(result["upload_event_id"], "evt-upload-2")
        self.assertEqual(result["event_id"], "evt-build-2")
        self.assertTrue(result["replaced"])
        self.assertTrue(result["build_triggered"])
        mock_change_package_info.assert_called_once_with(
            "svc-pkg-1",
            "evt-upload-2",
            "2026-03-21 16:00:00",
            tenant_id="team-1",
            expected_git_url="/grdata/package_build/components/svc-pkg-1/events/evt-old",
        )
        mock_update_upload_record.assert_called_once_with(
            "demo-team",
            "evt-upload-2",
            status="finished",
            component_id="svc-pkg-1",
            source_dir=["demo-v2.war"],
        )
        mock_deploy.assert_called_once_with(team, service, user)
        mock_create_deploy_relation.assert_called_once_with(service_id="svc-pkg-1")

    # capability_id: console.package-component.replace-source-guard
    def test_replace_component_rejects_non_package_component(self):
        from console.services.package_component_service import package_component_service

        with self.assertRaises(ServiceHandleException) as context:
            package_component_service.replace_component(
                team=Obj(tenant_id="team-1", tenant_name="demo-team"),
                app=Obj(ID=12, region_name="rainbond"),
                service=Obj(service_id="svc-1", service_source="source_code", server_type="git"),
                user=Obj(nick_name="admin"),
                event_id="evt-upload-2",
            )

        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(context.exception.msg, "component is not package based")

    # capability_id: console.package-component.replace-upload-owner-guard
    @patch("console.services.package_component_service.package_upload_service.get_upload_record")
    def test_replace_component_rejects_upload_bound_to_another_component(self, mock_get_upload_record):
        from console.services.package_component_service import package_component_service

        mock_get_upload_record.return_value = Obj(create_time="2026-03-21 16:00:00",
                                                  component_id="svc-other",
                                                  status="finished")

        with self.assertRaises(ServiceHandleException) as context:
            package_component_service.replace_component(
                team=Obj(tenant_id="team-1", tenant_name="demo-team"),
                app=Obj(ID=12, region_name="rainbond"),
                service=Obj(
                    service_id="svc-pkg-1",
                    service_source="package_build",
                    server_type="pkg",
                    create_status="complete",
                    git_url="/grdata/package_build/components/svc-pkg-1/events/evt-old",
                ),
                user=Obj(nick_name="admin"),
                event_id="evt-upload-2",
            )

        self.assertEqual(context.exception.status_code, 409)
        self.assertEqual(context.exception.msg, "upload belongs to another component")

    # capability_id: console.package-component.replace-concurrency-guard
    def test_replace_component_rejects_stale_expected_event(self):
        from console.services.package_component_service import package_component_service

        with self.assertRaises(ServiceHandleException) as context:
            package_component_service.replace_component(
                team=Obj(tenant_id="team-1", tenant_name="demo-team"),
                app=Obj(ID=12, region_name="rainbond"),
                service=Obj(
                    service_id="svc-pkg-1",
                    service_source="package_build",
                    server_type="pkg",
                    create_status="complete",
                    git_url="/grdata/package_build/components/svc-pkg-1/events/evt-current",
                ),
                user=Obj(nick_name="admin"),
                event_id="evt-upload-2",
                expected_current_event_id="evt-old",
            )

        self.assertEqual(context.exception.status_code, 409)
        self.assertEqual(context.exception.msg, "package source changed concurrently")

    # capability_id: console.package-component.replace-idempotent
    @patch("console.services.package_component_service.PackageComponentService._get_uploaded_packages")
    @patch("console.services.package_component_service.package_upload_service.get_upload_record")
    def test_replace_component_is_idempotent_for_current_event(self, mock_get_upload_record, mock_get_uploaded_packages):
        from console.services.package_component_service import package_component_service

        service = Obj(
            service_id="svc-pkg-1",
            service_alias="alias-pkg-1",
            service_source="package_build",
            server_type="pkg",
            create_status="complete",
            git_url="/grdata/package_build/components/svc-pkg-1/events/evt-current",
        )
        mock_get_upload_record.return_value = Obj(
            create_time="new-version",
            component_id="svc-pkg-1",
            status="finished",
            source_dir="['demo-v2.zip']",
        )

        result = package_component_service.replace_component(
            team=Obj(tenant_id="team-1", tenant_name="demo-team"),
            app=Obj(ID=12, region_name="rainbond"),
            service=service,
            user=Obj(nick_name="admin"),
            event_id="evt-current",
            expected_current_event_id="evt-current",
            is_deploy=True,
        )

        self.assertFalse(result["replaced"])
        self.assertFalse(result["build_triggered"])
        self.assertEqual(result["uploaded_packages"], ["demo-v2.zip"])
        self.assertEqual(result["next_action"], "rainbond_build_component")
        mock_get_uploaded_packages.assert_not_called()

    # capability_id: console.package-component.replace-sync-failure-rollback
    @patch("console.services.package_component_service.console_app_service.restore_package_upload_info")
    @patch("console.services.package_component_service.app_manage_service.deploy")
    @patch("console.services.package_component_service.package_upload_service.update_upload_record")
    @patch("console.services.package_component_service.console_app_service.change_package_upload_info")
    @patch("console.services.package_component_service.package_upload_service.get_upload_record")
    @patch("console.services.package_component_service.PackageComponentService._get_uploaded_packages")
    def test_replace_component_restores_source_when_build_dispatch_fails(
        self,
        mock_get_uploaded_packages,
        mock_get_upload_record,
        mock_change_package_info,
        mock_update_upload_record,
        mock_deploy,
        mock_restore_package_info,
    ):
        from console.services.package_component_service import package_component_service

        team = Obj(tenant_id="team-1", tenant_name="demo-team")
        app = Obj(ID=12, region_name="rainbond")
        service = Obj(
            service_id="svc-pkg-1",
            service_source="package_build",
            server_type="pkg",
            create_status="complete",
            git_url="/grdata/package_build/components/svc-pkg-1/events/evt-old",
            code_version="old-version",
        )
        mock_get_upload_record.return_value = Obj(create_time="new-version", component_id="", status="unfinished")
        mock_get_uploaded_packages.return_value = ["demo-v2.zip"]
        mock_change_package_info.return_value = 1
        mock_update_upload_record.return_value = 1
        mock_deploy.return_value = (507, "构建异常", "")
        mock_restore_package_info.return_value = 1

        with self.assertRaises(ServiceHandleException) as context:
            package_component_service.replace_component(
                team=team,
                app=app,
                service=service,
                user=Obj(nick_name="admin"),
                event_id="evt-upload-2",
                is_deploy=True,
            )

        self.assertEqual(context.exception.status_code, 507)
        self.assertEqual(service.git_url, "/grdata/package_build/components/svc-pkg-1/events/evt-old")
        self.assertEqual(service.code_version, "old-version")
        mock_restore_package_info.assert_called_once_with(
            "svc-pkg-1",
            "team-1",
            "/grdata/package_build/components/svc-pkg-1/events/evt-upload-2",
            "/grdata/package_build/components/svc-pkg-1/events/evt-old",
            "old-version",
        )

    # capability_id: console.package-component.auto-create-flow
    @patch("console.services.package_component_service.deploy_repo.create_deploy_relation_by_service_id")
    @patch("console.services.package_component_service.app_manage_service.deploy")
    @patch("console.services.package_component_service.arch_service.update_affinity_by_arch")
    @patch("console.services.package_component_service.console_app_service.create_region_service")
    @patch("console.services.package_component_service.source_component_service.apply_default_build_config")
    @patch("console.services.package_component_service.app_check_service.save_service_check_info")
    @patch("console.services.package_component_service.source_component_service._wait_for_check_result")
    @patch("console.services.package_component_service.app_check_service.check_service")
    @patch("console.services.package_component_service.group_service.add_service_to_group")
    @patch("console.services.package_component_service.package_upload_service.update_upload_record")
    @patch("console.services.package_component_service.console_app_service.create_package_upload_info")
    @patch("console.services.package_component_service.package_upload_service.get_upload_record")
    @patch("console.services.package_component_service.region_api.get_upload_file_dir")
    @patch("console.services.package_component_service.console_app_service.is_k8s_component_name_duplicate")
    # capability_id: console.package-component.auto-create-flow
    def test_auto_create_component_runs_full_package_flow(
            self,
            mock_name_duplicate,
            mock_get_upload_dir,
            mock_get_upload_record,
            mock_create_package_info,
            mock_update_upload_record,
            mock_add_to_group,
            mock_check_service,
            mock_wait_for_check_result,
            mock_save_check_info,
            mock_apply_default_build_config,
            mock_create_region_service,
            mock_update_affinity,
            mock_deploy,
            mock_create_deploy_relation,
    ):
        from console.services.package_component_service import package_component_service

        user = Obj(user_id=1, pk=1, nick_name="admin")
        team = Obj(tenant_id="team-1", tenant_name="demo-team", enterprise_id="eid-1")
        app = Obj(ID=12, region_name="rainbond", group_name="demo-app")
        upload_record = Obj(create_time="2026-03-20 16:00:00")
        component = Obj(
            service_id="svc-pkg-1",
            service_alias="alias-pkg-1",
            service_cname="demo-war",
            service_region="rainbond",
            service_source="package_build",
            create_status="creating",
            arch="amd64",
            check_uuid="chk-pkg-1",
        )
        component.save = lambda: None
        built_component = Obj(service_id="svc-pkg-1", create_status="complete", arch="amd64")

        mock_name_duplicate.return_value = False
        mock_get_upload_record.return_value = upload_record
        mock_get_upload_dir.return_value = (None, {"bean": {"packages": ["demo.war"]}})
        mock_create_package_info.return_value = component
        mock_add_to_group.return_value = (200, "success")
        mock_check_service.return_value = (200, "success", {"check_uuid": "chk-pkg-1"})
        mock_wait_for_check_result.return_value = {
            "check_status": "success",
            "service_info": [{"language": "Java-war"}],
            "error_infos": [],
        }
        mock_create_region_service.return_value = built_component
        mock_deploy.return_value = (200, "success", "evt-pkg-1")

        result = package_component_service.auto_create_component(
            team=team,
            app=app,
            user=user,
            event_id="evt-upload-1",
            service_cname="demo-war",
            is_deploy=True,
        )

        self.assertTrue(result["built"])
        self.assertEqual(result["service_id"], "svc-pkg-1")
        self.assertEqual(result["uploaded_packages"], ["demo.war"])
        mock_update_upload_record.assert_called_once_with(
            "demo-team", "evt-upload-1", status="finished", component_id="svc-pkg-1", source_dir=["demo.war"]
        )
        mock_check_service.assert_called_once_with(team, component, False, "evt-upload-1", user)
        mock_apply_default_build_config.assert_called_once()
        mock_create_region_service.assert_called_once()
        mock_deploy.assert_called_once_with(team, built_component, user)
        mock_create_deploy_relation.assert_called_once_with(service_id="svc-pkg-1")

    # capability_id: console.package-component.duplicate-name-guard
    @patch("console.services.package_component_service.console_app_service.is_k8s_component_name_duplicate", return_value=True)
    def test_auto_create_component_rejects_duplicate_k8s_component_name(self, mock_name_duplicate):
        from console.services.package_component_service import package_component_service

        user = Obj(user_id=1, pk=1, nick_name="admin")
        team = Obj(tenant_id="team-1", tenant_name="demo-team", enterprise_id="eid-1")
        app = Obj(ID=12, region_name="rainbond", group_name="demo-app")

        with self.assertRaises(ServiceHandleException) as context:
            package_component_service.auto_create_component(
                team=team,
                app=app,
                user=user,
                event_id="evt-upload-1",
                service_cname="demo-war",
                k8s_component_name="demo-war",
            )

        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(context.exception.msg_show, "组件英文名称已存在")
        mock_name_duplicate.assert_called_once_with(12, "demo-war")

    @patch("console.services.package_component_service.package_upload_service.get_upload_record")
    @patch("console.services.package_component_service.console_app_service.is_k8s_component_name_duplicate")
    # capability_id: console.package-component.require-upload-record
    def test_auto_create_component_requires_existing_upload_record(self, mock_name_duplicate, mock_get_upload_record):
        from console.services.package_component_service import package_component_service

        user = Obj(user_id=1, pk=1, nick_name="admin")
        team = Obj(tenant_id="team-1", tenant_name="demo-team", enterprise_id="eid-1")
        app = Obj(ID=12, region_name="rainbond", group_name="demo-app")

        mock_name_duplicate.return_value = False
        mock_get_upload_record.return_value = None

        with self.assertRaises(ServiceHandleException) as context:
            package_component_service.auto_create_component(
                team=team,
                app=app,
                user=user,
                event_id="evt-upload-1",
                service_cname="demo-war",
            )

        self.assertEqual(context.exception.status_code, 404)
        self.assertIn("上传记录", context.exception.msg_show)

    # capability_id: console.package-component.upload-missing
    @patch("console.services.package_component_service.package_upload_service.get_upload_record")
    @patch("console.services.package_component_service.region_api.get_upload_file_dir")
    @patch("console.services.package_component_service.console_app_service.is_k8s_component_name_duplicate")
    def test_auto_create_component_requires_uploaded_package_list(
            self, mock_name_duplicate, mock_get_upload_dir, mock_get_upload_record):
        from console.services.package_component_service import package_component_service

        user = Obj(user_id=1, pk=1, nick_name="admin")
        team = Obj(tenant_id="team-1", tenant_name="demo-team", enterprise_id="eid-1")
        app = Obj(ID=12, region_name="rainbond", group_name="demo-app")
        mock_name_duplicate.return_value = False
        mock_get_upload_record.return_value = Obj(create_time="2026-03-20 16:00:00")
        mock_get_upload_dir.return_value = (None, {"bean": {"packages": []}})

        with self.assertRaises(ServiceHandleException) as context:
            package_component_service.auto_create_component(
                team=team,
                app=app,
                user=user,
                event_id="evt-upload-1",
                service_cname="demo-war",
            )

        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(context.exception.msg_show, "软件包未上传完成")

    # capability_id: console.package-component.multi-service-guard
    @patch("console.services.package_component_service.console_app_service.is_k8s_component_name_duplicate")
    @patch("console.services.package_component_service.region_api.get_upload_file_dir")
    @patch("console.services.package_component_service.package_upload_service.get_upload_record")
    @patch("console.services.package_component_service.console_app_service.create_package_upload_info")
    @patch("console.services.package_component_service.package_upload_service.update_upload_record")
    @patch("console.services.package_component_service.group_service.add_service_to_group")
    @patch("console.services.package_component_service.app_check_service.check_service")
    @patch("console.services.package_component_service.source_component_service._wait_for_check_result")
    def test_auto_create_component_rejects_multi_service_package(
            self,
            mock_wait_for_check_result,
            mock_check_service,
            mock_add_to_group,
            mock_update_upload_record,
            mock_create_package_info,
            mock_get_upload_record,
            mock_get_upload_dir,
            mock_name_duplicate,
    ):
        from console.services.package_component_service import package_component_service

        user = Obj(user_id=1, pk=1, nick_name="admin")
        team = Obj(tenant_id="team-1", tenant_name="demo-team", enterprise_id="eid-1")
        app = Obj(ID=12, region_name="rainbond", group_name="demo-app")
        component = Obj(service_id="svc-pkg-1", service_cname="demo-war", service_region="rainbond", arch="amd64", check_uuid="chk-pkg-1")

        mock_name_duplicate.return_value = False
        mock_get_upload_record.return_value = Obj(create_time="2026-03-20 16:00:00")
        mock_get_upload_dir.return_value = (None, {"bean": {"packages": ["demo.war"]}})
        mock_create_package_info.return_value = component
        mock_add_to_group.return_value = (200, "success")
        mock_check_service.return_value = (200, "success", {"check_uuid": "chk-pkg-1"})
        mock_wait_for_check_result.return_value = {"check_status": "success", "service_info": [{}, {}], "error_infos": []}

        with self.assertRaises(ServiceHandleException) as context:
            package_component_service.auto_create_component(
                team=team,
                app=app,
                user=user,
                event_id="evt-upload-1",
                service_cname="demo-war",
            )

        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(context.exception.msg_show, "检测到多组件软件包，请使用多组件创建流程")

    # capability_id: console.package-component.check-request-failure
    @patch("console.services.package_component_service.console_app_service.is_k8s_component_name_duplicate")
    @patch("console.services.package_component_service.region_api.get_upload_file_dir")
    @patch("console.services.package_component_service.package_upload_service.get_upload_record")
    @patch("console.services.package_component_service.console_app_service.create_package_upload_info")
    @patch("console.services.package_component_service.package_upload_service.update_upload_record")
    @patch("console.services.package_component_service.group_service.add_service_to_group")
    @patch("console.services.package_component_service.app_check_service.check_service")
    def test_auto_create_component_rejects_check_request_failure(
            self,
            mock_check_service,
            mock_add_to_group,
            mock_update_upload_record,
            mock_create_package_info,
            mock_get_upload_record,
            mock_get_upload_dir,
            mock_name_duplicate,
    ):
        from console.services.package_component_service import package_component_service

        user = Obj(user_id=1, pk=1, nick_name="admin")
        team = Obj(tenant_id="team-1", tenant_name="demo-team", enterprise_id="eid-1")
        app = Obj(ID=12, region_name="rainbond", group_name="demo-app")
        component = Obj(service_id="svc-pkg-1", service_cname="demo-war", service_region="rainbond")

        mock_name_duplicate.return_value = False
        mock_get_upload_record.return_value = Obj(create_time="2026-03-20 16:00:00")
        mock_get_upload_dir.return_value = (None, {"bean": {"packages": ["demo.war"]}})
        mock_create_package_info.return_value = component
        mock_add_to_group.return_value = (200, "success")
        mock_check_service.return_value = (500, "check package failed", {})

        with self.assertRaises(ServiceHandleException) as context:
            package_component_service.auto_create_component(
                team=team,
                app=app,
                user=user,
                event_id="evt-upload-1",
                service_cname="demo-war",
            )

        self.assertEqual(context.exception.status_code, 500)
        self.assertEqual(context.exception.msg_show, "check package failed")

    # capability_id: console.package-component.deploy-failure
    @patch("console.services.package_component_service.console_app_service.is_k8s_component_name_duplicate")
    @patch("console.services.package_component_service.region_api.get_upload_file_dir")
    @patch("console.services.package_component_service.package_upload_service.get_upload_record")
    @patch("console.services.package_component_service.console_app_service.create_package_upload_info")
    @patch("console.services.package_component_service.package_upload_service.update_upload_record")
    @patch("console.services.package_component_service.group_service.add_service_to_group")
    @patch("console.services.package_component_service.app_check_service.check_service")
    @patch("console.services.package_component_service.source_component_service._wait_for_check_result")
    @patch("console.services.package_component_service.console_app_service.create_region_service")
    @patch("console.services.package_component_service.arch_service.update_affinity_by_arch")
    @patch("console.services.package_component_service.app_manage_service.deploy")
    def test_auto_create_component_rejects_deploy_failure(
            self,
            mock_deploy,
            mock_update_affinity,
            mock_create_region_service,
            mock_wait_for_check_result,
            mock_check_service,
            mock_add_to_group,
            mock_update_upload_record,
            mock_create_package_info,
            mock_get_upload_record,
            mock_get_upload_dir,
            mock_name_duplicate,
    ):
        from console.services.package_component_service import package_component_service

        user = Obj(user_id=1, pk=1, nick_name="admin")
        team = Obj(tenant_id="team-1", tenant_name="demo-team", enterprise_id="eid-1")
        app = Obj(ID=12, region_name="rainbond", group_name="demo-app")
        component = Obj(service_id="svc-pkg-1", service_cname="demo-war", service_region="rainbond", arch="amd64", check_uuid="chk-pkg-1")
        built_component = Obj(service_id="svc-pkg-1", create_status="building", arch="amd64")

        mock_name_duplicate.return_value = False
        mock_get_upload_record.return_value = Obj(create_time="2026-03-20 16:00:00")
        mock_get_upload_dir.return_value = (None, {"bean": {"packages": ["demo.war"]}})
        mock_create_package_info.return_value = component
        mock_add_to_group.return_value = (200, "success")
        mock_check_service.return_value = (200, "success", {"check_uuid": "chk-pkg-1"})
        mock_wait_for_check_result.return_value = {"check_status": "success", "service_info": [], "error_infos": []}
        mock_create_region_service.return_value = built_component
        mock_deploy.return_value = (500, "deploy package failed", None)

        with self.assertRaises(ServiceHandleException) as context:
            package_component_service.auto_create_component(
                team=team,
                app=app,
                user=user,
                event_id="evt-upload-1",
                service_cname="demo-war",
            )

        self.assertEqual(context.exception.status_code, 500)
        self.assertEqual(context.exception.msg_show, "deploy package failed")
