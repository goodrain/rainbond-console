# -*- coding: utf-8 -*-
import collections
import json
import os
import sys
import threading
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
from console.services.app_actions import properties_changes as properties_changes_module  # noqa: E402


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


class LegacyMarketPortUpgradeTests(TestCase):
    def _market_service(self):
        tenant = mock.Mock(tenant_id="tenant-1", tenant_name="team-1", enterprise_id="enterprise-1")
        service = mock.Mock(
            service_id="service-1",
            service_alias="grabcd",
            service_region="region-1",
            tenant_id="tenant-1",
        )
        service_source = mock.Mock(version="1.0.0", group_key="group-key")
        service_source.is_install_from_cloud.return_value = False
        service_source.get_market_name.return_value = None
        with mock.patch.object(
                app_deploy_module.service_source_repo,
                "get_service_source",
                return_value=service_source):
            return app_deploy_module.MarketService(tenant, service, version="1.0.0")

    def test_port_changes_preserves_legacy_defaults_and_does_not_close_existing_port(self):
        changes = properties_changes_module.PropertiesChanges.__new__(properties_changes_module.PropertiesChanges)
        changes.service = mock.Mock(tenant_id="tenant-1", service_id="service-1")
        existing_port = mock.Mock(container_port=5000, is_inner_service=True, is_outer_service=False)

        ports = [
            {"container_port": 5000},
            {"container_port": 5001},
            {"container_port": 5002, "is_inner_service": "false", "is_outer_service": 0},
            {"container_port": 5003, "is_inner_service": False, "is_outer_service": True},
        ]

        with mock.patch.object(properties_changes_module.port_repo, "get_service_ports", return_value=[existing_port]):
            result = changes.port_changes(ports)

        self.assertEqual([5001, 5002, 5003], [port["container_port"] for port in result["add"]])
        self.assertNotIn("upd", result)
        self.assertEqual([(False, False), (False, False), (True, True)], [
            (port["is_inner_service"], port["is_outer_service"]) for port in result["add"]
        ])

    def test_port_upgrade_preserves_existing_k8s_name_and_syncs_inner_service_envs(self):
        market_service = self._market_service()
        existing_port = mock.Mock(
            port_alias="WEB",
            k8s_service_name="web-ab12",
            is_inner_service=False,
            is_outer_service=True,
        )
        changes = {
            "upd": [{
                "container_port": 8080,
                "protocol": "http",
                "port_alias": "WEB",
                "k8s_service_name": "web",
                "is_inner_service": True,
                "is_outer_service": True,
            }]
        }

        with mock.patch.object(
                app_deploy_module.port_repo,
                "get_service_port_by_port",
                return_value=existing_port), mock.patch.object(
                    app_deploy_module.port_repo,
                    "get_by_k8s_service_name",
                    return_value=mock.Mock(service_id="other-service")), mock.patch.object(
                        app_deploy_module.port_repo,
                        "update") as update_port, mock.patch.object(
                            app_deploy_module,
                            "make_uuid",
                            side_effect=["0000fcbb", "0000b1f6"]), mock.patch.object(
                                app_deploy_module.env_var_repo,
                                "get_by_attr_name_and_scope",
                                return_value=None), mock.patch.object(
                                    app_deploy_module.env_var_service,
                                    "create_env_var") as create_env_var, mock.patch.object(
                                        app_deploy_module.region_api,
                                        "add_service_port"), mock.patch.object(
                                        app_deploy_module.region_api,
                                        "update_service_port") as sync_ports, mock.patch.object(
                                        app_deploy_module.region_api,
                                        "add_service_env") as sync_env:
            market_service._update_ports(changes)
            market_service._sync_ports(changes)

        self.assertEqual("web-ab12", update_port.call_args.kwargs["k8s_service_name"])
        self.assertEqual("web-ab12", sync_ports.call_args.args[3]["port"][0]["k8s_service_name"])
        self.assertEqual(["WEB_HOST", "WEB_PORT"], [
            call.args[3] for call in create_env_var.call_args_list
        ])
        self.assertEqual(["WEB_HOST", "WEB_PORT"], [
            call.args[3]["attr_name"] for call in sync_env.call_args_list
        ])
        self.assertEqual([8080, 8080], [call.args[1] for call in create_env_var.call_args_list])
        self.assertEqual(["127.0.0.1", "8080"], [call.args[4] for call in create_env_var.call_args_list])

    def test_new_port_envs_are_port_scoped_and_sync_without_type_errors(self):
        market_service = self._market_service()
        changes = {
            "add": [{
                "container_port": 8080,
                "protocol": "http",
                "port_alias": "WEB",
                "k8s_service_name": "web",
                "is_inner_service": True,
                "is_outer_service": False,
            }]
        }

        with mock.patch.object(
                app_deploy_module.port_repo,
                "get_by_k8s_service_name",
                return_value=None), mock.patch.object(
                    app_deploy_module.port_repo,
                    "add_service_port"), mock.patch.object(
                        app_deploy_module.env_var_repo,
                        "get_by_attr_name_and_scope",
                        return_value=None), mock.patch.object(
                            app_deploy_module.env_var_service,
                            "create_env_var") as create_env_var, mock.patch.object(
                                app_deploy_module.region_api,
                                "add_service_port"), mock.patch.object(
                                    app_deploy_module.region_api,
                                    "update_service_port"), mock.patch.object(
                                        app_deploy_module.region_api,
                                        "add_service_env") as sync_env:
            market_service._update_ports(changes)
            market_service._sync_ports(changes)

        self.assertEqual([8080, 8080], [call.args[1] for call in create_env_var.call_args_list])
        self.assertEqual(["127.0.0.1", "8080"], [call.args[4] for call in create_env_var.call_args_list])
        self.assertEqual([8080, 8080], [call.args[3]["container_port"] for call in sync_env.call_args_list])

    def test_port_upgrade_keeps_existing_outer_envs_unchanged(self):
        market_service = self._market_service()
        existing_port = mock.Mock(
            port_alias="WEB",
            k8s_service_name="web-ab12",
            is_inner_service=False,
            is_outer_service=True,
        )
        changes = {
            "upd": [{
                "container_port": 8080,
                "protocol": "http",
                "port_alias": "WEB",
                "is_inner_service": True,
                "is_outer_service": True,
            }]
        }

        with mock.patch.object(
                app_deploy_module.port_repo,
                "get_service_port_by_port",
                return_value=existing_port), mock.patch.object(
                    app_deploy_module.port_repo,
                    "update"), mock.patch.object(
                        app_deploy_module.env_var_repo,
                        "get_by_attr_name_and_scope",
                        return_value=mock.Mock(attr_value="user-value")), mock.patch.object(
                            app_deploy_module.env_var_service,
                            "create_env_var") as create_env_var, mock.patch.object(
                                app_deploy_module.region_api,
                                "add_service_port"), mock.patch.object(
                                    app_deploy_module.region_api,
                                    "update_service_port"), mock.patch.object(
                                        app_deploy_module.region_api,
                                        "add_service_env") as sync_env:
            market_service._update_ports(changes)
            market_service._sync_ports(changes)

        create_env_var.assert_not_called()
        sync_env.assert_not_called()


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
        execute.assert_called_once_with(
            tenant,
            service,
            user,
            "1.0.0",
            None,
            oauth_instance=None,
            impl=mock.ANY,
        )
        self.assertIsInstance(execute.call_args[1]["impl"], app_deploy_module.OtherService)

    def test_explicit_new_market_version_runs_property_sync(self):
        tenant = mock.Mock(creater="creator", tenant_id="tenant-1")
        service = mock.Mock(service_source="market", service_id="service-1")
        user = mock.Mock()
        service_source = mock.Mock(version="1.0.0")
        deploy_service = app_deploy_module.AppDeployService()
        market_impl = mock.Mock()

        with mock.patch.object(app_deploy_module, "check_account_quota", return_value=True), \
                mock.patch.object(
                    app_deploy_module.service_source_repo,
                    "get_service_source",
                    return_value=service_source), \
                mock.patch.object(
                    deploy_service,
                    "pre_deploy_action",
                    return_value=market_impl) as pre_deploy_action, \
                mock.patch.object(
                    deploy_service,
                    "execute",
                    return_value=(200, "success", "event-1")) as execute:
            deploy_service.deploy(tenant, service, user, version="1.1.0")

        pre_deploy_action.assert_called_once_with(tenant, service, "1.1.0")
        execute.assert_called_once_with(
            tenant,
            service,
            user,
            "1.1.0",
            None,
            oauth_instance=None,
            impl=market_impl,
        )

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


