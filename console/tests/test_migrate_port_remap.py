# -*- coding: utf-8 -*-
"""Tests for k8s_service_name preservation and hostname remap on app copy/migrate.

Copying/migrating an app must keep each port's semantic k8s_service_name
(e.g. "postgres") instead of resetting it to the new service_alias. When the
name collides in the target tenant (the normal case for an in-tenant copy),
it is suffixed like the market-install remap engine does, and custom envs /
DSN-style connection strings referencing the old hostname are rewritten.
"""
import collections
import os
import sys
import typing
from types import ModuleType
from unittest.mock import MagicMock, patch

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))
if not hasattr(typing, "NotRequired"):
    try:
        from typing_extensions import NotRequired
        typing.NotRequired = NotRequired  # type: ignore[attr-defined]
    except ImportError:
        typing.NotRequired = lambda item: item  # type: ignore[attr-defined]

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from django.db.models.query import QuerySet  # noqa: E402

if not hasattr(QuerySet, "__class_getitem__"):
    QuerySet.__class_getitem__ = classmethod(lambda cls, item: cls)  # type: ignore[assignment]

from console.exception.bcode import ErrK8sServiceNameExists  # noqa: E402
from console.services.groupapp_recovery.groupapps_migrate import migrate_service  # noqa: E402
from www.models.main import TenantServiceEnvVar, TenantServiceInfo  # noqa: E402

MIGRATE_MODULE = "console.services.groupapp_recovery.groupapps_migrate"

collect_names = migrate_service._GroupappsMigrateService__collect_port_k8s_service_names
save_env = migrate_service._GroupappsMigrateService__save_env


def _tenant():
    tenant = MagicMock()
    tenant.tenant_id = "tenant-1"
    tenant.tenant_name = "team1"
    return tenant


def _apps(k8s_service_name="postgres", container_port=5432):
    return [{
        "service_base": {
            "service_id": "old-sid-1"
        },
        "service_ports": [{
            "container_port": container_port,
            "k8s_service_name": k8s_service_name,
        }],
    }]


CHANGED_SERVICE_MAP = {"old-sid-1": {"ServiceID": "new-sid-1", "ServiceAlias": "gr654321"}}


class CollectPortK8sServiceNamesTests:
    def test_semantic_name_preserved_when_free(self):
        with patch(MIGRATE_MODULE + ".port_service") as mock_ps:
            mock_ps.check_k8s_service_name.return_value = None
            port_name_map, remap = collect_names(_tenant(), _apps(), CHANGED_SERVICE_MAP)
        assert port_name_map == {"old-sid-1": {5432: "postgres"}}
        assert remap == {}

    def test_collision_suffixes_and_records_remap(self):
        with patch(MIGRATE_MODULE + ".port_service") as mock_ps, \
                patch(MIGRATE_MODULE + ".make_uuid", return_value="abcd1234"):
            mock_ps.check_k8s_service_name.side_effect = ErrK8sServiceNameExists()
            port_name_map, remap = collect_names(_tenant(), _apps(), CHANGED_SERVICE_MAP)
        assert port_name_map == {"old-sid-1": {5432: "postgres-abcd"}}
        assert remap == {"postgres": "postgres-abcd"}

    def test_empty_name_falls_back_to_alias_without_remap(self):
        with patch(MIGRATE_MODULE + ".port_service") as mock_ps:
            mock_ps.check_k8s_service_name.return_value = None
            port_name_map, remap = collect_names(_tenant(), _apps(k8s_service_name=""), CHANGED_SERVICE_MAP)
        assert port_name_map == {"old-sid-1": {5432: "gr654321"}}
        assert remap == {}

    def test_same_service_ports_share_name_without_self_conflict(self):
        apps = [{
            "service_base": {
                "service_id": "old-sid-1"
            },
            "service_ports": [
                {
                    "container_port": 5432,
                    "k8s_service_name": "postgres"
                },
                {
                    "container_port": 5433,
                    "k8s_service_name": "postgres"
                },
            ],
        }]
        with patch(MIGRATE_MODULE + ".port_service") as mock_ps:
            mock_ps.check_k8s_service_name.return_value = None
            port_name_map, remap = collect_names(_tenant(), apps, CHANGED_SERVICE_MAP)
        assert port_name_map == {"old-sid-1": {5432: "postgres", 5433: "postgres"}}
        assert remap == {}

    def test_cross_component_conflict_within_batch(self):
        apps = [
            {
                "service_base": {
                    "service_id": "old-sid-1"
                },
                "service_ports": [{
                    "container_port": 5432,
                    "k8s_service_name": "postgres"
                }],
            },
            {
                "service_base": {
                    "service_id": "old-sid-2"
                },
                "service_ports": [{
                    "container_port": 5432,
                    "k8s_service_name": "postgres"
                }],
            },
        ]
        changed = {
            "old-sid-1": {
                "ServiceID": "new-sid-1",
                "ServiceAlias": "gr111111"
            },
            "old-sid-2": {
                "ServiceID": "new-sid-2",
                "ServiceAlias": "gr222222"
            },
        }
        with patch(MIGRATE_MODULE + ".port_service") as mock_ps, \
                patch(MIGRATE_MODULE + ".make_uuid", return_value="abcd1234"):
            mock_ps.check_k8s_service_name.return_value = None
            port_name_map, remap = collect_names(_tenant(), apps, changed)
        assert port_name_map["old-sid-1"] == {5432: "postgres"}
        assert port_name_map["old-sid-2"] == {5432: "postgres-abcd"}
        assert remap == {"postgres": "postgres-abcd"}


class SaveEnvHostnameRemapTests:
    def _service(self):
        service = MagicMock(spec=TenantServiceInfo)
        service.service_id = "new-sid-1"
        service.service_alias = "gr654321"
        return service

    def _run_save_env(self, envs, remap):
        created = []
        with patch.object(TenantServiceEnvVar.objects, "bulk_create", side_effect=created.extend):
            save_env(_tenant(), self._service(), envs, remap)
        return created

    def test_custom_host_env_rewritten_on_collision(self):
        envs = [{"ID": 1, "attr_name": "DB_POSTGRESDB_HOST", "attr_value": "postgres"}]
        created = self._run_save_env(envs, {"postgres": "postgres-abcd"})
        assert created[0].attr_value == "postgres-abcd"

    def test_connection_string_rewritten_on_collision(self):
        envs = [
            {
                "ID": 1,
                "attr_name": "QUEUE_BULL_REDIS_URI",
                "attr_value": "redis://redis:6379"
            },
            {
                "ID": 2,
                "attr_name": "MONGODB_URI",
                "attr_value": "mongodb://user:pass@mongo:27017/db"
            },
        ]
        created = self._run_save_env(envs, {"redis": "redis-ab12", "mongo": "mongo-cd34"})
        assert created[0].attr_value == "redis://redis-ab12:6379"
        assert created[1].attr_value == "mongodb://user:pass@mongo-cd34:27017/db"

    def test_non_host_env_equal_to_service_name_left_alone(self):
        envs = [{"ID": 1, "attr_name": "POSTGRESQL_DATABASE", "attr_value": "postgres"}]
        created = self._run_save_env(envs, {"postgres": "postgres-abcd"})
        assert created[0].attr_value == "postgres"

    def test_no_remap_keeps_values(self):
        envs = [{"ID": 1, "attr_name": "DB_POSTGRESDB_HOST", "attr_value": "postgres"}]
        created = self._run_save_env(envs, {})
        assert created[0].attr_value == "postgres"
