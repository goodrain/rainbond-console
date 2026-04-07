# -*- coding: utf-8 -*-
import os
import sys
from types import ModuleType
from unittest import TestCase, mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402
from rest_framework.test import APIRequestFactory  # noqa: E402

django.setup()

from console.views.center_pool import groupapp_backup  # noqa: E402


class Obj(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class FakePaginator(object):
    def __init__(self, items, page_size):
        self.items = items
        self.count = len(items)

    def page(self, page):
        return self.items


class GroupAppsBackupListingTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    # capability_id: console.app-backup.list-by-app
    def test_team_group_apps_backup_view_returns_backup_list(self):
        view = groupapp_backup.TeamGroupAppsBackupView()
        view.tenant = Obj(tenant_name="demo-team")
        view.region_name = "demo-region"
        view.user = Obj(enterprise_id="eid-1", user_id=1)
        request = self.factory.get("/console/teams/demo-team/apps/42/backups", {"group_id": "42", "page": 1, "page_size": 10})
        backup = mock.Mock()
        backup.to_dict.return_value = {"backup_id": "backup-1", "group_id": 42}

        with mock.patch.object(groupapp_backup.groupapp_backup_service, "get_group_back_up_info", return_value=[backup]), \
                mock.patch.object(groupapp_backup, "JuncheePaginator", FakePaginator), \
                mock.patch.object(groupapp_backup, "EnterpriseConfigService", return_value=mock.Mock(get_cloud_obj_storage_info=mock.Mock(return_value={"provider": "s3"}))):
            response = view.get(request)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["data"]["bean"]["is_configed"])
        self.assertEqual(response.data["data"]["list"], [{"backup_id": "backup-1", "group_id": 42}])

    # capability_id: console.app-backup.list-by-app-group-required
    def test_team_group_apps_backup_view_requires_group_id(self):
        view = groupapp_backup.TeamGroupAppsBackupView()
        view.tenant = Obj(tenant_name="demo-team")
        view.region_name = "demo-region"
        view.user = Obj(enterprise_id="eid-1", user_id=1)
        request = self.factory.get("/console/teams/demo-team/apps/backups", {"page": 1, "page_size": 10})

        response = view.get(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["msg_show"], "请指定需要查询的组")

    # capability_id: console.app-backup.object-storage-unconfigured
    def test_team_group_apps_backup_view_marks_object_storage_unconfigured(self):
        view = groupapp_backup.TeamGroupAppsBackupView()
        view.tenant = Obj(tenant_name="demo-team")
        view.region_name = "demo-region"
        view.user = Obj(enterprise_id="eid-1", user_id=1)
        request = self.factory.get("/console/teams/demo-team/apps/42/backups", {"group_id": "42", "page": 1, "page_size": 10})

        with mock.patch.object(groupapp_backup.groupapp_backup_service, "get_group_back_up_info", return_value=[]), \
                mock.patch.object(groupapp_backup, "JuncheePaginator", FakePaginator), \
                mock.patch.object(groupapp_backup, "EnterpriseConfigService", return_value=mock.Mock(get_cloud_obj_storage_info=mock.Mock(return_value=None))):
            response = view.get(request)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["data"]["bean"]["is_configed"])

    # capability_id: console.app-backup.list-all
    def test_all_team_group_apps_backup_view_marks_deleted_groups(self):
        view = groupapp_backup.AllTeamGroupAppsBackupView()
        view.tenant = Obj(tenant_name="demo-team")
        view.response_region = "demo-region"
        request = self.factory.get("/console/teams/demo-team/backups", {"page": 1, "page_size": 10})
        existing_backup = mock.Mock()
        existing_backup.to_dict.return_value = {"backup_id": "backup-1", "group_id": 42}
        missing_backup = mock.Mock()
        missing_backup.to_dict.return_value = {"backup_id": "backup-2", "group_id": 43}

        with mock.patch.object(groupapp_backup.groupapp_backup_service, "get_all_group_back_up_info", return_value=[existing_backup, missing_backup]), \
                mock.patch.object(groupapp_backup, "JuncheePaginator", FakePaginator), \
                mock.patch.object(groupapp_backup.group_repo, "get_group_by_id", side_effect=[Obj(group_name="demo-app"), None]):
            response = view.get(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["list"][0]["group_name"], "demo-app")
        self.assertFalse(response.data["data"]["list"][0]["is_delete"])
        self.assertEqual(response.data["data"]["list"][1]["group_name"], "应用已删除")
        self.assertTrue(response.data["data"]["list"][1]["is_delete"])
