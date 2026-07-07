# -*- coding: utf-8 -*-
import collections
import os
import sys
import typing
from types import ModuleType
from unittest import mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))
if not hasattr(typing, "NotRequired"):
    try:
        from typing_extensions import NotRequired
        typing.NotRequired = NotRequired
    except ImportError:
        typing.NotRequired = lambda item: item

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
openapi_client = ModuleType("openapi_client")
openapi_client.MarketOpenapiApi = type("MarketOpenapiApi", (), {})
openapi_client.ApiClient = type("ApiClient", (), {"__init__": lambda self, configuration=None: None})
sys.modules.setdefault("openapi_client", openapi_client)
openapi_client_configuration = ModuleType("openapi_client.configuration")


class StubConfiguration(object):
    def __init__(self):
        self.api_key = {}
        self.client_side_validation = False
        self.host = ""


openapi_client_configuration.Configuration = StubConfiguration
sys.modules.setdefault("openapi_client.configuration", openapi_client_configuration)
openapi_client_rest = ModuleType("openapi_client.rest")
openapi_client_rest.ApiException = type("ApiException", (Exception,), {})
sys.modules.setdefault("openapi_client.rest", openapi_client_rest)
market_openapi_api = ModuleType("openapi_client.api.market_openapi_api")
market_openapi_api.MarketOpenapiApi = type("MarketOpenapiApi", (), {})
sys.modules.setdefault("openapi_client.api.market_openapi_api", market_openapi_api)
sys.modules.setdefault("rest_framework_simplejwt", ModuleType("rest_framework_simplejwt"))
simplejwt_tokens = ModuleType("rest_framework_simplejwt.tokens")
simplejwt_tokens.AccessToken = type("AccessToken", (), {})
sys.modules.setdefault("rest_framework_simplejwt.tokens", simplejwt_tokens)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402
from django.test import SimpleTestCase  # noqa: E402

django.setup()


