# -*- coding: utf-8 -*-
"""Tests for hostname remap during template installation.

When installing a template into a namespace where k8s_service_name
collisions occur, inner env values and config-file content that reference
the original hostnames must be updated to match the collision-suffixed names.
"""
import collections
import os
import sys
import typing
from types import ModuleType

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

from console.services.market_app.new_components import NewComponents  # noqa: E402


class ApplyHostnameRemapTests:

    def test_exact_match_host_env(self):
        # A bare hostname value is remapped only when the env is host-valued.
        assert NewComponents._apply_hostname_remap(
            "db-postgres", {"db-postgres": "db-postgres-a1b2"}, is_host_env=True) == "db-postgres-a1b2"

    def test_exact_match_non_host_env_left_alone(self):
        # A non-host value that merely equals a service name must not be rewritten
        # (e.g. Harbor POSTGRESQL_DATABASE=registry vs the registry component).
        assert NewComponents._apply_hostname_remap(
            "db-postgres", {"db-postgres": "db-postgres-a1b2"}) == "db-postgres"

    def test_embedded_in_url(self):
        remap = {"redis": "redis-c3d4"}
        assert NewComponents._apply_hostname_remap(
            "redis://redis:6379/1", remap) == "redis://redis-c3d4:6379/1"

    def test_url_scheme_not_corrupted(self):
        remap = {"redis": "redis-c3d4"}
        result = NewComponents._apply_hostname_remap("redis://redis:6379/1", remap)
        assert result.startswith("redis://"), "URL scheme should not be remapped"
        assert "redis-c3d4:6379" in result

    def test_multiple_urls_in_config(self):
        remap = {"api": "api-1234", "web": "web-5678"}
        config = "proxy_pass http://api:5001;\nproxy_pass http://web:3000;"
        result = NewComponents._apply_hostname_remap(config, remap)
        assert "http://api-1234:5001" in result
        assert "http://web-5678:3000" in result

    def test_no_remap_needed(self):
        assert NewComponents._apply_hostname_remap("some-value", {}) == "some-value"

    def test_empty_value(self):
        assert NewComponents._apply_hostname_remap("", {"api": "api-1234"}) == ""

    def test_none_remap(self):
        assert NewComponents._apply_hostname_remap("api", None) == "api"

    def test_http_endpoint(self):
        remap = {"sandbox": "sandbox-abcd"}
        result = NewComponents._apply_hostname_remap(
            "http://sandbox:8194", remap)
        assert result == "http://sandbox-abcd:8194"

    def test_hostname_port_without_scheme(self):
        remap = {"gitea-db": "gitea-db-a842"}
        result = NewComponents._apply_hostname_remap("gitea-db:5432", remap)
        assert result == "gitea-db-a842:5432"

    def test_hostname_port_no_false_positive_with_scheme(self):
        remap = {"redis": "redis-c3d4"}
        result = NewComponents._apply_hostname_remap("redis://redis:6379/1", remap)
        assert result.startswith("redis://")
        assert "redis-c3d4:6379" in result

    def test_config_file_content(self):
        remap = {"api": "api-1234", "web": "web-5678"}
        config = (
            "location /console/api { proxy_pass http://api:5001; }\n"
            "location /           { proxy_pass http://web:3000; }"
        )
        result = NewComponents._apply_hostname_remap(config, remap)
        assert "http://api-1234:5001" in result
        assert "http://web-5678:3000" in result
        assert "http://api:" not in result
        assert "http://web:" not in result

    def test_mongodb_dsn_with_credentials(self):
        remap = {"fastgpt-mongo": "fastgpt-mongo-3d13"}
        result = NewComponents._apply_hostname_remap(
            "mongodb://myusername:mypassword@fastgpt-mongo:27017/fastgpt?authSource=admin", remap)
        assert result == "mongodb://myusername:mypassword@fastgpt-mongo-3d13:27017/fastgpt?authSource=admin"

    def test_redis_url_with_credentials(self):
        remap = {"fastgpt-redis": "fastgpt-redis-3d13"}
        result = NewComponents._apply_hostname_remap(
            "redis://default:mypassword@fastgpt-redis:6379", remap)
        assert result == "redis://default:mypassword@fastgpt-redis-3d13:6379"

    def test_postgres_dsn_with_credentials(self):
        remap = {"fastgpt-aiproxy-pg": "fastgpt-aiproxy-pg-3d13"}
        result = NewComponents._apply_hostname_remap(
            "postgres://postgres:aiproxy@fastgpt-aiproxy-pg:5432/aiproxy", remap)
        assert result == "postgres://postgres:aiproxy@fastgpt-aiproxy-pg-3d13:5432/aiproxy"

    def test_dsn_with_credentials_and_path_no_port(self):
        remap = {"mongo": "mongo-ab12"}
        result = NewComponents._apply_hostname_remap(
            "mongodb://user:pass@mongo/mydb", remap)
        assert result == "mongodb://user:pass@mongo-ab12/mydb"

    def test_dsn_with_credentials_no_port_no_path(self):
        remap = {"rabbitmq": "rabbitmq-cd34"}
        result = NewComponents._apply_hostname_remap(
            "amqp://guest:secret@rabbitmq", remap)
        assert result == "amqp://guest:secret@rabbitmq-cd34"

    def test_credential_matching_service_name_left_alone(self):
        # A password that merely equals a remapped service name must not be touched.
        remap = {"registry": "registry-ef56"}
        result = NewComponents._apply_hostname_remap(
            "postgres://harboruser:registry@harbor-db:5432/registry", remap)
        assert result == "postgres://harboruser:registry@harbor-db:5432/registry"

    def test_email_like_value_left_alone(self):
        remap = {"api": "api-1234"}
        assert NewComponents._apply_hostname_remap("admin@api", remap) == "admin@api"

    def test_does_not_mutate_remap(self):
        remap = {"api": "api-1234"}
        original = dict(remap)
        NewComponents._apply_hostname_remap("http://api:5001", remap)
        assert remap == original


