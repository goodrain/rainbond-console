import unittest
from types import SimpleNamespace

from console.services.vm_boot_source import resolve_vm_boot_source


class VMBootSourceUnitTests(unittest.TestCase):

    def test_http_boot_source_is_rebound_to_internal_runtime_image(self):
        tenant = SimpleNamespace(namespace="tenant-ns")

        resolved = resolve_vm_boot_source(
            tenant,
            "exported-win",
            "https://download/exported-root.qcow2"
        )

        self.assertEqual("tenant-ns:exported-win", resolved["image"])
        self.assertEqual("https://download/exported-root.qcow2", resolved["vm_url"])

    def test_internal_runtime_image_is_left_unchanged(self):
        tenant = SimpleNamespace(namespace="tenant-ns")

        resolved = resolve_vm_boot_source(
            tenant,
            "base-win",
            "tenant-ns:base-win"
        )

        self.assertEqual("tenant-ns:base-win", resolved["image"])
        self.assertEqual("", resolved["vm_url"])

    def test_runtime_image_name_falls_back_to_tenant_name(self):
        tenant = SimpleNamespace(tenant_name="demo-team")

        resolved = resolve_vm_boot_source(
            tenant,
            "template-image-7",
            "https://download/root.qcow2"
        )

        self.assertEqual("demo-team:template-image-7", resolved["image"])


if __name__ == "__main__":
    unittest.main()
