import collections
import os
from types import ModuleType

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import sys  # noqa: E402

sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

import django  # noqa: E402

django.setup()

from django.db import IntegrityError  # noqa: E402
from django.test import TestCase  # noqa: E402

from www.models.main import VMTemplate, VMTemplateDisk, VMTemplateVersion  # noqa: E402


class VMTemplateModelTests(TestCase):

    def test_template_name_is_unique_within_team(self):
        VMTemplate.objects.create(
            tenant_id="tenant-a",
            name="win10-devtools",
            description="v1"
        )

        with self.assertRaises(IntegrityError):
            VMTemplate.objects.create(
                tenant_id="tenant-a",
                name="win10-devtools",
                description="v2"
            )

    def test_template_version_defaults_to_generating_partial(self):
        template = VMTemplate.objects.create(
            tenant_id="tenant-a",
            name="ubuntu-dev",
            description="Ubuntu template"
        )

        version = VMTemplateVersion.objects.create(
            tenant_id="tenant-a",
            template_id=template.ID,
            version="v1"
        )

        self.assertEqual("generating", version.status)
        self.assertEqual("partial", version.recoverability)
        self.assertEqual("{}", version.runtime_snapshot_json)

    def test_template_disk_persists_root_and_data_roles(self):
        template = VMTemplate.objects.create(
            tenant_id="tenant-a",
            name="ubuntu-multi-disk",
            description="Multiple disks"
        )
        version = VMTemplateVersion.objects.create(
            tenant_id="tenant-a",
            template_id=template.ID,
            version="v1",
            status="ready",
            recoverability="full"
        )

        root_disk = VMTemplateDisk.objects.create(
            tenant_id="tenant-a",
            template_version_id=version.ID,
            disk_key="rootdisk",
            disk_name="rootdisk",
            disk_role="root",
            order_index=0,
            boot=True,
            image_url="https://download/root.qcow2",
            status="ready"
        )
        data_disk = VMTemplateDisk.objects.create(
            tenant_id="tenant-a",
            template_version_id=version.ID,
            disk_key="datadisk",
            disk_name="datadisk",
            disk_role="data",
            order_index=1,
            boot=False,
            image_url="https://download/data.qcow2",
            status="ready"
        )

        self.assertEqual("root", root_disk.disk_role)
        self.assertTrue(root_disk.boot)
        self.assertEqual("data", data_disk.disk_role)
        self.assertFalse(data_disk.boot)
