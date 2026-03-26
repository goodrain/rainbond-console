# -*- coding: utf-8 -*-
import os
import sys
from types import ModuleType
from unittest import TestCase, mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402
from rest_framework.test import APIRequestFactory, force_authenticate  # noqa: E402

django.setup()

from console.views import base as base_views  # noqa: E402
from console.views.team_resources import HelmReleasesView  # noqa: E402
from console.views.team_resources import HelmReleaseDetailView  # noqa: E402
from console.views.team_resources import HelmReleaseHistoryView  # noqa: E402
from console.views.team_resources import HelmReleaseRollbackView  # noqa: E402
from console.views.team_resources import NsResourceDetailView  # noqa: E402
from console.views.team_resources import ResourceCenterPodLogsView  # noqa: E402
from console.views import team_resources  # noqa: E402
from www.apiclient.regionapi import RegionInvokeApi  # noqa: E402


class HelmReleasesViewTestCase(TestCase):
    def test_get_uses_team_namespace_for_helm_release_lookup(self):
        view = HelmReleasesView()
        view.tenant = mock.Mock(namespace="demo-ns", tenant_name="demo-team")
        request = APIRequestFactory().get("/console/team-resources/helm/releases")

        with mock.patch.object(team_resources.region_api,
                               "get_tenant_helm_releases",
                               return_value=({}, {
                                   "bean": {
                                       "list": []
                                   }
                               })) as list_mock:
            response = view.get(request, "demo-team", "demo-region")

        list_mock.assert_called_once_with("demo-region", "demo-team", namespace="demo-ns")
        self.assertEqual(response.status_code, 200)

    def test_post_uses_team_namespace_for_helm_install(self):
        payload = {
            "name": "demo-release",
            "chart_name": "apache",
            "version": "1.0.0",
            "values": {
                "replicaCount": 1
            }
        }
        expected_payload = dict(payload, namespace="demo-ns")
        view = HelmReleasesView()
        view.tenant = mock.Mock(namespace="demo-ns", tenant_name="demo-team")
        factory = APIRequestFactory()
        request = view.initialize_request(factory.post("/console/team-resources/helm/releases", payload, format="json"))

        # Simulate the permission preprocessing in TenantHeaderView.initial() that reads request.data first.
        self.assertEqual(request.data, payload)

        with mock.patch.object(team_resources.region_api,
                               "install_tenant_helm_release",
                               return_value=({}, {
                                   "bean": {
                                       "release_name": "demo-release"
                                   }
                               })) as install_mock:
            response = view.post(request, "demo-team", "demo-region")

        install_mock.assert_called_once_with("demo-region", "demo-team", expected_payload)
        self.assertEqual(response.data["data"]["bean"]["release_name"], "demo-release")

    def test_post_enriches_store_install_with_saved_repo_metadata(self):
        payload = {
            "source_type": "store",
            "repo_name": "bitnami",
            "chart": "argo-cd",
            "version": "7.8.0",
            "release_name": "demo-release",
            "values": "server:\\n  extraArgs: []"
        }
        expected_payload = {
            "source_type": "repo",
            "repo_name": "bitnami",
            "repo_url": "https://charts.bitnami.com/bitnami",
            "chart": "argo-cd",
            "chart_name": "argo-cd",
            "version": "7.8.0",
            "release_name": "demo-release",
            "values": "server:\\n  extraArgs: []",
            "namespace": "demo-ns",
            "username": "demo-user",
            "password": "demo-pass"
        }
        view = HelmReleasesView()
        view.tenant = mock.Mock(namespace="demo-ns", tenant_name="demo-team")
        factory = APIRequestFactory()
        request = view.initialize_request(factory.post("/console/team-resources/helm/releases", payload, format="json"))

        with mock.patch.object(team_resources, "helm_repo", create=True) as helm_repo_mock:
            helm_repo_mock.get_helm_repo_by_name.return_value = {
                "repo_name": "bitnami",
                "repo_url": "https://charts.bitnami.com/bitnami",
                "username": "demo-user",
                "password": "demo-pass"
            }
            with mock.patch.object(team_resources.region_api,
                                   "install_tenant_helm_release",
                                   return_value=({}, {
                                   "bean": {
                                       "release_name": "demo-release"
                                   }
                               })) as install_mock:
                response = view.post(request, "demo-team", "demo-region")

        install_mock.assert_called_once_with("demo-region", "demo-team", expected_payload)
        self.assertEqual(response.data["data"]["bean"]["release_name"], "demo-release")

    def test_post_persists_install_source_after_success(self):
        payload = {
            "source_type": "store",
            "repo_name": "bitnami",
            "chart": "argo-cd",
            "version": "7.8.0",
            "release_name": "demo-release",
            "values": "server:\\n  extraArgs: []"
        }
        view = HelmReleasesView()
        view.tenant = mock.Mock(namespace="demo-ns", tenant_name="demo-team")
        factory = APIRequestFactory()
        request = view.initialize_request(factory.post("/console/team-resources/helm/releases", payload, format="json"))

        with mock.patch.object(team_resources, "helm_repo", create=True) as helm_repo_mock:
            helm_repo_mock.get_helm_repo_by_name.return_value = {
                "repo_name": "bitnami",
                "repo_url": "https://charts.bitnami.com/bitnami",
                "username": "demo-user",
                "password": "demo-pass"
            }
            with mock.patch.object(team_resources, "helm_release_source_repo", create=True) as source_repo_mock:
                with mock.patch.object(team_resources.region_api,
                                       "install_tenant_helm_release",
                                       return_value=({}, {
                                           "bean": {
                                               "release_name": "demo-release"
                                           }
                                       })) as install_mock:
                    response = view.post(request, "demo-team", "demo-region")

        install_mock.assert_called_once()
        source_repo_mock.save_or_update.assert_called_once()
        _, kwargs = source_repo_mock.save_or_update.call_args
        self.assertEqual(kwargs["team_name"], "demo-team")
        self.assertEqual(kwargs["region_name"], "demo-region")
        self.assertEqual(kwargs["namespace"], "demo-ns")
        self.assertEqual(kwargs["release_name"], "demo-release")
        self.assertEqual(kwargs["source_type"], "store")
        self.assertEqual(kwargs["repo_name"], "bitnami")
        self.assertEqual(kwargs["repo_url"], "https://charts.bitnami.com/bitnami")
        self.assertEqual(kwargs["chart_name"], "argo-cd")
        self.assertEqual(kwargs["chart_version"], "7.8.0")
        self.assertEqual(kwargs["values_yaml"], "server:\\n  extraArgs: []")
        self.assertEqual(response.data["data"]["bean"]["release_name"], "demo-release")

    def test_delete_uses_team_namespace_for_helm_release_uninstall(self):
        view = HelmReleaseDetailView()
        view.tenant = mock.Mock(namespace="demo-ns", tenant_name="demo-team")
        request = APIRequestFactory().delete("/console/team-resources/helm/releases/demo-release")

        with mock.patch.object(team_resources.region_api, "uninstall_tenant_helm_release", return_value=({}, {})) as delete_mock:
            response = view.delete(request, "demo-team", "demo-region", "demo-release")

        delete_mock.assert_called_once_with("demo-region", "demo-team", "demo-release", namespace="demo-ns")
        self.assertEqual(response.status_code, 200)

    def test_put_uses_team_namespace_for_helm_release_upgrade(self):
        payload = {
            "source_type": "repo",
            "chart_url": "https://charts.example.com/nginx-1.2.3.tgz",
            "version": "1.2.3",
            "values": "service:\n  type: ClusterIP"
        }
        expected_payload = dict(payload, namespace="demo-ns")
        view = HelmReleaseDetailView()
        view.tenant = mock.Mock(namespace="demo-ns", tenant_name="demo-team")
        factory = APIRequestFactory()
        request = view.initialize_request(factory.put("/console/team-resources/helm/releases/demo-release", payload, format="json"))

        with mock.patch.object(team_resources.region_api,
                               "upgrade_tenant_helm_release",
                               return_value=({}, {
                                   "bean": {
                                       "name": "demo-release"
                                   }
                               })) as upgrade_mock:
            response = view.put(request, "demo-team", "demo-region", "demo-release")

        upgrade_mock.assert_called_once_with("demo-region", "demo-team", "demo-release", expected_payload)
        self.assertEqual(response.status_code, 200)

    def test_put_persists_upgrade_source_after_success(self):
        payload = {
            "source_type": "store",
            "repo_name": "bitnami",
            "chart": "argo-cd",
            "version": "7.9.0",
            "values": "server:\\n  ingress:\\n    enabled: true"
        }
        expected_payload = {
            "source_type": "repo",
            "repo_name": "bitnami",
            "repo_url": "https://charts.bitnami.com/bitnami",
            "chart": "argo-cd",
            "chart_name": "argo-cd",
            "version": "7.9.0",
            "values": "server:\\n  ingress:\\n    enabled: true",
            "namespace": "demo-ns",
            "username": "demo-user",
            "password": "demo-pass"
        }
        view = HelmReleaseDetailView()
        view.tenant = mock.Mock(namespace="demo-ns", tenant_name="demo-team")
        factory = APIRequestFactory()
        request = view.initialize_request(factory.put("/console/team-resources/helm/releases/demo-release", payload, format="json"))

        with mock.patch.object(team_resources, "helm_repo", create=True) as helm_repo_mock:
            helm_repo_mock.get_helm_repo_by_name.return_value = {
                "repo_name": "bitnami",
                "repo_url": "https://charts.bitnami.com/bitnami",
                "username": "demo-user",
                "password": "demo-pass"
            }
            with mock.patch.object(team_resources, "helm_release_source_repo", create=True) as source_repo_mock:
                with mock.patch.object(team_resources.region_api,
                                       "upgrade_tenant_helm_release",
                                       return_value=({}, {
                                           "bean": {
                                               "name": "demo-release"
                                           }
                                       })) as upgrade_mock:
                    response = view.put(request, "demo-team", "demo-region", "demo-release")

        upgrade_mock.assert_called_once_with("demo-region", "demo-team", "demo-release", expected_payload)
        source_repo_mock.save_or_update.assert_called_once()
        _, kwargs = source_repo_mock.save_or_update.call_args
        self.assertEqual(kwargs["team_name"], "demo-team")
        self.assertEqual(kwargs["region_name"], "demo-region")
        self.assertEqual(kwargs["namespace"], "demo-ns")
        self.assertEqual(kwargs["release_name"], "demo-release")
        self.assertEqual(kwargs["source_type"], "store")
        self.assertEqual(kwargs["repo_name"], "bitnami")
        self.assertEqual(kwargs["repo_url"], "https://charts.bitnami.com/bitnami")
        self.assertEqual(kwargs["chart_name"], "argo-cd")
        self.assertEqual(kwargs["chart_version"], "7.9.0")
        self.assertEqual(kwargs["values_yaml"], "server:\\n  ingress:\\n    enabled: true")
        self.assertEqual(response.status_code, 200)

    def test_get_uses_team_namespace_for_helm_release_history(self):
        view = HelmReleaseHistoryView()
        view.tenant = mock.Mock(namespace="demo-ns", tenant_name="demo-team")
        request = APIRequestFactory().get("/console/team-resources/helm/releases/demo-release/history")

        with mock.patch.object(team_resources.region_api,
                               "get_tenant_helm_release_history",
                               return_value=({}, {
                                   "bean": {
                                       "list": []
                                   }
                               })) as history_mock:
            response = view.get(request, "demo-team", "demo-region", "demo-release")

        history_mock.assert_called_once_with("demo-region", "demo-team", "demo-release", namespace="demo-ns")
        self.assertEqual(response.status_code, 200)

    def test_get_uses_team_namespace_for_helm_release_detail(self):
        view = HelmReleaseDetailView()
        view.tenant = mock.Mock(namespace="demo-ns", tenant_name="demo-team")
        request = APIRequestFactory().get("/console/team-resources/helm/releases/demo-release")

        with mock.patch.object(team_resources.region_api,
                               "get_tenant_helm_release_detail",
                               return_value=({}, {
                                   "bean": {
                                       "summary": {
                                           "name": "demo-release"
                                       }
                                   }
                               }),
                               create=True) as detail_mock:
            response = view.get(request, "demo-team", "demo-region", "demo-release")

        detail_mock.assert_called_once_with("demo-region", "demo-team", "demo-release", namespace="demo-ns")
        self.assertEqual(response.status_code, 200)

    def test_get_enriches_helm_release_list_with_source_info(self):
        view = HelmReleasesView()
        view.tenant = mock.Mock(namespace="demo-ns", tenant_name="demo-team")
        request = APIRequestFactory().get("/console/team-resources/helm/releases")

        with mock.patch.object(team_resources, "helm_release_source_repo", create=True) as source_repo_mock:
            source_repo_mock.list_by_releases.return_value = {
                "demo-ns/demo-release": {
                    "source_type": "store",
                    "repo_name": "bitnami",
                    "repo_url": "https://charts.bitnami.com/bitnami",
                    "chart_name": "argo-cd",
                    "chart_version": "7.8.0",
                    "upgrade_mode": "store_locked"
                }
            }
            with mock.patch.object(team_resources.region_api,
                                   "get_tenant_helm_releases",
                                   return_value=({}, {
                                       "bean": {
                                           "list": [{
                                               "name": "demo-release",
                                               "namespace": "demo-ns",
                                               "chart": "argo-cd",
                                               "chart_version": "7.8.0"
                                           }]
                                       }
                                   })) as list_mock:
                response = view.get(request, "demo-team", "demo-region")

        list_mock.assert_called_once_with("demo-region", "demo-team", namespace="demo-ns")
        release = response.data["data"]["bean"]["list"][0]
        self.assertEqual(release["source_info"]["source_type"], "store")
        self.assertEqual(release["source_info"]["upgrade_mode"], "store_locked")

    def test_get_enriches_helm_release_detail_with_source_info(self):
        view = HelmReleaseDetailView()
        view.tenant = mock.Mock(namespace="demo-ns", tenant_name="demo-team")
        request = APIRequestFactory().get("/console/team-resources/helm/releases/demo-release")

        with mock.patch.object(team_resources, "helm_release_source_repo", create=True) as source_repo_mock:
            source_repo_mock.get_by_release.return_value = {
                "source_type": "repo",
                "repo_name": "custom",
                "repo_url": "https://charts.example.com",
                "chart_name": "nginx",
                "chart_version": "1.2.3",
                "values_yaml": "service:\n  type: LoadBalancer",
                "upgrade_mode": "manual_select"
            }
            with mock.patch.object(team_resources.region_api,
                                   "get_tenant_helm_release_detail",
                                   return_value=({}, {
                                       "bean": {
                                           "summary": {
                                                "name": "demo-release",
                                                "namespace": "demo-ns",
                                                "chart": "nginx",
                                                "chart_version": "1.2.3",
                                                "values": "exampleValue: common-chart"
                                            }
                                        }
                                   }),
                                   create=True):
                response = view.get(request, "demo-team", "demo-region", "demo-release")

        summary = response.data["data"]["bean"]["summary"]
        self.assertEqual(summary["source_info"]["source_type"], "repo")
        self.assertEqual(summary["source_info"]["repo_name"], "custom")
        self.assertEqual(summary["source_info"]["upgrade_mode"], "manual_select")
        self.assertEqual(summary["values"], "service:\n  type: LoadBalancer")

    def test_get_defaults_legacy_source_info_when_record_missing(self):
        view = HelmReleaseDetailView()
        view.tenant = mock.Mock(namespace="demo-ns", tenant_name="demo-team")
        request = APIRequestFactory().get("/console/team-resources/helm/releases/demo-release")

        with mock.patch.object(team_resources, "helm_release_source_repo", create=True) as source_repo_mock:
            source_repo_mock.get_by_release.return_value = None
            with mock.patch.object(team_resources.region_api,
                                   "get_tenant_helm_release_detail",
                                   return_value=({}, {
                                       "bean": {
                                           "summary": {
                                               "name": "demo-release",
                                               "namespace": "demo-ns"
                                           }
                                       }
                                   }),
                                   create=True):
                response = view.get(request, "demo-team", "demo-region", "demo-release")

        summary = response.data["data"]["bean"]["summary"]
        self.assertEqual(summary["source_info"]["source_type"], "legacy")
        self.assertEqual(summary["source_info"]["upgrade_mode"], "manual_select")

    def test_delete_cleans_up_saved_install_source_after_success(self):
        view = HelmReleaseDetailView()
        view.tenant = mock.Mock(namespace="demo-ns", tenant_name="demo-team")
        request = APIRequestFactory().delete("/console/team-resources/helm/releases/demo-release")

        with mock.patch.object(team_resources, "helm_release_source_repo", create=True) as source_repo_mock:
            with mock.patch.object(team_resources.region_api, "uninstall_tenant_helm_release", return_value=({}, {})) as delete_mock:
                response = view.delete(request, "demo-team", "demo-region", "demo-release")

        delete_mock.assert_called_once_with("demo-region", "demo-team", "demo-release", namespace="demo-ns")
        source_repo_mock.delete_by_release.assert_called_once_with(
            region_name="demo-region",
            namespace="demo-ns",
            release_name="demo-release"
        )
        self.assertEqual(response.status_code, 200)

    def test_post_uses_team_namespace_for_helm_release_rollback(self):
        payload = {"revision": 2}
        view = HelmReleaseRollbackView()
        view.tenant = mock.Mock(namespace="demo-ns", tenant_name="demo-team")
        factory = APIRequestFactory()
        request = view.initialize_request(factory.post("/console/team-resources/helm/releases/demo-release/rollback", payload, format="json"))

        with mock.patch.object(team_resources.region_api,
                               "rollback_tenant_helm_release",
                               return_value=({}, {})) as rollback_mock:
            response = view.post(request, "demo-team", "demo-region", "demo-release")

        rollback_mock.assert_called_once_with("demo-region", "demo-team", "demo-release", dict(payload, namespace="demo-ns"))
        self.assertEqual(response.status_code, 200)


