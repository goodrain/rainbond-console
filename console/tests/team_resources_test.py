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
from console.views.team_resources import NsResourceDetailView  # noqa: E402
from console.views import team_resources  # noqa: E402
from www.apiclient.regionapi import RegionInvokeApi  # noqa: E402


class HelmReleasesViewTestCase(TestCase):
    def test_post_reuses_parsed_request_data_for_helm_install(self):
        payload = {
            "name": "demo-release",
            "chart_name": "apache",
            "version": "1.0.0",
            "values": {
                "replicaCount": 1
            }
        }
        view = HelmReleasesView()
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

        install_mock.assert_called_once_with("demo-region", "demo-team", payload)
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
            "username": "demo-user",
            "password": "demo-pass"
        }
        view = HelmReleasesView()
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
