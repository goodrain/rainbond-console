# -*- coding: utf-8 -*-
import os
import sys
from types import ModuleType
from unittest.mock import patch

import django
from django.test import SimpleTestCase

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")
django.setup()

from console.services.mcp_query_service import mcp_query_service


class Obj(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class MCPQueryDependencyOpsTests(SimpleTestCase):

    def setUp(self):
        self.user = Obj(
            user_id=1,
            pk=1,
            enterprise_id="eid-1",
            nick_name="admin",
            real_name="Admin User",
            email="admin@example.com",
            is_active=True,
            is_enterprise_admin=True,
        )

        def _get_username():
            return self.user.nick_name

        self.user.get_username = _get_username

        self.team = Obj(
            ID=11,
            tenant_id="team-1",
            tenant_name="demo-team",
            tenant_alias="Demo Team",
            enterprise_id="eid-1",
            namespace="default",
            creater=1,
        )
        self.app = Obj(
            ID=12,
            tenant_id="team-1",
            group_name="demo-app",
            region_name="rainbond",
            note="app-note",
            username="admin",
            governance_mode="KUBERNETES_NATIVE_SERVICE",
            create_time=None,
            update_time=None,
            app_type="rainbond",
            app_store_name="",
            app_store_url="",
            app_template_name="",
            version="",
            logo="",
            k8s_app="demo-k8s-app",
        )
        self.app.to_dict = lambda: {
            "ID": 12,
            "tenant_id": "team-1",
            "group_name": "demo-app",
            "region_name": "rainbond",
            "note": "app-note",
            "username": "admin",
            "governance_mode": "KUBERNETES_NATIVE_SERVICE",
            "app_type": "rainbond",
            "k8s_app": "demo-k8s-app",
        }

        self.service = Obj(
            service_id="svc-1",
            tenant_id="team-1",
            service_region="rainbond",
            service_alias="alias-1",
            service_cname="component-1",
            service_source="docker_image",
            create_status="complete",
            min_memory=128,
            min_node=1,
            image="nginx:1.25",
            version="1.25",
            arch="amd64",
            service_type="web",
        )
        self.service.to_dict = lambda: {
            "service_id": "svc-1",
            "tenant_id": "team-1",
            "service_region": "rainbond",
            "service_alias": "alias-1",
            "service_cname": "component-1",
            "service_source": "docker_image",
            "create_status": "complete",
            "min_memory": 128,
            "min_node": 1,
            "image": "nginx:1.25",
            "version": "1.25",
        }
        self.service.save = lambda: None
        self.region = Obj(region_name="rainbond", enterprise_id="eid-1")
        self.relations = [Obj(service_id="svc-1")]

        team_patcher = patch(
            "console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name",
            return_value=self.team,
        )
        region_patcher = patch(
            "console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name",
            return_value=self.region,
        )
        app_patcher = patch(
            "console.services.mcp_query_service.group_service.get_app_by_id",
            return_value=self.app,
        )
        service_patcher = patch(
            "console.services.mcp_query_service.service_repo.get_service_by_service_id",
            return_value=self.service,
        )
        relation_patcher = patch(
            "console.services.mcp_query_service.group_service_relation_repo.get_services_by_group",
            return_value=self.relations,
        )

        self.mock_get_team = team_patcher.start()
        self.mock_get_region = region_patcher.start()
        self.mock_get_app = app_patcher.start()
        self.mock_get_service = service_patcher.start()
        self.mock_get_relations = relation_patcher.start()

        self.addCleanup(team_patcher.stop)
        self.addCleanup(region_patcher.stop)
        self.addCleanup(app_patcher.stop)
        self.addCleanup(service_patcher.stop)
        self.addCleanup(relation_patcher.stop)

    # capability_id: console.component.dependency-add
    @patch("console.services.mcp_query_service.dependency_service.add_service_dependency")
    def test_add_single_dependency_success(self, mock_add_dependency):
        dependency = Obj(service_id="svc-2", dep_service_id="svc-2")
        dependency.to_dict = lambda: {"service_id": "svc-2", "dep_service_id": "svc-2"}
        mock_add_dependency.return_value = (200, "ok", dependency)

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_manage_component_dependency",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "service_id": "svc-1",
                "operation": "add",
                "dep_service_id": "svc-2",
            },
        )

        self.assertTrue(result["created"])
        self.assertEqual(result["dependency"]["service_id"], "svc-2")
        mock_add_dependency.assert_called_once()

    # capability_id: console.component.dependency-add
    @patch("console.services.mcp_query_service.dependency_service.add_service_dependency")
    def test_add_single_dependency_requires_open_inner(self, mock_add_dependency):
        port_list = [3306, 6379]
        mock_add_dependency.return_value = (201, "open inner", port_list)

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_manage_component_dependency",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "service_id": "svc-1",
                "operation": "add",
                "dep_service_id": "svc-2",
            },
        )

        self.assertFalse(result["created"])
        self.assertTrue(result["requires_open_inner"])
        self.assertEqual(result["port_list"], port_list)
        self.assertEqual(result["message"], "open inner")

    # capability_id: console.component.dependency-add-batch
    @patch("console.services.mcp_query_service.dependency_service.patch_add_dependency")
    def test_add_batch_dependencies_success(self, mock_patch_add):
        mock_patch_add.return_value = (200, "bulk ok")
        dep_ids = ["svc-2", "svc-3"]

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_manage_component_dependency",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "service_id": "svc-1",
                "operation": "add",
                "dep_service_ids": dep_ids,
            },
        )

        self.assertTrue(result["created"])
        self.assertEqual(result["dep_service_ids"], dep_ids)
        mock_patch_add.assert_called_once_with(self.team, self.service, dep_ids, self.user.nick_name)

    # capability_id: console.component.dependency-add-reverse
    @patch("console.services.mcp_query_service.dependency_service.patch_add_service_reverse_dependency")
    def test_add_reverse_dependencies_success(self, mock_patch_reverse):
        data = [
            {"tenant_id": "team-1", "service_id": "svc-2"},
            {"tenant_id": "team-1", "service_id": "svc-3"},
        ]
        mock_patch_reverse.return_value = data
        source_ids = ["svc-2", "svc-3"]

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_manage_component_dependency",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "service_id": "svc-1",
                "operation": "add_reverse",
                "be_dep_service_ids": source_ids,
            },
        )

        self.assertTrue(result["created"])
        self.assertEqual(result["items"], data)
        self.assertEqual(result["total"], len(data))
        mock_patch_reverse.assert_called_once_with(self.team, self.service, ",".join(source_ids), self.user.nick_name)

    # capability_id: console.component.dependency-delete
    @patch("console.services.mcp_query_service.dependency_service.delete_service_dependency")
    def test_delete_dependency_success(self, mock_delete_dependency):
        dependency = Obj(service_id="svc-2", dep_service_id="svc-2")
        dependency.to_dict = lambda: {"service_id": "svc-2", "dep_service_id": "svc-2"}
        mock_delete_dependency.return_value = (200, "deleted", dependency)

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_manage_component_dependency",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "service_id": "svc-1",
                "operation": "delete",
                "dep_service_id": "svc-2",
            },
        )

        self.assertTrue(result["deleted"])
        self.assertEqual(result["dependency"]["service_id"], "svc-2")
        mock_delete_dependency.assert_called_once_with(self.team, self.service, "svc-2", self.user.nick_name)