class CollectHostnameRemapTests:

    def _make_port_tmpl(self, k8s_name, port, alias):
        return {
            "k8s_service_name": k8s_name,
            "container_port": port,
            "port_alias": alias,
            "protocol": "tcp",
            "is_inner_service": True,
            "is_outer_service": False,
        }

    def test_no_collision_empty_remap(self):
        """When check_k8s_service_name doesn't raise, remap is empty."""
        from unittest.mock import patch, MagicMock
        from www.models.main import TenantServiceInfo

        cpt = MagicMock(spec=TenantServiceInfo)
        cpt.service_key = "svc-1"
        cpt.tenant_id = "t1"
        cpt.service_id = "sid-1"
        cpt.service_alias = "gr123456"
        cpt.component_id = "sid-1"

        templates = {
            "svc-1": {"port_map_list": [self._make_port_tmpl("api", 5001, "API")]},
        }

        nc = NewComponents.__new__(NewComponents)
        nc._port_cache = {}

        with patch("console.services.market_app.new_components.port_service") as mock_ps:
            mock_ps.check_k8s_service_name.return_value = None
            remap = nc._collect_hostname_remap([cpt], templates)

        assert remap == {}

    def test_collision_produces_remap(self):
        from unittest.mock import patch, MagicMock
        from console.exception.bcode import ErrK8sServiceNameExists
        from www.models.main import TenantServiceInfo

        cpt = MagicMock(spec=TenantServiceInfo)
        cpt.service_key = "svc-1"
        cpt.tenant_id = "t1"
        cpt.service_id = "sid-1"
        cpt.service_alias = "gr123456"
        cpt.component_id = "sid-1"

        templates = {
            "svc-1": {"port_map_list": [self._make_port_tmpl("api", 5001, "API")]},
        }

        nc = NewComponents.__new__(NewComponents)
        nc._port_cache = {}

        with patch("console.services.market_app.new_components.port_service") as mock_ps, \
             patch("console.services.market_app.new_components.make_uuid", return_value="abcd1234"):
            mock_ps.check_k8s_service_name.side_effect = ErrK8sServiceNameExists()
            remap = nc._collect_hostname_remap([cpt], templates)

        assert "api" in remap
        assert remap["api"] == "api-abcd"
