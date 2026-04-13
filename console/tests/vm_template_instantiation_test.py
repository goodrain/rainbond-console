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
regionapi_module = ModuleType("www.apiclient.regionapi")


class _RegionInvokeApiStub(object):
    pass


regionapi_module.RegionInvokeApi = _RegionInvokeApiStub
sys.modules.setdefault("www.apiclient.regionapi", regionapi_module)

import django  # noqa: E402

django.setup()

from django.test import TestCase  # noqa: E402
from rest_framework.test import APIRequestFactory  # noqa: E402
from rest_framework.views import APIView  # noqa: E402

base_module = ModuleType("console.views.base")
app_service_module = ModuleType("console.services.app")
group_service_module = ModuleType("console.services.group_service")
app_config_module = ModuleType("console.services.app_config")
app_config_module.__path__ = []


class _RegionTenantHeaderView(APIView):
    pass


base_module.RegionTenantHeaderView = _RegionTenantHeaderView
app_service_module.app_service = SimpleNamespace(
    is_k8s_component_name_duplicate=lambda *args, **kwargs: False,
    create_vm_run_app=lambda *args, **kwargs: (200, "创建成功", None)
)
group_service_module.group_service = SimpleNamespace(add_service_to_group=lambda *args, **kwargs: (200, "success"))
app_config_module.volume_service = SimpleNamespace(add_service_volume=lambda *args, **kwargs: None)
sys.modules.setdefault("console.views.base", base_module)
sys.modules.setdefault("console.services.app", app_service_module)
sys.modules.setdefault("console.services.group_service", group_service_module)
sys.modules.setdefault("console.services.app_config", app_config_module)

from console.models.main import ComponentK8sAttributes  # noqa: E402
from console.services.virtual_machine import vms  # noqa: E402
from console.views.app_create.vm_run import VMRunCreateView  # noqa: E402
from www.models.main import VMTemplate, VMTemplateDisk, VMTemplateVersion, VirtualMachineImage  # noqa: E402


