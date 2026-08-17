# -*- coding: utf-8 -*-
import collections
import os
import sys
from contextlib import ExitStack
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

from console.services import team_services as team_module  # noqa: E402


class Obj(object):

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def to_dict(self):
        return dict(self.__dict__)


class EnterpriseTeamsQueryScopeTest(TestCase):

    def setUp(self):
        self.service = team_module.TeamService()
        self.teams = [
            Obj(ID=11, tenant_id="team-1", tenant_name="team-one", tenant_alias="Team One", namespace="ns-one", creater=1),
            Obj(ID=12, tenant_id="team-2", tenant_name="team-two", tenant_alias="Team Two", namespace="ns-two", creater=2),
        ]

    def test_jg_teams_scopes_expensive_queries_to_paginated_teams(self):
        permission_queryset = mock.MagicMock()
        permission_values = mock.MagicMock()
        permission_values.__iter__.return_value = iter([
            {"tenant_id": 11, "user_id": 1},
            {"tenant_id": 11, "user_id": 2},
            {"tenant_id": 12, "user_id": 3},
        ])
        permission_values.annotate.return_value = [
            {"tenant_id": 11, "user_number": 2},
            {"tenant_id": 12, "user_number": 1},
        ]
        permission_queryset.values.return_value = permission_values

        component_queryset = mock.MagicMock()
        component_queryset.__iter__.return_value = iter([
            Obj(tenant_id="team-1", service_id="service-1"),
            Obj(tenant_id="team-2", service_id="service-2"),
        ])
        component_queryset.values_list.return_value = [
            ("service-1", "team-1"),
            ("service-2", "team-2"),
        ]

        tenant_region_queryset = mock.MagicMock()
        tenant_region_queryset.values.return_value = [
            {"tenant_id": "team-1", "region_name": "region-a"},
            {"tenant_id": "team-2", "region_name": "region-a"},
        ]

        permission_manager = mock.MagicMock()
        permission_manager.filter.return_value = permission_queryset
        component_manager = mock.MagicMock()
        component_manager.filter.return_value = component_queryset
        tenant_region_manager = mock.MagicMock()
        tenant_region_manager.filter.return_value = tenant_region_queryset

        users = [Obj(user_id=1, get_name=lambda: "Owner One"), Obj(user_id=2, get_name=lambda: "Owner Two")]
        volumes = [
            Obj(service_id="service-1", volume_type="share-file", volume_capacity=20),
            Obj(service_id="service-1", volume_type="config-file", volume_capacity=100),
            Obj(service_id="service-2", volume_type="local", volume_capacity=0),
        ]
        region = Obj(region_name="region-a", region_alias="Region A", region_id="region-id-a")
        region_resources = [
            {"UUID": "team-1", "LimitMemory": 4096, "LimitCPU": 4, "memory_limit": 1024, "cpu_limit": 1},
            {"UUID": "team-2", "LimitMemory": 8192, "LimitCPU": 8, "memory_limit": 2048, "cpu_limit": 2},
        ]

        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(team_module.PermRelTenant, "objects", permission_manager))
            stack.enter_context(mock.patch.object(team_module.TenantServiceInfo, "objects", component_manager))
            stack.enter_context(mock.patch.object(team_module.TenantRegionInfo, "objects", tenant_region_manager))
            stack.enter_context(mock.patch.object(team_module.user_repo, "get_by_user_ids", return_value=users))
            volume_mock = stack.enter_context(
                mock.patch.object(team_module.volume_repo, "get_services_volumes", return_value=volumes))
            stack.enter_context(
                mock.patch.object(team_module.team_repo, "get_team_region_names", return_value=["region-a"]))
            region_mock = stack.enter_context(
                mock.patch.object(team_module.region_repo, "get_region_by_region_names", return_value=[region]))
            resources_mock = stack.enter_context(
                mock.patch.object(self.service, "get_region_tenant", return_value=region_resources))
            stack.enter_context(mock.patch.object(team_module.os, "getenv", return_value=None))

            result = list(self.service.jg_teams("enterprise-1", self.teams))

        permission_manager.filter.assert_called_once_with(tenant_id__in=[11, 12])
        permission_values.annotate.assert_called_once()
        component_manager.filter.assert_called_once_with(tenant_id__in=["team-1", "team-2"])
        tenant_region_manager.filter.assert_called_once_with(tenant_id__in=["team-1", "team-2"])
        volume_mock.assert_called_once_with(["service-1", "service-2"])
        region_mock.assert_called_once_with(["region-a"])
        resources_mock.assert_called_once_with("enterprise-1", "region-a", ["team-1", "team-2"])
        self.assertEqual(result[0]["user_number"], 2)
        self.assertEqual(result[0]["storage_request"], 20)
        self.assertEqual(result[1]["storage_request"], 10)
        self.assertEqual(result[1]["memory_request"], 2048)

    def test_jg_teams_returns_empty_without_global_queries(self):
        with ExitStack() as stack:
            permission_mock = stack.enter_context(mock.patch.object(team_module.PermRelTenant.objects, "filter"))
            component_mock = stack.enter_context(mock.patch.object(team_module.TenantServiceInfo.objects, "filter"))
            volume_mock = stack.enter_context(mock.patch.object(team_module.volume_repo, "get_services_volumes"))
            tenant_region_mock = stack.enter_context(mock.patch.object(team_module.TenantRegionInfo.objects, "filter"))

            result = list(self.service.jg_teams("enterprise-1", []))

        self.assertEqual(result, [])
        permission_mock.assert_not_called()
        component_mock.assert_not_called()
        volume_mock.assert_not_called()
        tenant_region_mock.assert_not_called()

    def test_jg_teams_uses_region_config_order_and_skips_orphan_relations(self):
        permission_queryset = mock.MagicMock()
        permission_values = mock.MagicMock()
        permission_values.annotate.return_value = []
        permission_queryset.values.return_value = permission_values
        permission_manager = mock.MagicMock()
        permission_manager.filter.return_value = permission_queryset

        component_manager = mock.MagicMock()
        component_manager.filter.return_value = []

        tenant_region_queryset = mock.MagicMock()
        tenant_region_queryset.values.return_value = [
            {"tenant_id": "team-1", "region_name": "region-b"},
            {"tenant_id": "team-1", "region_name": "orphan-region"},
            {"tenant_id": "team-1", "region_name": "region-a"},
        ]
        tenant_region_manager = mock.MagicMock()
        tenant_region_manager.filter.return_value = tenant_region_queryset

        region_a = Obj(region_name="region-a", region_alias="Region A", region_id="region-id-a")
        region_b = Obj(region_name="region-b", region_alias="Region B", region_id="region-id-b")

        def region_resources(_eid, region_name, _tenant_ids):
            return [{
                "UUID": "team-1",
                "memory_limit": 100 if region_name == "region-a" else 200,
            }]

        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(team_module.PermRelTenant, "objects", permission_manager))
            stack.enter_context(mock.patch.object(team_module.TenantServiceInfo, "objects", component_manager))
            stack.enter_context(mock.patch.object(team_module.TenantRegionInfo, "objects", tenant_region_manager))
            stack.enter_context(mock.patch.object(team_module.user_repo, "get_by_user_ids", return_value=[]))
            stack.enter_context(mock.patch.object(team_module.volume_repo, "get_services_volumes", return_value=[]))
            stack.enter_context(
                mock.patch.object(team_module.region_repo, "get_region_by_region_names", return_value=[region_a, region_b]))
            resources_mock = stack.enter_context(
                mock.patch.object(self.service, "get_region_tenant", side_effect=region_resources))
            stack.enter_context(mock.patch.object(team_module.os, "getenv", return_value=None))

            result = list(self.service.jg_teams("enterprise-1", [self.teams[0]]))

        self.assertEqual(result[0]["region"], "region-a")
        self.assertEqual(result[0]["region_list"], [
            {"region_name": "region-a", "region_alias": "Region A", "region_id": "region-id-a"},
            {"region_name": "region-b", "region_alias": "Region B", "region_id": "region-id-b"},
        ])
        self.assertEqual(result[0]["memory_request"], 200)
        self.assertEqual(resources_mock.call_args_list, [
            mock.call("enterprise-1", "region-a", ["team-1"]),
            mock.call("enterprise-1", "region-b", ["team-1"]),
        ])
