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
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from console.services.app_config.volume_service import AppVolumeService  # noqa: E402

volume_service_module = importlib.import_module("console.services.app_config.volume_service")


class AppVolumeDeleteTests(TestCase):
    # capability_id: console.component.volume-delete-blocks-shared-mount
    def test_delete_service_volume_rejects_shared_mount_even_when_forced(self):
        service = AppVolumeService()
        tenant = SimpleNamespace(tenant_name="team-1", enterprise_id="enterprise-1")
        component = SimpleNamespace(
            service_id="component-a",
            service_region="region-1",
            service_alias="component-a",
            service_cname="Component A",
            create_status="complete",
        )
        volume = SimpleNamespace(ID=7, volume_name="shared-data", volume_type="share-file")
        mount_relation = SimpleNamespace(service_id="component-b")
        dependent = SimpleNamespace(service_cname="Component B", service_alias="component-b")

        with mock.patch.object(volume_service_module.volume_repo, "get_service_volume_by_pk", return_value=volume):
            with mock.patch.object(
                    volume_service_module.mnt_repo,
                    "get_mnt_by_dep_id_and_mntname",
                    return_value=[mount_relation],
            ):
                with mock.patch.object(
                        volume_service_module.service_repo,
                        "get_service_by_service_id",
                        return_value=dependent,
                ):
                    with mock.patch.object(volume_service_module.region_api, "delete_service_volumes") as delete_region:
                        with mock.patch.object(volume_service_module.volume_repo, "delete_volume_by_id") as delete_local:
                            code, msg, dependents = service.delete_service_volume_by_id(
                                tenant,
                                component,
                                volume.ID,
                                user_name="operator",
                                force="1",
                            )

        self.assertEqual(code, 400)
        self.assertIn("共享挂载", msg)
        self.assertEqual(dependents, [{"service_cname": "Component B", "service_alias": "component-b"}])
        delete_region.assert_not_called()
        delete_local.assert_not_called()
