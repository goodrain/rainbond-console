# -*- coding: utf-8 -*-
import collections
import copy
import json
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

import pytest  # noqa: E402
from console.services.app_version_service import AppVersionService  # noqa: E402


def _make_component(cname: str, upstream_image: str, internal_image: str, with_affinity: bool = True) -> dict:
    component = {
        "service_cname": cname,
        "service_id": f"svc-{cname}",
        "image": upstream_image,
        "share_image": internal_image,
        "service_image": {"image_url": internal_image},
        "share_type": "image",
        "component_k8s_attributes": [],
    }
    if with_affinity:
        component["component_k8s_attributes"].append({
            "name": "affinity",
            "save_type": "yaml",
            "attribute_value": (
                "nodeAffinity:\n  requiredDuringSchedulingIgnoredDuringExecution:\n"
                "    nodeSelectorTerms:\n    - matchExpressions:\n"
                "      - key: kubernetes.io/arch\n        operator: In\n"
                "        values:\n        - amd64\n"
            ),
        })
    return component


def _make_template(components: list, plugins: list = None) -> dict:
    return {
        "template_version": "v2",
        "group_key": "test-app-key",
        "group_name": "test-app",
        "group_version": "1.0.0",
        "arch": "amd64",
        "apps": components,
        "plugins": plugins or [],
    }


class TestRewriteComponentImageToUpstream:

    def test_basic_rewrite(self):
        component = _make_component("api", "langgenius/dify-api:1.14.2", "internal.goodrain.me/dev-api:20260625")
        result = AppVersionService._rewrite_component_image_to_upstream(component)
        assert result["share_image"] == "langgenius/dify-api:1.14.2"
        assert result["service_image"]["image_url"] == "langgenius/dify-api:1.14.2"

    def test_removes_arch_affinity(self):
        component = _make_component("redis", "redis:6-alpine", "internal.goodrain.me/dev-redis:123")
        result = AppVersionService._rewrite_component_image_to_upstream(component)
        assert result["component_k8s_attributes"] == []

    def test_preserves_non_arch_k8s_attributes(self):
        component = _make_component("api", "langgenius/dify-api:1.14.2", "internal/api:123")
        component["component_k8s_attributes"].append({
            "name": "tolerations",
            "save_type": "yaml",
            "attribute_value": "- key: gpu\n  operator: Exists\n",
        })
        result = AppVersionService._rewrite_component_image_to_upstream(component)
        assert len(result["component_k8s_attributes"]) == 1
        assert result["component_k8s_attributes"][0]["name"] == "tolerations"

    def test_image_override(self):
        component = _make_component("db", "postgres:15-alpine", "internal/db:123")
        overrides = {"db": "postgres:16-alpine"}
        result = AppVersionService._rewrite_component_image_to_upstream(component, overrides)
        assert result["share_image"] == "postgres:16-alpine"
        assert result["service_image"]["image_url"] == "postgres:16-alpine"

    def test_override_takes_precedence_over_image_field(self):
        component = _make_component("api", "langgenius/dify-api:1.14.2", "internal/api:123")
        overrides = {"api": "langgenius/dify-api:1.15.0"}
        result = AppVersionService._rewrite_component_image_to_upstream(component, overrides)
        assert result["share_image"] == "langgenius/dify-api:1.15.0"

    def test_no_image_field_noop(self):
        component = {"service_cname": "mystery", "share_image": "internal/x:1", "service_image": {"image_url": "internal/x:1"}}
        result = AppVersionService._rewrite_component_image_to_upstream(component)
        assert result["share_image"] == "internal/x:1"

    def test_no_mutation_of_input(self):
        component = _make_component("api", "langgenius/dify-api:1.14.2", "internal/api:123")
        original = copy.deepcopy(component)
        AppVersionService._rewrite_component_image_to_upstream(component)
        assert component == original

    def test_component_without_affinity(self):
        component = _make_component("redis", "redis:6-alpine", "internal/redis:1", with_affinity=False)
        result = AppVersionService._rewrite_component_image_to_upstream(component)
        assert result["share_image"] == "redis:6-alpine"
        assert result["component_k8s_attributes"] == []


class TestRewriteTemplateImagesToUpstream:

    def test_rewrites_all_components(self):
        template = _make_template([
            _make_component("api", "langgenius/dify-api:1.14.2", "internal/api:1"),
            _make_component("redis", "redis:6-alpine", "internal/redis:1"),
            _make_component("db", "postgres:15-alpine", "internal/db:1"),
        ])
        result = AppVersionService._rewrite_template_images_to_upstream(template)
        for comp in result["apps"]:
            assert comp["share_image"] == comp["image"]
            assert comp["service_image"]["image_url"] == comp["image"]
            assert comp["component_k8s_attributes"] == []

    def test_does_not_mutate_original(self):
        template = _make_template([
            _make_component("api", "langgenius/dify-api:1.14.2", "internal/api:1"),
        ])
        original = copy.deepcopy(template)
        AppVersionService._rewrite_template_images_to_upstream(template)
        assert template == original

    def test_rewrites_plugins(self):
        plugin = _make_component("mesh-plugin", "goodrain.me/mesh:v1", "internal/mesh:1")
        template = _make_template([], plugins=[plugin])
        result = AppVersionService._rewrite_template_images_to_upstream(template)
        assert result["plugins"][0]["share_image"] == "goodrain.me/mesh:v1"

    def test_with_overrides(self):
        template = _make_template([
            _make_component("api", "langgenius/dify-api:1.14.2", "internal/api:1"),
            _make_component("redis", "redis:6-alpine", "internal/redis:1"),
        ])
        overrides = {"api": "langgenius/dify-api:1.15.0"}
        result = AppVersionService._rewrite_template_images_to_upstream(template, overrides)
        api = next(c for c in result["apps"] if c["service_cname"] == "api")
        redis = next(c for c in result["apps"] if c["service_cname"] == "redis")
        assert api["share_image"] == "langgenius/dify-api:1.15.0"
        assert redis["share_image"] == "redis:6-alpine"

    def test_empty_template(self):
        result = AppVersionService._rewrite_template_images_to_upstream({})
        assert result["apps"] == []
        assert result["plugins"] == []