class VMTemplateInstantiationTests(TestCase):
    def setUp(self):
        self.root_asset = VirtualMachineImage.objects.create(
            tenant_id="tenant-a",
            name="root-image",
            image_url="tenant-ns:root-image",
            source_type="vm_export",
            source_uri="service://service-a",
            status="ready",
            format="qcow2"
        )
        self.template = VMTemplate.objects.create(
            tenant_id="tenant-a",
            name="ubuntu-dev",
            description="Ubuntu developer template",
            status="ready",
            latest_ready_version_id=1
        )
        self.version = VMTemplateVersion.objects.create(
            tenant_id="tenant-a",
            template_id=self.template.ID,
            version="v1",
            status="ready",
            recoverability="full",
            disk_count=2,
            boot_mode="uefi",
            root_asset_id=self.root_asset.ID,
            runtime_snapshot_json=json.dumps({
                "boot_mode": "uefi",
                "network_mode": "fixed",
                "network_name": "default/bridge-net",
                "fixed_ip": "10.10.10.10/24"
            })
        )
        self.template.latest_version_id = self.version.ID
        self.template.latest_ready_version_id = self.version.ID
        self.template.save()
        VMTemplateDisk.objects.create(
            tenant_id="tenant-a",
            template_version_id=self.version.ID,
            disk_key="rootdisk",
            disk_name="rootdisk",
            disk_role="root",
            order_index=0,
            boot=True,
            image_url=self.root_asset.image_url,
            status="ready",
            size_bytes=20 * 1024 * 1024 * 1024,
            extra_json=json.dumps({"boot_order": 1})
        )
        root_disk = VMTemplateDisk.objects.get(
            tenant_id="tenant-a",
            template_version_id=self.version.ID,
            disk_key="rootdisk"
        )
        root_disk.image_url = "https://download/root.qcow2"
        root_disk.save(update_fields=["image_url"])
        VMTemplateDisk.objects.create(
            tenant_id="tenant-a",
            template_version_id=self.version.ID,
            disk_key="data-1",
            disk_name="data-1",
            disk_role="data",
            order_index=1,
            boot=False,
            image_url="https://download/data.qcow2",
            status="ready",
            size_bytes=50 * 1024 * 1024 * 1024,
            extra_json=json.dumps({"boot_order": 2})
        )

    def test_resolve_vm_template_for_create_returns_root_image_and_disk_layout(self):
        payload = vms.resolve_vm_template_for_create("tenant-a", self.template.ID, self.version.ID)

        self.assertEqual("https://download/root.qcow2", payload["image_url"])
        self.assertEqual(self.root_asset.ID, payload["asset_id"])
        self.assertEqual("uefi", payload["runtime_snapshot"]["boot_mode"])
        self.assertEqual(2, len(payload["disk_layout"]))
        self.assertEqual("root", payload["disk_layout"][0]["disk_role"])
        self.assertEqual(1, payload["disk_layout"][0]["boot_order"])
        self.assertEqual("data", payload["data_disks"][0]["disk_role"])
        self.assertEqual(2, payload["data_disks"][0]["boot_order"])

    def test_vm_run_create_with_template_version_persists_template_attrs_and_adds_data_disk_volumes(self):
        factory = APIRequestFactory()
        view = VMRunCreateView()
        view.tenant = SimpleNamespace(tenant_id="tenant-a", tenant_name="demo-team", namespace="tenant-ns")
        view.response_region = "demo-region"
        view.user = SimpleNamespace(pk=1, nick_name="tester")

        request = view.initialize_request(factory.post(
            "/console/teams/demo-team/apps/create/vm",
            {
                "group_id": 7,
                "service_cname": "cloned-vm",
                "k8s_component_name": "cloned-vm",
                "template_id": self.template.ID,
                "template_version_id": self.version.ID,
                "network_mode": "fixed",
                "network_name": "default/bridge-net",
                "fixed_ip": "10.10.10.11/24"
            },
            format="json"
        ))

        new_service = SimpleNamespace(
            service_id="service-new",
            service_alias="gr123456",
            service_source="vm_run",
            create_status="creating",
            to_dict=lambda: {"service_id": "service-new", "service_alias": "gr123456"}
        )

        with mock.patch(
                "console.views.app_create.vm_run.app_service.is_k8s_component_name_duplicate",
                return_value=False,
                create=True), \
                mock.patch(
                    "console.views.app_create.vm_run.app_service.create_vm_run_app",
                    return_value=(200, "创建成功", new_service),
                    create=True) as create_vm_run_app_mock, \
                mock.patch(
                    "console.views.app_create.vm_run.group_service.add_service_to_group",
                    return_value=(200, "success")), \
                mock.patch(
                    "console.views.app_create.vm_run.volume_service.add_service_volume") as add_volume_mock:
            response = view.post(request)

        self.assertEqual(response.status_code, 200)
        _, create_args, _ = create_vm_run_app_mock.mock_calls[0]
        self.assertEqual("tenant-ns:template-image-{}".format(self.version.ID), create_args[5])
        self.assertEqual("https://download/root.qcow2", create_args[8])
        attrs = {
            item.name: item.attribute_value
            for item in ComponentK8sAttributes.objects.filter(component_id="service-new")
        }
        self.assertEqual(str(self.template.ID), attrs["vm_template_id"])
        self.assertEqual(str(self.version.ID), attrs["vm_template_version_id"])
        disk_layout = json.loads(attrs["vm_disk_layout"])
        self.assertEqual(2, len(disk_layout))
        self.assertEqual("root", disk_layout[0]["disk_role"])
        self.assertEqual(1, disk_layout[0]["boot_order"])
        self.assertEqual("data", disk_layout[1]["disk_role"])
        self.assertEqual(2, disk_layout[1]["boot_order"])
        disk_imports = json.loads(attrs["vm_disk_imports"])
        self.assertEqual(
            {
                "data-1": {
                    "volume_name": "data-1",
                    "disk_key": "data-1",
                    "disk_name": "data-1",
                    "image_url": "https://download/data.qcow2",
                    "source_uri": "",
                    "format": "",
                    "checksum": "",
                }
            },
            disk_imports
        )
        add_volume_mock.assert_called_once()
        _, _, volume_path, volume_type, volume_name = add_volume_mock.call_args[0][:5]
        self.assertEqual("/disk", volume_path)
        self.assertEqual("vm-file", volume_type)
        self.assertEqual("data-1", volume_name)

    def test_vm_run_create_does_not_force_region_attr_sync_before_service_registration(self):
        factory = APIRequestFactory()
        view = VMRunCreateView()
        view.tenant = SimpleNamespace(tenant_id="tenant-a", tenant_name="demo-team", namespace="tenant-ns")
        view.response_region = "demo-region"
        view.user = SimpleNamespace(pk=1, nick_name="tester")

        request = view.initialize_request(factory.post(
            "/console/teams/demo-team/apps/create/vm",
            {
                "group_id": 7,
                "service_cname": "cloned-vm",
                "k8s_component_name": "cloned-vm",
                "template_id": self.template.ID,
                "template_version_id": self.version.ID,
                "network_mode": "fixed",
                "network_name": "default/bridge-net",
                "fixed_ip": "10.10.10.11/24"
            },
            format="json"
        ))

        new_service = SimpleNamespace(
            service_id="service-new",
            service_alias="gr123456",
            service_region="demo-region",
            service_source="vm_run",
            create_status="creating",
            to_dict=lambda: {"service_id": "service-new", "service_alias": "gr123456"}
        )

        with mock.patch(
                "console.views.app_create.vm_run.app_service.is_k8s_component_name_duplicate",
                return_value=False,
                create=True), \
                mock.patch(
                    "console.views.app_create.vm_run.app_service.create_vm_run_app",
                    return_value=(200, "创建成功", new_service),
                    create=True), \
                mock.patch(
                    "console.views.app_create.vm_run.group_service.add_service_to_group",
                    return_value=(200, "success")), \
                mock.patch(
                    "console.views.app_create.vm_run.vms.save_vm_runtime_config") as save_runtime_mock, \
                mock.patch(
                    "console.views.app_create.vm_run.vms.save_vm_disk_imports"), \
                mock.patch(
                    "console.views.app_create.vm_run.volume_service.add_service_volume"):
            response = view.post(request)

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("sync_context", save_runtime_mock.call_args.kwargs)

    def test_vm_run_create_from_machine_asset_internalizes_http_root_disk_before_boot(self):
        machine_asset = VirtualMachineImage.objects.create(
            tenant_id="tenant-a",
            name="exported-win",
            image_url="https://download/exported-root.qcow2",
            source_type="vm_export",
            source_uri="service://service-a",
            status="ready",
            extra_json=json.dumps({
                "asset_kind": "machine",
                "disk_count": 1,
                "disks": [
                    {
                        "disk_key": "rootdisk",
                        "disk_role": "root",
                        "download_url": "https://download/exported-root.qcow2",
                    }
                ]
            })
        )
        factory = APIRequestFactory()
        view = VMRunCreateView()
        view.tenant = SimpleNamespace(tenant_id="tenant-a", tenant_name="demo-team", namespace="tenant-ns")
        view.response_region = "demo-region"
        view.user = SimpleNamespace(pk=1, nick_name="tester")

        request = view.initialize_request(factory.post(
            "/console/teams/demo-team/apps/create/vm",
            {
                "group_id": 7,
                "service_cname": "exported-vm",
                "k8s_component_name": "exported-vm",
                "asset_id": machine_asset.ID,
                "image_name": machine_asset.name
            },
            format="json"
        ))

        new_service = SimpleNamespace(
            service_id="service-new",
            service_alias="gr123456",
            service_source="vm_run",
            create_status="creating",
            to_dict=lambda: {"service_id": "service-new", "service_alias": "gr123456"}
        )

        with mock.patch(
                "console.views.app_create.vm_run.app_service.is_k8s_component_name_duplicate",
                return_value=False,
                create=True), \
                mock.patch(
                    "console.views.app_create.vm_run.app_service.create_vm_run_app",
                    return_value=(200, "创建成功", new_service),
                    create=True) as create_vm_run_app_mock, \
                mock.patch(
                    "console.views.app_create.vm_run.group_service.add_service_to_group",
                    return_value=(200, "success")):
            response = view.post(request)

        self.assertEqual(response.status_code, 200)
        _, create_args, _ = create_vm_run_app_mock.mock_calls[0]
        self.assertEqual("tenant-ns:exported-win", create_args[5])
        self.assertEqual("https://download/exported-root.qcow2", create_args[8])
