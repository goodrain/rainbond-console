# capability_id: console.vm-example.password-login-bootstrap
import collections
import io
import json
import logging
import os
import secrets
from contextlib import contextmanager
from contextlib import ExitStack
from types import ModuleType, SimpleNamespace
from unittest import mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import sys  # noqa: E402

sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
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

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat  # noqa: E402
from django.test import TestCase  # noqa: E402
from passlib.hash import sha512_crypt  # noqa: E402
from rest_framework.test import APIRequestFactory  # noqa: E402

from console.exception.main import ServiceHandleException  # noqa: E402
from console.models.main import ComponentK8sAttributes  # noqa: E402
from console.services.app import app_service  # noqa: E402
from console.services.app_check_service import AppCheckService  # noqa: E402
from console.services.backup_service import groupapp_backup_service  # noqa: E402
from console.services.k8s_attribute import k8s_attribute_service  # noqa: E402
from console.services.market_app.component import Component  # noqa: E402
from console.services.market_app.market_app import MarketApp  # noqa: E402
from console.services.market_app.new_components import NewComponents  # noqa: E402
from console.services.share_services import share_service  # noqa: E402
from console.services.virtual_machine import vms  # noqa: E402
from console.views.k8s_attribute import (  # noqa: E402
    ComponentK8sAttributeListView,
    ComponentK8sAttributeView,
)
from console.views.app_config.app_domain import VirtualMachineCapabilityView  # noqa: E402
from console.views.app_create.vm_run import VMRunCreateView  # noqa: E402
from www.models.main import (  # noqa: E402
    ServiceGroupRelation,
    TenantServiceEnvVar,
    TenantServiceInfo,
    TenantServicesPort,
)

UBUNTU_NOBLE_QCOW2_URL = (
    "https://cloud-images.ubuntu.com/minimal/releases/noble/release/"
    "ubuntu-24.04-minimal-cloudimg-amd64.img"
)


def runtime_generated_password(length=24):
    return (secrets.token_urlsafe(length) + "Aa1!")[:length]


def runtime_generated_password_hash():
    password = runtime_generated_password()
    return password, sha512_crypt.using(rounds=500000, salt_size=16).hash(password)


def synthetic_public_key():
    key = Ed25519PrivateKey.generate().public_key()
    return key.public_bytes(Encoding.OpenSSH, PublicFormat.OpenSSH).decode("ascii")


@contextmanager
def isolated_default_logger():
    logger = logging.getLogger("default")
    previous_handlers = logger.handlers[:]
    previous_propagate = logger.propagate
    previous_level = logger.level
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.DEBUG)
    try:
        yield stream
    finally:
        logger.handlers = previous_handlers
        logger.propagate = previous_propagate
        logger.setLevel(previous_level)


class VMExamplePasswordLoginTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.vm_view = VMRunCreateView()
        self.vm_view.tenant = SimpleNamespace(
            tenant_id="tenant-vm-login",
            tenant_name="vm-login-team",
            namespace="vm-login-namespace",
            enterprise_id="vm-login-enterprise",
        )
        self.vm_view.response_region = "vm-login-region"
        self.vm_view.user = SimpleNamespace(pk=1, nick_name="vm-login-test-user")

    def _runtime_password(self):
        return runtime_generated_password()

    def _base_password_request(self, password=None):
        return {
            "group_id": 7,
            "service_cname": "ubuntu-example",
            "k8s_component_name": "ubuntu-example",
            "image_name": "ubuntu-24.04-example",
            "source_type": "url",
            "vm_url": UBUNTU_NOBLE_QCOW2_URL,
            "format": "qcow2",
            "arch": "amd64",
            "boot_mode": "uefi",
            "os_name": "Ubuntu 24.04",
            "os_family": "linux",
            "login_method": "password",
            "ssh_username": "ubuntu",
            "login_password": password or self._runtime_password(),
        }

    def _post_vm_run(self, values):
        request = self.vm_view.initialize_request(self.factory.post(
            "/console/teams/vm-login-team/apps/vm_run",
            values,
            format="json",
        ))
        return self.vm_view.post(request)

    def test_password_validator_preserves_whitespace_and_counts_unicode_codepoints(self):
        accepted = "  " + self._runtime_password() + "  "
        self.assertTrue(
            vms.validate_vm_login_password(accepted) == accepted,
            "password whitespace was not preserved",
        )
        self.assertTrue(
            vms.validate_vm_login_password("🚀" * 12) == "🚀" * 12,
            "password length must count Unicode codepoints",
        )
        self.assertTrue(
            vms.validate_vm_login_password("a" * 128) == "a" * 128,
            "maximum password length was rejected",
        )

        invalid = (
            ("short", "a" * 11),
            ("too long", "a" * 129),
            ("blank", " " * 12),
            ("c0", "safe-prefix\nunsafe-suffix"),
            ("c1", "safe-prefix\u0085unsafe-suffix"),
            ("line separator", "safe-prefix\u2028unsafe-suffix"),
            ("paragraph separator", "safe-prefix\u2029unsafe-suffix"),
        )
        for case_name, value in invalid:
            with self.subTest(case=case_name), self.assertRaises(ValueError):
                vms.validate_vm_login_password(value)

    def test_password_hash_uses_sha512_crypt_rounds_random_salt_and_verifies(self):
        password = self._runtime_password()
        first = vms.hash_vm_login_password(password)
        second = vms.hash_vm_login_password(password)
        parsed = sha512_crypt.from_string(first)

        self.assertTrue(first.startswith("$6$rounds=500000$"), "hash format mismatch")
        self.assertTrue(parsed.rounds == 500000, "hash rounds mismatch")
        self.assertTrue(len(parsed.salt) == 16, "hash salt size mismatch")
        self.assertTrue(sha512_crypt.verify(password, first), "hash verification failed")
        self.assertTrue(first != second, "hash salt was reused")
        self.assertFalse(password in first, "plaintext appeared in hash output")

    def test_legacy_ssh_pair_and_no_credential_requests_remain_compatible(self):
        common = {
            "source_type": "url",
            "vm_url": UBUNTU_NOBLE_QCOW2_URL,
            "image_format": "qcow2",
            "arch": "amd64",
            "boot_mode": "uefi",
            "os_name": "Ubuntu 24.04",
            "os_family": "linux",
        }
        key = synthetic_public_key()
        legacy = vms.prepare_vm_login_bootstrap(
            login_method="",
            ssh_username="ubuntu",
            ssh_public_key=key,
            **common
        )
        self.assertTrue(legacy["login_method"] == "ssh_key", "legacy SSH mode was not inferred")
        self.assertTrue(legacy["ssh_public_key"] == key, "legacy public key was changed")
        self.assertFalse(legacy["login_password_hash"], "legacy SSH mode generated a password hash")

        no_credentials = vms.prepare_vm_login_bootstrap(login_method="", **common)
        self.assertTrue(no_credentials["login_method"] == "", "empty legacy request changed behavior")
        self.assertFalse(no_credentials["login_password_hash"], "empty legacy request created credentials")

    def test_login_modes_reject_incomplete_and_mutually_exclusive_credentials(self):
        username = "ubuntu"
        public_key = synthetic_public_key()
        password = self._runtime_password()
        common = {
            "source_type": "url",
            "vm_url": UBUNTU_NOBLE_QCOW2_URL,
            "image_format": "qcow2",
            "arch": "amd64",
            "boot_mode": "uefi",
            "os_name": "Ubuntu 24.04",
            "os_family": "linux",
        }
        invalid = (
            ("ssh key with password", {
                "login_method": "ssh_key", "ssh_username": username, "ssh_public_key": public_key,
                "login_password": password,
            }),
            ("password with key", {
                "login_method": "password", "ssh_username": username, "ssh_public_key": public_key,
                "login_password": password,
            }),
            ("missing key", {"login_method": "ssh_key", "ssh_username": username}),
            ("missing password", {"login_method": "password", "ssh_username": username}),
            ("unknown method", {"login_method": "token", "ssh_username": username}),
        )
        for case_name, credentials in invalid:
            with self.subTest(case=case_name), self.assertRaises(ValueError):
                vms.prepare_vm_login_bootstrap(
                    **common,
                    ssh_username=credentials.pop("ssh_username", ""),
                    ssh_public_key=credentials.pop("ssh_public_key", ""),
                    login_password=credentials.pop("login_password", ""),
                    **credentials,
                )

    def test_password_mode_is_limited_to_canonical_noble_and_enabled_capability(self):
        password = self._runtime_password()
        valid = {
            "login_method": "password",
            "ssh_username": "ubuntu",
            "login_password": password,
            "source_type": "url",
            "vm_url": UBUNTU_NOBLE_QCOW2_URL,
            "image_format": "qcow2",
            "arch": "amd64",
            "boot_mode": "uefi",
            "os_name": "Ubuntu 24.04",
            "os_family": "linux",
            "password_bootstrap_supported": True,
        }
        result = vms.prepare_vm_login_bootstrap(**valid)
        self.assertTrue(result["login_method"] == "password", "password mode was not selected")
        self.assertTrue(result["login_password_hash"].startswith("$6$rounds=500000$"), "hash was not returned")
        self.assertFalse(password in json.dumps(result), "plaintext was returned from bootstrap preparation")

        invalid_overrides = (
            ("root user", {"ssh_username": "root"}),
            ("wrong source", {"source_type": "upload"}),
            ("noncanonical URL", {"vm_url": UBUNTU_NOBLE_QCOW2_URL + "?download=1"}),
            ("installer media", {"image_format": "iso"}),
            ("wrong architecture", {"arch": "arm64"}),
            ("wrong firmware", {"boot_mode": "bios"}),
            ("non-Linux metadata", {"os_family": "windows"}),
            ("region capability absent", {"password_bootstrap_supported": False}),
        )
        for case_name, overrides in invalid_overrides:
            request_values = {**valid, **overrides}
            with self.subTest(case=case_name), self.assertRaises(ValueError) as raised:
                vms.prepare_vm_login_bootstrap(**request_values)
            self.assertFalse(password in str(raised.exception), "validation error included plaintext")

    def test_vm_capabilities_route_passes_region_password_gate_without_defaulting_true(self):
        view = VirtualMachineCapabilityView()
        view.tenant = SimpleNamespace(tenant_id="tenant-vm-login", tenant_name="vm-login-team")
        view.response_region = "vm-login-region"

        for region_capabilities, expected_methods in (
                ({"password_bootstrap_supported": True}, ["ssh_key", "password"]),
                ({"password_bootstrap_supported": False}, ["ssh_key"]),
                ({}, ["ssh_key"]),
                ({"password_bootstrap_supported": "true"}, ["ssh_key"]),
                ({"password_bootstrap_supported": 1}, ["ssh_key"]),
                ({"password_bootstrap_supported": None}, ["ssh_key"])):
            with self.subTest(capability_present="password_bootstrap_supported" in region_capabilities), \
                    mock.patch("console.views.app_config.app_domain.vms.get_vm_capabilities",
                               return_value=region_capabilities), \
                    mock.patch("console.views.app_config.app_domain.volume_service.get_vm_persistent_storage_options",
                               return_value=[]):
                response = view.get(None)
            bean = response.data["data"]["bean"]
            self.assertTrue(
                bean.get("password_bootstrap_supported") is region_capabilities.get("password_bootstrap_supported"),
                "Console capability response did not preserve Region gate",
            )
            self.assertTrue(bean.get("login_methods") == expected_methods,
                            "Console advertised an unsupported VM login method")
            self.assertFalse("login_methods" in region_capabilities, "Console mutated the Region capability bean")

    def test_region_capability_is_required_before_asset_or_vm_component_creation(self):
        password = self._runtime_password()
        payload = self._base_password_request(password)
        fake_asset = SimpleNamespace(
            ID=99,
            image_url="tenant:ubuntu-example",
            boot_mode="uefi",
            source_uri=UBUNTU_NOBLE_QCOW2_URL,
            os_name="Ubuntu 24.04",
            save=mock.Mock(),
        )

        with isolated_default_logger() as logs:
            with mock.patch("console.views.app_create.vm_run.vms.get_vm_capabilities", return_value={}) as capabilities, \
                    mock.patch("console.views.app_create.vm_run.vms.ensure_vm_platform_running") as ensure_platform, \
                    mock.patch("console.views.app_create.vm_run.vms.create_vm_image_asset",
                               return_value=fake_asset) as create_asset, \
                    mock.patch("console.views.app_create.vm_run.vms.resolve_vm_boot_mode", return_value="uefi"), \
                    mock.patch("console.views.app_create.vm_run.app_service.is_k8s_component_name_duplicate",
                               return_value=False), \
                    mock.patch("console.views.app_create.vm_run.app_service.create_vm_run_app",
                               return_value=(503, "component creation blocked", None)) as create_component, \
                    mock.patch(
                        "console.views.app_create.vm_run.enterprise_first_deploy_service.safe_begin_deploy_tracking"
                    ) as tracker, \
                    mock.patch("console.views.app_create.vm_run.enterprise_first_deploy_service.safe_mark_failure"):
                response = self._post_vm_run(payload)

        capabilities.assert_called_once_with("vm-login-region", "vm-login-team")
        ensure_platform.assert_not_called()
        create_asset.assert_not_called()
        create_component.assert_not_called()
        tracker.assert_not_called()
        self.assertTrue(response.status_code == 409, "missing capability was not rejected before creation")
        self.assertFalse(password in json.dumps(response.data), "response included plaintext")
        self.assertFalse(password in logs.getvalue(), "logs included plaintext")

    def test_noncanonical_password_image_is_rejected_before_asset_or_vm_component_creation(self):
        password = self._runtime_password()
        payload = self._base_password_request(password)
        payload["vm_url"] = UBUNTU_NOBLE_QCOW2_URL + "?download=1"
        fake_asset = SimpleNamespace(
            ID=100,
            image_url="tenant:ubuntu-example",
            boot_mode="uefi",
            source_uri=payload["vm_url"],
            os_name="Ubuntu 24.04",
            save=mock.Mock(),
        )

        with isolated_default_logger() as logs:
            with mock.patch("console.views.app_create.vm_run.vms.get_vm_capabilities",
                            return_value={"password_bootstrap_supported": True}) as capabilities, \
                    mock.patch("console.views.app_create.vm_run.vms.ensure_vm_platform_running") as ensure_platform, \
                    mock.patch("console.views.app_create.vm_run.vms.create_vm_image_asset",
                               return_value=fake_asset) as create_asset, \
                    mock.patch("console.views.app_create.vm_run.vms.resolve_vm_boot_mode", return_value="uefi"), \
                    mock.patch("console.views.app_create.vm_run.app_service.is_k8s_component_name_duplicate",
                               return_value=False), \
                    mock.patch("console.views.app_create.vm_run.app_service.create_vm_run_app",
                               return_value=(503, "component creation blocked", None)) as create_component, \
                    mock.patch(
                        "console.views.app_create.vm_run.enterprise_first_deploy_service.safe_begin_deploy_tracking"
                    ) as tracker, \
                    mock.patch("console.views.app_create.vm_run.enterprise_first_deploy_service.safe_mark_failure"):
                response = self._post_vm_run(payload)

        capabilities.assert_called_once_with("vm-login-region", "vm-login-team")
        ensure_platform.assert_not_called()
        create_asset.assert_not_called()
        create_component.assert_not_called()
        tracker.assert_not_called()
        self.assertTrue(response.status_code == 400, "noncanonical password image was not rejected")
        self.assertFalse(password in json.dumps(response.data), "response included plaintext")
        self.assertFalse(password in logs.getvalue(), "logs included plaintext")

    def test_password_create_stores_hash_only_and_registers_inner_port(self):
        self._assert_password_create_stores_hash_and_registers_inner_port()

    # capability_id: console.vm-create.port-operator
    def test_missing_display_name_keeps_ssh_port_operator_a_string(self):
        self.vm_view.user.nick_name = None
        self._assert_password_create_stores_hash_and_registers_inner_port()

    def _assert_password_create_stores_hash_and_registers_inner_port(self):
        password = self._runtime_password()
        payload = self._base_password_request(password)
        service = SimpleNamespace(
            service_id="service-created-password",
            service_alias="service-created-password",
            service_source="vm_run",
            create_status="creating",
            to_dict=lambda: {"service_id": "service-created-password"},
        )
        fake_asset = SimpleNamespace(
            ID=101,
            image_url="vm-login-namespace:ubuntu-example",
            boot_mode="uefi",
            source_uri=UBUNTU_NOBLE_QCOW2_URL,
            os_name="Ubuntu 24.04",
            save=mock.Mock(),
        )
        add_port_calls = []

        def record_port(*args, **kwargs):
            add_port_calls.append((args, kwargs))
            return 200, "success", object()

        with isolated_default_logger() as logs:
            with mock.patch("console.views.app_create.vm_run.vms.get_vm_capabilities",
                            return_value={"password_bootstrap_supported": True}), \
                    mock.patch("console.views.app_create.vm_run.vms.ensure_vm_platform_running"), \
                    mock.patch("console.views.app_create.vm_run.vms.create_vm_image_asset",
                               return_value=fake_asset), \
                    mock.patch("console.views.app_create.vm_run.vms.resolve_vm_boot_mode", return_value="uefi"), \
                    mock.patch("console.views.app_create.vm_run.vms.build_initial_vm_disk_layout", return_value=[]), \
                    mock.patch("console.views.app_create.vm_run.vms.build_vm_create_disk_imports", return_value=[]), \
                    mock.patch("console.views.app_create.vm_run.app_service.is_k8s_component_name_duplicate",
                               return_value=False), \
                    mock.patch("console.views.app_create.vm_run.app_service.create_vm_run_app",
                               return_value=(200, "success", service)), \
                    mock.patch("console.views.app_create.vm_run.vms.save_vm_runtime_config") as save_runtime, \
                    mock.patch("console.views.app_create.vm_run.group_service.add_service_to_group",
                               return_value=(200, "success")), \
                    mock.patch("console.views.app_create.vm_run.port_service.add_service_port",
                               side_effect=record_port), \
                    mock.patch("console.views.app_create.vm_run.enterprise_first_deploy_service.safe_begin_deploy_tracking",
                               return_value=None), \
                    mock.patch("console.views.app_create.vm_run.enterprise_first_deploy_service.safe_bind_events"):
                response = self._post_vm_run(payload)

        self.assertTrue(response.status_code == 200, "password VM create failed")
        runtime_config = save_runtime.call_args[0][2]
        self.assertTrue(runtime_config["login_password_hash"].startswith("$6$rounds=500000$"),
                        "password create did not provide a SHA512-crypt value")
        self.assertTrue(runtime_config["ssh_username"] == "ubuntu", "password create omitted the guest username")
        self.assertFalse("login_password" in runtime_config, "runtime config included plaintext field")
        self.assertFalse(password in json.dumps(runtime_config), "runtime config included plaintext")
        self.assertFalse(password in json.dumps(response.data), "response included plaintext")
        self.assertFalse(password in logs.getvalue(), "logs included plaintext")
        self.assertTrue(len(add_port_calls) == 1, "password create did not register SSH port")
        port_args, port_kwargs = add_port_calls[0]
        self.assertTrue(port_args[2] == 22, "SSH port number mismatch")
        self.assertTrue(port_kwargs["protocol"] == "tcp", "SSH port protocol mismatch")
        self.assertTrue(port_kwargs["is_inner_service"], "SSH port is not internal")
        self.assertFalse(port_kwargs["is_outer_service"], "SSH port was exposed externally")
        self.assertEqual(port_kwargs["user_name"], self.vm_view.user.nick_name or "")

    def test_password_create_rolls_back_component_attrs_group_and_port_on_registration_failure(self):
        password = self._runtime_password()
        payload = self._base_password_request(password)
        service_id = "service-password-port-rollback"
        service_name = "ubuntu-port-rollback"
        fake_asset = SimpleNamespace(
            ID=102,
            image_url="vm-login-namespace:ubuntu-example",
            boot_mode="uefi",
            source_uri=UBUNTU_NOBLE_QCOW2_URL,
            os_name="Ubuntu 24.04",
            save=mock.Mock(),
        )

        def create_local_component(*args):
            service = TenantServiceInfo.objects.create(
                service_id=service_id,
                tenant_id="tenant-vm-login",
                service_key=service_id,
                service_alias="gr-password-rollback",
                service_cname=service_name,
                service_region="vm-login-region",
                category="application",
                version="v1",
                image="vm-login-namespace:ubuntu-example",
                extend_method="vm",
                create_status="creating",
                service_source="vm_run",
                code_from="image_manual",
                namespace="default",
                service_type="application",
                k8s_component_name=service_name,
            )
            return 200, "success", service

        def add_local_group_relation(tenant, region_name, group_id, target_service_id):
            ServiceGroupRelation.objects.create(
                service_id=target_service_id,
                group_id=group_id,
                tenant_id=tenant.tenant_id,
                region_name=region_name,
            )
            return 200, "success"

        def write_port_then_fail(tenant, service, port, **kwargs):
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

        with mock.patch("console.views.app_create.vm_run.vms.get_vm_capabilities",
                        return_value={"password_bootstrap_supported": True}), \
                mock.patch("console.views.app_create.vm_run.vms.ensure_vm_platform_running"), \
                mock.patch("console.views.app_create.vm_run.vms.create_vm_image_asset", return_value=fake_asset), \
                mock.patch("console.views.app_create.vm_run.vms.resolve_vm_boot_mode", return_value="uefi"), \
                mock.patch("console.views.app_create.vm_run.vms.build_initial_vm_disk_layout", return_value=[]), \
                mock.patch("console.views.app_create.vm_run.vms.build_vm_create_disk_imports", return_value=[]), \
                mock.patch("console.views.app_create.vm_run.app_service.is_k8s_component_name_duplicate",
                           return_value=False), \
                mock.patch("console.views.app_create.vm_run.app_service.create_vm_run_app",
                           side_effect=create_local_component), \
                mock.patch("console.views.app_create.vm_run.group_service.add_service_to_group",
                           side_effect=add_local_group_relation), \
                mock.patch("console.views.app_create.vm_run.port_service.add_service_port",
                           side_effect=write_port_then_fail), \
                mock.patch("console.views.app_create.vm_run.enterprise_first_deploy_service.safe_begin_deploy_tracking",
                           return_value=None), \
                mock.patch("console.views.app_create.vm_run.enterprise_first_deploy_service.safe_mark_failure"):
            response = self._post_vm_run(payload)

        self.assertTrue(response.status_code == 500, "failed port registration was not returned")
        self.assertFalse(TenantServiceInfo.objects.filter(service_id=service_id).exists(),
                         "component row survived port rollback")
        self.assertFalse(ComponentK8sAttributes.objects.filter(component_id=service_id).exists(),
                         "runtime attribute survived port rollback")
        self.assertFalse(ServiceGroupRelation.objects.filter(service_id=service_id).exists(),
                         "group relation survived port rollback")
        self.assertFalse(TenantServiceEnvVar.objects.filter(service_id=service_id).exists(),
                         "port environment row survived port rollback")
        self.assertFalse(TenantServicesPort.objects.filter(service_id=service_id).exists(),
                         "port row survived port rollback")

    def test_save_runtime_config_persists_hash_but_public_profile_excludes_it(self):
        password, password_hash = runtime_generated_password_hash()
        vms.save_vm_runtime_config(
            "tenant-vm-login",
            "service-vm-password",
            {
                "os_name": "Ubuntu 24.04",
                "ssh_username": "ubuntu",
                "login_password_hash": password_hash,
            },
        )

        stored = ComponentK8sAttributes.objects.filter(
            component_id="service-vm-password",
            name="vm_login_password_hash",
        ).first()
        self.assertTrue(stored is not None, "managed login hash was not persisted")
        self.assertTrue(stored.attribute_value == password_hash, "stored hash differs from bootstrap hash")
        profile = vms.get_vm_runtime_config("service-vm-password")
        self.assertFalse("vm_login_password_hash" in profile, "runtime profile exposed managed login hash")
        self.assertFalse(password in json.dumps(profile), "runtime profile included plaintext")

    def test_initial_region_service_payload_contains_hash_and_internal_tcp22(self):
        password, password_hash = runtime_generated_password_hash()
        service = TenantServiceInfo.objects.create(
            service_id="service-region-vm-password",
            tenant_id="tenant-vm-login",
            service_key="service-region-vm-password",
            service_alias="service-region-vm-password",
            service_cname="ubuntu-password-vm",
            service_region="vm-login-region",
            category="application",
            version="v1",
            image="vm-login-namespace:ubuntu-password-vm",
            extend_method="vm",
            min_cpu=1000,
            min_memory=1024,
            min_node=1,
            create_status="creating",
            service_source="vm_run",
            code_from="image_manual",
            namespace="default",
            service_type="application",
            k8s_component_name="ubuntu-password-vm",
        )
        vms.save_vm_runtime_config(
            "tenant-vm-login",
            service.service_id,
            {
                "os_name": "Ubuntu 24.04",
                "ssh_username": "ubuntu",
                "login_password_hash": password_hash,
                "boot_mode": "uefi",
                "boot_source_format": "qcow2",
            },
        )
        TenantServicesPort.objects.create(
            tenant_id="tenant-vm-login",
            service_id=service.service_id,
            container_port=22,
            mapping_port=22,
            protocol="tcp",
            port_alias="SERVICE_REGION_SSH22",
            is_inner_service=True,
            is_outer_service=False,
            k8s_service_name=service.service_alias,
        )
        TenantServiceEnvVar.objects.create(
            tenant_id="tenant-vm-login",
            service_id=service.service_id,
            container_port=22,
            name="连接地址",
            attr_name="SERVICE_REGION_SSH22_HOST",
            attr_value=service.service_alias,
            is_change=False,
            scope="outer",
        )

        tenant = SimpleNamespace(
            tenant_id="tenant-vm-login",
            tenant_name="vm-login-team",
            enterprise_id="vm-login-enterprise",
        )
        with mock.patch("console.services.app.service_group_relation_repo.get_group_id_by_service", return_value=7), \
                mock.patch("console.services.app.region_app_repo.get_region_app_id", return_value="region-app-vm-login"), \
                mock.patch("console.services.app.region_api.create_service") as create_service, \
                mock.patch("console.services.app.region_api.create_component_k8s_attribute", create=True), \
                mock.patch("console.services.app.arch_service.update_affinity_by_arch"):
            app_service.create_region_service(tenant, service, "vm-login-test-user")

        payload = create_service.call_args[0][2]
        attrs = {item["name"]: item["attribute_value"] for item in payload["component_k8s_attributes"]}
        self.assertTrue(attrs.get("vm_login_password_hash") == password_hash, "Region attrs omitted login hash")
        self.assertTrue(attrs.get("vm_ssh_username") == "ubuntu", "Region attrs omitted bootstrap username")
        self.assertFalse('"login_password":' in json.dumps(payload), "Region payload included plaintext field")
        self.assertFalse(password in json.dumps(payload), "Region payload included plaintext")
        port = next(item for item in payload["ports_info"] if item["container_port"] == 22)
        self.assertTrue(port["protocol"] == "tcp", "SSH port protocol mismatch")
        self.assertTrue(port["is_inner_service"], "SSH port is not internal")
        self.assertFalse(port["is_outer_service"], "SSH port was exposed externally")

    def test_share_export_and_template_import_remove_password_pair_but_keep_ssh_pair(self):
        _, password_hash = runtime_generated_password_hash()
        legacy_password = self._runtime_password()
        public_key = synthetic_public_key()
        rows = (
            ("password-vm", "vm_login_password_hash", password_hash),
            ("password-vm", "login_password", legacy_password),
            ("password-vm", "vm_login_password", legacy_password),
            ("password-vm", "vm_ssh_username", "ubuntu"),
            ("key-vm", "vm_ssh_username", "ubuntu"),
            ("key-vm", "vm_ssh_authorized_key", public_key),
        )
        for component_id, name, value in rows:
            ComponentK8sAttributes.objects.create(
                tenant_id="tenant-vm-login",
                component_id=component_id,
                name=name,
                save_type="string",
                attribute_value=value,
            )

        exported = share_service.list_component_k8s_attributes(["password-vm", "key-vm"])
        password_rows = exported.get("password-vm", [])
        key_rows = exported.get("key-vm", [])
        self.assertFalse(any(item["name"] == "vm_login_password_hash" for item in password_rows),
                         "share export retained password hash")
        self.assertFalse(any(item["name"] == "vm_ssh_username" for item in password_rows),
                         "share export left password-only username")
        self.assertTrue(any(item["name"] == "vm_ssh_username" for item in key_rows),
                        "share export removed SSH username")
        self.assertTrue(any(item["name"] == "vm_ssh_authorized_key" for item in key_rows),
                        "share export removed SSH key")
        self.assertFalse(password_hash in json.dumps(exported), "share export leaked hash value")
        self.assertFalse(legacy_password in json.dumps(exported), "share export leaked raw credential value")

        importer = NewComponents.__new__(NewComponents)
        component = SimpleNamespace(tenant_id="tenant-vm-login", service_id="imported-password-vm")
        password_template_rows = [
            {"name": "vm_login_password_hash", "save_type": "string", "attribute_value": password_hash},
            {"name": "login_password", "save_type": "string", "attribute_value": legacy_password},
            {"name": "vm_login_password", "save_type": "string", "attribute_value": legacy_password},
            {"name": "vm_ssh_username", "save_type": "string", "attribute_value": "ubuntu"},
        ]
        imported = importer._template_to_k8s_attributes(
            component, password_template_rows, {"extend_method": "vm"})
        imported_names = {item.name for item in imported}
        self.assertFalse("vm_login_password_hash" in imported_names, "template import retained hash")
        self.assertFalse("vm_ssh_username" in imported_names, "template import left password-only username")

        key_template_rows = [
            {"name": "vm_ssh_username", "save_type": "string", "attribute_value": "ubuntu"},
            {"name": "vm_ssh_authorized_key", "save_type": "string", "attribute_value": public_key},
        ]
        imported_key = importer._template_to_k8s_attributes(
            component, key_template_rows, {"extend_method": "vm"})
        imported_key_names = {item.name for item in imported_key}
        self.assertTrue("vm_ssh_username" in imported_key_names, "template import removed SSH username")
        self.assertTrue("vm_ssh_authorized_key" in imported_key_names, "template import removed SSH key")

    def test_market_component_export_removes_password_hash_and_paired_username(self):
        _, password_hash = runtime_generated_password_hash()
        component = SimpleNamespace(
            component_id="market-password-vm",
            service_id="market-password-vm",
            service_name="market-password-vm",
            service_alias="market-password-vm",
            min_cpu=1000,
            min_memory=1024,
            min_node=1,
            to_dict=lambda: {
                "service_id": "market-password-vm",
                "service_name": "market-password-vm",
                "service_alias": "market-password-vm",
            },
        )
        component_template = SimpleNamespace(
            component=component,
            probes=[],
            envs=[],
            ports=[],
            config_files=[],
            monitors=[],
            http_rules=[],
            http_rule_configs=[],
            k8s_attributes=[
                SimpleNamespace(component_id="market-password-vm", name="vm_login_password_hash",
                                attribute_value=password_hash),
                SimpleNamespace(component_id="market-password-vm", name="vm_ssh_username",
                                attribute_value="ubuntu"),
            ],
            volumes=[],
            labels=[],
            volume_deps=[],
            component_deps=[],
            app_config_groups=[],
        )
        market_app = MarketApp.__new__(MarketApp)
        market_app.labels = {}
        with mock.patch("console.services.market_app.market_app.domain_repo.list_all_certificate", return_value=[]), \
                mock.patch.object(market_app, "_create_plugin_body", return_value={}), \
                mock.patch.object(market_app, "_create_http_rules", return_value=[]):
            components = market_app._create_component_body(SimpleNamespace(components=lambda: [component_template]))

        exported_attributes = components[0]["component_k8s_attributes"]
        exported_names = {attribute["name"] for attribute in exported_attributes}
        self.assertFalse("vm_login_password_hash" in exported_names, "market export retained password hash")
        self.assertFalse("vm_ssh_username" in exported_names, "market export left password-only username")
        self.assertFalse(password_hash in json.dumps(components), "market export leaked hash value")

    def test_component_template_update_removes_password_hash_and_paired_username_together(self):
        _, password_hash = runtime_generated_password_hash()
        component = Component.__new__(Component)
        component.component = SimpleNamespace(tenant_id="tenant-vm-login", component_id="updated-vm")
        component.k8s_attributes = []
        component.action_type = 0
        component._update_component_k8s_attributes({
            "add": [{
                "name": "vm_login_password_hash",
                "save_type": "string",
                "attribute_value": password_hash,
            }],
            "upd": [{
                "name": "vm_ssh_username",
                "save_type": "string",
                "attribute_value": "ubuntu",
            }],
        })
        updated_names = {item.name for item in component.k8s_attributes}
        self.assertFalse("vm_login_password_hash" in updated_names, "template update retained password hash")
        self.assertFalse("vm_ssh_username" in updated_names, "template update left password-only username")

    def test_private_group_backup_keeps_hash_for_vm_restore(self):
        _, password_hash = runtime_generated_password_hash()
        attribute = ComponentK8sAttributes(
            tenant_id="tenant-vm-login",
            component_id="service-private-backup",
            name="vm_login_password_hash",
            save_type="string",
            attribute_value=password_hash,
        )
        service = SimpleNamespace(
            service_id="service-private-backup",
            component_id="service-private-backup",
            service_source="vm_run",
            to_dict=lambda: {"service_id": "service-private-backup"},
        )
        empty_queries = (
            "service_label_repo.get_service_labels",
            "domain_repo.get_service_domains",
            "configuration_repo.list_by_rule_ids",
            "tcp_domain.get_service_tcpdomains",
            "probe_repo.get_service_probe",
            "auth_repo.get_service_auth",
            "env_var_repo.get_service_env",
            "mnt_repo.get_service_mnts",
            "volume_repo.get_service_volumes_with_config_file",
            "volume_repo.get_service_config_files",
            "port_repo.get_service_ports",
            "dep_relation_repo.get_service_dependencies",
            "service_monitor_repo.get_component_service_monitors",
            "component_graph_repo.list",
            "app_plugin_relation_repo.get_service_plugin_relation_by_service_id",
            "service_plugin_config_repo.get_service_plugin_all_config",
            "service_endpoints_repo.get_service_endpoints_by_service_id",
        )
        with ExitStack() as stack:
            for query in empty_queries:
                stack.enter_context(mock.patch("console.services.backup_service." + query, return_value=[]))
            stack.enter_context(mock.patch(
                "console.services.backup_service.service_source_repo.get_service_source", return_value=None))
            stack.enter_context(mock.patch(
                "console.services.backup_service.compile_env_repo.get_service_compile_env", return_value=None))
            stack.enter_context(mock.patch(
                "console.services.backup_service.extend_repo.get_extend_method_by_service", return_value=None))
            stack.enter_context(mock.patch(
                "console.services.backup_service.k8s_attribute_repo.get_by_component_id",
                return_value=[attribute]))
            backup_service_data, _ = groupapp_backup_service.get_service_details(
                SimpleNamespace(tenant_id="tenant-vm-login"), service)

        backup_attributes = backup_service_data["component_k8s_attributes"]
        self.assertTrue(
            any(item.get("name") == "vm_login_password_hash" and
                item.get("attribute_value") == password_hash for item in backup_attributes),
            "private backup omitted VM login hash needed for restore",
        )

    def test_generic_attribute_get_hides_managed_hash(self):
        credentials = (
            ("vm_login_password_hash", runtime_generated_password_hash()[1]),
            ("login_password", self._runtime_password()),
            ("vm_login_password", self._runtime_password()),
        )
        for name, value in credentials:
            ComponentK8sAttributes.objects.create(
                tenant_id="tenant-vm-login",
                component_id="service-generic-attrs",
                name=name,
                save_type="string",
                attribute_value=value,
            )
        listed = k8s_attribute_service.list_by_component_ids(["service-generic-attrs"])
        for name, _ in credentials:
            single = k8s_attribute_service.get_by_component_ids_and_name("service-generic-attrs", name)
            self.assertTrue(len(single) == 0, "single-attribute endpoint exposed managed credentials")
        self.assertFalse(any(item["name"] in {name for name, _ in credentials} for item in listed),
                         "attribute list endpoint exposed managed credentials")

        single_view = ComponentK8sAttributeView()
        single_view.service = SimpleNamespace(service_id="service-generic-attrs")
        list_view = ComponentK8sAttributeListView()
        list_view.service = SimpleNamespace(service_id="service-generic-attrs")
        list_response = list_view.get(None)
        for name, _ in credentials:
            single_response = single_view.get(None, name)
            self.assertTrue(len(single_response.data["data"]["list"]) == 0,
                            "single GET response exposed managed credentials")
        self.assertFalse(any(item["name"] in {name for name, _ in credentials}
                             for item in list_response.data["data"]["list"]),
                         "list GET response exposed managed credentials")

    def test_generic_attribute_create_and_update_reject_server_managed_hash(self):
        _, password_hash = runtime_generated_password_hash()
        tenant = SimpleNamespace(tenant_id="tenant-vm-login", tenant_name="vm-login-team")
        credentials = (
            ("vm_login_password_hash", password_hash),
            ("login_password", self._runtime_password()),
            ("vm_login_password", self._runtime_password()),
        )
        for index, (name, credential_value) in enumerate(credentials):
            service_id = "service-managed-attrs-{0}".format(index)
            component = SimpleNamespace(service_id=service_id, service_alias=service_id)
            payload = {"name": name, "save_type": "string", "attribute_value": credential_value}
            with self.subTest(field=name), \
                    mock.patch("console.services.k8s_attribute.region_api.create_component_k8s_attribute"), \
                    self.assertRaises(ServiceHandleException):
                k8s_attribute_service.create_k8s_attribute(
                    tenant, component, "vm-login-region", dict(payload), "vm-login-test-user")

            ComponentK8sAttributes.objects.create(
                tenant_id=tenant.tenant_id,
                component_id=service_id,
                name=name,
                save_type="string",
                attribute_value=credential_value,
            )
            with self.subTest(field=name), \
                    mock.patch("console.services.k8s_attribute.region_api.update_component_k8s_attribute"), \
                    self.assertRaises(ServiceHandleException):
                k8s_attribute_service.update_k8s_attribute(
                    tenant, component, "vm-login-region", dict(payload))

    def test_compose_attribute_writer_rejects_reserved_credentials_before_logging(self):
        _, password_hash = runtime_generated_password_hash()
        tenant = SimpleNamespace(tenant_id="tenant-vm-login", tenant_name="vm-login-team")
        service = SimpleNamespace(service_id="service-compose-attrs")
        service_check = AppCheckService()
        with isolated_default_logger() as logs:
            for name, value in (
                    ("vm_login_password_hash", password_hash),
                    ("login_password", self._runtime_password()),
                    ("vm_login_password", self._runtime_password())):
                with self.subTest(field=name), \
                        mock.patch("console.services.app_check_service.k8s_attribute_repo.create") as create_attribute, \
                        self.assertRaises(ServiceHandleException) as raised:
                    service_check._AppCheckService__save_k8s_attribute(
                        tenant, service, name, value, save_type="string")

                self.assertTrue(raised.exception.status_code == 403, "reserved credential guard status mismatch")
                create_attribute.assert_not_called()

        self.assertFalse(password_hash in logs.getvalue(), "compose attribute logger emitted hash")
        self.assertFalse(any(name in logs.getvalue() for name in ("login_password", "vm_login_password")),
                         "compose attribute logger emitted a credential field")

    def test_compose_attribute_writer_stores_public_key_but_redacts_its_value_from_debug_log(self):
        public_key = synthetic_public_key()
        tenant = SimpleNamespace(tenant_id="tenant-vm-login", tenant_name="vm-login-team")
        service = SimpleNamespace(service_id="service-compose-key")
        service_check = AppCheckService()
        existing = mock.Mock()
        existing.exists.return_value = False
        with isolated_default_logger() as logs:
            with mock.patch("console.services.app_check_service.k8s_attribute_repo.get_by_component_id_name",
                            return_value=existing), \
                    mock.patch("console.services.app_check_service.k8s_attribute_repo.create") as create_attribute:
                service_check._AppCheckService__save_k8s_attribute(
                    tenant, service, "vm_ssh_authorized_key", public_key, save_type="string")

        self.assertTrue(create_attribute.call_args.kwargs["attribute_value"] == public_key,
                        "Compose public key storage changed")
        self.assertFalse(public_key in logs.getvalue(), "Compose debug log emitted public key")

    def test_region_attribute_fallback_masks_login_values_from_debug_log(self):
        password, password_hash = runtime_generated_password_hash()
        public_key = synthetic_public_key()
        for name, value in (
                ("vm_login_password_hash", password_hash),
                ("vm_ssh_authorized_key", public_key)):
            ComponentK8sAttributes.objects.create(
                tenant_id="tenant-vm-login",
                component_id="service-region-log-mask",
                name=name,
                save_type="string",
                attribute_value=value,
            )
        service = SimpleNamespace(
            service_id="service-region-log-mask",
            service_alias="region-log-mask-vm",
            service_region="vm-login-region",
        )
        tenant = SimpleNamespace(tenant_name="vm-login-team")
        with isolated_default_logger() as logs:
            with mock.patch("console.services.app.region_api.create_component_k8s_attribute"):
                app_service._AppService__sync_k8s_attributes_to_region(tenant, service)

        self.assertFalse(password in logs.getvalue(), "Region fallback log emitted plaintext")
        self.assertFalse(password_hash in logs.getvalue(), "Region fallback log emitted login hash")
        self.assertFalse(public_key in logs.getvalue(), "Region fallback log emitted public key")

    def test_generic_attribute_write_responses_do_not_echo_hash(self):
        _, password_hash = runtime_generated_password_hash()
        tenant = SimpleNamespace(tenant_id="tenant-vm-login", tenant_name="vm-login-team")
        service = SimpleNamespace(service_id="service-generic-write", service_alias="service-generic-write")
        user = SimpleNamespace(nick_name="vm-login-test-user")
        request_data = {
            "attribute": {
                "name": "vm_login_password_hash",
                "save_type": "string",
                "attribute_value": password_hash,
            },
        }

        post_view = ComponentK8sAttributeListView()
        post_view.tenant = tenant
        post_view.service = service
        post_view.region_name = "vm-login-region"
        post_view.user = user
        post_request = post_view.initialize_request(
            self.factory.post("/console/component/attributes", request_data, format="json"))
        with mock.patch.object(k8s_attribute_service, "create_k8s_attribute"):
            post_response = post_view.post(post_request)
        post_json = json.dumps(post_response.data)
        self.assertFalse(password_hash in post_json, "generic POST response echoed managed hash")

        put_view = ComponentK8sAttributeView()
        put_view.tenant = tenant
        put_view.service = service
        put_view.region_name = "vm-login-region"
        put_view.user = user
        put_request = put_view.initialize_request(
            self.factory.put("/console/component/attributes/vm_login_password_hash", request_data,
                             format="json"))
        with mock.patch.object(k8s_attribute_service, "update_k8s_attribute"):
            put_response = put_view.put(put_request, "vm_login_password_hash")
        put_json = json.dumps(put_response.data)
        self.assertFalse(password_hash in put_json, "generic PUT response echoed managed hash")
