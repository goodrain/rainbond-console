# -*- coding: utf-8 -*-
import collections
import importlib
import os
import sys
from types import ModuleType, SimpleNamespace
from unittest import TestCase, mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "appstore-sdk-python")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from console.services.app import app_service  # noqa: E402
from console.services.app_config.volume_service import AppVolumeService  # noqa: E402

volume_service_module = importlib.import_module("console.services.app_config.volume_service")


class VMLiveMigrationStorageTests(TestCase):
    def setUp(self):
        self.volume_service = AppVolumeService()
        self.tenant = SimpleNamespace(tenant_id="tenant-1")
        self.service = mock.Mock(
            extend_method="vm",
            service_region="region-1",
            service_id="service-1",
            service_cname="demo-vm",
            image="tenant-ns:image",
            cmd="",
            docker_cmd="",
            git_url="",
            min_memory=2048,
            min_cpu=2000,
            job_strategy="",
        )

    # capability_id: console.vm-storage-any-access-mode
    def test_build_vm_volume_settings_uses_rwx_when_available(self):
        with mock.patch.object(
            self.volume_service,
            "get_service_support_volume_options",
            return_value=[{"volume_type": "nfs-storage", "access_mode": ["RWX"], "provisioner": "cluster.local/nfs"}],
        ):
            settings, option = self.volume_service.build_vm_live_migration_volume_settings(
                self.tenant, self.service, "nfs-storage", {"volume_capacity": 20}
            )

        self.assertEqual(settings["access_mode"], "RWX")
        self.assertEqual(option["provisioner"], "cluster.local/nfs")

    # capability_id: console.vm-storage-any-access-mode
    def test_build_vm_volume_settings_accepts_non_rwx_storage(self):
        with mock.patch.object(
            self.volume_service,
            "get_service_support_volume_options",
            return_value=[{"volume_type": "local-path", "access_mode": ["RWO"], "provisioner": "cluster.local/local"}],
        ):
            settings, option = self.volume_service.build_vm_live_migration_volume_settings(
                self.tenant, self.service, "local-path", {"volume_capacity": 20}
            )

        self.assertEqual(settings["access_mode"], "RWO")
        self.assertEqual(option["provisioner"], "cluster.local/local")

    # capability_id: rainbond-console.vm-live-migration-unique-disk-path
    def test_resolve_vm_volume_path_allocates_unique_disk_suffix_for_duplicate_vm_device_path(self):
        service = SimpleNamespace(extend_method="vm", service_id="service-1")
        existing = [
            SimpleNamespace(volume_path="/disk"),
            SimpleNamespace(volume_path="/disk-1"),
            SimpleNamespace(volume_path="/lun"),
        ]

        with mock.patch.object(volume_service_module.volume_repo, "get_service_volumes", return_value=existing):
            resolved = self.volume_service.resolve_vm_volume_path(service, "/disk")

        self.assertEqual("/disk-2", resolved)

    # capability_id: rainbond-console.vm-live-migration-unique-disk-path
    def test_resolve_vm_volume_path_keeps_existing_path_when_editing_same_vm_device_type(self):
        service = SimpleNamespace(extend_method="vm", service_id="service-1")
        current_volume = SimpleNamespace(ID=3, volume_path="/disk-1")
        existing = [
            SimpleNamespace(ID=1, volume_path="/disk"),
            current_volume,
        ]

        with mock.patch.object(volume_service_module.volume_repo, "get_service_volumes", return_value=existing):
            resolved = self.volume_service.resolve_vm_volume_path(service, "/disk", current_volume=current_volume)

        self.assertEqual("/disk-1", resolved)

    # capability_id: console.vm-root-disk-selected-storage-type
    def test_update_check_app_uses_selected_storage_type_for_new_vm_root_disk(self):
        tenant = SimpleNamespace(tenant_id="tenant-1")
        user = SimpleNamespace(nick_name="tester")
        service = mock.Mock(
            extend_method="vm",
            service_region="region-1",
            service_id="service-1",
            service_cname="demo-vm",
            image="tenant-ns:image",
            cmd="",
            docker_cmd="",
            git_url="",
            min_memory=2048,
            min_cpu=2000,
            job_strategy="",
        )

        with mock.patch("console.services.app.service_source_repo.get_service_source", return_value=None), \
                mock.patch("console.services.app.volume_repo.get_service_volumes_with_config_file", return_value=[]), \
                mock.patch(
                    "console.services.app.volume_service.build_vm_live_migration_volume_settings",
                    return_value=({"volume_capacity": 20, "access_mode": "RWX"}, {"provisioner": "cluster.local/nfs"})
                ) as build_settings, \
                mock.patch("console.services.app.volume_service.add_service_volume") as add_service_volume:
            code, msg = app_service.update_check_app(
                tenant,
                service,
                {
                    "disk_cap": 20,
                    "disk_volume_type": "nfs-storage",
                    "min_memory": 2048,
                    "min_cpu": 2000,
                },
                user,
            )

        self.assertEqual(code, 200)
        self.assertEqual(msg, "success")
        build_settings.assert_called_once()
        add_service_volume.assert_called_once_with(
            tenant,
            service,
            "/disk",
            "nfs-storage",
            "disk",
            "",
            {"volume_capacity": 20, "access_mode": "RWX"},
            "tester",
            mode=None,
        )
