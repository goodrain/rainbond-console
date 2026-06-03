# -*- coding: utf-8 -*-
import os
import sys
import importlib
from types import ModuleType
from unittest import mock
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402
from django.test import SimpleTestCase  # noqa: E402

django.setup()


class Obj(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class MarketAppServiceCreateRainbondAppTests(SimpleTestCase):
    def create_rainbond_app(self, market_app_service, enterprise_id, app_info, app_id):
        return market_app_service.create_rainbond_app.__wrapped__(
            market_app_service, enterprise_id, app_info, app_id)

    # capability_id: console.market-app.create-template-scope-name
    def test_create_rainbond_app_allows_enterprise_template_named_like_team_snapshot(self):
        from console.services.market_app_service import market_app_service

        existing_team_snapshot = Obj(app_name="demo-app", enterprise_id="eid-1", scope="team", create_team="demo-team")

        class QuerySet(object):
            def __init__(self, first_result):
                self.first_result = first_result

            def first(self):
                return self.first_result

        class Manager(object):
            def __init__(self):
                self.calls = []

            def filter(self, **kwargs):
                self.calls.append(kwargs)
                if kwargs.get("enterprise_id") == "eid-1" and kwargs.get("scope") == "enterprise":
                    return QuerySet(None)
                return QuerySet(existing_team_snapshot)

        manager = Manager()

        def build_app(**kwargs):
            return Obj(save=mock.Mock(), **kwargs)

        app_info = {
            "app_name": "demo-app",
            "create_user": 7,
            "create_team": "demo-team",
            "pic": "",
            "source": "local",
            "dev_status": "",
            "scope": "enterprise",
            "describe": "publish snapshot to internal library",
            "details": "",
            "tag_ids": [],
        }

        with mock.patch("console.services.market_app_service.RainbondCenterApp") as app_model, \
                mock.patch("console.services.market_app_service.app_tag_repo.create_app_tags_relation"):
            app_model.objects = manager
            app_model.side_effect = build_app

            created = self.create_rainbond_app(market_app_service, "eid-1", app_info, "enterprise-app-id")

        self.assertIsNotNone(created)
        self.assertEqual(created.scope, "enterprise")
        self.assertEqual(created.app_name, "demo-app")
        self.assertEqual(manager.calls[0], {
            "app_name": "demo-app",
            "enterprise_id": "eid-1",
            "scope": "enterprise",
        })

    # capability_id: console.market-app.create-template-scope-name
    def test_create_rainbond_app_rejects_duplicate_enterprise_template_name_in_same_enterprise(self):
        from console.services.market_app_service import market_app_service

        existing_enterprise_template = Obj(
            app_name="demo-app", enterprise_id="eid-1", scope="enterprise", create_team="demo-team")
        duplicate_query = mock.Mock()
        duplicate_query.first.return_value = existing_enterprise_template

        app_info = {
            "app_name": "demo-app",
            "create_user": 7,
            "create_team": "demo-team",
            "pic": "",
            "source": "local",
            "dev_status": "",
            "scope": "enterprise",
            "describe": "duplicate enterprise template",
            "details": "",
            "tag_ids": [],
        }

        with mock.patch("console.services.market_app_service.RainbondCenterApp") as app_model:
            app_model.objects.filter.return_value = duplicate_query

            created = self.create_rainbond_app(market_app_service, "eid-1", app_info, "enterprise-app-id")

        self.assertIsNone(created)
        app_model.assert_not_called()

    # capability_id: console.market-app.create-template-scope-name
    def test_create_rainbond_app_rejects_duplicate_team_template_name_in_same_team(self):
        from console.services.market_app_service import market_app_service

        existing_team_template = Obj(app_name="demo-app", enterprise_id="eid-1", scope="team", create_team="demo-team")
        duplicate_query = mock.Mock()
        duplicate_query.filter.return_value = duplicate_query
        duplicate_query.first.return_value = existing_team_template

        app_info = {
            "app_name": "demo-app",
            "create_user": 7,
            "create_team": "demo-team",
            "pic": "",
            "source": "local",
            "dev_status": "",
            "scope": "team",
            "describe": "duplicate team template",
            "details": "",
            "tag_ids": [],
        }

        with mock.patch("console.services.market_app_service.RainbondCenterApp") as app_model:
            app_model.objects.filter.return_value = duplicate_query

            created = self.create_rainbond_app(market_app_service, "eid-1", app_info, "team-app-id")

        self.assertIsNone(created)
        app_model.objects.filter.assert_called_once_with(app_name="demo-app", enterprise_id="eid-1", scope="team")
        duplicate_query.filter.assert_called_once_with(create_team="demo-team")
        app_model.assert_not_called()

    # capability_id: console.market-app.create-template-scope-name
    def test_create_rainbond_app_allows_team_template_named_like_another_team_snapshot(self):
        from console.services.market_app_service import market_app_service

        existing_other_team_template = Obj(
            app_name="demo-app", enterprise_id="eid-1", scope="team", create_team="other-team")
        duplicate_query = mock.Mock()
        duplicate_query.first.return_value = existing_other_team_template
        target_team_query = mock.Mock()
        target_team_query.first.return_value = None
        duplicate_query.filter.return_value = target_team_query

        def build_app(**kwargs):
            return Obj(save=mock.Mock(), **kwargs)

        app_info = {
            "app_name": "demo-app",
            "create_user": 7,
            "create_team": "target-team",
            "pic": "",
            "source": "local",
            "dev_status": "",
            "scope": "team",
            "describe": "publish snapshot to another team",
            "details": "",
            "tag_ids": [],
        }

        with mock.patch("console.services.market_app_service.RainbondCenterApp") as app_model, \
                mock.patch("console.services.market_app_service.app_tag_repo.create_app_tags_relation"):
            app_model.objects.filter.return_value = duplicate_query
            app_model.side_effect = build_app

            created = self.create_rainbond_app(market_app_service, "eid-1", app_info, "team-app-id")

        self.assertIsNotNone(created)
        self.assertEqual(created.scope, "team")
        self.assertEqual(created.create_team, "target-team")
        app_model.objects.filter.assert_called_once_with(app_name="demo-app", enterprise_id="eid-1", scope="team")
        duplicate_query.filter.assert_called_once_with(create_team="target-team")
        target_team_query.first.assert_called_once_with()


class MarketAppServicePortPersistenceTests(SimpleTestCase):

    @patch("console.services.market_app_service.group_repo.get_by_service_id")
    @patch("console.services.market_app_service.MarketAppService._MarketAppService__handle_k8s_service_name")
    def test_handle_service_connect_info_tracks_resolved_names_per_port(
            self, mock_handle_k8s_service_name, mock_get_group_by_service_id):
        from console.enum.app import GovernanceModeEnum
        from console.services.market_app_service import market_app_service

        mock_get_group_by_service_id.return_value = Obj(
            governance_mode=GovernanceModeEnum.KUBERNETES_NATIVE_SERVICE.name
        )
        mock_handle_k8s_service_name.side_effect = ["java-maven-demo-gray", "java-maven-demo-gray-admin"]

        tenant = Obj(tenant_id="tenant-1")
        service = Obj(service_id="service-1", service_alias="gr123456")
        ports = [
            {
                "container_port": 5000,
                "port_alias": "WEB",
                "is_inner_service": True,
                "k8s_service_name": "java-maven-demo",
            },
            {
                "container_port": 5001,
                "port_alias": "ADMIN",
                "is_inner_service": True,
                "k8s_service_name": "java-maven-demo-admin",
            },
        ]

        port_k8s_svc_name, outer_envs = market_app_service._MarketAppService__handle_service_connect_info(
            tenant, service, ports, []
        )

        self.assertEqual({
            "service-1:5000": "java-maven-demo-gray",
            "service-1:5001": "java-maven-demo-gray-admin",
        }, port_k8s_svc_name)
        env_map = {env["attr_name"]: env["attr_value"] for env in outer_envs}
        self.assertEqual("java-maven-demo-gray", env_map["WEB_HOST"])
        self.assertEqual(5000, env_map["WEB_PORT"])
        self.assertEqual("java-maven-demo-gray-admin", env_map["ADMIN_HOST"])
        self.assertEqual(5001, env_map["ADMIN_PORT"])

    @patch("console.services.market_app_service.port_repo.bulk_create")
    def test_save_port_uses_resolved_k8s_service_names(self, mock_bulk_create):
        from console.services.market_app_service import market_app_service

        tenant = Obj(tenant_id="tenant-1")
        region = Obj(region_id="region-1")
        service = Obj(tenant_id="tenant-1", service_id="service-1", service_alias="gr123456")
        ports = [
            {
                "container_port": 5000,
                "protocol": "http",
                "port_alias": "WEB",
                "is_inner_service": True,
                "is_outer_service": False,
                "k8s_service_name": "java-maven-demo",
            },
            {
                "container_port": 5001,
                "protocol": "http",
                "port_alias": "ADMIN",
                "is_inner_service": True,
                "is_outer_service": False,
                "k8s_service_name": "java-maven-demo-admin",
            },
        ]

        market_app_service._MarketAppService__save_port(
            tenant=tenant,
            region=region,
            service=service,
            ports=ports,
            port_k8s_svc_name={
                "service-1:5000": "java-maven-demo-gray",
                "service-1:5001": "java-maven-demo-gray-admin",
            },
            app_id="app-1",
            skip_create_domain=True,
        )

        created_ports = mock_bulk_create.call_args[0][0]
        self.assertEqual(["java-maven-demo-gray", "java-maven-demo-gray-admin"],
                         [port.k8s_service_name for port in created_ports])


class MarketAppServiceVMGuardTests(SimpleTestCase):
    def test_market_app_service_imports_with_app_version_service(self):
        sys.modules.pop("console.services.market_app_service", None)
        sys.modules.pop("console.services.app_version_service", None)

        market_app_service_module = importlib.import_module("console.services.market_app_service")
        app_version_service_module = importlib.import_module("console.services.app_version_service")

        self.assertTrue(hasattr(market_app_service_module, "market_app_service"))
        self.assertTrue(hasattr(app_version_service_module, "app_version_service"))

    # capability_id: console.market-app.vm-runtime-status-guard
    def test_install_app_rejects_vm_template_when_vm_plugin_not_running(self):
        from console.exception.main import ServiceHandleException
        from console.services.market_app_service import market_app_service

        tenant = Obj(tenant_id="tenant-1", tenant_name="demo-team", enterprise_id="eid")
        region = Obj(region_name="demo-region")
        user = Obj(enterprise_id="eid", nick_name="tester")
        app = Obj(ID=7, governance_mode="KUBERNETES_NATIVE_SERVICE", app_id="app-7")
        market_app = Obj(app_id="model-1", app_name="vm-template")
        app_template = {
            "apps": [
                {
                    "service_cname": "vm-service",
                    "service_type": "vm",
                }
            ]
        }

        with patch("console.services.market_app_service.group_repo.get_group_by_id", return_value=app), \
                patch.object(market_app_service, "get_app_template", return_value=(app_template, market_app)), \
                patch("console.services.market_app_service.region_api.get_cluster_nodes_arch",
                      return_value=(None, {"list": ["amd64"]})), \
                patch("console.services.market_app_service.vms.ensure_vm_platform_running",
                      side_effect=ServiceHandleException(
                          msg="vm plugin not running",
                          msg_show="虚拟机功能未正常运行，不允许执行虚拟机相关操作",
                          status_code=412,
                      )) as ensure_guard:
            with self.assertRaises(ServiceHandleException) as context:
                market_app_service.install_app(
                    tenant,
                    region,
                    user,
                    7,
                    "model-1",
                    "1.0.0",
                    None,
                    False,
                    False,
                    False,
                )

        ensure_guard.assert_called_once_with("eid", "demo-region")
        self.assertEqual(412, context.exception.status_code)
        self.assertEqual("虚拟机功能未正常运行，不允许执行虚拟机相关操作", context.exception.msg_show)