class NsResourceDetailViewTestCase(TestCase):
    def test_put_accepts_yaml_media_type_and_forwards_raw_body(self):
        yaml_body = "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: web-ui\n"
        request = APIRequestFactory().put(
            "/console/teams/demo-team/regions/demo-region/ns-resources/web-ui?group=apps&version=v1&resource=deployments",
            data=yaml_body,
            content_type="application/yaml"
        )
        user = mock.Mock(enterprise_id="eid", user_id=1, nick_name="demo")
        force_authenticate(request, user=user)
        tenant = mock.Mock(tenant_name="demo-team", tenant_id="tenant-id", creater=2, enterprise_id="eid", namespace="demo-ns")

        with mock.patch.object(base_views.TenantEnterprise.objects, "filter") as enterprise_filter_mock, \
                mock.patch.object(base_views.EnterpriseUserPerm.objects, "filter") as enterprise_perm_filter_mock, \
                mock.patch.object(base_views.Tenants.objects, "get", return_value=tenant), \
                mock.patch.object(base_views.TenantHeaderView, "get_perms"), \
                mock.patch.object(base_views.TenantHeaderView, "check_perms"), \
                mock.patch.object(team_resources.region_api,
                                  "put_tenant_ns_resource",
                                  return_value=({}, {
                                      "bean": {
                                          "name": "web-ui"
                                      }
                                  })) as put_mock:
            enterprise_filter_mock.return_value.first.return_value = None
            enterprise_perm_filter_mock.return_value.first.return_value = None

            response = NsResourceDetailView.as_view()(request,
                                                      team_name="demo-team",
                                                      region_name="demo-region",
                                                      name="web-ui")

        self.assertEqual(response.status_code, 200)
        put_mock.assert_called_once_with(
            "demo-region",
            "demo-team",
            "web-ui",
            yaml_body.encode("utf-8"),
            params={
                "group": "apps",
                "version": "v1",
                "resource": "deployments"
            },
            content_type="application/yaml"
        )


