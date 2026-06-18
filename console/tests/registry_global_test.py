# -*- coding: utf-8 -*-
import collections
import os
import sys
from types import ModuleType, SimpleNamespace
from unittest import TestCase, mock

from rest_framework.test import APIRequestFactory

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from console.exception.main import ServiceHandleException  # noqa: E402
from console.services.team_services import team_services  # noqa: E402
from console.views.app_create.docker_run import DockerRunCreateView  # noqa: E402
from console.views import registry as registry_views  # noqa: E402
from console.views.registry import HubRegistryImageView, HubRegistryView  # noqa: E402


class RegistryAuth(SimpleNamespace):
    def to_dict(self):
        return dict(self.__dict__)


class _ExistsQuery(object):
    def __init__(self, exists=False):
        self._exists = exists

    def exists(self):
        return self._exists


class GlobalRegistryAuthTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = SimpleNamespace(user_id=7, enterprise_id="eid-1", is_authenticated=True)

    def test_hub_registry_list_merges_user_and_enterprise_auths_without_enterprise_password(self):
        personal = RegistryAuth(
            secret_id="personal",
            domain="https://harbor.example.com",
            username="alice",
            password="personal-password",
            hub_type="Harbor",
            user_id=7,
            enterprise_id="",
            scope="user",
        )
        enterprise = RegistryAuth(
            secret_id="company",
            domain="https://registry.cn-hangzhou.aliyuncs.com",
            username="company-user",
            password="enterprise-password",
            hub_type="Aliyun",
            user_id=0,
            enterprise_id="eid-1",
            scope="enterprise",
        )
        request = self.factory.get("/console/hub/registry")
        view = HubRegistryView()
        view.user = self.user

        with mock.patch.object(team_services, "list_accessible_registry_auths", return_value=[personal, enterprise]):
            response = view.get(request)

        self.assertEqual(response.status_code, 200)
        items = response.data["data"]["list"]
        self.assertEqual([item["secret_id"] for item in items], ["personal", "company"])
        self.assertEqual(items[0]["password"], "personal-password")
        self.assertEqual(items[0]["scope"], "user")
        self.assertEqual(items[1]["scope"], "enterprise")
        self.assertEqual(items[1]["hub_type"], "AliyunACR")
        self.assertNotIn("password", items[1])

    def test_serialize_registry_auth_keeps_legacy_cloud_type_compatible_without_access_key_fields(self):
        auth = RegistryAuth(
            secret_id="company",
            domain="https://registry.cn-hangzhou.aliyuncs.com",
            username="company-user",
            password="enterprise-password",
            hub_type="Aliyun",
            user_id=0,
            enterprise_id="eid-1",
            scope="enterprise",
        )

        data = team_services.serialize_registry_auth(auth, include_password=True)

        self.assertEqual(data["hub_type"], "AliyunACR")
        self.assertNotIn("access_key", data)
        self.assertNotIn("access_secret", data)

    def test_enterprise_registry_list_masks_password_for_admins(self):
        enterprise = RegistryAuth(
            secret_id="company",
            domain="https://registry.cn-hangzhou.aliyuncs.com",
            username="company-user",
            password="enterprise-password",
            hub_type="Aliyun",
            user_id=0,
            enterprise_id="eid-1",
            scope="enterprise",
        )
        request = self.factory.get("/console/enterprise/eid-1/hub/registry")
        self.assertTrue(hasattr(registry_views, "EnterpriseHubRegistryView"))
        view = registry_views.EnterpriseHubRegistryView()
        view.user = self.user
        view.is_enterprise_admin = True

        with mock.patch("console.views.registry.team_registry_auth_repo.list_enterprise_registry_auths",
                        return_value=[enterprise]):
            response = view.get(request, enterprise_id="eid-1")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["list"][0]["scope"], "enterprise")
        self.assertNotIn("password", response.data["data"]["list"][0])

    def test_enterprise_registry_create_uses_username_password_for_cloud_registry(self):
        request = SimpleNamespace(data={
            "secret_id": "company",
            "domain": "https://registry.cn-hangzhou.aliyuncs.com",
            "username": "registry-user",
            "password": "registry-password",
            "hub_type": "AliyunACR",
        })
        view = registry_views.EnterpriseHubRegistryView()
        view.user = self.user
        view.is_enterprise_admin = True

        with mock.patch("console.views.registry.team_registry_auth_repo.check_exist_enterprise_registry_auth",
                        return_value=_ExistsQuery(False)), \
                mock.patch.object(team_services, "check_registry_connection") as check_mock, \
                mock.patch("console.views.registry.team_registry_auth_repo.create_team_registry_auth") as create_mock:
            response = view.post(request, enterprise_id="eid-1")

        self.assertEqual(response.status_code, 200)
        check_mock.assert_called_once_with(
            "https://registry.cn-hangzhou.aliyuncs.com", "registry-user", "registry-password", "AliyunACR")
        params = create_mock.call_args[1]
        self.assertEqual(params["username"], "registry-user")
        self.assertEqual(params["password"], "registry-password")
        self.assertEqual(params["hub_type"], "AliyunACR")

    def test_user_registry_update_uses_username_password_for_cloud_registry(self):
        request = SimpleNamespace(
            GET={"secret_id": "personal"},
            data={
                "username": "registry-user",
                "password": "registry-password",
                "hub_type": "TencentTCR",
            },
        )
        auth = RegistryAuth(secret_id="personal", hub_type="TencentTCR")
        view = HubRegistryView()
        view.user = self.user

        with mock.patch("console.views.registry.team_registry_auth_repo.get_user_registry_auth", return_value=auth), \
                mock.patch("console.views.registry.team_registry_auth_repo.update_user_registry_auth") as update_mock:
            response = view.put(request)

        self.assertEqual(response.status_code, 200)
        update_mock.assert_called_once_with(
            "personal", self.user.user_id, username="registry-user", password="registry-password", hub_type="TencentTCR")

    def test_resolve_registry_auth_prefers_user_auth_then_enterprise_auth(self):
        personal = RegistryAuth(secret_id="same", username="alice", password="personal-password", scope="user")
        enterprise = RegistryAuth(secret_id="same", username="company", password="enterprise-password", scope="enterprise")
        user = SimpleNamespace(user_id=7, enterprise_id="eid-1")

        with mock.patch("console.services.team_services.team_registry_auth_repo.get_user_registry_auth",
                        return_value=personal), \
                mock.patch("console.services.team_services.team_registry_auth_repo.get_enterprise_registry_auth",
                           return_value=enterprise):
            resolved = team_services.resolve_registry_auth(user, "same")

        self.assertIs(resolved, personal)

    def test_resolve_registry_auth_falls_back_to_enterprise_auth(self):
        enterprise = RegistryAuth(secret_id="company", username="company", password="enterprise-password", scope="enterprise")
        user = SimpleNamespace(user_id=7, enterprise_id="eid-1")

        with mock.patch("console.services.team_services.team_registry_auth_repo.get_user_registry_auth",
                        return_value=None), \
                mock.patch("console.services.team_services.team_registry_auth_repo.get_enterprise_registry_auth",
                           return_value=enterprise):
            resolved = team_services.resolve_registry_auth(user, "company")

        self.assertIs(resolved, enterprise)

    def test_hub_registry_image_uses_accessible_registry_auth(self):
        auth = RegistryAuth(
            secret_id="company",
            domain="https://registry.cn-hangzhou.aliyuncs.com",
            username="company-user",
            password="enterprise-password",
            hub_type="Aliyun",
            scope="enterprise",
        )
        request = self.factory.get("/console/hub/registry/image?secret_id=company")
        view = HubRegistryImageView()
        view.user = self.user

        with mock.patch.object(team_services, "resolve_registry_auth", return_value=auth) as resolve_mock, \
                mock.patch.object(team_services, "get_registry_namespaces", return_value=["prod"]) as namespaces_mock:
            response = view.get(request)

        self.assertEqual(response.status_code, 200)
        resolve_mock.assert_called_once_with(self.user, "company")
        namespaces_mock.assert_called_once_with(
            domain=auth.domain,
            username=auth.username,
            password=auth.password,
            hub_type=auth.hub_type,
        )
        self.assertEqual(response.data["data"]["list"], ["prod"])

    def test_docker_run_resolves_registry_auth_id_credentials_on_server(self):
        registry_auth = RegistryAuth(secret_id="company", username="company-user", password="enterprise-password")
        service = SimpleNamespace(service_id="sid-1", to_dict=lambda: {"service_id": "sid-1"})
        request = SimpleNamespace(data={
            "image_type": "docker_run",
            "group_id": 1,
            "service_cname": "demo",
            "docker_cmd": "registry.example.com/ns/demo:latest",
            "registry_auth_id": "company",
        })
        view = DockerRunCreateView()
        view.user = SimpleNamespace(user_id=7, enterprise_id="eid-1", get_username=lambda: "alice")
        view.tenant = SimpleNamespace(tenant_id="tenant-1")
        view.response_region = "region-1"
        view.region_name = "region-1"

        with mock.patch.object(team_services, "resolve_registry_auth", return_value=registry_auth) as resolve_mock, \
                mock.patch("console.views.app_create.docker_run.app_service.is_k8s_component_name_duplicate",
                           return_value=False), \
                mock.patch("console.views.app_create.docker_run.app_service.create_docker_run_app",
                           return_value=(200, "ok", service)), \
                mock.patch("console.views.app_create.docker_run.app_service.create_service_source_info") as source_mock, \
                mock.patch("console.views.app_create.docker_run.group_service.add_service_to_group",
                           return_value=(200, "ok")):
            response = view.post(request)

        self.assertEqual(response.status_code, 200)
        resolve_mock.assert_called_once_with(view.user, "company")
        source_mock.assert_called_once_with(view.tenant, service, "company-user", "enterprise-password")


    def test_team_registry_create_region_payload_excludes_console_scope_fields(self):
        tenant = SimpleNamespace(tenant_id="tenant-1", tenant_name="team-a")

        with mock.patch("django.db.transaction.Atomic.__enter__", return_value=None), \
                mock.patch("django.db.transaction.Atomic.__exit__", return_value=False), \
                mock.patch("console.services.team_services.team_registry_auth_repo.get_by_team_id_domain",
                           return_value=[]), \
                mock.patch("console.services.team_services.team_registry_auth_repo.create_team_registry_auth"), \
                mock.patch("console.services.team_services.region_api.create_registry_auth") as region_mock:
            team_services.create_registry_auth(
                tenant, "region-a", "https://harbor.example.com", "user", "password")

        payload = region_mock.call_args[0][2]
        self.assertNotIn("scope", payload)
        self.assertNotIn("enterprise_id", payload)
        self.assertNotIn("user_id", payload)

    def test_team_registry_update_region_payload_excludes_console_scope_fields(self):
        tenant = SimpleNamespace(tenant_id="tenant-1", tenant_name="team-a")
        auth = RegistryAuth(
            tenant_id="tenant-1",
            secret_id="secret-a",
            domain="https://harbor.example.com",
            username="user",
            password="password",
            region_name="region-a",
            hub_type="Docker",
            user_id=7,
            scope="user",
            enterprise_id="eid-1",
        )

        with mock.patch("django.db.transaction.Atomic.__enter__", return_value=None), \
                mock.patch("django.db.transaction.Atomic.__exit__", return_value=False), \
                mock.patch("console.services.team_services.team_registry_auth_repo.get_by_secret_id",
                           return_value=[auth]), \
                mock.patch("console.services.team_services.team_registry_auth_repo.update_team_registry_auth"), \
                mock.patch("console.services.team_services.region_api.update_registry_auth") as region_mock:
            team_services.update_registry_auth(tenant, "region-a", "secret-a", {"username": "new-user"})

        payload = region_mock.call_args[0][2]
        self.assertNotIn("scope", payload)
        self.assertNotIn("enterprise_id", payload)
        self.assertNotIn("user_id", payload)

    def test_check_registry_connection_accepts_supported_cloud_registry_types(self):
        response = mock.Mock(status_code=200)

        for hub_type in ["AliyunACR", "TencentTCR", "HuaweiSWR", "VolcanoCR"]:
            with self.subTest(hub_type=hub_type):
                with mock.patch("console.services.team_services.requests.get", return_value=response) as get_mock:
                    team_services.check_registry_connection(
                        domain="https://registry.example.com",
                        username="user",
                        password="password",
                        hub_type=hub_type,
                    )

                self.assertEqual(get_mock.call_args[0][0], "https://registry.example.com/v2/")

    def test_check_registry_connection_accepts_legacy_cloud_registry_type_aliases(self):
        response = mock.Mock(status_code=200)

        for hub_type in ["Aliyun", "Tencent", "Huawei", "Volcano"]:
            with self.subTest(hub_type=hub_type):
                with mock.patch("console.services.team_services.requests.get", return_value=response) as get_mock:
                    team_services.check_registry_connection(
                        domain="https://registry.example.com",
                        username="user",
                        password="password",
                        hub_type=hub_type,
                    )

                self.assertEqual(get_mock.call_args[0][0], "https://registry.example.com/v2/")

    def test_check_registry_connection_rejects_volcano_tos_alias(self):
        with self.assertRaises(ServiceHandleException):
            team_services.check_registry_connection(
                domain="https://registry.example.com",
                username="user",
                password="password",
                hub_type="VolcanoTOS",
            )

    def test_check_registry_connection_handles_registry_v2_bearer_challenge(self):
        challenge = mock.Mock(
            status_code=401,
            headers={
                "WWW-Authenticate": (
                    'Bearer realm="https://auth.example.com/token",'
                    'service="registry.example.com"'
                )
            },
            text="",
        )
        token_response = mock.Mock(status_code=200)
        token_response.json.return_value = {"token": "registry-token"}
        ok_response = mock.Mock(status_code=200)

        with mock.patch("console.services.team_services.requests.get",
                        side_effect=[challenge, token_response, ok_response]) as get_mock:
            team_services.check_registry_connection(
                domain="https://registry.example.com",
                username="user",
                password="password",
                hub_type="VolcanoCR",
            )

        self.assertEqual(get_mock.call_args_list[0][0][0], "https://registry.example.com/v2/")
        self.assertEqual(get_mock.call_args_list[1][0][0], "https://auth.example.com/token")
        self.assertEqual(get_mock.call_args_list[2][1]["headers"], {"Authorization": "Bearer registry-token"})

    def test_check_registry_connection_error_includes_registry_response_body(self):
        response = mock.Mock(status_code=403, text='{"errors":[{"message":"denied"}]}')

        with mock.patch("console.services.team_services.requests.get", return_value=response):
            with self.assertRaises(ServiceHandleException) as ctx:
                team_services.check_registry_connection(
                    domain="https://registry.example.com",
                    username="user",
                    password="password",
                    hub_type="VolcanoCR",
                )

        self.assertIn("status:403", ctx.exception.msg)
        self.assertIn("denied", ctx.exception.msg)
        self.assertIn("403", ctx.exception.msg_show)

    def test_check_registry_connection_rejects_unsupported_registry_type(self):
        with self.assertRaises(ServiceHandleException):
            team_services.check_registry_connection(
                domain="https://registry.example.com",
                username="user",
                password="password",
                hub_type="Unknown",
            )
