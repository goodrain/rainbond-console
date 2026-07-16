# capability_id: rainbond-console.vm-run.disk-asset-create
# capability_id: rainbond-console.vm-run.vm-export-multi-disk-create
# capability_id: console.vm-run.platform-runtime-guard
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
if "rest_framework_simplejwt.tokens" not in sys.modules:
    simplejwt_module = ModuleType("rest_framework_simplejwt")
    simplejwt_tokens_module = ModuleType("rest_framework_simplejwt.tokens")

    class _DummyAccessToken(dict):
        @classmethod
        def for_user(cls, user):
            return cls()

        def __str__(self):
            return ""

    simplejwt_tokens_module.AccessToken = _DummyAccessToken
    simplejwt_module.tokens = simplejwt_tokens_module
    sys.modules["rest_framework_simplejwt"] = simplejwt_module
    sys.modules["rest_framework_simplejwt.tokens"] = simplejwt_tokens_module
if "openapi_client" not in sys.modules:
    openapi_client_module = ModuleType("openapi_client")
    configuration_module = ModuleType("openapi_client.configuration")
    rest_module = ModuleType("openapi_client.rest")

    class _DummyConfiguration(object):
        def __init__(self):
            self.client_side_validation = False
            self.host = ""
            self.api_key = {}

    class _DummyApiException(Exception):
        status = 500
        body = ""

    openapi_client_module.ApiClient = object
    openapi_client_module.MarketOpenapiApi = object
    configuration_module.Configuration = _DummyConfiguration
    rest_module.ApiException = _DummyApiException

    sys.modules["openapi_client"] = openapi_client_module
    sys.modules["openapi_client.configuration"] = configuration_module
    sys.modules["openapi_client.rest"] = rest_module

import django  # noqa: E402

django.setup()

from django.test import TestCase  # noqa: E402
from rest_framework.test import APIRequestFactory  # noqa: E402

from console.exception.main import ServiceHandleException  # noqa: E402
from console.models.main import ComponentK8sAttributes  # noqa: E402
from console.views.app_create.vm_run import VMRunCreateView  # noqa: E402
from www.models.main import VirtualMachineImage  # noqa: E402


