# -*- coding: utf-8 -*-
import os
import sys
from types import ModuleType
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django
from django.test import SimpleTestCase

django.setup()

from console.services.app_config.network_policy_dependency_sync_service import NetworkPolicyDependencySyncService

SYNC_SERVICE_PATH = "console.services.app_config.network_policy_dependency_sync_service"


class Obj(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class NetworkPolicyDependencySyncServiceTests(SimpleTestCase):

    @patch(SYNC_SERVICE_PATH + ".region_api.sync_security_center_network_policy_dependencies")
    @patch(SYNC_SERVICE_PATH + ".port_repo.list_inner_ports")
    @patch(SYNC_SERVICE_PATH + ".service_repo.get_services_by_service_ids")
    @patch(SYNC_SERVICE_PATH + ".dep_relation_repo.get_service_reverse_dependencies")
    @patch(SYNC_SERVICE_PATH + ".dep_relation_repo.get_service_dependencies")
    def test_sync_component_builds_dependency_rules_from_current_relations(
            self,
            mock_get_dependencies,
            mock_get_reverse_dependencies,
            mock_get_services_by_ids,
            mock_list_inner_ports,
            mock_sync,
    ):
        tenant = Obj(tenant_id="team-1", tenant_name="demo-team")
        service = Obj(
            tenant_id="team-1",
            service_id="svc-a",
            service_alias="api",
            service_region="rainbond",
        )
        dep_service = Obj(service_id="svc-b", service_alias="mysql", service_cname="mysql")
        source_service = Obj(service_id="svc-c", service_alias="web", service_cname="web")

        mock_get_dependencies.return_value = [Obj(dep_service_id="svc-b")]
        mock_get_reverse_dependencies.return_value = [Obj(service_id="svc-c")]
        mock_get_services_by_ids.return_value = [dep_service, source_service]

        def list_inner_ports(_tenant_id, service_id):
            if service_id == "svc-a":
                return [Obj(container_port=8080)]
            if service_id == "svc-b":
                return [Obj(container_port=3306), Obj(container_port=3306)]
            return []

        mock_list_inner_ports.side_effect = list_inner_ports

        NetworkPolicyDependencySyncService().sync_component(tenant, service)

        mock_sync.assert_called_once()
        _, region_name, query, payload = mock_sync.call_args[0]
        self.assertEqual(region_name, "rainbond")
        self.assertEqual(query["team_name"], "demo-team")
        self.assertEqual(query["region_name"], "rainbond")
        self.assertEqual(query["service_alias"], "api")
        self.assertEqual(query["service_id"], "svc-a")
        self.assertEqual(payload["outbound_rules"], [{
            "peer": "svc-b",
            "port": 3306,
            "origin": "依赖自动生成",
            "removable": False,
        }])
        self.assertEqual(payload["inbound_rules"], [{
            "peer": "svc-c",
            "port": 8080,
            "origin": "依赖自动生成",
            "removable": False,
        }])

    @patch(SYNC_SERVICE_PATH + ".logger")
    @patch(SYNC_SERVICE_PATH + ".region_api.sync_security_center_network_policy_dependencies")
    @patch(SYNC_SERVICE_PATH + ".port_repo.list_inner_ports", return_value=[])
    @patch(SYNC_SERVICE_PATH + ".service_repo.get_services_by_service_ids", return_value=[])
    @patch(SYNC_SERVICE_PATH + ".dep_relation_repo.get_service_reverse_dependencies", return_value=[])
    @patch(SYNC_SERVICE_PATH + ".dep_relation_repo.get_service_dependencies", return_value=[])
    def test_sync_after_dependency_change_logs_and_does_not_raise_when_plugin_unavailable(
            self,
            _mock_get_dependencies,
            _mock_get_reverse_dependencies,
            _mock_get_services_by_ids,
            _mock_list_inner_ports,
            mock_sync,
            mock_logger,
    ):
        tenant = Obj(tenant_id="team-1", tenant_name="demo-team")
        service = Obj(
            tenant_id="team-1",
            service_id="svc-a",
            service_alias="api",
            service_region="rainbond",
        )
        mock_sync.side_effect = RuntimeError("plugin unavailable")

        NetworkPolicyDependencySyncService().sync_after_dependency_change(tenant, service, "svc-b")

        mock_logger.warning.assert_called()
