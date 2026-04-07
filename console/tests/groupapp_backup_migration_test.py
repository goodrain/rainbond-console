# -*- coding: utf-8 -*-
import os
import sys
from types import ModuleType
from unittest import TestCase, mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402
from django.core.files.uploadedfile import SimpleUploadedFile  # noqa: E402
from rest_framework.test import APIRequestFactory  # noqa: E402

django.setup()

from console.views.center_pool import groupapp_backup  # noqa: E402
from console.views.center_pool import groupapp_migration  # noqa: E402


class Obj(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class GroupAppsBackupViewWorkflowTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = groupapp_backup.GroupAppsBackupView()
        self.view.tenant = Obj(tenant_id="team-1", tenant_name="demo-team", enterprise_id="eid-1")
        self.view.user = Obj(user_id=1, enterprise_id="eid-1")
        self.view.region_name = "demo-region"
        self.view.response_region = "demo-region"

    # capability_id: console.app-backup.create
    def test_post_starts_group_backup(self):
        request = self.view.initialize_request(
            self.factory.post("/console/teams/demo-team/apps/42/backup", {"note": "daily", "mode": "full-online"}, format="json")
        )
        backup_record = mock.Mock()
        backup_record.to_dict.return_value = {"backup_id": "backup-1", "group_id": 42}

        with mock.patch.object(groupapp_backup.groupapp_backup_service, "check_backup_condition", return_value=(200, [])), \
                mock.patch.object(groupapp_backup.groupapp_backup_service, "check_backup_app_used_custom_volume", return_value=[]), \
                mock.patch.object(groupapp_backup.groupapp_backup_service, "backup_group_apps", return_value=backup_record) as backup_mock, \
                mock.patch.object(groupapp_backup.operation_log_service, "create_app_log"):
            response = self.view.post(request, group_id=42)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["bean"]["backup_id"], "backup-1")
        backup_mock.assert_called_once_with(self.view.tenant, self.view.user, "demo-region", 42, "full-online", "daily", False)

    # capability_id: console.app-backup.group-required
    def test_post_requires_group_id(self):
        request = self.view.initialize_request(
            self.factory.post("/console/teams/demo-team/apps/backup", {"note": "daily", "mode": "full-online"}, format="json")
        )

        response = self.view.post(request, group_id=0)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["msg_show"], "请选择需要备份的组")

    # capability_id: console.app-backup.note-required
    def test_post_requires_backup_note(self):
        request = self.view.initialize_request(
            self.factory.post("/console/teams/demo-team/apps/42/backup", {"mode": "full-online"}, format="json")
        )

        response = self.view.post(request, group_id=42)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["msg_show"], "请填写备份信息")

    # capability_id: console.app-backup.mode-required
    def test_post_requires_backup_mode(self):
        request = self.view.initialize_request(
            self.factory.post("/console/teams/demo-team/apps/42/backup", {"note": "daily"}, format="json")
        )

        response = self.view.post(request, group_id=42)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["msg_show"], "请选择备份模式")

    # capability_id: console.app-backup.state-service-guard
    def test_post_rejects_running_stateful_services(self):
        request = self.view.initialize_request(
            self.factory.post("/console/teams/demo-team/apps/42/backup", {"note": "daily", "mode": "full-online"}, format="json")
        )

        with mock.patch.object(
                groupapp_backup.groupapp_backup_service,
                "check_backup_condition",
                return_value=(4121, [{"service_id": "svc-1"}]),
        ):
            response = self.view.post(request, group_id=42)

        self.assertEqual(response.status_code, 412)
        self.assertEqual(response.data["msg_show"], "有状态组件未关闭")
        self.assertEqual(response.data["data"]["list"], [{"service_id": "svc-1"}])

    # capability_id: console.app-backup.custom-volume-guard
    def test_post_rejects_custom_volume_usage(self):
        request = self.view.initialize_request(
            self.factory.post("/console/teams/demo-team/apps/42/backup", {"note": "daily", "mode": "full-online"}, format="json")
        )

        with mock.patch.object(groupapp_backup.groupapp_backup_service, "check_backup_condition", return_value=(200, [])), \
                mock.patch.object(
                    groupapp_backup.groupapp_backup_service,
                    "check_backup_app_used_custom_volume",
                    return_value=[{"service_id": "svc-2"}],
                ):
            response = self.view.post(request, group_id=42)

        self.assertEqual(response.status_code, 412)
        self.assertEqual(response.data["msg_show"], "组件使用了自定义存储")
        self.assertEqual(response.data["data"]["list"], [{"service_id": "svc-2"}])

    # capability_id: console.app-backup.force-bypass-guards
    def test_post_force_bypasses_backup_guards(self):
        request = self.view.initialize_request(
            self.factory.post(
                "/console/teams/demo-team/apps/42/backup",
                {"note": "daily", "mode": "full-online", "force": True},
                format="json",
            )
        )
        backup_record = mock.Mock()
        backup_record.to_dict.return_value = {"backup_id": "backup-1", "group_id": 42}

        with mock.patch.object(groupapp_backup.groupapp_backup_service, "check_backup_condition") as check_condition_mock, \
                mock.patch.object(groupapp_backup.groupapp_backup_service, "check_backup_app_used_custom_volume") as check_volume_mock, \
                mock.patch.object(groupapp_backup.groupapp_backup_service, "backup_group_apps", return_value=backup_record) as backup_mock, \
                mock.patch.object(groupapp_backup.operation_log_service, "create_app_log"):
            response = self.view.post(request, group_id=42)

        self.assertEqual(response.status_code, 200)
        check_condition_mock.assert_not_called()
        check_volume_mock.assert_not_called()
        backup_mock.assert_called_once_with(self.view.tenant, self.view.user, "demo-region", 42, "full-online", "daily", True)

    # capability_id: console.app-backup.delete
    def test_delete_removes_group_backup(self):
        request = self.view.initialize_request(
            self.factory.delete("/console/teams/demo-team/apps/42/backup", {"backup_id": "backup-1"}, format="json")
        )
        backup_record = Obj(mode="full-online", note="daily")

        with mock.patch.object(
                groupapp_backup.groupapp_backup_service,
                "get_groupapp_backup_status_by_backup_id",
                return_value=(200, "success", backup_record),
        ), mock.patch.object(
            groupapp_backup.groupapp_backup_service,
            "delete_group_backup_by_backup_id",
        ) as delete_mock, mock.patch.object(
            groupapp_backup.operation_log_service,
            "create_app_log",
        ):
            response = self.view.delete(request, group_id=42)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["msg_show"], "删除成功")
        delete_mock.assert_called_once_with(self.view.tenant, "demo-region", "backup-1")

    # capability_id: console.app-backup.delete-id-required
    def test_delete_requires_backup_id(self):
        request = self.view.initialize_request(
            self.factory.delete("/console/teams/demo-team/apps/42/backup", {}, format="json")
        )

        with mock.patch.object(
                groupapp_backup.groupapp_backup_service,
                "get_groupapp_backup_status_by_backup_id",
        ) as get_status_mock:
            response = self.view.delete(request, group_id=42)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["msg_show"], "请指明当前组的具体备份项")
        get_status_mock.assert_not_called()

    # capability_id: console.app-backup.delete-status-lookup-failure
    def test_delete_returns_error_when_status_lookup_fails(self):
        request = self.view.initialize_request(
            self.factory.delete("/console/teams/demo-team/apps/42/backup", {"backup_id": "backup-1"}, format="json")
        )

        with mock.patch.object(
                groupapp_backup.groupapp_backup_service,
                "get_groupapp_backup_status_by_backup_id",
                return_value=(500, "lookup failed", None),
        ):
            response = self.view.delete(request, group_id=42)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data["msg_show"], "lookup failed")

    # capability_id: console.app-backup.query-status
    def test_get_returns_group_backup_status(self):
        request = self.factory.get("/console/teams/demo-team/apps/42/backup", {"backup_id": "backup-1"})
        backup_record = mock.Mock()
        backup_record.to_dict.return_value = {"backup_id": "backup-1", "status": "success", "backup_server_info": {}}

        with mock.patch.object(
                groupapp_backup.groupapp_backup_service,
                "get_groupapp_backup_status_by_backup_id",
                return_value=(200, "success", backup_record),
        ):
            response = self.view.get(request, group_id=42)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["bean"]["backup_id"], "backup-1")
        self.assertNotIn("backup_server_info", response.data["data"]["bean"])

    # capability_id: console.app-backup.query-status-failure
    def test_get_returns_error_when_status_query_fails(self):
        request = self.factory.get("/console/teams/demo-team/apps/42/backup", {"backup_id": "backup-1"})

        with mock.patch.object(
                groupapp_backup.groupapp_backup_service,
                "get_groupapp_backup_status_by_backup_id",
                return_value=(500, "query failed", None),
        ):
            response = self.view.get(request, group_id=42)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data["msg_show"], "query failed")

    # capability_id: console.app-backup.query-status-guard
    def test_get_requires_backup_id(self):
        request = self.factory.get("/console/teams/demo-team/apps/42/backup")

        response = self.view.get(request, group_id=42)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["msg_show"], "请指明当前组的具体备份项")


class GroupAppsBackupTransferWorkflowTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    # capability_id: console.app-backup.export
    def test_export_returns_attachment_response(self):
        view = groupapp_backup.GroupAppsBackupExportView()
        request = self.factory.get("/console/teams/demo-team/apps/42/backup/export", {"backup_id": "backup-1"})
        team = Obj(tenant_name="demo-team", enterprise_id="eid-1")
        group = Obj(group_name="demo-app", region_name="demo-region", app_id=42)

        with mock.patch.object(groupapp_backup.team_services, "get_tenant_by_tenant_name", return_value=team), \
                mock.patch.object(groupapp_backup.group_repo, "get_group_by_id", return_value=group), \
                mock.patch.object(groupapp_backup.groupapp_backup_service, "export_group_backup", return_value=(200, "success", "backup-data")), \
                mock.patch.object(groupapp_backup.operation_log_service, "process_app_name", return_value="demo-app"), \
                mock.patch.object(groupapp_backup.operation_log_service, "create_log"):
            response = view.get(request, tenantName="demo-team", group_id=42)

        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment;", response["Content-Disposition"])

    # capability_id: console.app-backup.export-group-required
    def test_export_requires_group_id(self):
        view = groupapp_backup.GroupAppsBackupExportView()
        request = self.factory.get("/console/teams/demo-team/apps/backup/export", {"backup_id": "backup-1"})

        response = view.get(request, tenantName="demo-team", group_id=0)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["msg_show"], "请选择需要导出备份的组")

    # capability_id: console.app-backup.export-teamname-required
    def test_export_requires_team_name(self):
        view = groupapp_backup.GroupAppsBackupExportView()
        request = self.factory.get("/console/teams//apps/42/backup/export", {"backup_id": "backup-1"})

        response = view.get(request, tenantName=None, group_id=42)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["msg_show"], "请选择需要导出备份的组")

    # capability_id: console.app-backup.export-id-required
    def test_export_requires_backup_id(self):
        view = groupapp_backup.GroupAppsBackupExportView()
        request = self.factory.get("/console/teams/demo-team/apps/42/backup/export")
        team = Obj(tenant_name="demo-team", enterprise_id="eid-1")
        group = Obj(group_name="demo-app", region_name="demo-region", app_id=42)

        with mock.patch.object(groupapp_backup.team_services, "get_tenant_by_tenant_name", return_value=team), \
                mock.patch.object(groupapp_backup.group_repo, "get_group_by_id", return_value=group):
            response = view.get(request, tenantName="demo-team", group_id=42)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["msg_show"], "请指明当前组的具体备份项")

    # capability_id: console.app-backup.export-team-missing
    def test_export_rejects_missing_team(self):
        view = groupapp_backup.GroupAppsBackupExportView()
        request = self.factory.get("/console/teams/demo-team/apps/42/backup/export", {"backup_id": "backup-1"})

        with mock.patch.object(groupapp_backup.team_services, "get_tenant_by_tenant_name", return_value=None):
            response = view.get(request, tenantName="demo-team", group_id=42)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["msg_show"], "团队demo-team不存在")

    # capability_id: console.app-backup.export-group-missing
    def test_export_rejects_missing_group(self):
        view = groupapp_backup.GroupAppsBackupExportView()
        request = self.factory.get("/console/teams/demo-team/apps/42/backup/export", {"backup_id": "backup-1"})
        team = Obj(tenant_name="demo-team", enterprise_id="eid-1")

        with mock.patch.object(groupapp_backup.team_services, "get_tenant_by_tenant_name", return_value=team), \
                mock.patch.object(groupapp_backup.group_repo, "get_group_by_id", return_value=None):
            response = view.get(request, tenantName="demo-team", group_id=42)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["msg_show"], "组42不存在")

    # capability_id: console.app-backup.export-failure
    def test_export_returns_error_when_service_fails(self):
        view = groupapp_backup.GroupAppsBackupExportView()
        request = self.factory.get("/console/teams/demo-team/apps/42/backup/export", {"backup_id": "backup-1"})
        team = Obj(tenant_name="demo-team", enterprise_id="eid-1")
        group = Obj(group_name="demo-app", region_name="demo-region", app_id=42)

        with mock.patch.object(groupapp_backup.team_services, "get_tenant_by_tenant_name", return_value=team), \
                mock.patch.object(groupapp_backup.group_repo, "get_group_by_id", return_value=group), \
                mock.patch.object(groupapp_backup.groupapp_backup_service, "export_group_backup", return_value=(500, "export failed", None)):
            response = view.get(request, tenantName="demo-team", group_id=42)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data["msg_show"], "export failed")

    # capability_id: console.app-backup.import
    def test_import_creates_restore_record(self):
        view = groupapp_backup.GroupAppsBackupImportView()
        view.tenant = Obj(tenant_name="demo-team", enterprise_id="eid-1")
        view.response_region = "demo-region"
        request = view.initialize_request(
            self.factory.post(
                "/console/teams/demo-team/apps/42/backup/import",
                {"file": SimpleUploadedFile("demo.bak", b"demo-backup")},
                format="multipart",
            )
        )
        record = mock.Mock()
        record.to_dict.return_value = {"restore_id": "restore-1"}

        with mock.patch.object(
                groupapp_backup.groupapp_backup_service,
                "import_group_backup",
                return_value=(200, "success", record),
        ) as import_mock, mock.patch.object(
            groupapp_backup.operation_log_service,
            "create_app_log",
        ):
            response = view.post(request, group_id=42)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["bean"]["restore_id"], "restore-1")
        import_mock.assert_called_once()

    # capability_id: console.app-backup.import-group-required
    def test_import_requires_group_id(self):
        view = groupapp_backup.GroupAppsBackupImportView()
        view.tenant = Obj(tenant_name="demo-team", enterprise_id="eid-1")
        view.response_region = "demo-region"
        request = view.initialize_request(
            self.factory.post(
                "/console/teams/demo-team/apps/backup/import",
                {"file": SimpleUploadedFile("demo.bak", b"demo-backup")},
                format="multipart",
            )
        )

        response = view.post(request, group_id=0)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["msg_show"], "请选择需要导出备份的组")

    # capability_id: console.app-backup.import-file-required
    def test_import_requires_file(self):
        view = groupapp_backup.GroupAppsBackupImportView()
        view.tenant = Obj(tenant_name="demo-team", enterprise_id="eid-1")
        view.response_region = "demo-region"
        request = view.initialize_request(
            self.factory.post(
                "/console/teams/demo-team/apps/42/backup/import",
                {},
                format="multipart",
            )
        )

        response = view.post(request, group_id=42)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["msg_show"], "请指定需要导入的备份信息")

    # capability_id: console.app-backup.import-file-size-guard
    def test_import_rejects_file_larger_than_limit(self):
        view = groupapp_backup.GroupAppsBackupImportView()
        view.tenant = Obj(tenant_name="demo-team", enterprise_id="eid-1")
        view.response_region = "demo-region"
        request = view.initialize_request(
            self.factory.post(
                "/console/teams/demo-team/apps/42/backup/import",
                {"file": SimpleUploadedFile("big.bak", b"x" * (2 * 1024 * 1024 + 1))},
                format="multipart",
            )
        )

        response = view.post(request, group_id=42)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["msg_show"], "文件大小不能超过2M")

    # capability_id: console.app-backup.import-failure
    def test_import_returns_error_when_service_fails(self):
        view = groupapp_backup.GroupAppsBackupImportView()
        view.tenant = Obj(tenant_name="demo-team", enterprise_id="eid-1")
        view.response_region = "demo-region"
        request = view.initialize_request(
            self.factory.post(
                "/console/teams/demo-team/apps/42/backup/import",
                {"file": SimpleUploadedFile("demo.bak", b"demo-backup")},
                format="multipart",
            )
        )

        with mock.patch.object(
                groupapp_backup.groupapp_backup_service,
                "import_group_backup",
                return_value=(500, "import failed", None),
        ):
            response = view.post(request, group_id=42)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data["msg_show"], "import failed")


class GroupAppsBackupStatusViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = groupapp_backup.GroupAppsBackupStatusView()
        self.view.tenant = Obj(tenant_name="demo-team")
        self.view.response_region = "demo-region"

    # capability_id: console.app-backup.list-status
    # capability_id: console.app-backup.status-sanitize
    def test_get_returns_backup_status_list_without_internal_server_info(self):
        request = self.factory.get("/console/teams/demo-team/apps/42/backups/status")
        backup_record = mock.Mock()
        backup_record.to_dict.return_value = {"backup_id": "backup-1", "status": "success", "backup_server_info": {"node": "n1"}}

        with mock.patch.object(
                groupapp_backup.groupapp_backup_service,
                "get_group_backup_status_by_group_id",
                return_value=(200, "success", [backup_record]),
        ):
            response = self.view.get(request, group_id=42)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["list"], [{"backup_id": "backup-1", "status": "success"}])

    # capability_id: console.app-backup.list-status-group-required
    def test_get_requires_group_id(self):
        request = self.factory.get("/console/teams/demo-team/apps/backups/status")

        response = self.view.get(request, group_id=0)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["msg_show"], "请选择需要备份的组")

    # capability_id: console.app-backup.list-status-empty
    def test_get_returns_success_when_status_not_found(self):
        request = self.factory.get("/console/teams/demo-team/apps/42/backups/status")

        with mock.patch.object(
                groupapp_backup.groupapp_backup_service,
                "get_group_backup_status_by_group_id",
                return_value=(404, "not found", None),
        ):
            response = self.view.get(request, group_id=42)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["msg_show"], "查询成功")

    # capability_id: console.app-backup.list-status-failure
    def test_get_returns_error_when_status_query_fails(self):
        request = self.factory.get("/console/teams/demo-team/apps/42/backups/status")

        with mock.patch.object(
                groupapp_backup.groupapp_backup_service,
                "get_group_backup_status_by_group_id",
                return_value=(500, "query failed", None),
        ):
            response = self.view.get(request, group_id=42)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data["msg_show"], "query failed")


class GroupAppsMigrationViewWorkflowTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = groupapp_migration.GroupAppsMigrateView()
        self.view.tenant = Obj(tenant_id="team-1", tenant_name="demo-team", tenant_alias="Demo Team", enterprise_id="eid-1")
        self.view.user = Obj(user_id=1)
        self.view.region_name = "demo-region"
        self.view.tenant_name = "demo-team"
        self.view.team_name = "demo-team"
        self.view.response_region = "demo-region"
        self.view.app = Obj(app_name="demo-app", app_id=42)

    # capability_id: console.app-migration.start
    def test_post_starts_group_migration(self):
        request = self.view.initialize_request(
            self.factory.post(
                "/console/teams/demo-team/apps/42/migrate",
                {
                    "region": "target-region",
                    "team": "target-team",
                    "backup_id": "backup-1",
                    "migrate_type": "migrate",
                    "event_id": "evt-1",
                },
                format="json",
            )
        )
        migrate_team = Obj(tenant_name="target-team", tenant_alias="Target Team")
        migrate_record = mock.Mock()
        migrate_record.to_dict.return_value = {"restore_id": "restore-1", "status": "running"}

        with mock.patch.object(groupapp_migration.team_services, "get_tenant_by_tenant_name", return_value=migrate_team), \
                mock.patch.object(groupapp_migration.region_services, "get_team_usable_regions",
                                  return_value=[Obj(region_name="target-region")]), \
                mock.patch.object(groupapp_migration.migrate_service, "start_migrate", return_value=migrate_record) as start_mock, \
                mock.patch.object(groupapp_migration.operation_log_service, "process_app_name", return_value="demo-app"), \
                mock.patch.object(groupapp_migration.operation_log_service, "process_team_name", return_value=" target-team"), \
                mock.patch.object(groupapp_migration.operation_log_service, "create_app_log"):
            response = self.view.post(request, group_id=42)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["bean"]["restore_id"], "restore-1")
        start_mock.assert_called_once_with(
            self.view.user,
            self.view.tenant,
            "demo-region",
            migrate_team,
            "target-region",
            "backup-1",
            "migrate",
            "evt-1",
            None,
        )

    # capability_id: console.app-migration.team-required
    def test_post_requires_target_team(self):
        request = self.view.initialize_request(
            self.factory.post(
                "/console/teams/demo-team/apps/42/migrate",
                {
                    "region": "target-region",
                    "backup_id": "backup-1",
                    "migrate_type": "migrate",
                },
                format="json",
            )
        )

        response = self.view.post(request, group_id=42)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["msg_show"], "请指明要迁移的团队")

    # capability_id: console.app-migration.target-team-missing
    def test_post_rejects_missing_target_team(self):
        request = self.view.initialize_request(
            self.factory.post(
                "/console/teams/demo-team/apps/42/migrate",
                {
                    "region": "target-region",
                    "team": "target-team",
                    "backup_id": "backup-1",
                    "migrate_type": "migrate",
                },
                format="json",
            )
        )

        with mock.patch.object(groupapp_migration.team_services, "get_tenant_by_tenant_name", return_value=None):
            response = self.view.post(request, group_id=42)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["msg_show"], "需要迁移的团队target-team不存在")

    # capability_id: console.app-migration.usable-region-guard
    def test_post_rejects_when_target_team_has_no_usable_regions(self):
        request = self.view.initialize_request(
            self.factory.post(
                "/console/teams/demo-team/apps/42/migrate",
                {
                    "region": "target-region",
                    "team": "target-team",
                    "backup_id": "backup-1",
                    "migrate_type": "migrate",
                },
                format="json",
            )
        )
        migrate_team = Obj(tenant_name="target-team", tenant_alias="Target Team")

        with mock.patch.object(groupapp_migration.team_services, "get_tenant_by_tenant_name", return_value=migrate_team), \
                mock.patch.object(groupapp_migration.region_services, "get_team_usable_regions", return_value=[]):
            response = self.view.post(request, group_id=42)

        self.assertEqual(response.status_code, 412)
        self.assertEqual(response.data["msg_show"], "团队未开通任何集群")

    # capability_id: console.app-migration.target-region-guard
    def test_post_rejects_region_without_team_access(self):
        request = self.view.initialize_request(
            self.factory.post(
                "/console/teams/demo-team/apps/42/migrate",
                {
                    "region": "target-region",
                    "team": "target-team",
                    "backup_id": "backup-1",
                    "migrate_type": "migrate",
                },
                format="json",
            )
        )
        migrate_team = Obj(tenant_name="target-team", tenant_alias="Target Team")

        with mock.patch.object(groupapp_migration.team_services, "get_tenant_by_tenant_name", return_value=migrate_team), \
                mock.patch.object(groupapp_migration.region_services, "get_team_usable_regions",
                                  return_value=[Obj(region_name="other-region")]):
            response = self.view.post(request, group_id=42)

        self.assertEqual(response.status_code, 412)
        self.assertIn("无法迁移至集群target-region", response.data["msg_show"])

    # capability_id: console.app-migration.query-status
    def test_get_returns_migration_status(self):
        request = self.factory.get("/console/teams/demo-team/apps/42/migrate", {"restore_id": "restore-1"})
        migrate_record = mock.Mock()
        migrate_record.to_dict.return_value = {"restore_id": "restore-1", "status": "success"}

        with mock.patch.object(groupapp_migration.migrate_service, "get_and_save_migrate_status", return_value=migrate_record) as status_mock:
            response = self.view.get(request, group_id=42)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["bean"]["restore_id"], "restore-1")
        status_mock.assert_called_once_with(self.view.user, "restore-1", "demo-team", "demo-region")

    # capability_id: console.app-migration.restore-id-required
    def test_get_requires_restore_id(self):
        request = self.factory.get("/console/teams/demo-team/apps/42/migrate")

        response = self.view.get(request, group_id=42)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["msg_show"], "请指明查询的备份ID")

    # capability_id: console.app-migration.record-missing
    def test_get_returns_not_found_when_record_missing(self):
        request = self.factory.get("/console/teams/demo-team/apps/42/migrate", {"restore_id": "restore-1"})

        with mock.patch.object(groupapp_migration.migrate_service, "get_and_save_migrate_status", return_value=None):
            response = self.view.get(request, group_id=42)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["msg_show"], "记录不存在")


class GroupAppsMigrationCleanupTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = groupapp_migration.GroupAppsView()
        self.view.tenant = Obj(tenant_name="demo-team")

    # capability_id: console.app-migration.cleanup-old-app
    def test_delete_cleans_old_group_after_restore(self):
        request = self.view.initialize_request(
            self.factory.delete("/console/teams/demo-team/apps/42/migrate/cleanup", {"new_group_id": 99}, format="json")
        )
        old_group = mock.Mock()
        new_group = mock.Mock()
        service = Obj(service_id="svc-1")

        with mock.patch.object(groupapp_migration.group_repo, "get_group_by_id", side_effect=[old_group, new_group]), \
                mock.patch.object(groupapp_migration.group_service, "get_group_services", return_value=[service]), \
                mock.patch.object(groupapp_migration.app_manage_service, "truncate_service") as truncate_mock:
            response = self.view.delete(request, group_id=42)

        self.assertEqual(response.status_code, 200)
        truncate_mock.assert_called_once_with(self.view.tenant, service)
        old_group.delete.assert_called_once_with()

    # capability_id: console.app-migration.cleanup-new-group-required
    def test_delete_requires_new_group_id(self):
        request = self.view.initialize_request(
            self.factory.delete("/console/teams/demo-team/apps/42/migrate/cleanup", {}, format="json")
        )

        response = self.view.delete(request, group_id=42)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["msg_show"], "请确认新恢复的组")

    # capability_id: console.app-migration.cleanup-group-required
    def test_delete_requires_group_id(self):
        request = self.view.initialize_request(
            self.factory.delete("/console/teams/demo-team/apps/migrate/cleanup", {"new_group_id": 99}, format="json")
        )

        response = self.view.delete(request, group_id=0)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["msg_show"], "请确认需要删除的组")

    # capability_id: console.app-migration.cleanup-group-missing
    def test_delete_rejects_missing_original_group(self):
        request = self.view.initialize_request(
            self.factory.delete("/console/teams/demo-team/apps/42/migrate/cleanup", {"new_group_id": 99}, format="json")
        )

        with mock.patch.object(groupapp_migration.group_repo, "get_group_by_id", return_value=None):
            response = self.view.delete(request, group_id=42)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["msg_show"], "该备份组已删除")

    # capability_id: console.app-migration.cleanup-same-group-noop
    def test_delete_skips_cleanup_when_restored_to_same_group(self):
        request = self.view.initialize_request(
            self.factory.delete("/console/teams/demo-team/apps/42/migrate/cleanup", {"new_group_id": 42}, format="json")
        )

        response = self.view.delete(request, group_id=42)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["msg_show"], "恢复到当前组无需删除")

    # capability_id: console.app-migration.cleanup-target-group-missing
    def test_delete_rejects_missing_restored_group(self):
        request = self.view.initialize_request(
            self.factory.delete("/console/teams/demo-team/apps/42/migrate/cleanup", {"new_group_id": 99}, format="json")
        )
        old_group = mock.Mock()

        with mock.patch.object(groupapp_migration.group_repo, "get_group_by_id", side_effect=[old_group, None]):
            response = self.view.delete(request, group_id=42)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["msg_show"], "组ID 99 不存在")


class GroupAppsMigrateRecordViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = groupapp_migration.MigrateRecordView()

    # capability_id: console.app-migration.unfinished-record
    def test_get_returns_unfinished_migration_record(self):
        request = self.factory.get("/console/teams/demo-team/apps/42/migrate-record", {"group_uuid": "group-uuid"})
        record = Obj(status="running", event_id="evt-1", migrate_type="migrate", restore_id="restore-1", backup_id="backup-1", group_id=42)

        with mock.patch.object(groupapp_migration.migrate_repo, "get_user_unfinished_migrate_record", return_value=[record]):
            response = self.view.get(request, 42)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["data"]["bean"]["is_finished"])
        self.assertEqual(response.data["data"]["bean"]["data"]["restore_id"], "restore-1")

    # capability_id: console.app-migration.unfinished-record-guard
    def test_get_requires_group_uuid(self):
        request = self.factory.get("/console/teams/demo-team/apps/42/migrate-record")

        response = self.view.get(request, 42)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["msg_show"], "参数缺失")

    # capability_id: console.app-migration.unfinished-record-empty
    def test_get_returns_finished_when_no_unfinished_record(self):
        request = self.factory.get("/console/teams/demo-team/apps/42/migrate-record", {"group_uuid": "group-uuid"})

        with mock.patch.object(groupapp_migration.migrate_repo, "get_user_unfinished_migrate_record", return_value=[]):
            response = self.view.get(request, 42)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["data"]["bean"]["is_finished"])
        self.assertIsNone(response.data["data"]["bean"]["data"])