class RegionInvokeApiNsResourceTestCase(TestCase):
    def test_put_tenant_ns_resource_preserves_custom_content_type(self):
        api = RegionInvokeApi()
        yaml_body = b"apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: web-ui\n"

        with mock.patch.object(api,
                               "_RegionInvokeApi__get_region_access_info",
                               return_value=("https://region.example", "token")), \
                mock.patch.object(api, "_put", return_value=({}, {
                    "bean": {}
                })) as put_mock:
            api.put_tenant_ns_resource("demo-region",
                                       "demo-team",
                                       "web-ui",
                                       yaml_body,
                                       params={
                                           "group": "apps",
                                           "version": "v1",
                                           "resource": "deployments"
                                       },
                                       content_type="application/yaml")

        self.assertEqual(put_mock.call_args[0][1]["Content-Type"], "application/yaml")


class ResourceCenterPodLogsViewTestCase(TestCase):
    def test_get_sends_heartbeat_before_upstream_logs(self):
        view = ResourceCenterPodLogsView()
        upstream_stream = mock.Mock(status=200, headers={})
        upstream_stream.stream.return_value = iter([b"data: hello\n\n"])
        request = APIRequestFactory().get("/console/teams/demo-team/regions/demo-region/resource-center/pods/demo-pod/logs?container=demo&lines=200")

        with mock.patch.object(team_resources.region_api, "get_resource_center_pod_log", return_value=upstream_stream):
            response = view.get(request, "demo-team", "demo-region", "demo-pod")

        chunks = iter(response.streaming_content)

        self.assertEqual(next(chunks), b": heartbeat\n\n")
        self.assertEqual(next(chunks), b"data: hello\n\n")
