# capability_id: rainbond-console.vm-run.disk-asset-create
# capability_id: rainbond-console.vm-run.vm-export-multi-disk-create
# capability_id: console.vm-run.platform-runtime-guard
# capability_id: console.vm-run.new-asset-image-name-validation
# capability_id: console.vm-run.ssh-public-key-bootstrap
import collections
import json
import os
import base64
import struct
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
from console.services.vm_boot_source import is_valid_vm_runtime_image_name  # noqa: E402
from console.services.virtual_machine import vms  # noqa: E402
from console.views.app_create.vm_run import VMRunCreateView  # noqa: E402
from www.models.main import (  # noqa: E402
    ServiceGroupRelation,
    TenantServiceEnvVar,
    TenantServiceInfo,
    TenantServicesPort,
    VirtualMachineImage,
)


class VMAssetInstantiationTests(TestCase):
    @staticmethod
    def _ed25519_public_key():
        def ssh_string(value):
            return struct.pack(">I", len(value)) + value

        blob = ssh_string(b"ssh-ed25519") + ssh_string(b"\x11" * 32)
        return "ssh-ed25519 {} ubuntu office desktop".format(base64.b64encode(blob).decode("ascii"))

    def test_vm_ssh_bootstrap_accepts_only_linux_disk_images(self):
        key = self._ed25519_public_key()

        self.assertEqual(
            ("ubuntu", key),
            vms.validate_vm_ssh_bootstrap(
                "ubuntu", key, os_name="Ubuntu 24.04", os_family="linux", boot_source_format="qcow2"))

        invalid = (
            ("ubuntu", "", "Ubuntu 24.04", "linux", "qcow2"),
            ("ubuntu;id", key, "Ubuntu 24.04", "linux", "qcow2"),
            ("ubuntu", "-----BEGIN OPENSSH PRIVATE KEY-----DO_NOT_ECHO", "Ubuntu 24.04", "linux", "qcow2"),
            ("ubuntu", "ssh-ed25519 QUJD\nssh-ed25519 REVG", "Ubuntu 24.04", "linux", "qcow2"),
            ("ubuntu", "ssh-ed25519 !!!", "Ubuntu 24.04", "linux", "qcow2"),
            ("ubuntu", "ssh-ed25519 QUJDRA==", "Ubuntu 24.04", "linux", "qcow2"),
            ("ubuntu", "ssh-ed25519 " + "A" * 17000, "Ubuntu 24.04", "linux", "qcow2"),
            ("ubuntu", key, "Windows Server 2025", "windows", "qcow2"),
            ("ubuntu", key, "Ubuntu 24.04", "linux", "iso"),
            ("ubuntu", key, "Ubuntu 24.04", "linux", ""),
        )
        for username, public_key, os_name, os_family, source_format in invalid:
            with self.subTest(username=username, source_format=source_format), self.assertRaises(ValueError) as raised:
                vms.validate_vm_ssh_bootstrap(
                    username, public_key, os_name=os_name, os_family=os_family, boot_source_format=source_format)
            if public_key:
                self.assertNotIn(public_key, str(raised.exception))

    def test_vm_run_rejects_invalid_ssh_before_creating_asset_or_component(self):
        view = VMRunCreateView()
        view.tenant = SimpleNamespace(
            tenant_id="tenant-a", tenant_name="demo-team", namespace="tenant-ns", enterprise_id="eid")
        view.response_region = "demo-region"
        view.user = SimpleNamespace(pk=1, nick_name="tester")
        request = view.initialize_request(APIRequestFactory().post(
            "/console/teams/demo-team/apps/vm_run",
            {
                "group_id": 7,
                "service_cname": "invalid-vm",
                "k8s_component_name": "invalid-vm",
                "image_name": "invalid-vm",
                "source_type": "url",
                "vm_url": "https://example.com/invalid-vm.iso",
                "format": "iso",
                "os_name": "Ubuntu 24.04",
                "os_family": "linux",
                "ssh_username": "ubuntu",
                "ssh_public_key": self._ed25519_public_key(),
            },
            format="json"
        ))

        with mock.patch("console.views.app_create.vm_run.vms.create_vm_image_asset") as create_asset, \
                mock.patch("console.views.app_create.vm_run.app_service.create_vm_run_app") as create_component, \
                mock.patch(
                    "console.views.app_create.vm_run.enterprise_first_deploy_service.safe_begin_deploy_tracking"
                ) as track:
            response = view.post(request)

        self.assertEqual(400, response.status_code)
        create_asset.assert_not_called()
        create_component.assert_not_called()
        track.assert_not_called()

    def test_vm_run_rolls_back_asset_component_attrs_group_and_port_when_ssh_port_fails(self):
        view = VMRunCreateView()
        view.tenant = SimpleNamespace(
            tenant_id="tenant-a", tenant_name="demo-team", namespace="tenant-ns", enterprise_id="eid")
        view.response_region = "demo-region"
        view.user = SimpleNamespace(pk=1, nick_name="tester")
        asset_name = "ubuntu-rollback-test"
        service_id = "service-rollback-ssh"
        request = view.initialize_request(APIRequestFactory().post(
            "/console/teams/demo-team/apps/vm_run",
            {
                "group_id": 7,
                "service_cname": "rollback-vm",
                "k8s_component_name": "rollback-vm",
                "image_name": asset_name,
                "source_type": "url",
                "vm_url": "https://example.com/ubuntu-rollback.img",
                "format": "qcow2",
                "os_name": "Ubuntu 24.04",
                "os_family": "linux",
                "boot_mode": "uefi",
                "ssh_username": "ubuntu",
                "ssh_public_key": self._ed25519_public_key(),
            },
            format="json"
        ))

        def create_component(*args):
            service = TenantServiceInfo.objects.create(
                service_id=service_id,
                tenant_id="tenant-a",
                service_key=service_id,
                service_alias="gr123457",
                service_cname="rollback-vm",
                service_region="demo-region",
                category="application",
                version="v1",
                image="tenant-ns:{}".format(asset_name),
                extend_method="vm",
                create_status="creating",
                service_source="vm_run",
                code_from="image_manual",
                namespace="default",
                service_type="application",
                k8s_component_name="rollback-vm",
            )
            return 200, "success", service

        def add_port(tenant, service, port, **kwargs):
            TenantServiceEnvVar.objects.create(
                tenant_id=tenant.tenant_id,
                service_id=service.service_id,
                container_port=port,
                name="连接地址",
                attr_name="SSH_HOST",
                attr_value=service.service_alias,
                is_change=False,
                scope="outer",
            )
            TenantServicesPort.objects.create(
                tenant_id=tenant.tenant_id,
                service_id=service.service_id,
                container_port=port,
                mapping_port=port,
                protocol=kwargs["protocol"],
                port_alias="SSH22",
                is_inner_service=kwargs["is_inner_service"],
                is_outer_service=kwargs["is_outer_service"],
                k8s_service_name=service.service_alias,
            )
            return 500, "port failed", None

        def add_to_group(tenant, region, group_id, target_service_id):
            ServiceGroupRelation.objects.create(
                service_id=target_service_id,
                group_id=group_id,
                tenant_id=tenant.tenant_id,
                region_name=region,
            )
            return 200, "success"

        with mock.patch("console.views.app_create.vm_run.app_service.is_k8s_component_name_duplicate",
                        return_value=False), \
                mock.patch("console.views.app_create.vm_run.vms.ensure_vm_platform_running"), \
                mock.patch("console.views.app_create.vm_run.vms.resolve_vm_boot_mode", return_value="uefi"), \
                mock.patch("console.views.app_create.vm_run.app_service.create_vm_run_app",
                           side_effect=create_component), \
                mock.patch("console.views.app_create.vm_run.vms.build_initial_vm_disk_layout", return_value=[]), \
                mock.patch("console.views.app_create.vm_run.vms.build_vm_create_disk_imports", return_value=[]), \
                mock.patch("console.views.app_create.vm_run.group_service.add_service_to_group",
                           side_effect=add_to_group), \
                mock.patch("console.views.app_create.vm_run.port_service.add_service_port", side_effect=add_port), \
                mock.patch("console.views.app_create.vm_run.enterprise_first_deploy_service.safe_begin_deploy_tracking",
                           return_value=None), \
                mock.patch("console.views.app_create.vm_run.enterprise_first_deploy_service.safe_mark_failure"):
            response = view.post(request)

        self.assertEqual(500, response.status_code)
        self.assertFalse(VirtualMachineImage.objects.filter(tenant_id="tenant-a", name=asset_name).exists())
        self.assertFalse(TenantServiceInfo.objects.filter(service_id=service_id).exists())
        self.assertFalse(ComponentK8sAttributes.objects.filter(component_id=service_id).exists())
        self.assertFalse(ServiceGroupRelation.objects.filter(service_id=service_id).exists())
        self.assertFalse(TenantServiceEnvVar.objects.filter(service_id=service_id).exists())
        self.assertFalse(TenantServicesPort.objects.filter(service_id=service_id).exists())

    def test_vm_run_records_linux_ssh_runtime_and_internal_port_before_returning(self):
        view = VMRunCreateView()
        view.tenant = SimpleNamespace(
            tenant_id="tenant-a", tenant_name="demo-team", namespace="tenant-ns", enterprise_id="eid")
        view.response_region = "demo-region"
        view.user = SimpleNamespace(pk=1, nick_name="tester")
        public_key = self._ed25519_public_key()
        request = view.initialize_request(APIRequestFactory().post(
            "/console/teams/demo-team/apps/vm_run",
            {
                "group_id": 7,
                "service_cname": "ubuntu-vm",
                "k8s_component_name": "ubuntu-vm",
                "image_name": "ubuntu-24.04-minimal-cloudimg-amd64",
                "source_type": "url",
                "vm_url": (
                    "https://cloud-images.ubuntu.com/minimal/releases/noble/release/"
                    "ubuntu-24.04-minimal-cloudimg-amd64.img"
                ),
                "format": "qcow2",
                "os_name": "Ubuntu 24.04",
                "os_family": "linux",
                "boot_mode": "uefi",
                "ssh_username": "ubuntu",
                "ssh_public_key": public_key,
            },
            format="json"
        ))
        service = SimpleNamespace(
            service_id="service-new-ubuntu",
            service_alias="gr123456",
            service_source="vm_run",
            create_status="creating",
            to_dict=lambda: {"service_id": "service-new-ubuntu", "service_alias": "gr123456"}
        )
        call_order = []

        def record_port(*args, **kwargs):
            call_order.append("port")
            return 200, "success", object()

        with mock.patch(
                "console.views.app_create.vm_run.app_service.is_k8s_component_name_duplicate", return_value=False), \
                mock.patch("console.views.app_create.vm_run.vms.ensure_vm_platform_running"), \
                mock.patch(
                    "console.views.app_create.vm_run.vms.create_vm_image_asset",
                    return_value=SimpleNamespace(ID="asset-1", os_name="Ubuntu 24.04", boot_mode="uefi")), \
                mock.patch("console.views.app_create.vm_run.vms.resolve_vm_boot_mode", return_value="uefi"), \
                mock.patch("console.views.app_create.vm_run.app_service.create_vm_run_app",
                           return_value=(200, "success", service)), \
                mock.patch("console.views.app_create.vm_run.vms.build_initial_vm_disk_layout", return_value=[]), \
                mock.patch("console.views.app_create.vm_run.vms.save_vm_runtime_config") as save_runtime, \
                mock.patch("console.views.app_create.vm_run.vms.build_vm_create_disk_imports", return_value=[]), \
                mock.patch("console.views.app_create.vm_run.group_service.add_service_to_group",
                           side_effect=lambda *args: (call_order.append("group"), (200, "success"))[1]), \
                mock.patch("console.views.app_create.vm_run.port_service.add_service_port",
                           side_effect=record_port) as add_port, \
                mock.patch("console.views.app_create.vm_run.enterprise_first_deploy_service.safe_begin_deploy_tracking",
                           return_value=None), \
                mock.patch("console.views.app_create.vm_run.enterprise_first_deploy_service.safe_bind_events"):
            response = view.post(request)

        self.assertEqual(200, response.status_code)
        self.assertEqual(["group", "port"], call_order)
        self.assertEqual("uefi", save_runtime.call_args[0][2]["boot_mode"])
        self.assertEqual("Ubuntu 24.04", save_runtime.call_args[0][2]["os_name"])
        self.assertEqual("ubuntu", save_runtime.call_args[0][2]["ssh_username"])
        self.assertEqual(public_key, save_runtime.call_args[0][2]["ssh_public_key"])
        add_port.assert_called_once()
        self.assertEqual(22, add_port.call_args[0][2])
        self.assertEqual("tcp", add_port.call_args.kwargs["protocol"])
        self.assertTrue(add_port.call_args.kwargs["is_inner_service"])
        self.assertFalse(add_port.call_args.kwargs["is_outer_service"])
        self.assertNotIn(public_key, json.dumps(response.data))

    def test_vm_runtime_image_name_validator_enforces_oci_tag_boundaries(self):
        self.assertTrue(is_valid_vm_runtime_image_name("a" * 128))
        for image_name in (".image", "-image", "a" * 129, [], {}, 1, True):
            with self.subTest(image_name=image_name):
                self.assertFalse(is_valid_vm_runtime_image_name(image_name))

    def test_vm_run_rejects_non_string_image_name_and_import_sources(self):
        factory = APIRequestFactory()
        view = VMRunCreateView()
        view.tenant = SimpleNamespace(
            tenant_id="tenant-a", tenant_name="demo-team", namespace="tenant-ns", enterprise_id="eid")
        view.response_region = "demo-region"
        view.user = SimpleNamespace(pk=1, nick_name="tester")
        invalid_requests = [
            {"image_name": value, "vm_url": "https://example.com/windows.qcow2"}
            for value in ([], {}, 1, True)
        ]
        invalid_requests.extend(
            {"image_name": "windows", field: value}
            for field in ("event_id", "vm_url")
            for value in (None, [], {}, 0, False)
        )

        for invalid_data in invalid_requests:
            with self.subTest(invalid_data=invalid_data):
                request = view.initialize_request(factory.post(
                    "/console/teams/demo-team/apps/create/vm",
                    {
                        "group_id": 7,
                        "service_cname": "db-server-vm",
                        "k8s_component_name": "db-server-vm",
                        "format": "qcow2",
                        **invalid_data,
                    },
                    format="json"
                ))

                with mock.patch(
                        "console.views.app_create.vm_run.app_service.is_k8s_component_name_duplicate",
                        return_value=False), \
                        mock.patch(
                        "console.views.app_create.vm_run.vms.ensure_vm_platform_running",
                        return_value=None), \
                        mock.patch(
                        "console.views.app_create.vm_run.vms.create_vm_image_asset") as create_asset, \
                        mock.patch(
                        "console.views.app_create.vm_run.app_service.create_vm_run_app") as create_component:
                    response = view.post(request)

                self.assertEqual(400, response.status_code)
                create_asset.assert_not_called()
                create_component.assert_not_called()

    def test_vm_run_rejects_invalid_image_name_before_new_asset_or_component_creation(self):
        factory = APIRequestFactory()
        view = VMRunCreateView()
        view.tenant = SimpleNamespace(
            tenant_id="tenant-a", tenant_name="demo-team", namespace="tenant-ns", enterprise_id="eid")
        view.response_region = "demo-region"
        view.user = SimpleNamespace(pk=1, nick_name="tester")

        for source_data in (
                {"source_type": "url", "vm_url": "https://example.com/windows.qcow2"},
                {"event_id": "upload-event-id"}):
            request = view.initialize_request(factory.post(
                "/console/teams/demo-team/apps/create/vm",
                {
                    "group_id": 7,
                    "service_cname": "db-server-vm",
                    "k8s_component_name": "db-server-vm",
                    "image_name": "DBServer(TongYong)",
                    "format": "qcow2",
                    **source_data,
                },
                format="json"
            ))

            with mock.patch(
                    "console.views.app_create.vm_run.app_service.is_k8s_component_name_duplicate",
                    return_value=False), \
                    mock.patch(
                    "console.views.app_create.vm_run.vms.create_vm_image_asset") as create_asset, \
                    mock.patch(
                    "console.views.app_create.vm_run.app_service.create_vm_run_app") as create_component:
                response = view.post(request)

            self.assertEqual(400, response.status_code)
            create_asset.assert_not_called()
            create_component.assert_not_called()

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

    def test_vm_run_create_uses_requested_format_for_suffixless_existing_disk_asset_import(self):
        asset = VirtualMachineImage.objects.create(
            tenant_id="tenant-a",
            name="vava",
            image_url="tenant-ns:vava",
            source_type="upload",
            source_uri="/grdata/package_build/temp/events/daba864158f342cab041cb3e008d4afd",
            status="ready",
            format="",
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
                "service_cname": "vava-vm",
                "k8s_component_name": "vava-vm",
                "asset_id": asset.ID,
                "image_name": asset.name,
                "format": "qcow2",
            },
            format="json"
        ))

        new_service = SimpleNamespace(
            service_id="service-new-vava",
            service_alias="gr123462",
            service_source="vm_run",
            create_status="creating",
            to_dict=lambda: {"service_id": "service-new-vava", "service_alias": "gr123462"}
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
                    create=True), \
                mock.patch(
                    "console.views.app_create.vm_run.group_service.add_service_to_group",
                    return_value=(200, "success")):
            response = view.post(request)

        self.assertEqual(response.status_code, 200)
        attrs = {
            item.name: item.attribute_value
            for item in ComponentK8sAttributes.objects.filter(component_id="service-new-vava")
        }
        self.assertEqual("qcow2", attrs["vm_boot_source_format"])
        disk_imports = json.loads(attrs["vm_disk_imports"])
        self.assertEqual("registry", disk_imports["disk"]["source_type"])
        self.assertEqual("tenant-ns:vava", disk_imports["disk"]["image_url"])
        self.assertEqual("/grdata/package_build/temp/events/daba864158f342cab041cb3e008d4afd",
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
