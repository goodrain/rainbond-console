# -*- coding: utf-8 -*-
import os
import sys
from types import ModuleType
from unittest.mock import patch
from unittest import mock

import django
from django.test import SimpleTestCase

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")
django.setup()

from console.exception.main import ServiceHandleException
from console.services.mcp_query_service import mcp_query_service


class Obj(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class ManageComponentStorageTests(SimpleTestCase):
    def _make_context(self):
        team = Obj(tenant_id="tenant-1", tenant_name="team-1")
        app = Obj(ID=100, region_name="region-1")
        service = Obj(service_id="service-1", service_region="region-1")
        return team, app, service

    def _make_user(self):
        return Obj(
            user_id=1,
            enterprise_id="enterprise-1",
            nick_name="storage-operator",
            is_enterprise_admin=True,
            is_active=True,
        )

    # capability_id: console.component.storage-create-volume
    def test_create_volume_returns_created_and_volume(self):
        volume = Obj(volume_id=11, volume_name="data-vol", volume_path="/data", volume_type="nas")
        team, app, service = self._make_context()
        user = self._make_user()
        arguments = {
            "team_name": "team-1",
            "region_name": "region-1",
            "app_id": 100,
            "service_id": "service-1",
            "operation": "create_volume",
            "volume_path": "/data",
            "volume_type": "nas",
            "volume_name": "data-vol",
            "volume_capacity": 20,
        }
        empty_query = mock.Mock()
        empty_query.values.return_value = []
        with patch.object(mcp_query_service, "_get_team_app_service_context", return_value=(team, app, service)):
            with patch(
                "console.services.mcp_query_service.volume_repo.get_service_volumes_with_config_file",
                return_value=empty_query,
            ):
                with patch(
                    "console.services.mcp_query_service.volume_service.add_service_volume",
                    return_value=volume,
                ) as mock_add:
                    result = mcp_query_service.manage_component_storage(user, arguments)

        self.assertTrue(result["created"])
        self.assertEqual(result["volume"]["volume_id"], 11)
        self.assertEqual(result["volume"]["volume_name"], "data-vol")
        called_args, called_kwargs = mock_add.call_args
        self.assertIs(called_args[0], team)
        self.assertIs(called_args[1], service)
        self.assertEqual(called_args[2], "/data")
        self.assertEqual(called_args[3], "nas")
        self.assertEqual(called_args[4], "data-vol")
        options = called_args[6]
        self.assertEqual(options["volume_capacity"], 20)
        self.assertEqual(called_kwargs.get("mode"), None)

    # capability_id: console.component.storage-delete-volume
    def test_delete_volume_requires_force_branch(self):
        team, app, service = self._make_context()
        user = self._make_user()
        arguments = {
            "team_name": "team-1",
            "region_name": "region-1",
            "app_id": 100,
            "service_id": "service-1",
            "operation": "delete_volume",
            "volume_id": 7,
            "force": True,
        }
        with patch.object(mcp_query_service, "_get_team_app_service_context", return_value=(team, app, service)):
            with patch(
                "console.services.mcp_query_service.volume_service.delete_service_volume_by_id",
                return_value=(202, "has dependents", ["dep-1"]),
            ) as mock_delete:
                result = mcp_query_service.manage_component_storage(user, arguments)

        self.assertFalse(result["deleted"])
        self.assertTrue(result["requires_force"])
        self.assertEqual(result["message"], "has dependents")
        self.assertEqual(result["dependents"], ["dep-1"])
        mock_delete.assert_called_once_with(team, service, 7, user.nick_name, "1")

    # capability_id: console.component.storage-delete-volume
    def test_delete_volume_success_branch(self):
        context_team, context_app, context_service = self._make_context()
        user = self._make_user()
        arguments = {
            "team_name": "team-1",
            "region_name": "region-1",
            "app_id": 100,
            "service_id": "service-1",
            "operation": "delete_volume",
            "volume_id": 8,
        }
        volume = Obj(volume_id=55, volume_name="bulk-vol", volume_path="/data", volume_type="nas")
        with patch.object(
            mcp_query_service, "_get_team_app_service_context", return_value=(context_team, context_app, context_service)
        ):
            with patch(
                "console.services.mcp_query_service.volume_service.delete_service_volume_by_id",
                return_value=(200, "deleted", volume),
            ) as mock_delete:
                result = mcp_query_service.manage_component_storage(user, arguments)

        self.assertTrue(result["deleted"])
        self.assertEqual(result["volume"]["volume_id"], 55)
        self.assertEqual(result["volume"]["volume_name"], "bulk-vol")
        mock_delete.assert_called_once_with(context_team, context_service, 8, user.nick_name, None)

    # capability_id: console.component.storage-update-volume-capacity
    def test_update_volume_allows_capacity_change_without_path_change(self):
        team, app, service = self._make_context()
        service.service_alias = "service-1"
        user = self._make_user()
        volume = Obj(ID=11, volume_id=11, service_id="service-1", volume_name="data-vol", volume_path="/data", volume_type="nas", volume_capacity=10, mode=None)
        volume.save = mock.Mock()
        arguments = {
            "team_name": "team-1",
            "region_name": "region-1",
            "app_id": 100,
            "service_id": "service-1",
            "operation": "update_volume",
            "volume_id": 11,
            "new_volume_path": "/data",
            "volume_capacity": 20,
        }
        with patch.object(mcp_query_service, "_get_team_app_service_context", return_value=(team, app, service)):
            with patch.object(mcp_query_service, "service_requires_region_sync", return_value=True):
                with patch("console.services.mcp_query_service.volume_repo.get_service_volume_by_pk", return_value=volume):
                    with patch("console.services.mcp_query_service.volume_repo.get_service_config_file", return_value=None):
                        with patch(
                            "console.services.mcp_query_service.region_api.upgrade_service_volumes",
                            return_value=(Obj(status=200), {}),
                        ) as mock_region:
                            result = mcp_query_service.manage_component_storage(user, arguments)

        self.assertTrue(result["updated"])
        self.assertEqual(volume.volume_capacity, 20)
        volume.save.assert_called_once_with()
        self.assertEqual(mock_region.call_args[0][3]["volume_capacity"], 20)

    # capability_id: console.component.storage-update-volume
    def test_update_volume_can_resolve_target_by_current_volume_path(self):
        team, app, service = self._make_context()
        service.service_alias = "service-1"
        user = self._make_user()
        volume = Obj(ID=11, service_id="service-1", volume_name="data-vol", volume_path="/data", volume_type="nas", volume_capacity=10, mode=None)
        volume.save = mock.Mock()
        arguments = {
            "team_name": "team-1",
            "region_name": "region-1",
            "app_id": 100,
            "service_id": "service-1",
            "operation": "update_volume",
            "volume_path": "/data",
            "volume_capacity": 20,
        }
        with patch.object(mcp_query_service, "_get_team_app_service_context", return_value=(team, app, service)):
            with patch.object(mcp_query_service, "service_requires_region_sync", return_value=False):
                with patch("console.services.mcp_query_service.volume_repo.get_service_volume_by_path", return_value=volume):
                    with patch("console.services.mcp_query_service.volume_repo.get_service_config_file", return_value=None):
                        result = mcp_query_service.manage_component_storage(user, arguments)

        self.assertTrue(result["updated"])
        self.assertEqual(volume.volume_path, "/data")
        self.assertEqual(volume.volume_capacity, 20)
        volume.save.assert_called_once_with()

    # capability_id: console.component.storage-delete-volume
    def test_delete_volume_can_resolve_target_by_volume_name(self):
        team, app, service = self._make_context()
        user = self._make_user()
        volume = Obj(ID=11, service_id="service-1", volume_name="data-vol", volume_path="/data", volume_type="nas")
        arguments = {
            "team_name": "team-1",
            "region_name": "region-1",
            "app_id": 100,
            "service_id": "service-1",
            "operation": "delete_volume",
            "volume_name": "data-vol",
        }
        deleted_volume = Obj(volume_id=11, volume_name="data-vol", volume_path="/data", volume_type="nas")
        with patch.object(mcp_query_service, "_get_team_app_service_context", return_value=(team, app, service)):
            with patch("console.services.mcp_query_service.volume_repo.get_service_volume_by_name", return_value=volume):
                with patch(
                    "console.services.mcp_query_service.volume_service.delete_service_volume_by_id",
                    return_value=(200, "deleted", deleted_volume),
                ) as mock_delete:
                    result = mcp_query_service.manage_component_storage(user, arguments)

        self.assertTrue(result["deleted"])
        mock_delete.assert_called_once_with(team, service, 11, user.nick_name, None)

    # capability_id: console.component.storage-target-scope
    def test_update_volume_rejects_volume_id_from_another_component(self):
        team, app, service = self._make_context()
        user = self._make_user()
        foreign_volume = Obj(ID=11, service_id="other-service", volume_name="data-vol", volume_path="/data", volume_type="nas")
        arguments = {
            "team_name": "team-1",
            "region_name": "region-1",
            "app_id": 100,
            "service_id": "service-1",
            "operation": "update_volume",
            "volume_id": 11,
            "new_volume_path": "/data",
        }
        with patch.object(mcp_query_service, "_get_team_app_service_context", return_value=(team, app, service)):
            with patch("console.services.mcp_query_service.volume_repo.get_service_volume_by_pk", return_value=foreign_volume):
                with self.assertRaises(ServiceHandleException) as ctx:
                    mcp_query_service.manage_component_storage(user, arguments)

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("当前组件", ctx.exception.msg_show)

    # capability_id: console.component.storage-create-mount
    def test_create_mnt_batches_mounts(self):
        team, app, service = self._make_context()
        user = self._make_user()
        mounts = [{"dep_vol_id": 101, "mount_path": "/mnt-1"}, {"dep_vol_id": 102, "mount_path": "/mnt-2"}]
        arguments = {
            "team_name": "team-1",
            "region_name": "region-1",
            "app_id": 100,
            "service_id": "service-1",
            "operation": "create_mnt",
            "mounts": mounts,
        }
        with patch.object(mcp_query_service, "_get_team_app_service_context", return_value=(team, app, service)):
            with patch("console.services.mcp_query_service.mnt_service.batch_mnt_serivce_volume") as mock_batch:
                with patch(
                    "console.services.mcp_query_service.mnt_service.get_service_mnt_details_byid",
                    return_value=[{"dep_vol_id": 101}, {"dep_vol_id": 102}],
                ) as mock_details:
                    result = mcp_query_service.manage_component_storage(user, arguments)

        mock_batch.assert_called_once_with(team, service, mounts, user.nick_name)
        mock_details.assert_called_once_with(mounts)
        self.assertTrue(result["created"])
        self.assertEqual(result["items"], [{"dep_vol_id": 101}, {"dep_vol_id": 102}])
        self.assertEqual(result["total"], len(mounts))

    # capability_id: console.component.storage-summary
    def test_summary_includes_config_file_volumes(self):
        team, app, service = self._make_context()
        service.create_status = "complete"
        user = self._make_user()
        arguments = {
            "team_name": "team-1",
            "region_name": "region-1",
            "app_id": 100,
            "service_id": "service-1",
            "operation": "summary",
        }
        all_volumes = [
            {"volume_id": 21, "volume_name": "cfg", "volume_type": "config-file", "volume_path": "/etc/app/conf.json"},
            {"volume_id": 22, "volume_name": "data", "volume_type": "nas", "volume_path": "/data"},
        ]
        with patch.object(mcp_query_service, "_get_team_app_service_context", return_value=(team, app, service)):
            with patch(
                "console.services.mcp_query_service.volume_service.get_service_support_volume_options",
                return_value=[],
            ):
                with patch(
                    "console.services.mcp_query_service.volume_service.get_all_service_volumes_with_status",
                    return_value=all_volumes,
                ) as mock_all:
                    with patch(
                        "console.services.mcp_query_service.mnt_service.get_service_mnt_details",
                        return_value=([], 0),
                    ):
                        result = mcp_query_service.manage_component_storage(user, arguments)

        mock_all.assert_called_once_with(team, service)
        volume_types = {v["volume_type"] for v in result["volumes"]["items"]}
        self.assertEqual(volume_types, {"config-file", "nas"})
        self.assertEqual(result["volumes"]["total"], 2)

    # capability_id: console.component.storage-create-volume
    def test_create_volume_rejects_collision_with_existing_config_file_path(self):
        team, app, service = self._make_context()
        user = self._make_user()
        arguments = {
            "team_name": "team-1",
            "region_name": "region-1",
            "app_id": 100,
            "service_id": "service-1",
            "operation": "create_volume",
            "volume_path": "/etc/app/config.json",
            "volume_type": "nas",
            "volume_name": "data-vol",
        }
        existing_query = mock.Mock()
        existing_query.values.return_value = [{"volume_path": "/etc/app/config.json"}]
        with patch.object(mcp_query_service, "_get_team_app_service_context", return_value=(team, app, service)):
            with patch(
                "console.services.mcp_query_service.volume_repo.get_service_volumes_with_config_file",
                return_value=existing_query,
            ):
                with patch(
                    "console.services.mcp_query_service.volume_service.add_service_volume"
                ) as mock_add:
                    with self.assertRaises(ServiceHandleException) as ctx:
                        mcp_query_service.manage_component_storage(user, arguments)

        mock_add.assert_not_called()
        self.assertEqual(ctx.exception.status_code, 412)

    # capability_id: console.component.storage-create-volume
    def test_create_volume_rejects_update_param_name_with_actionable_message(self):
        team, app, service = self._make_context()
        user = self._make_user()
        arguments = {
            "team_name": "team-1",
            "region_name": "region-1",
            "app_id": 100,
            "service_id": "service-1",
            "operation": "create_volume",
            "volume_type": "config-file",
            "volume_name": "nginx-conf",
            # LLM mistakenly passes update_volume parameter names.
            "new_volume_path": "/etc/nginx/conf.d/default.conf",
            "new_file_content": "server {}",
        }
        with patch.object(mcp_query_service, "_get_team_app_service_context", return_value=(team, app, service)):
            with patch(
                "console.services.mcp_query_service.volume_service.add_service_volume"
            ) as mock_add:
                with self.assertRaises(ServiceHandleException) as ctx:
                    mcp_query_service.manage_component_storage(user, arguments)

        mock_add.assert_not_called()
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("volume_path", ctx.exception.msg_show)
        self.assertIn("new_volume_path", ctx.exception.msg_show)

    # capability_id: console.component.storage-create-volume
    def test_create_volume_rejects_update_file_content_param_name(self):
        team, app, service = self._make_context()
        user = self._make_user()
        arguments = {
            "team_name": "team-1",
            "region_name": "region-1",
            "app_id": 100,
            "service_id": "service-1",
            "operation": "create_volume",
            "volume_type": "config-file",
            "volume_name": "nginx-conf",
            "volume_path": "/etc/nginx/conf.d/default.conf",
            # volume_path supplied correctly, but file_content uses the update name.
            "new_file_content": "server {}",
        }
        with patch.object(mcp_query_service, "_get_team_app_service_context", return_value=(team, app, service)):
            with patch(
                "console.services.mcp_query_service.volume_service.add_service_volume"
            ) as mock_add:
                with self.assertRaises(ServiceHandleException) as ctx:
                    mcp_query_service.manage_component_storage(user, arguments)

        mock_add.assert_not_called()
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("file_content", ctx.exception.msg_show)
        self.assertIn("new_file_content", ctx.exception.msg_show)

    # capability_id: console.component.storage-delete-mount
    def test_delete_mnt_removes_relation(self):
        team, app, service = self._make_context()
        user = self._make_user()
        arguments = {
            "team_name": "team-1",
            "region_name": "region-1",
            "app_id": 100,
            "service_id": "service-1",
            "operation": "delete_mnt",
            "dep_vol_id": 77,
        }
        with patch.object(mcp_query_service, "_get_team_app_service_context", return_value=(team, app, service)):
            with patch(
                "console.services.mcp_query_service.mnt_service.delete_service_mnt_relation", return_value=(200, "ok")
            ) as mock_delete:
                result = mcp_query_service.manage_component_storage(user, arguments)

        mock_delete.assert_called_once_with(team, service, 77, user.nick_name)
        self.assertTrue(result["deleted"])
        self.assertEqual(result["dep_vol_id"], 77)
