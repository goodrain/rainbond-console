# -*- coding: utf-8 -*-
from unittest.mock import patch

from django.test import SimpleTestCase

from console.exception.main import ServiceHandleException


class Obj(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class PackageComponentServiceTests(SimpleTestCase):

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

    @patch("console.services.package_component_service.package_upload_service.get_upload_record")
    @patch("console.services.package_component_service.console_app_service.is_k8s_component_name_duplicate")
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