class TestRewriteSnapshotImagesToUpstream:

    def test_rewrites_and_saves(self):
        template = _make_template([
            _make_component("api", "langgenius/dify-api:1.14.2", "internal/api:1"),
            _make_component("redis", "redis:6-alpine", "internal/redis:1"),
        ])
        mock_version = MagicMock()
        mock_version.app_template = json.dumps(template)

        svc = AppVersionService()
        with patch("console.services.app_version_service.app_snapshot_repo") as mock_repo:
            mock_repo.get_by_snapshot_id_and_app.return_value = mock_version
            result = svc.rewrite_snapshot_images_to_upstream("app-123", "42")

        assert result["version_id"] == "42"
        assert result["components_rewritten"] == 2
        assert result["details"][0]["upstream_image"] == "langgenius/dify-api:1.14.2"
        assert result["details"][1]["upstream_image"] == "redis:6-alpine"

        saved_template = json.loads(mock_version.app_template)
        assert saved_template["apps"][0]["share_image"] == "langgenius/dify-api:1.14.2"
        mock_version.save.assert_called_once_with(update_fields=["app_template"])

    def test_not_found_raises(self):
        svc = AppVersionService()
        with patch("console.services.app_version_service.app_snapshot_repo") as mock_repo:
            mock_repo.get_by_snapshot_id_and_app.return_value = None
            with pytest.raises(Exception) as exc_info:
                svc.rewrite_snapshot_images_to_upstream("app-123", "999")
            assert "404" in str(exc_info.value.status_code) or exc_info.value.status_code == 404

    def test_with_image_overrides(self):
        template = _make_template([
            _make_component("api", "langgenius/dify-api:1.14.2", "internal/api:1"),
        ])
        mock_version = MagicMock()
        mock_version.app_template = json.dumps(template)

        svc = AppVersionService()
        with patch("console.services.app_version_service.app_snapshot_repo") as mock_repo:
            mock_repo.get_by_snapshot_id_and_app.return_value = mock_version
            result = svc.rewrite_snapshot_images_to_upstream("app-123", "42", {"api": "langgenius/dify-api:2.0.0"})

        assert result["details"][0]["upstream_image"] == "langgenius/dify-api:2.0.0"
        saved_template = json.loads(mock_version.app_template)
        assert saved_template["apps"][0]["share_image"] == "langgenius/dify-api:2.0.0"


class TestRewriteWithRealDifyTemplate:
    """Verify rewrite against a realistic Dify-like template structure."""

    DIFY_COMPONENTS = [
        ("api", "langgenius/dify-api:1.14.2", "internal-image.goodrain.com/rainbond/dev-dify-poc-api:20260625173555"),
        ("worker", "langgenius/dify-api:1.14.2", "internal-image.goodrain.com/rainbond/dev-dify-poc-worker:20260625175430"),
        ("web", "langgenius/dify-web:1.14.2", "internal-image.goodrain.com/rainbond/dev-dify-poc-web:20260625173555"),
        ("sandbox", "langgenius/dify-sandbox:0.2.15",
         "internal-image.goodrain.com/rainbond/dev-dify-poc-sandbox:20260625171415"),
        ("plugin-daemon", "langgenius/dify-plugin-daemon:0.6.1-local",
         "internal-image.goodrain.com/rainbond/dev-dify-poc-plugin-daemon:20260625171537"),
        ("redis", "redis:6-alpine", "internal-image.goodrain.com/rainbond/dev-dify-poc-redis:20260625171415"),
        ("db-postgres", "postgres:15-alpine", "internal-image.goodrain.com/rainbond/dev-dify-poc-db-postgres:20260625171415"),
        ("weaviate", "semitechnologies/weaviate:1.27.0",
         "internal-image.goodrain.com/rainbond/dev-dify-poc-weaviate:20260625171415"),
        ("nginx", "nginx:1.27-alpine", "internal-image.goodrain.com/rainbond/dev-dify-poc-nginx:20260625173528"),
    ]

    def test_all_9_components_rewritten(self):
        components = [_make_component(name, upstream, internal) for name, upstream, internal in self.DIFY_COMPONENTS]
        template = _make_template(components)
        result = AppVersionService._rewrite_template_images_to_upstream(template)

        for comp in result["apps"]:
            cname = comp["service_cname"]
            expected = next(upstream for name, upstream, _ in self.DIFY_COMPONENTS if name == cname)
            assert comp["share_image"] == expected, f"{cname}: share_image mismatch"
            assert comp["service_image"]["image_url"] == expected, f"{cname}: service_image mismatch"
            assert comp["component_k8s_attributes"] == [], f"{cname}: arch affinity not removed"

    def test_no_internal_registry_references_remain(self):
        components = [
            _make_component(name, upstream, internal)
            for name, upstream, internal in self.DIFY_COMPONENTS
        ]
        template = _make_template(components)
        result = AppVersionService._rewrite_template_images_to_upstream(template)
        serialized = json.dumps(result)
        assert "goodrain.com" not in serialized
        assert "internal-image" not in serialized
