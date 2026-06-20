# -*- coding: utf-8 -*-
import collections
import os
import sys
from types import ModuleType, SimpleNamespace
from unittest import TestCase, mock
try:
    from urllib.parse import parse_qs, urlparse
except ImportError:
    from urlparse import parse_qs, urlparse

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from console.services.team_services import team_services  # noqa: E402
from console.exception.main import ServiceHandleException  # noqa: E402


class RegistryNamespaceServiceTestCase(TestCase):
    def test_parse_volcano_cr_domain_extracts_registry_and_region(self):
        registry, region = team_services._parse_volcano_cr_domain("https://zqq-cn-shanghai.cr.volces.com")

        self.assertEqual(registry, "zqq")
        self.assertEqual(region, "cn-shanghai")

    def test_parse_volcano_cr_domain_rejects_non_volcano_domain(self):
        with self.assertRaises(ServiceHandleException):
            team_services._parse_volcano_cr_domain("https://registry.example.com")

    def test_volcano_cr_api_uses_regional_service_endpoint(self):
        api = team_services._volcano_cr_api("cloud-ak", "cloud-sk", "cn-shanghai")

        self.assertEqual(api.api_client.configuration.host, "cr.cn-shanghai.volcengineapi.com")
        self.assertEqual(api.api_client.configuration.region, "cn-shanghai")
        self.assertEqual(api.api_client.configuration.ak, "cloud-ak")
        self.assertEqual(api.api_client.configuration.sk, "cloud-sk")

    def test_parse_aliyun_acr_domain_extracts_region(self):
        region = team_services._parse_aliyun_acr_domain("https://registry.cn-hangzhou.aliyuncs.com/")

        self.assertEqual(region, "cn-hangzhou")

    def test_parse_tencent_tcr_domain_extracts_registry_host(self):
        host = team_services._parse_tencent_tcr_domain("https://demo-tcr.tencentcloudcr.com")

        self.assertEqual(host, "demo-tcr.tencentcloudcr.com")

    def test_parse_tencent_tcr_personal_domain_extracts_registry_host(self):
        host = team_services._parse_tencent_tcr_domain("https://ccr.ccs.tencentyun.com")

        self.assertEqual(host, "ccr.ccs.tencentyun.com")

    def test_parse_tencent_tcr_hongkong_personal_domain_extracts_registry_host(self):
        host = team_services._parse_tencent_tcr_domain("https://hkccr.ccs.tencentyun.com")

        self.assertEqual(host, "hkccr.ccs.tencentyun.com")

    def test_parse_huawei_swr_domain_extracts_region(self):
        region = team_services._parse_huawei_swr_domain("https://swr.cn-north-4.myhuaweicloud.com")

        self.assertEqual(region, "cn-north-4")

    def test_get_aliyun_acr_namespaces_uses_cloud_api(self):
        client = mock.Mock()
        client.call_api.return_value = {
            "body": {
                "data": {
                    "namespaces": [
                        {"namespace": "rainbond"},
                        {"namespace": "demo"},
                    ],
                },
            },
        }

        with mock.patch.object(team_services, "_aliyun_acr_client", return_value=client, create=True) as client_factory:
            namespaces = team_services.get_cloud_registry_namespaces(
                domain="https://registry.cn-hangzhou.aliyuncs.com",
                access_key="cloud-ak",
                access_secret="cloud-sk",
                hub_type="AliyunACR",
            )

        client_factory.assert_called_once_with("cloud-ak", "cloud-sk", "cn-hangzhou")
        params, request, _ = client.call_api.call_args[0]
        self.assertEqual(params.action, "GetNamespaceList")
        self.assertEqual(params.pathname, "/namespace")
        self.assertEqual(request.query, {})
        self.assertEqual(namespaces, ["rainbond", "demo"])

    def test_get_aliyun_acr_images_uses_cloud_api(self):
        client = mock.Mock()
        client.call_api.return_value = {
            "body": {
                "data": {
                    "repos": [
                        {
                            "repoName": "nginx",
                            "repoNamespace": "rainbond",
                            "repoType": "PRIVATE",
                            "summary": "demo repo",
                            "gmtCreate": "2026-06-18T00:00:00Z",
                            "gmtModified": "2026-06-18T01:00:00Z",
                        },
                    ],
                    "total": 1,
                },
            },
        }

        with mock.patch.object(team_services, "_aliyun_acr_client", return_value=client, create=True):
            data = team_services.get_cloud_registry_images(
                domain="https://registry.cn-hangzhou.aliyuncs.com",
                access_key="cloud-ak",
                access_secret="cloud-sk",
                hub_type="AliyunACR",
                namespace="rainbond",
                page=2,
                page_size=10,
            )

        params, request, _ = client.call_api.call_args[0]
        self.assertEqual(params.action, "GetRepoListByNamespace")
        self.assertEqual(params.pathname, "/repos/rainbond")
        self.assertEqual(request.query, {"Page": "2", "PageSize": "10"})
        self.assertEqual(data["images"][0]["name"], "nginx")
        self.assertEqual(data["images"][0]["namespace"], "rainbond")
        self.assertFalse(data["images"][0]["is_public"])
        self.assertEqual(data["total"], 1)

    def test_get_aliyun_acr_images_searches_across_pages(self):
        client = mock.Mock()
        client.call_api.side_effect = [
            {
                "body": {
                    "data": {
                        "repos": [
                            {
                                "repoName": "redis",
                                "repoNamespace": "goodrain",
                            },
                        ],
                        "total": 2,
                    },
                },
            },
            {
                "body": {
                    "data": {
                        "repos": [
                            {
                                "repoName": "nginx",
                                "repoNamespace": "goodrain",
                            },
                        ],
                        "total": 2,
                    },
                },
            },
        ]

        with mock.patch.object(team_services, "_aliyun_acr_client", return_value=client, create=True):
            data = team_services.get_cloud_registry_images(
                domain="https://registry.cn-hangzhou.aliyuncs.com",
                access_key="cloud-ak",
                access_secret="cloud-sk",
                hub_type="AliyunACR",
                namespace="goodrain",
                page=1,
                page_size=20,
                search_key="nginx",
            )

        queries = [call_args[0][1].query for call_args in client.call_api.call_args_list]
        self.assertEqual(queries, [
            {
                "Page": "1",
                "PageSize": "100"
            },
            {
                "Page": "2",
                "PageSize": "100"
            },
        ])
        self.assertEqual(data["images"][0]["name"], "nginx")
        self.assertEqual(data["images"][0]["namespace"], "goodrain")
        self.assertEqual(data["total"], 1)

    def test_get_tencent_tcr_namespaces_resolves_registry_and_uses_cloud_api(self):
        discovery_client = mock.Mock()
        registry_client = mock.Mock()
        discovery_client.DescribeInstances.return_value = SimpleNamespace(
            Registries=[
                SimpleNamespace(
                    RegistryId="tcr-abc",
                    RegistryName="demo-tcr",
                    PublicDomain="demo-tcr.tencentcloudcr.com",
                    RegionName="ap-shanghai",
                )
            ],
            TotalCount=1,
        )
        registry_client.DescribeNamespaces.return_value = SimpleNamespace(
            NamespaceList=[
                SimpleNamespace(Name="rainbond"),
                SimpleNamespace(Namespace="legacy"),
            ],
            TotalCount=2,
        )

        with mock.patch.object(
                team_services, "_tencent_tcr_client",
                side_effect=[discovery_client, registry_client],
                create=True) as client_factory:
            namespaces = team_services.get_cloud_registry_namespaces(
                domain="https://demo-tcr.tencentcloudcr.com",
                access_key="cloud-ak",
                access_secret="cloud-sk",
                hub_type="TencentTCR",
            )

        client_factory.assert_has_calls([
            mock.call("cloud-ak", "cloud-sk", "ap-guangzhou"),
            mock.call("cloud-ak", "cloud-sk", "ap-shanghai"),
        ])
        instance_request = discovery_client.DescribeInstances.call_args[0][0]
        self.assertTrue(instance_request.AllRegion)
        namespace_request = registry_client.DescribeNamespaces.call_args[0][0]
        self.assertEqual(namespace_request.RegistryId, "tcr-abc")
        self.assertEqual(namespace_request.Offset, 0)
        self.assertEqual(namespace_request.Limit, 100)
        self.assertTrue(namespace_request.All)
        self.assertEqual(namespaces, ["rainbond", "legacy"])

    def test_get_tencent_tcr_personal_namespaces_uses_personal_api(self):
        client = mock.Mock()
        client.DescribeNamespacePersonal.return_value = SimpleNamespace(
            NamespaceInfo=[
                SimpleNamespace(Namespace="rainbond"),
                SimpleNamespace(Name="legacy"),
            ],
            NamespaceCount=2,
        )

        with mock.patch.object(team_services, "_tencent_tcr_client", return_value=client, create=True) as client_factory:
            namespaces = team_services.get_cloud_registry_namespaces(
                domain="https://ccr.ccs.tencentyun.com",
                access_key="cloud-ak",
                access_secret="cloud-sk",
                hub_type="TencentTCR",
            )

        client_factory.assert_called_once_with("cloud-ak", "cloud-sk", "ap-guangzhou")
        request = client.DescribeNamespacePersonal.call_args[0][0]
        self.assertEqual(request.Namespace, "")
        self.assertEqual(request.Offset, 0)
        self.assertEqual(request.Limit, 100)
        self.assertEqual(namespaces, ["rainbond", "legacy"])

    def test_get_tencent_tcr_images_uses_cloud_api(self):
        discovery_client = mock.Mock()
        registry_client = mock.Mock()
        discovery_client.DescribeInstances.return_value = SimpleNamespace(
            Registries=[
                SimpleNamespace(
                    RegistryId="tcr-abc",
                    RegistryName="demo-tcr",
                    PublicDomain="demo-tcr.tencentcloudcr.com",
                    RegionName="ap-shanghai",
                )
            ],
            TotalCount=1,
        )
        registry_client.DescribeRepositories.return_value = SimpleNamespace(
            RepositoryList=[
                SimpleNamespace(
                    Name="rainbond/nginx",
                    Namespace="rainbond",
                    Public=False,
                    Description="",
                    BriefDescription="demo repo",
                    CreationTime="2026-06-18 00:00:00 +0000 UTC",
                    UpdateTime="2026-06-18 01:00:00 +0000 UTC",
                ),
            ],
            TotalCount=1,
        )

        with mock.patch.object(
                team_services, "_tencent_tcr_client",
                side_effect=[discovery_client, registry_client],
                create=True):
            data = team_services.get_cloud_registry_images(
                domain="https://demo-tcr.tencentcloudcr.com",
                access_key="cloud-ak",
                access_secret="cloud-sk",
                hub_type="TencentTCR",
                namespace="rainbond",
                page=2,
                page_size=10,
            )

        request = registry_client.DescribeRepositories.call_args[0][0]
        self.assertEqual(request.RegistryId, "tcr-abc")
        self.assertEqual(request.NamespaceName, "rainbond")
        self.assertEqual(request.Offset, 10)
        self.assertEqual(request.Limit, 10)
        self.assertEqual(data["images"][0]["name"], "nginx")
        self.assertEqual(data["images"][0]["namespace"], "rainbond")
        self.assertFalse(data["images"][0]["is_public"])
        self.assertEqual(data["total"], 1)

    def test_get_tencent_tcr_personal_images_uses_personal_api(self):
        client = mock.Mock()
        client.DescribeRepositoryFilterPersonal.return_value = SimpleNamespace(
            RepoInfo=[
                SimpleNamespace(
                    RepoName="nginx",
                    Public=0,
                    Description="demo repo",
                    CreationTime="2026-06-18 00:00:00 +0000 UTC",
                    UpdateTime="2026-06-18 01:00:00 +0000 UTC",
                ),
            ],
            TotalCount=1,
        )

        with mock.patch.object(team_services, "_tencent_tcr_client", return_value=client, create=True):
            data = team_services.get_cloud_registry_images(
                domain="https://ccr.ccs.tencentyun.com",
                access_key="cloud-ak",
                access_secret="cloud-sk",
                hub_type="TencentTCR",
                namespace="rainbond",
                page=2,
                page_size=10,
                search_key="nginx",
            )

        request = client.DescribeRepositoryFilterPersonal.call_args[0][0]
        self.assertEqual(request.Namespace, "rainbond")
        self.assertEqual(request.RepoName, "nginx")
        self.assertEqual(request.Offset, 10)
        self.assertEqual(request.Limit, 10)
        self.assertEqual(data["images"][0]["name"], "nginx")
        self.assertEqual(data["images"][0]["namespace"], "rainbond")
        self.assertFalse(data["images"][0]["is_public"])
        self.assertEqual(data["total"], 1)

    def test_get_huawei_swr_namespaces_uses_cloud_api(self):
        client = mock.Mock()
        client.list_namespaces.return_value = SimpleNamespace(
            namespaces=[
                SimpleNamespace(name="rainbond"),
                SimpleNamespace(name="demo"),
            ],
        )

        with mock.patch.object(team_services, "_huawei_swr_client", return_value=client, create=True) as client_factory:
            namespaces = team_services.get_cloud_registry_namespaces(
                domain="https://swr.cn-north-4.myhuaweicloud.com",
                access_key="cloud-ak",
                access_secret="cloud-sk",
                hub_type="HuaweiSWR",
            )

        client_factory.assert_called_once_with("cloud-ak", "cloud-sk", "cn-north-4")
        request = client.list_namespaces.call_args[0][0]
        self.assertEqual(request.__class__.__name__, "ListNamespacesRequest")
        self.assertEqual(namespaces, ["rainbond", "demo"])

    def test_get_huawei_swr_images_uses_cloud_api(self):
        client = mock.Mock()
        client.list_repos_details.return_value = SimpleNamespace(
            body=[
                SimpleNamespace(
                    name="nginx",
                    namespace="rainbond",
                    description="demo repo",
                    is_public=False,
                    num_download=3,
                    created_at="2026-06-18T00:00:00Z",
                    updated_at="2026-06-18T01:00:00Z",
                    status=True,
                    total_range=1,
                ),
            ],
            content_range="0-0/1",
        )

        with mock.patch.object(team_services, "_huawei_swr_client", return_value=client, create=True):
            data = team_services.get_cloud_registry_images(
                domain="https://swr.cn-north-4.myhuaweicloud.com",
                access_key="cloud-ak",
                access_secret="cloud-sk",
                hub_type="HuaweiSWR",
                namespace="rainbond",
                page=2,
                page_size=10,
            )

        request = client.list_repos_details.call_args[0][0]
        self.assertEqual(request.namespace, "rainbond")
        self.assertEqual(request.limit, 10)
        self.assertEqual(request.offset, 10)
        self.assertEqual(data["images"][0]["name"], "nginx")
        self.assertEqual(data["images"][0]["namespace"], "rainbond")
        self.assertFalse(data["images"][0]["is_public"])
        self.assertEqual(data["images"][0]["pull_count"], 3)
        self.assertEqual(data["total"], 1)

    def test_get_volcano_cr_namespaces_uses_cloud_api(self):
        api = mock.Mock()
        api.list_namespaces.return_value = SimpleNamespace(
            items=[SimpleNamespace(name="rainbond"), SimpleNamespace(name="demo")],
            total_count=2,
        )

        with mock.patch.object(team_services, "_volcano_cr_api", return_value=api) as api_factory:
            namespaces = team_services.get_cloud_registry_namespaces(
                domain="https://zqq-cn-shanghai.cr.volces.com",
                access_key="cloud-ak",
                access_secret="cloud-sk",
                hub_type="VolcanoCR",
            )

        api_factory.assert_called_once_with("cloud-ak", "cloud-sk", "cn-shanghai")
        request = api.list_namespaces.call_args[0][0]
        self.assertEqual(request.registry, "zqq")
        self.assertEqual(request.page_number, 1)
        self.assertEqual(request.page_size, 100)
        self.assertEqual(namespaces, ["rainbond", "demo"])

    def test_get_volcano_cr_images_uses_cloud_api(self):
        api = mock.Mock()
        api.list_repositories.return_value = SimpleNamespace(
            items=[
                SimpleNamespace(
                    name="nginx",
                    namespace="rainbond",
                    description="",
                    access_level="Private",
                    create_time="2026-06-18T00:00:00Z",
                    update_time="2026-06-18T01:00:00Z"),
            ],
            total_count=1,
        )

        with mock.patch.object(team_services, "_volcano_cr_api", return_value=api) as api_factory:
            data = team_services.get_cloud_registry_images(
                domain="https://zqq-cn-shanghai.cr.volces.com",
                access_key="cloud-ak",
                access_secret="cloud-sk",
                hub_type="VolcanoCR",
                namespace="rainbond",
                page=1,
                page_size=10,
            )

        api_factory.assert_called_once_with("cloud-ak", "cloud-sk", "cn-shanghai")
        request = api.list_repositories.call_args[0][0]
        self.assertEqual(request.registry, "zqq")
        self.assertEqual(request.filter.namespaces, ["rainbond"])
        self.assertEqual(data["images"][0]["name"], "nginx")
        self.assertEqual(data["images"][0]["namespace"], "rainbond")
        self.assertEqual(data["total"], 1)

    def test_get_volcano_cr_tags_uses_cloud_api_metadata(self):
        volcenginesdkcr = ModuleType("volcenginesdkcr")

        class ListTagsRequest(object):
            def __init__(self, namespace=None, page_number=None, page_size=None, registry=None, repository=None):
                self.namespace = namespace
                self.page_number = page_number
                self.page_size = page_size
                self.registry = registry
                self.repository = repository

        volcenginesdkcr.ListTagsRequest = ListTagsRequest
        api = mock.Mock()
        api.list_tags.return_value = SimpleNamespace(
            items=[
                SimpleNamespace(
                    name="alpine",
                    digest="sha256:manifest",
                    push_time="2026-06-18T03:48:13Z",
                    size=123,
                    image_attributes=[
                        SimpleNamespace(
                            architecture="amd64",
                            digest="sha256:image",
                            os="linux",
                            size=456,
                        )
                    ],
                )
            ],
            total_count=1,
        )

        with mock.patch.dict(sys.modules, {"volcenginesdkcr": volcenginesdkcr}), \
                mock.patch.object(team_services, "_volcano_cr_api", return_value=api) as api_factory:
            data = team_services.get_cloud_registry_tags(
                domain="https://zqq-cn-shanghai.cr.volces.com",
                username="user",
                password="password",
                access_key="cloud-ak",
                access_secret="cloud-sk",
                hub_type="VolcanoCR",
                namespace="rainbond",
                name="nginx",
                page=1,
                page_size=10,
            )

        api_factory.assert_called_once_with("cloud-ak", "cloud-sk", "cn-shanghai")
        request = api.list_tags.call_args[0][0]
        self.assertEqual(request.registry, "zqq")
        self.assertEqual(request.namespace, "rainbond")
        self.assertEqual(request.repository, "nginx")
        self.assertEqual(data["tags"], [{
            "name": "alpine",
            "size": 123,
            "digest": "sha256:manifest",
            "created_at": "2026-06-18T03:48:13Z",
            "updated_at": "2026-06-18T03:48:13Z",
            "os": "linux",
            "architecture": "amd64",
            "status": "active",
        }])
        self.assertEqual(data["total"], 1)

    def test_cloud_registry_auth_error_returns_clear_unauthorized_message(self):
        class CloudApiException(Exception):
            def __init__(self):
                self.status = 401
                self.reason = "Unauthorized"
                self.body = (
                    '{"ResponseMetadata":{"Error":{"Code":"SignatureDoesNotMatch",'
                    '"Message":"signature mismatch"}}}'
                )
                super(CloudApiException, self).__init__("raw cloud api auth failure")

        with self.assertRaises(ServiceHandleException) as ctx:
            team_services._handle_cloud_registry_exception(
                "list namespaces from",
                "VolcanoCR",
                CloudApiException())

        self.assertEqual(ctx.exception.status_code, 401)
        self.assertEqual(ctx.exception.msg, "cloud registry credential unauthorized")
        self.assertEqual(ctx.exception.msg_show, "云厂商镜像仓库认证失败，请检查 Access Key、Access Secret 是否正确并确认已授予镜像仓库访问权限")

    def test_get_harbor_namespaces_fetches_all_pages(self):
        names = ["project-{}".format(i) for i in range(205)]

        def harbor_projects_response(url, *args, **kwargs):
            query = parse_qs(urlparse(url).query)
            page = int(query.get("page", ["1"])[0])
            page_size = int(query.get("page_size", ["10"])[0])
            start = (page - 1) * page_size
            page_names = names[start:start + page_size]
            response = mock.Mock(status_code=200, headers={"X-Total-Count": str(len(names))})
            response.json.return_value = [{"name": name} for name in page_names]
            return response

        with mock.patch("console.services.team_services.requests.get", side_effect=harbor_projects_response) as get_mock:
            result = team_services.get_registry_namespaces(
                domain="https://harbor.example.com",
                username="demo-user",
                password="demo-password",
                hub_type="Harbor",
            )

        self.assertEqual(result, names)
        self.assertEqual(get_mock.call_count, 3)

    def test_get_harbor_namespaces_fetches_until_short_page_without_total_header(self):
        names = ["project-{}".format(i) for i in range(120)]

        def harbor_projects_response(url, *args, **kwargs):
            query = parse_qs(urlparse(url).query)
            page = int(query.get("page", ["1"])[0])
            page_size = int(query.get("page_size", ["10"])[0])
            start = (page - 1) * page_size
            page_names = names[start:start + page_size]
            response = mock.Mock(status_code=200, headers={})
            response.json.return_value = [{"name": name} for name in page_names]
            return response

        with mock.patch("console.services.team_services.requests.get", side_effect=harbor_projects_response) as get_mock:
            result = team_services.get_registry_namespaces(
                domain="https://harbor.example.com",
                username="demo-user",
                password="demo-password",
                hub_type="Harbor",
            )

        self.assertEqual(result, names)
        self.assertEqual(get_mock.call_count, 2)
