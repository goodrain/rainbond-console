# -*- coding: utf-8 -*-
import collections
import collections.abc
import os
import sys
from types import ModuleType
from unittest import TestCase, mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from console.services import backup_service as backup_service_module  # noqa: E402
from console.services.backup_service import GroupAppBackupService  # noqa: E402
from console.services.exception import ErrBackupInProgress  # noqa: E402


class Obj(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


# capability_id: console.app-backup.region-app-scope
class GroupAppBackupServiceScopeTests(TestCase):
    def setUp(self):
        self.service = GroupAppBackupService()
        self.tenant = Obj(tenant_id="team-1", tenant_name="demo-team", enterprise_id="eid-1")
        self.user = Obj(user_id=1, nick_name="tester")

    @staticmethod
    def _group_services():
        return [
            Obj(
                service_id="svc-a",
                service_name="app-a-svc",
                k8s_component_name="app-a-workload",
                service_alias="app-a",
                service_cname="应用A",
                extend_method="stateless_multiple",
                create_status="complete",
                service_source="source_code",
                min_memory=128,
                min_node=1,
            ),
            Obj(
                service_id="svc-b",
                service_name="app-b-svc",
                k8s_component_name="app-b-workload",
                service_alias="app-b",
                service_cname="应用B",
                extend_method="state_singleton",
                create_status="complete",
                service_source="source_code",
                min_memory=256,
                min_node=1,
            ),
        ]

    def test_check_backup_condition_only_checks_services_in_current_region_app(self):
        services = self._group_services()

        def service_status(region_name, tenant_name, body):
            self.assertEqual(body["service_ids"], ["svc-a"])
            return {"list": [{"service_id": "svc-a", "status": "running"}]}

        with mock.patch.object(backup_service_module.group_service, "get_group_services", return_value=services), \
                mock.patch.object(backup_service_module.region_app_repo, "get_region_app_id", return_value="region-app-1"), \
                mock.patch.object(
                    backup_service_module.region_api,
                    "list_app_services",
                    return_value=[{"service_name": "app-a-svc"}],
                ), \
                mock.patch.object(backup_service_module.region_api, "service_status", side_effect=service_status):
            code, running_state_services = self.service.check_backup_condition(self.tenant, "demo-region", 42)

        self.assertEqual(code, 200)
        self.assertEqual(running_state_services, [])

    def test_backup_group_apps_only_submits_services_in_current_region_app(self):
        services = self._group_services()
        backup_record = mock.Mock()

        def backup_group_apps(region_name, tenant_name, body):
            self.assertEqual(body["service_ids"], ["svc-a"])
            return {"bean": {"status": "starting"}}

        with mock.patch.object(backup_service_module.group_service, "get_group_services", return_value=services), \
                mock.patch.object(backup_service_module.region_app_repo, "get_region_app_id", return_value="region-app-1"), \
                mock.patch.object(
                    backup_service_module.region_api,
                    "list_app_services",
                    return_value=[{"service_name": "app-a-svc"}],
                ), \
                mock.patch.object(
                    backup_service_module,
                    "EnterpriseConfigService",
                    return_value=mock.Mock(get_cloud_obj_storage_info=mock.Mock(return_value=None)),
                ), \
                mock.patch.object(self.service, "get_backup_group_uuid", return_value="group-uuid"), \
                mock.patch.object(self.service, "get_group_app_metadata", return_value=(128, {"apps": []})), \
                mock.patch.object(backup_service_module, "current_time_str", return_value="20260330010101"), \
                mock.patch.object(backup_service_module, "make_uuid", return_value="event-1"), \
                mock.patch.object(backup_service_module.region_api, "backup_group_apps", side_effect=backup_group_apps), \
                mock.patch.object(backup_service_module.backup_record_repo, "create_backup_records", return_value=backup_record):
            result = self.service.backup_group_apps(
                self.tenant,
                self.user,
                "demo-region",
                42,
                "full-offline",
                "daily backup",
            )

        self.assertIs(result, backup_record)


# capability_id: console.app-backup.delete-in-progress
class GroupAppBackupServiceDeleteInProgressTests(TestCase):
    def test_delete_group_backup_raises_when_backup_in_progress(self):
        tenant = Obj(tenant_id="team-1", tenant_name="demo-team")
        with mock.patch.object(
                backup_service_module.backup_record_repo,
                "get_record_by_backup_id",
                return_value=Obj(status="starting"),
        ):
            with self.assertRaises(ErrBackupInProgress.__class__):
                GroupAppBackupService().delete_group_backup_by_backup_id(tenant, "region", "bid")
