# -*- coding: utf-8 -*-
import collections
import json
import os
import sys
from types import ModuleType
from unittest import TestCase, mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from console.services.app_actions import app_deploy as app_deploy_module  # noqa: E402


class MarketServiceSourceUpdateTestCase(TestCase):
    def test_update_service_source_prefers_share_image_when_stale_share_slug_path_exists(self):
        tenant = mock.Mock(tenant_id="tenant-1")
        service = mock.Mock(service_id="service-1")
        service_source = mock.Mock(
            version="1.0.0",
            group_key="group-key",
        )
        service_source.is_install_from_cloud.return_value = False
        service_source.get_market_name.return_value = None

        with mock.patch.object(
                app_deploy_module.service_source_repo,
                "get_service_source",
                return_value=service_source), mock.patch.object(
                    app_deploy_module.service_source_repo,
                    "update_service_source") as update_service_source:
            market_service = app_deploy_module.MarketService(tenant, service, version="1.2.3")
            market_service._update_service_source(
                {
                    "share_image": "registry.example.com/demo/web:1.2.3",
                    "share_slug_path": "/grdata/build/tenant/demo/stale-slug.tgz",
                    "service_image": {
                        "image_url": "registry.example.com/demo/web:1.2.3",
                        "cmd": "",
                    },
                    "service_slug": {
                        "slug_path": "/grdata/build/tenant/demo/stale-slug.tgz",
                        "namespace": "demo-space",
                    },
                    "service_share_uuid": "svc-1+svc-1",
                    "deploy_version": "snapshot-deploy-version",
                },
                version="1.2.3",
                template_updatetime=None,
            )

        kwargs = update_service_source.call_args[1]
        extend_info = json.loads(kwargs["extend_info"])
        self.assertEqual(extend_info["image_url"], "registry.example.com/demo/web:1.2.3")
        self.assertEqual(extend_info["source_service_share_uuid"], "svc-1+svc-1")
        self.assertEqual(extend_info["source_deploy_version"], "snapshot-deploy-version")
        self.assertNotIn("slug_path", extend_info)


# capability_id: console.market-app.manual-build-preserves-port-alias
class MarketServiceBuildBoundaryRegressionTests(TestCase):
    def _market_service(self):
        tenant = mock.Mock(tenant_id="tenant-1", enterprise_id="enterprise-1")
        service = mock.Mock(service_id="service-1", service_alias="grabcd", tenant_id="tenant-1")
        service_source = mock.Mock(version="1.0.0", group_key="group-key")
        service_source.is_install_from_cloud.return_value = False
        service_source.get_market_name.return_value = None
        with mock.patch.object(
                app_deploy_module.service_source_repo,
                "get_service_source",
                return_value=service_source):
            market_service = app_deploy_module.MarketService(tenant, service, version="1.0.0")
        return market_service

    def test_manual_build_at_installed_version_skips_market_property_sync(self):
        tenant = mock.Mock(creater="creator", tenant_id="tenant-1")
        service = mock.Mock(service_source="market", service_id="service-1")
        user = mock.Mock()
        service_source = mock.Mock(version="1.0.0")
        deploy_service = app_deploy_module.AppDeployService()

        with mock.patch.object(app_deploy_module, "check_account_quota", return_value=True), \
                mock.patch.object(
                    app_deploy_module.service_source_repo,
                    "get_service_source",
                    return_value=service_source), \
                mock.patch.object(deploy_service, "pre_deploy_action") as pre_deploy_action, \
                mock.patch.object(deploy_service, "execute", return_value=(200, "success", "event-1")) as execute:
            result = deploy_service.deploy(tenant, service, user, version="1.0.0")

        self.assertEqual((200, "success", "event-1"), result)
        pre_deploy_action.assert_not_called()
        execute.assert_called_once_with(tenant, service, user, "1.0.0", None, oauth_instance=None)

    def test_explicit_new_market_version_runs_property_sync(self):
        tenant = mock.Mock(creater="creator", tenant_id="tenant-1")
        service = mock.Mock(service_source="market", service_id="service-1")
        user = mock.Mock()
        service_source = mock.Mock(version="1.0.0")
        deploy_service = app_deploy_module.AppDeployService()

        with mock.patch.object(app_deploy_module, "check_account_quota", return_value=True), \
                mock.patch.object(
                    app_deploy_module.service_source_repo,
                    "get_service_source",
                    return_value=service_source), \
                mock.patch.object(deploy_service, "pre_deploy_action") as pre_deploy_action, \
                mock.patch.object(deploy_service, "execute", return_value=(200, "success", "event-1")):
            deploy_service.deploy(tenant, service, user, version="1.1.0")

        pre_deploy_action.assert_called_once_with(tenant, service, "1.1.0")

    def test_template_port_alias_is_preserved_during_market_property_sync(self):
        market_service = self._market_service()
        port = {
            "container_port": 8080,
            "port_alias": "WEB",
            "k8s_service_name": "web",
        }

        with mock.patch.object(app_deploy_module.port_repo, "get_by_k8s_service_name", return_value=None):
            market_service.update_port_data(port)

        self.assertEqual("WEB", port["port_alias"])

    def test_existing_port_alias_is_preserved_when_template_omits_it(self):
        market_service = self._market_service()
        port = {
            "container_port": 8080,
            "k8s_service_name": "web",
        }
        existing_port = mock.Mock(port_alias="CUSTOM_WEB")

        with mock.patch.object(app_deploy_module.port_repo, "get_by_k8s_service_name", return_value=None):
            market_service.update_port_data(port, existing_port)

        self.assertEqual("CUSTOM_WEB", port["port_alias"])

    def test_new_port_envs_use_the_resolved_template_alias(self):
        market_service = self._market_service()
        port = {
            "container_port": 8080,
            "port_alias": "WEB",
        }

        envs = market_service._create_envs_4_ports(port)

        self.assertEqual(["WEB_HOST", "WEB_PORT"], [env["attr_name"] for env in envs])

    def test_new_port_envs_keep_the_legacy_default_when_alias_is_missing(self):
        market_service = self._market_service()
        port = {
            "container_port": 8080,
        }

        envs = market_service._create_envs_4_ports(port)

        self.assertEqual(["GRABCD8080_HOST", "GRABCD8080_PORT"], [env["attr_name"] for env in envs])