class AppDeployConcurrencyTestCase(TestCase):
    def test_concurrent_market_upgrade_and_ordinary_build_keep_their_own_actions(self):
        deploy_service = app_deploy_module.AppDeployService()
        market_tenant = mock.Mock(creater="market-creator")
        ordinary_tenant = mock.Mock(creater="ordinary-creator")
        market_service = mock.Mock(service_id="market-service", service_source="market")
        ordinary_service = mock.Mock(service_id="ordinary-service", service_source="source_code")
        user = mock.Mock()

        market_pre_action_started = threading.Event()
        release_market_pre_action = threading.Event()
        fake_market_strategy = mock.Mock()

        def wait_while_ordinary_build_runs():
            market_pre_action_started.set()
            release_market_pre_action.wait(2)

        fake_market_strategy.pre_action.side_effect = wait_while_ordinary_build_runs
        fake_market_strategy.get_async_action.return_value = app_deploy_module.AsyncAction.UPDATE.value

        results = {}
        errors = []

        def run_deploy(result_key, tenant, service, version):
            try:
                results[result_key] = deploy_service.deploy(tenant, service, user, version)
            except BaseException as exc:  # pragma: no cover - surfaced by the assertion below
                errors.append(exc)

        with mock.patch.object(app_deploy_module, "check_account_quota", return_value=True), \
                mock.patch.object(
                    deploy_service,
                    "_should_sync_market_properties",
                    side_effect=lambda service, version: service is market_service), \
                mock.patch.object(
                    app_deploy_module,
                    "MarketService",
                    return_value=fake_market_strategy), \
                mock.patch.object(
                    app_deploy_module.app_manage_service,
                    "deploy",
                    side_effect=lambda tenant, service, user, oauth_instance=None:
                    (200, "success", "build-{}".format(service.service_id))) as deploy, \
                mock.patch.object(
                    app_deploy_module.app_manage_service,
                    "upgrade",
                    side_effect=lambda tenant, service, user, committer_name, oauth_instance=None:
                    (200, "success", "update-{}".format(service.service_id))) as upgrade:
            market_thread = threading.Thread(
                target=run_deploy,
                args=("market", market_tenant, market_service, "2.0.0"),
            )
            market_thread.start()
            self.assertTrue(market_pre_action_started.wait(1))

            ordinary_thread = threading.Thread(
                target=run_deploy,
                args=("ordinary", ordinary_tenant, ordinary_service, None),
            )
            ordinary_thread.start()
            ordinary_thread.join(2)
            self.assertFalse(ordinary_thread.is_alive())

            release_market_pre_action.set()
            market_thread.join(2)
            self.assertFalse(market_thread.is_alive())

        self.assertEqual([], errors)
        self.assertEqual((200, "success", "build-ordinary-service"), results["ordinary"])
        self.assertEqual((200, "success", "update-market-service"), results["market"])
        deploy.assert_called_once_with(ordinary_tenant, ordinary_service, user, oauth_instance=None)
        upgrade.assert_called_once_with(market_tenant, market_service, user, None, oauth_instance=None)