class Obj(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        if "data" in kwargs and "META" not in kwargs:
            self.META = {}


class DeployPreflightServiceTests(SimpleTestCase):
    def setUp(self):
        from console.services.deploy_preflight_service import DeployPreflightService

        self.service = DeployPreflightService()
        self.tenant = Obj(tenant_id="tenant-1", tenant_name="team-a", enterprise_id="eid-1")
        self.region = Obj(region_name="region-a")

    def test_image_preflight_blocks_when_image_tag_is_missing(self):
        self._stub_template_checks()
        self.service.template_preflight._probe_image_manifest = mock.Mock(
            return_value=("block", "镜像版本不存在", "image_not_found"))

        result = self.service.run(self.tenant, self.region, "image", {
            "docker_cmd": "registry.example.com/team/demo:missing",
            "image_type": "docker_image",
            "arch": "amd64",
        })

        self.assertEqual("block", result["status"])
        self.assertTrue(result["should_block"])
        self.assertEqual("image_not_found", self._check(result, "image_manifest")["reason"])

    def test_source_code_preflight_blocks_when_repository_is_missing(self):
        result = self.service.run(self.tenant, self.region, "source_code", {
            "code_from": "gitlab_manual",
            "server_type": "git",
            "code_version": "main",
        })

        self.assertEqual("block", result["status"])
        self.assertEqual("repository_missing", self._check(result, "source_repository")["reason"])

    def test_source_code_preflight_warns_without_branch_and_does_not_block(self):
        result = self.service.run(self.tenant, self.region, "source_code", {
            "code_from": "gitlab_manual",
            "server_type": "git",
            "git_url": "https://git.example.com/team/web.git",
        })

        self.assertEqual("warning", result["status"])
        self.assertFalse(result["should_block"])
        self.assertEqual("branch_defaulted", self._check(result, "source_repository")["reason"])

    def test_source_code_preflight_passes_for_oauth_repository_with_service(self):
        result = self.service.run(self.tenant, self.region, "source_code", {
            "code_from": "oauth_github",
            "server_type": "git",
            "git_url": "git@github.com:goodrain/demo.git",
            "code_version": "main",
            "is_oauth": True,
            "service_id": 17,
        })

        self.assertEqual("pass", result["status"])
        self.assertFalse(result["should_block"])
        self.assertEqual("", self._check(result, "source_repository")["reason"])

    def test_source_code_preflight_blocks_when_oauth_service_is_missing(self):
        result = self.service.run(self.tenant, self.region, "source_code", {
            "code_from": "oauth_github",
            "server_type": "git",
            "git_url": "git@github.com:goodrain/demo.git",
            "code_version": "main",
            "is_oauth": True,
        })

        self.assertEqual("block", result["status"])
        self.assertTrue(result["should_block"])
        self.assertEqual("oauth_service_missing", self._check(result, "source_repository")["reason"])

    def test_package_preflight_blocks_when_uploaded_file_type_is_not_supported(self):
        record = Obj(event_id="event-1", status="finished", source_dir="['demo.txt']")
        self.service.package_upload_service.get_upload_record = mock.Mock(return_value=record)

        result = self.service.run(self.tenant, self.region, "package", {
            "region": "region-a",
            "event_id": "event-1",
        })

        self.assertEqual("block", result["status"])
        self.assertEqual("package_type_unsupported", self._check(result, "package_upload")["reason"])

    def test_package_preflight_passes_for_supported_uploaded_packages(self):
        record = Obj(event_id="event-1", status="finished", source_dir="['demo.JAR', 'api.war', 'web.zip']")
        self.service.package_upload_service.get_upload_record = mock.Mock(return_value=record)

        result = self.service.run(self.tenant, self.region, "package", {
            "region": "region-a",
            "event_id": "event-1",
        })

        self.assertEqual("pass", result["status"])
        self.assertFalse(result["should_block"])
        self.assertEqual(["demo.JAR", "api.war", "web.zip"],
                         self._check(result, "package_upload")["details"]["packages"])

    def test_package_preflight_warns_when_upload_status_is_not_finished(self):
        record = Obj(event_id="event-1", status="uploading", source_dir=["demo.jar"])
        self.service.package_upload_service.get_upload_record = mock.Mock(return_value=record)

        result = self.service.run(self.tenant, self.region, "package", {
            "event_id": "event-1",
        })

        self.service.package_upload_service.get_upload_record.assert_called_once_with(
            "team-a", "region-a", "event-1")
        self.assertEqual("warning", result["status"])
        self.assertFalse(result["should_block"])
        self.assertEqual("package_status_unknown", self._check(result, "package_upload")["reason"])

    def test_package_preflight_blocks_when_upload_event_is_missing(self):
        result = self.service.run(self.tenant, self.region, "package", {})

        self.assertEqual("block", result["status"])
        self.assertTrue(result["should_block"])
        self.assertEqual("package_event_missing", self._check(result, "package_upload")["reason"])

    def test_uploaded_template_preflight_reuses_template_checks(self):
        self._stub_template_checks()
        self.service.template_preflight._probe_image_manifest = mock.Mock(return_value=("pass", "镜像版本存在", ""))

        result = self.service.run(self.tenant, self.region, "uploaded_template", {
            "app_template": {
                "arch": "amd64",
                "apps": [{
                    "service_cname": "web",
                    "share_image": "registry.example.com/team/web:v1",
                    "container_cpu": 100,
                    "memory": 256,
                }],
            }
        })

        self.assertEqual("pass", result["status"])
        self.assertEqual("template", result["deploy_type"])
        self.assertEqual("image_manifest", result["checks"][-1]["name"])

    def test_docker_run_preflight_extracts_image_after_common_options(self):
        self._stub_template_checks()
        self.service.template_preflight._probe_image_manifest = mock.Mock(return_value=("pass", "镜像版本存在", ""))

        result = self.service.run(self.tenant, self.region, "docker_run", {
            "docker_cmd": "docker run -d --name web -p 80:80 registry.example.com/team/web:v1",
            "image_type": "docker_run",
            "arch": "amd64",
        })

        self.assertEqual("pass", result["status"])
        self.assertEqual("docker_run", result["deploy_type"])
        self.assertEqual("registry.example.com/team/web:v1", result["payload_summary"]["image"])

    def test_unknown_deploy_type_blocks(self):
        result = self.service.run(self.tenant, self.region, "helm", {})

        self.assertEqual("block", result["status"])
        self.assertTrue(result["should_block"])
        self.assertEqual("deploy_type_unsupported", self._check(result, "deploy_type")["reason"])

    def test_observe_mode_downgrades_block_to_warning_without_blocking(self):
        with mock.patch.dict(os.environ, {"DEPLOY_PREFLIGHT_MODE": "observe"}):
            result = self.service.run(self.tenant, self.region, "helm", {})

        self.assertEqual("warning", result["status"])
        self.assertFalse(result["should_block"])
        self.assertEqual("observe", result["mode"])

    def test_deploy_preflight_view_returns_structured_result(self):
        from console.views.app_create.deploy_preflight import DeployPreflightView

        preflight = {"status": "pass", "should_block": False, "summary": "可以部署", "checks": []}
        view = DeployPreflightView()
        view.tenant = self.tenant
        view.region = self.region
        view.user = Obj(user_id=1, enterprise_id="eid-1")
        request = Obj(data={"deploy_type": "image", "payload": {"docker_cmd": "nginx:latest"}})

        with mock.patch("console.views.app_create.deploy_preflight.deploy_preflight_service.run",
                        return_value=preflight) as run:
            response = view.post(request)

        run.assert_called_once_with(self.tenant, self.region, "image", {"docker_cmd": "nginx:latest"}, view.user)
        self.assertEqual(200, response.status_code)
        self.assertEqual(preflight, response.data["data"]["bean"])

    def test_docker_run_create_view_blocks_when_preflight_blocks(self):
        from console.exception.main import AbortRequest
        from console.views.app_create.docker_run import DockerRunCreateView

        preflight = {"status": "block", "should_block": True, "summary": "镜像版本不存在", "checks": []}
        view = DockerRunCreateView()
        view.tenant = self.tenant
        view.region = self.region
        view.region_name = "region-a"
        view.response_region = "region-a"
        view.user = Obj(pk=1, enterprise_id="eid-1", nick_name="tester")
        request = Obj(data={
            "group_id": 7,
            "service_cname": "web",
            "docker_cmd": "registry.example.com/team/web:missing",
            "image_type": "docker_image",
            "arch": "amd64",
        })

        with mock.patch("console.views.app_create.docker_run.app_service.is_k8s_component_name_duplicate",
                        return_value=False), \
                mock.patch("console.views.app_create.docker_run.deploy_preflight_service.run",
                           return_value=preflight):
            with self.assertRaises(AbortRequest) as ctx:
                view.post(request)

        self.assertEqual(412, ctx.exception.status_code)
        self.assertEqual(preflight, ctx.exception.bean)

    def test_source_code_create_view_blocks_when_preflight_blocks(self):
        from console.exception.main import AbortRequest
        from console.views.app_create.source_code import SourceCodeCreateView

        preflight = {"status": "block", "should_block": True, "summary": "仓库地址不能为空", "checks": []}
        view = SourceCodeCreateView()
        view.tenant = self.tenant
        view.region = self.region
        view.region_name = "region-a"
        view.response_region = "region-a"
        view.app_id = 7
        view.user = Obj(user_id=1, pk=1, enterprise_id="eid-1", nick_name="tester")
        request = Obj(user=view.user, data={
            "group_id": 7,
            "service_cname": "web",
            "code_from": "gitlab_manual",
            "git_url": "https://git.example.com/team/web.git",
            "code_version": "main",
            "server_type": "git",
        })
        request.get_host = lambda: "console.example.com"

        with mock.patch("console.views.app_create.source_code.app_service.is_k8s_component_name_duplicate",
                        return_value=False), \
                mock.patch("console.views.app_create.source_code.deploy_preflight_service.run",
                           return_value=preflight):
            with self.assertRaises(AbortRequest) as ctx:
                view.post(request)

        self.assertEqual(412, ctx.exception.status_code)
        self.assertEqual(preflight, ctx.exception.bean)

    def test_package_create_view_blocks_when_preflight_blocks(self):
        from console.exception.main import AbortRequest
        from console.views.app_create.source_code import PackageCreateView

        preflight = {"status": "block", "should_block": True, "summary": "软件包格式不支持", "checks": []}
        view = PackageCreateView()
        view.tenant = self.tenant
        view.region = self.region
        view.region_name = "region-a"
        view.response_region = "region-a"
        view.team_name = "team-a"
        view.user = Obj(user_id=1, pk=1, enterprise_id="eid-1", nick_name="tester")
        request = Obj(data={
            "region": "region-a",
            "event_id": "event-1",
            "group_id": 7,
            "service_cname": "web",
        })

        with mock.patch("console.views.app_create.source_code.app_service.is_k8s_component_name_duplicate",
                        return_value=False), \
                mock.patch("console.views.app_create.source_code.deploy_preflight_service.run",
                           return_value=preflight):
            with self.assertRaises(AbortRequest) as ctx:
                view.post(request, tenantName="team-a")

        self.assertEqual(412, ctx.exception.status_code)
        self.assertEqual(preflight, ctx.exception.bean)

    def _stub_template_checks(self):
        self.service.template_preflight._get_region_resources = mock.Mock(return_value={
            "all_node": 1,
            "node_ready": 1,
            "cap_cpu": 4000,
            "req_cpu": 0,
            "cap_mem": 8192,
            "req_mem": 0,
        })
        self.service.template_preflight._get_cluster_arches = mock.Mock(return_value=["amd64"])

    @staticmethod
    def _check(result, name):
        for item in result["checks"]:
            if item["name"] == name:
                return item
        raise AssertionError("missing check {}".format(name))
