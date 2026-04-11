import collections
import json
import os
from types import ModuleType, SimpleNamespace
from unittest import mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import sys  # noqa: E402

sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

import django  # noqa: E402

django.setup()

from django.test import TestCase  # noqa: E402

from console.models.main import ComponentK8sAttributes  # noqa: E402
from console.repositories.virtual_machine import vm_repo  # noqa: E402
from console.services.app import app_service  # noqa: E402
from console.services.virtual_machine import vms  # noqa: E402
from www.models.main import TenantServiceInfo, VirtualMachineImage  # noqa: E402


class VirtualMachineServiceTests(TestCase):

    def _create_vm_service(self, tenant_id, service_id, image, extend_method="vm"):
        return TenantServiceInfo.objects.create(
            service_id=service_id,
            tenant_id=tenant_id,
            service_key=service_id,
            service_alias=service_id,
            service_region="demo-region",
            category="application",
            version="v1",
            image=image,
            extend_method=extend_method,
            k8s_component_name="{}-k8s".format(service_id)
        )

    def test_create_vm_image_asset_accepts_extra_metadata(self):
        asset = vms.create_vm_image_asset(
            tenant_id="tenant-a",
            name="uploaded-image",
            image_url="tenant-a:uploaded-image",
            source_type="upload",
            source_uri="/tmp/uploaded-image.qcow2",
            extra={
                "created_from": "vm_run"
            }
        )

        self.assertEqual("uploaded-image", asset.name)
        self.assertEqual({"created_from": "vm_run"}, json.loads(asset.extra_json))

    def test_get_vm_capabilities_returns_region_payload(self):
        expected = {
            "chunk_upload_supported": True,
            "network_modes": ["random", "fixed"],
            "gpu_supported": True,
        }

        with mock.patch("console.services.virtual_machine.region_api.get_vm_capabilities",
                        return_value=(None, {"bean": expected})):
            result = vms.get_vm_capabilities("demo-region", "demo-team")

        self.assertEqual(expected, result)

    def test_get_vm_capabilities_defaults_to_empty_payload(self):
        with mock.patch("console.services.virtual_machine.region_api.get_vm_capabilities",
                        return_value=(None, {})):
            result = vms.get_vm_capabilities("demo-region", "demo-team")

        self.assertEqual({}, result)

    def test_delete_vm_image_by_image_url_preserves_shared_image_records(self):
        VirtualMachineImage.objects.create(
            tenant_id="tenant-a",
            name="image-a",
            image_url="demo/shared-image"
        )
        VirtualMachineImage.objects.create(
            tenant_id="tenant-a",
            name="image-b",
            image_url="demo/shared-image"
        )

        deleted = vm_repo.delete_vm_image_by_image_url("tenant-a", "demo/shared-image")

        self.assertEqual((0, {}), deleted)
        self.assertEqual(2, VirtualMachineImage.objects.filter(tenant_id="tenant-a").count())

    # capability_id: console.vm-asset.delete-active-reference-guard
    def test_delete_vm_image_ignores_orphan_vm_asset_attrs(self):
        asset = VirtualMachineImage.objects.create(
            tenant_id="tenant-a",
            name="orphan-asset",
            image_url="demo/orphan-asset"
        )
        ComponentK8sAttributes.objects.create(
            tenant_id="tenant-a",
            component_id="deleted-service",
            name="vm_asset_id",
            save_type="string",
            attribute_value=str(asset.ID)
        )

        deleted, _ = vms.delete_vm_image("tenant-a", asset.ID)

        self.assertEqual(1, deleted)
        self.assertFalse(VirtualMachineImage.objects.filter(tenant_id="tenant-a", ID=asset.ID).exists())

    # capability_id: console.vm-asset.delete-active-reference-guard
    def test_delete_vm_image_blocks_active_vm_asset_reference(self):
        asset = VirtualMachineImage.objects.create(
            tenant_id="tenant-a",
            name="used-asset",
            image_url="demo/used-asset"
        )
        service = self._create_vm_service("tenant-a", "service-a", asset.image_url)
        ComponentK8sAttributes.objects.create(
            tenant_id="tenant-a",
            component_id=service.service_id,
            name="vm_asset_id",
            save_type="string",
            attribute_value=str(asset.ID)
        )

        with self.assertRaises(ValueError):
            vms.delete_vm_image("tenant-a", asset.ID)

    def test_list_vm_image_returns_asset_catalog_metadata(self):
        source = VirtualMachineImage.objects.create(
            tenant_id="tenant-a",
            name="source-image",
            image_url="demo/source-image",
            source_type="upload",
            source_uri="/tmp/source-image.qcow2",
            arch="amd64",
            os_name="Ubuntu 24.04",
            format="qcow2",
            size_bytes=1024,
            checksum="sha256:demo",
            status="ready",
            labels_json=json.dumps({"family": "ubuntu"}),
            extra_json=json.dumps({"note": "base-image"})
        )
        VirtualMachineImage.objects.create(
            tenant_id="tenant-a",
            name="target-image",
            image_url="demo/source-image",
            source_type="clone",
            source_uri="demo/source-image",
            arch="amd64",
            os_name="Ubuntu 24.04",
            format="qcow2",
            size_bytes=1024,
            checksum="sha256:demo",
            status="ready",
            source_asset_id=source.ID,
            clone_mode="reuse",
            labels_json=json.dumps({"family": "ubuntu"}),
            extra_json=json.dumps({"clone_source_name": "source-image"})
        )

        result = vms.list_vm_image("tenant-a")

        self.assertEqual(2, len(result))
        cloned = next(item for item in result if item["name"] == "target-image")
        self.assertEqual("clone", cloned["source_type"])
        self.assertEqual("qcow2", cloned["format"])
        self.assertEqual(1024, cloned["size_bytes"])
        self.assertEqual("ready", cloned["status"])
        self.assertEqual({"family": "ubuntu"}, cloned["labels"])
        self.assertEqual({"clone_source_name": "source-image"}, cloned["extra"])
        self.assertEqual({
            "id": source.ID,
            "name": source.name
        }, cloned["source_asset"])

    def test_create_region_service_includes_component_k8s_attributes(self):
        service = TenantServiceInfo.objects.create(
            service_id="service-region-a",
            tenant_id="tenant-a",
            service_key="service-region-a",
            service_alias="service-region-a",
            service_cname="service-region-a",
            service_region="demo-region",
            category="application",
            version="v1",
            image="demo/image",
            extend_method="vm",
            min_cpu=1000,
            min_memory=1024,
            min_node=1,
            create_status="creating",
            service_source="vm_run",
            code_from="image_manual",
            namespace="default",
            service_type="application",
            k8s_component_name="service-region-a-k8s"
        )
        ComponentK8sAttributes.objects.create(
            tenant_id="tenant-a",
            component_id=service.service_id,
            name="vm_network_mode",
            save_type="string",
            attribute_value="fixed"
        )
        ComponentK8sAttributes.objects.create(
            tenant_id="tenant-a",
            component_id=service.service_id,
            name="vm_network_name",
            save_type="string",
            attribute_value="rbd-plugins/bridge-test"
        )
        ComponentK8sAttributes.objects.create(
            tenant_id="tenant-a",
            component_id=service.service_id,
            name="vm_fixed_ip",
            save_type="string",
            attribute_value="172.16.20.230/24"
        )
        ComponentK8sAttributes.objects.create(
            tenant_id="tenant-a",
            component_id=service.service_id,
            name="vm_os_family",
            save_type="string",
            attribute_value="windows"
        )

        tenant = SimpleNamespace(
            tenant_id="tenant-a",
            tenant_name="tenant-a",
            enterprise_id="enterprise-a"
        )

        with mock.patch("console.services.app.service_group_relation_repo.get_group_id_by_service", return_value=1), \
                mock.patch("console.services.app.region_app_repo.get_region_app_id", return_value="region-app-1"), \
                mock.patch("console.services.app.region_api.create_service") as create_service_mock, \
                mock.patch("console.services.app.region_api.create_component_k8s_attribute", create=True), \
                mock.patch("console.services.app.arch_service.update_affinity_by_arch"):
            app_service.create_region_service(tenant, service, "tester")

        create_payload = create_service_mock.call_args[0][2]
        self.assertIn("component_k8s_attributes", create_payload)
        self.assertEqual(
            {
                ("vm_network_mode", "fixed"),
                ("vm_network_name", "rbd-plugins/bridge-test"),
                ("vm_fixed_ip", "172.16.20.230/24"),
                ("vm_os_family", "windows"),
            },
            {
                (item["name"], item["attribute_value"])
                for item in create_payload["component_k8s_attributes"]
            }
        )
        app_service.region_api.create_component_k8s_attribute.assert_not_called()

    def test_save_vm_runtime_config_preserves_non_vm_attrs_and_refreshes_vm_extension_keys(self):
        ComponentK8sAttributes.objects.create(
            tenant_id="tenant-a",
            component_id="service-a",
            name="labels",
            save_type="json",
            attribute_value=json.dumps({"app": "demo"})
        )
        ComponentK8sAttributes.objects.create(
            tenant_id="tenant-a",
            component_id="service-a",
            name="vm_gpu_enabled",
            save_type="string",
            attribute_value="stale"
        )
        ComponentK8sAttributes.objects.create(
            tenant_id="tenant-a",
            component_id="service-a",
            name="vm_fixed_ip",
            save_type="string",
            attribute_value="10.0.0.1/24"
        )

        vms.save_vm_runtime_config(
            "tenant-a",
            "service-a",
            {
                "gpu_enabled": True,
                "gpu_resources": ["gpu.example.com/A10"],
                "usb_enabled": True,
                "usb_resources": ["kubevirt.io/usb-a"],
                "network_mode": "fixed",
                "network_name": "default/bridge-net",
                "fixed_ip": "10.250.250.10/24",
                "asset_id": 18,
                "boot_mode": "uefi"
            }
        )

        attrs = {
            item.name: item.attribute_value
            for item in ComponentK8sAttributes.objects.filter(component_id="service-a")
        }

        self.assertEqual(json.dumps({"app": "demo"}), attrs["labels"])
        self.assertEqual("fixed", attrs["vm_network_mode"])
        self.assertEqual("default/bridge-net", attrs["vm_network_name"])
        self.assertEqual("10.250.250.10/24", attrs["vm_fixed_ip"])
        self.assertEqual("true", attrs["vm_gpu_enabled"])
        self.assertEqual(json.dumps(["gpu.example.com/A10"]), attrs["vm_gpu_resources"])
        self.assertEqual("true", attrs["vm_usb_enabled"])
        self.assertEqual(json.dumps(["kubevirt.io/usb-a"]), attrs["vm_usb_resources"])
        self.assertEqual("18", attrs["vm_asset_id"])
        self.assertEqual("uefi", attrs["vm_boot_mode"])

    def test_save_vm_runtime_config_removes_disabled_vm_extension_keys(self):
        ComponentK8sAttributes.objects.create(
            tenant_id="tenant-a",
            component_id="service-a",
            name="labels",
            save_type="json",
            attribute_value=json.dumps({"app": "demo"})
        )
        for name, value in (
            ("vm_network_mode", "fixed"),
            ("vm_network_name", "default/bridge-net"),
            ("vm_fixed_ip", "10.250.250.10/24"),
            ("vm_gpu_enabled", "true"),
            ("vm_gpu_resources", json.dumps(["gpu.example.com/A10"])),
            ("vm_asset_id", "18"),
        ):
            ComponentK8sAttributes.objects.create(
                tenant_id="tenant-a",
                component_id="service-a",
                name=name,
                save_type="string",
                attribute_value=value
            )

        ComponentK8sAttributes.objects.create(
            tenant_id="tenant-a",
            component_id="service-a",
            name="vm_usb_enabled",
            save_type="string",
            attribute_value="true"
        )

        vms.save_vm_runtime_config(
            "tenant-a",
            "service-a",
            {
                "gpu_enabled": False,
                "gpu_resources": [],
                "usb_enabled": False,
                "usb_resources": [],
                "network_mode": "random",
                "network_name": "",
                "fixed_ip": ""
            }
        )

        attrs = {
            item.name: item.attribute_value
            for item in ComponentK8sAttributes.objects.filter(component_id="service-a")
        }

        self.assertEqual({"labels", "vm_network_mode"}, set(attrs.keys()))
        self.assertEqual(json.dumps({"app": "demo"}), attrs["labels"])
        self.assertEqual("random", attrs["vm_network_mode"])

    def test_save_vm_runtime_config_syncs_region_when_service_is_complete(self):
        TenantServiceInfo.objects.create(
            service_id="service-a",
            tenant_id="tenant-a",
            service_key="service-a",
            service_alias="service-a",
            service_region="demo-region",
            category="application",
            version="v1",
            image="demo/image",
            extend_method="vm",
            create_status="complete",
            k8s_component_name="service-a-k8s"
        )
        ComponentK8sAttributes.objects.create(
            tenant_id="tenant-a",
            component_id="service-a",
            name="vm_network_name",
            save_type="string",
            attribute_value="stale-network"
        )

        with mock.patch("console.services.virtual_machine.region_api.create_component_k8s_attribute", create=True) as create_attr, \
                mock.patch("console.services.virtual_machine.region_api.update_component_k8s_attribute", create=True) as update_attr, \
                mock.patch("console.services.virtual_machine.region_api.delete_component_k8s_attribute", create=True) as delete_attr:
            vms.save_vm_runtime_config(
                "tenant-a",
                "service-a",
                {
                    "network_mode": "random",
                    "network_name": "",
                    "fixed_ip": "",
                    "gpu_enabled": False,
                    "gpu_resources": [],
                    "usb_enabled": False,
                    "usb_resources": [],
                }
            )

        create_attr.assert_called_once_with(
            "tenant-a",
            "demo-region",
            "service-a",
            {"name": "vm_network_mode", "save_type": "string", "attribute_value": "random"},
        )
        update_attr.assert_not_called()
        delete_attr.assert_called_once_with(
            "tenant-a",
            "demo-region",
            "service-a",
            {"name": "vm_network_name"},
        )

    def test_save_vm_runtime_config_uses_explicit_sync_context_during_create(self):
        TenantServiceInfo.objects.create(
            service_id="service-b",
            tenant_id="tenant-a",
            service_key="service-b",
            service_alias="service-b",
            service_region="demo-region",
            category="application",
            version="v1",
            image="demo/image",
            extend_method="vm",
            create_status="creating",
            k8s_component_name="service-b-k8s"
        )

        with mock.patch("console.services.virtual_machine.region_api.create_component_k8s_attribute", create=True) as create_attr, \
                mock.patch("console.services.virtual_machine.region_api.update_component_k8s_attribute", create=True) as update_attr, \
                mock.patch("console.services.virtual_machine.region_api.delete_component_k8s_attribute", create=True) as delete_attr:
            vms.save_vm_runtime_config(
                "tenant-a",
                "service-b",
                {
                    "network_mode": "fixed",
                    "network_name": "rbd-plugins/bridge-test",
                    "fixed_ip": "172.16.20.230/24",
                    "os_family": "windows",
                    "os_name": "Windows Server 2022",
                    "gpu_enabled": False,
                    "gpu_resources": [],
                    "usb_enabled": False,
                    "usb_resources": [],
                },
                sync_context={
                    "tenant_name": "tenant-a",
                    "region_name": "demo-region",
                    "service_alias": "service-b",
                }
            )

        create_attr.assert_has_calls([
            mock.call("tenant-a", "demo-region", "service-b", {
                "name": "vm_network_mode",
                "save_type": "string",
                "attribute_value": "fixed",
            }),
            mock.call("tenant-a", "demo-region", "service-b", {
                "name": "vm_network_name",
                "save_type": "string",
                "attribute_value": "rbd-plugins/bridge-test",
            }),
            mock.call("tenant-a", "demo-region", "service-b", {
                "name": "vm_fixed_ip",
                "save_type": "string",
                "attribute_value": "172.16.20.230/24",
            }),
            mock.call("tenant-a", "demo-region", "service-b", {
                "name": "vm_os_family",
                "save_type": "string",
                "attribute_value": "windows",
            }),
            mock.call("tenant-a", "demo-region", "service-b", {
                "name": "vm_os_name",
                "save_type": "string",
                "attribute_value": "Windows Server 2022",
            }),
        ], any_order=True)
        update_attr.assert_not_called()
        delete_attr.assert_not_called()

    def test_save_vm_disk_imports_persists_json_payload(self):
        imports = vms.save_vm_disk_imports(
            "tenant-a",
            "service-a",
            [
                {
                    "disk_key": "data-1",
                    "disk_name": "data-1",
                    "image_url": "https://download/data-1.qcow2",
                    "source_uri": "evt-1-data-1",
                    "format": "qcow2",
                    "checksum": "sha256:data-1",
                },
                {
                    "disk_name": "missing-key",
                    "image_url": "",
                }
            ]
        )

        attr = ComponentK8sAttributes.objects.get(component_id="service-a", name="vm_disk_imports")
        self.assertEqual("json", attr.save_type)
        self.assertEqual(imports, json.loads(attr.attribute_value))
        self.assertEqual(
            {
                "data-1": {
                    "volume_name": "data-1",
                    "disk_key": "data-1",
                    "disk_name": "data-1",
                    "image_url": "https://download/data-1.qcow2",
                    "source_uri": "evt-1-data-1",
                    "format": "qcow2",
                    "checksum": "sha256:data-1",
                }
            },
            imports,
        )

    def test_get_vm_profile_returns_asset_runtime_and_connections(self):
        asset = VirtualMachineImage.objects.create(
            tenant_id="tenant-a",
            name="ubuntu-24.04-base",
            image_url="demo/ubuntu-24.04-base",
            source_type="upload",
            source_uri="/tmp/ubuntu-24.04-base.qcow2",
            arch="amd64",
            os_name="Ubuntu 24.04",
            format="qcow2",
            size_bytes=2048,
            checksum="sha256:demo",
            status="ready"
        )
        for name, value in (
            ("vm_asset_id", str(asset.ID)),
            ("vm_network_mode", "fixed"),
            ("vm_network_name", "default/bridge-net"),
            ("vm_fixed_ip", "10.250.250.10/24"),
            ("vm_gpu_enabled", "true"),
            ("vm_gpu_resources", json.dumps(["gpu.example.com/A10"])),
            ("vm_usb_enabled", "true"),
            ("vm_usb_resources", json.dumps(["kubevirt.io/usb-a"])),
        ):
            ComponentK8sAttributes.objects.create(
                tenant_id="tenant-a",
                component_id="service-a",
                name=name,
                save_type="string",
                attribute_value=value
            )

        profile = vms.get_vm_profile(
            SimpleNamespace(
                tenant_id="tenant-a",
                service_id="service-a",
                image=asset.image_url,
                extend_method="vm"
            ),
            connections={
                "vnc_url": "http://example.com/vnc",
                "console_url": ""
            }
        )

        self.assertEqual(asset.ID, profile["asset"]["id"])
        self.assertEqual(asset.name, profile["asset"]["name"])
        self.assertEqual("fixed", profile["runtime"]["network_mode"])
        self.assertEqual("default/bridge-net", profile["runtime"]["network_name"])
        self.assertEqual("10.250.250.10/24", profile["runtime"]["fixed_ip"])
        self.assertTrue(profile["runtime"]["gpu_enabled"])
        self.assertEqual(["gpu.example.com/A10"], profile["runtime"]["gpu_resources"])
        self.assertTrue(profile["runtime"]["usb_enabled"])
        self.assertEqual(["kubevirt.io/usb-a"], profile["runtime"]["usb_resources"])
        self.assertEqual("http://example.com/vnc", profile["connections"]["vnc_url"])

    def test_validate_vm_runtime_config_allows_fixed_ip_without_network_name(self):
        vms.validate_vm_runtime_config({
            "network_mode": "fixed",
            "network_name": "",
            "fixed_ip": "10.250.250.10/24"
        })

    def test_validate_vm_runtime_config_requires_fixed_ip(self):
        with self.assertRaises(ValueError):
            vms.validate_vm_runtime_config({
                "network_mode": "fixed",
                "network_name": "default/bridge-net",
                "fixed_ip": ""
            })

    def test_validate_vm_runtime_config_requires_gpu_resources_when_enabled(self):
        with self.assertRaises(ValueError):
            vms.validate_vm_runtime_config({
                "gpu_enabled": True,
                "gpu_resources": []
            })

    def test_validate_vm_runtime_config_requires_usb_resources_when_enabled(self):
        with self.assertRaises(ValueError):
            vms.validate_vm_runtime_config({
                "usb_enabled": True,
                "usb_resources": []
            })