class VMAssetInstantiationTests(TestCase):
    def test_vm_run_create_rejects_when_vm_plugin_not_running(self):
        factory = APIRequestFactory()
        view = VMRunCreateView()
        view.tenant = SimpleNamespace(
            tenant_id="tenant-a",
            tenant_name="demo-team",
            namespace="tenant-ns",
            enterprise_id="eid",
        )
        view.response_region = "demo-region"
        view.user = SimpleNamespace(pk=1, nick_name="tester")

        request = view.initialize_request(factory.post(
            "/console/teams/demo-team/apps/create/vm",
            {
                "group_id": 7,
                "service_cname": "blocked-vm",
                "k8s_component_name": "blocked-vm",
                "image_name": "blocked-vm",
                "vm_url": "https://example.com/blocked-vm.iso",
            },
            format="json"
        ))

        with mock.patch(
                "console.views.app_create.vm_run.app_service.is_k8s_component_name_duplicate",
                return_value=False,
                create=True), \
                mock.patch(
                "console.views.app_create.vm_run.vms.ensure_vm_platform_running",
                side_effect=ServiceHandleException(
                    msg="vm plugin not running",
                    msg_show="虚拟机功能未正常运行，不允许执行虚拟机相关操作",
                    status_code=412,
                ),
                create=True):
            response = view.post(request)

        self.assertEqual(412, response.status_code)
        self.assertEqual("虚拟机功能未正常运行，不允许执行虚拟机相关操作", response.data["msg_show"])

    def test_vm_run_create_from_existing_disk_asset_reuses_ready_runtime_image(self):
        asset = VirtualMachineImage.objects.create(
            tenant_id="tenant-a",
            name="uploaded-root",
            image_url="tenant-ns:uploaded-root",
            source_type="upload",
            source_uri="/grdata/package_build/temp/events/uploaded-root.qcow2",
            status="ready",
            format="qcow2",
            boot_mode="uefi"
        )
        factory = APIRequestFactory()
        view = VMRunCreateView()
        view.tenant = SimpleNamespace(
            tenant_id="tenant-a", tenant_name="demo-team", namespace="tenant-ns", enterprise_id="eid")
        view.response_region = "demo-region"
        view.user = SimpleNamespace(pk=1, nick_name="tester")

        request = view.initialize_request(factory.post(
            "/console/teams/demo-team/apps/create/vm",
            {
                "group_id": 7,
                "service_cname": "uploaded-root-vm",
                "k8s_component_name": "uploaded-root-vm",
                "asset_id": asset.ID,
                "image_name": asset.name,
            },
            format="json"
        ))

        new_service = SimpleNamespace(
            service_id="service-new-uploaded-root",
            service_alias="gr123461",
            service_source="vm_run",
            create_status="creating",
            to_dict=lambda: {"service_id": "service-new-uploaded-root", "service_alias": "gr123461"}
        )

        with mock.patch(
                "console.views.app_create.vm_run.app_service.is_k8s_component_name_duplicate",
                return_value=False,
                create=True), \
                mock.patch(
                    "console.views.app_create.vm_run.vms.ensure_vm_platform_running",
                    return_value=None,
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
        self.assertEqual("tenant-ns:uploaded-root", create_args[5])
        self.assertEqual("", create_args[8])
        attrs = {
            item.name: item.attribute_value
            for item in ComponentK8sAttributes.objects.filter(component_id="service-new-uploaded-root")
        }
        self.assertEqual("uefi", attrs["vm_boot_mode"])
        self.assertEqual("qcow2", attrs["vm_boot_source_format"])
        self.assertIn("vm_disk_imports", attrs)
        disk_imports = json.loads(attrs["vm_disk_imports"])
        self.assertEqual("registry", disk_imports["disk"]["source_type"])
        self.assertEqual("tenant-ns:uploaded-root", disk_imports["disk"]["image_url"])
        self.assertEqual("/grdata/package_build/temp/events/uploaded-root.qcow2",
                         disk_imports["disk"]["source_uri"])

    def test_vm_run_create_from_iso_asset_keeps_boot_media_out_of_root_imports(self):
        iso_asset = VirtualMachineImage.objects.create(
            tenant_id="tenant-a",
            name="windows-installer",
            image_url="https://download/windows-server.iso",
            source_type="upload",
            source_uri="/tmp/windows-server.iso",
            status="ready",
            format="iso"
        )
        factory = APIRequestFactory()
        view = VMRunCreateView()
        view.tenant = SimpleNamespace(
            tenant_id="tenant-a", tenant_name="demo-team", namespace="tenant-ns", enterprise_id="eid")
        view.response_region = "demo-region"
        view.user = SimpleNamespace(pk=1, nick_name="tester")

        request = view.initialize_request(factory.post(
            "/console/teams/demo-team/apps/create/vm",
            {
                "group_id": 7,
                "service_cname": "installer-vm",
                "k8s_component_name": "installer-vm",
                "asset_id": iso_asset.ID,
                "image_name": iso_asset.name
            },
            format="json"
        ))

        new_service = SimpleNamespace(
            service_id="service-new-iso",
            service_alias="gr123457",
            service_source="vm_run",
            create_status="creating",
            to_dict=lambda: {"service_id": "service-new-iso", "service_alias": "gr123457"}
        )

        with mock.patch(
                "console.views.app_create.vm_run.app_service.is_k8s_component_name_duplicate",
                return_value=False,
                create=True), \
                mock.patch(
                    "console.views.app_create.vm_run.vms.ensure_vm_platform_running",
                    return_value=None,
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
        self.assertEqual("tenant-ns:windows-installer", create_args[5])
        self.assertEqual("https://download/windows-server.iso", create_args[8])
        self.assertFalse(
            ComponentK8sAttributes.objects.filter(component_id="service-new-iso", name="vm_disk_imports").exists()
        )
