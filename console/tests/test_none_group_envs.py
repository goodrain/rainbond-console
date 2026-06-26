# -*- coding: utf-8 -*-
"""Unit tests for the **None** / **None:group_name** env parameterization feature.

The ``NewComponents`` class processes env vars from app templates during
installation.  This test module covers:

- ``_resolve_none_placeholder``: generates random values for ``**None**``
  and grouped ``**None:group**`` placeholders.
- ``_template_to_envs``: wires the resolution into both inner and outer
  env processing, including cross-component group consistency.

No database or running services required -- all Django model instances
are created in memory and all external dependencies are mocked.
"""
import collections
import copy
import os
import sys
import typing
from types import ModuleType
from unittest.mock import patch

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

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MAKE_UUID_PATH = "console.services.market_app.new_components.make_uuid"

# Deterministic "uuid" values for patching.  Each is 32 hex chars.
FAKE_UUID_A = "aaaa1111bbbb2222cccc3333dddd4444"
FAKE_UUID_B = "eeee5555ffff6666000077778888abcd"
FAKE_UUID_C = "11112222333344445555666677778888"


def _make_creator(**overrides):
    """Build a ``NewComponents`` instance without running ``__init__``.

    Uses ``__new__`` to skip the constructor (which needs tenant, region,
    user, etc.).  Only ``_secret_groups`` is required for the placeholder
    tests; additional attributes can be passed via *overrides*.
    """
    creator = NewComponents.__new__(NewComponents)
    creator._secret_groups = {}
    for key, value in overrides.items():
        setattr(creator, key, value)
    return creator


def _fake_component(tenant_id="tid-1", service_id="sid-1"):
    """Minimal stand-in for ``TenantServiceInfo``."""
    return type("FakeComponent", (), {
        "tenant_id": tenant_id,
        "service_id": service_id,
    })()


def _fake_original_app(governance_mode="BUILD_IN_SERVICE_MESH"):
    """Minimal stand-in for the original app object."""
    return type("FakeOriginalApp", (), {
        "governance_mode": governance_mode,
    })()


# ===================================================================
# Test suite 1: _resolve_none_placeholder
# ===================================================================


class ResolveNonePlaceholderTests:
    """Test the ``_resolve_none_placeholder`` method."""

    def test_plain_none_returns_8_chars(self):
        """``**None**`` produces an 8-character random string."""
        creator = _make_creator()
        with patch(MAKE_UUID_PATH, return_value=FAKE_UUID_A):
            result = creator._resolve_none_placeholder("**None**")
        assert result is not None
        assert len(result) == 8
        assert result == FAKE_UUID_A[:8]

    def test_grouped_none_returns_32_chars(self):
        """``**None:group**`` produces a 32-character random string."""
        creator = _make_creator()
        with patch(MAKE_UUID_PATH, return_value=FAKE_UUID_A):
            result = creator._resolve_none_placeholder("**None:db_password**")
        assert result is not None
        assert len(result) == 32

    def test_same_group_returns_same_value(self):
        """Two calls with the same group name return the identical value."""
        creator = _make_creator()
        with patch(MAKE_UUID_PATH, return_value=FAKE_UUID_A):
            first = creator._resolve_none_placeholder("**None:shared_secret**")
        # Second call -- make_uuid returns something different, but the
        # cached value should be reused.
        with patch(MAKE_UUID_PATH, return_value=FAKE_UUID_B):
            second = creator._resolve_none_placeholder("**None:shared_secret**")
        assert first == second

    def test_different_groups_return_different_values(self):
        """Different group names produce distinct values."""
        creator = _make_creator()
        with patch(MAKE_UUID_PATH, side_effect=[FAKE_UUID_A, FAKE_UUID_B]):
            val_a = creator._resolve_none_placeholder("**None:group_a**")
            val_b = creator._resolve_none_placeholder("**None:group_b**")
        assert val_a != val_b

    def test_regular_value_returns_none(self):
        """A normal env value (not a placeholder) returns ``None``."""
        creator = _make_creator()
        result = creator._resolve_none_placeholder("some_regular_value")
        assert result is None

    def test_empty_string_returns_none(self):
        """An empty string returns ``None`` (no substitution)."""
        creator = _make_creator()
        result = creator._resolve_none_placeholder("")
        assert result is None

    def test_group_state_persists(self):
        """Group cache persists across multiple independent calls."""
        creator = _make_creator()
        with patch(MAKE_UUID_PATH, return_value=FAKE_UUID_C):
            first = creator._resolve_none_placeholder("**None:persist_test**")

        # Make a plain **None** call in between to verify groups are
        # independent of non-grouped calls.
        with patch(MAKE_UUID_PATH, return_value=FAKE_UUID_A):
            _ = creator._resolve_none_placeholder("**None**")

        # The grouped value must still be the cached one.
        with patch(MAKE_UUID_PATH, return_value=FAKE_UUID_B):
            second = creator._resolve_none_placeholder("**None:persist_test**")

        assert first == second
        assert first == FAKE_UUID_C


# ===================================================================
# Test suite 2: _template_to_envs None processing
# ===================================================================


class TemplateToEnvsNoneProcessingTests:
    """Test that ``_template_to_envs`` processes ``**None**`` for both
    inner and outer envs, including the ``**None:group**`` variant.
    """

    def test_inner_env_none_resolved(self):
        """Inner env with ``**None**`` gets auto-generated value (8 chars)."""
        creator = _make_creator(original_app=_fake_original_app())
        component = _fake_component()
        inner_envs = [{"attr_name": "DB_PASS", "name": "db password", "attr_value": "**None**"}]

        with patch(MAKE_UUID_PATH, return_value=FAKE_UUID_A):
            envs = creator._template_to_envs(component, inner_envs, [], [])

        assert len(envs) == 1
        assert envs[0].attr_value != "**None**"
        assert len(envs[0].attr_value) == 8
        assert envs[0].scope == "inner"

    def test_inner_env_grouped_none_resolved(self):
        """Inner env with ``**None:group**`` gets auto-generated 32-char value."""
        creator = _make_creator(original_app=_fake_original_app())
        component = _fake_component()
        inner_envs = [{"attr_name": "SECRET_KEY", "name": "secret", "attr_value": "**None:app_secret**"}]

        with patch(MAKE_UUID_PATH, return_value=FAKE_UUID_B):
            envs = creator._template_to_envs(component, inner_envs, [], [])

        assert len(envs) == 1
        assert envs[0].attr_value != "**None:app_secret**"
        assert len(envs[0].attr_value) == 32
        assert envs[0].scope == "inner"

    def test_outer_env_none_backward_compat(self):
        """Outer env with ``**None**`` still resolves (backward compat)."""
        creator = _make_creator(original_app=_fake_original_app())
        component = _fake_component()
        outer_envs = [{"attr_name": "MYSQL_PASS", "name": "mysql password", "attr_value": "**None**"}]

        with patch(MAKE_UUID_PATH, return_value=FAKE_UUID_A):
            envs = creator._template_to_envs(component, [], outer_envs, [])

        assert len(envs) == 1
        assert envs[0].attr_value != "**None**"
        assert envs[0].scope == "outer"

    def test_outer_env_grouped_none_resolved(self):
        """Outer env with ``**None:group**`` gets auto-generated value."""
        creator = _make_creator(original_app=_fake_original_app())
        component = _fake_component()
        outer_envs = [{"attr_name": "REDIS_PASS", "name": "redis password", "attr_value": "**None:redis_pw**"}]

        with patch(MAKE_UUID_PATH, return_value=FAKE_UUID_B):
            envs = creator._template_to_envs(component, [], outer_envs, [])

        assert len(envs) == 1
        assert envs[0].attr_value != "**None:redis_pw**"
        assert len(envs[0].attr_value) == 32
        assert envs[0].scope == "outer"

    def test_cross_component_group_consistency(self):
        """Same group name across two ``_template_to_envs`` calls produces
        the same resolved value, ensuring cross-component consistency."""
        creator = _make_creator(original_app=_fake_original_app())
        component_a = _fake_component(service_id="svc-a")
        component_b = _fake_component(service_id="svc-b")

        inner_a = [{"attr_name": "DB_PASS", "name": "db password", "attr_value": "**None:db_password**"}]
        inner_b = [{"attr_name": "DB_PASS", "name": "db password", "attr_value": "**None:db_password**"}]

        # First call generates the value; second call should reuse it.
        with patch(MAKE_UUID_PATH, return_value=FAKE_UUID_A):
            envs_a = creator._template_to_envs(component_a, inner_a, [], [])

        with patch(MAKE_UUID_PATH, return_value=FAKE_UUID_B):
            envs_b = creator._template_to_envs(component_b, inner_b, [], [])

        assert envs_a[0].attr_value == envs_b[0].attr_value

    def test_regular_env_unchanged(self):
        """Env vars with regular values pass through without modification."""
        creator = _make_creator(original_app=_fake_original_app())
        component = _fake_component()
        inner_envs = [{"attr_name": "APP_MODE", "name": "app mode", "attr_value": "production"}]
        outer_envs = [{"attr_name": "LOG_LEVEL", "name": "log level", "attr_value": "info"}]

        envs = creator._template_to_envs(component, inner_envs, outer_envs, [])

        assert len(envs) == 2
        inner = [e for e in envs if e.scope == "inner"]
        outer = [e for e in envs if e.scope == "outer"]
        assert inner[0].attr_value == "production"
        assert outer[0].attr_value == "info"

    def test_inner_env_no_mutation(self):
        """Processing ``**None**`` in inner envs must NOT mutate the original
        env dict that was passed in."""
        creator = _make_creator(original_app=_fake_original_app())
        component = _fake_component()
        inner_env = {"attr_name": "SECRET", "name": "secret", "attr_value": "**None**"}
        original = copy.deepcopy(inner_env)

        with patch(MAKE_UUID_PATH, return_value=FAKE_UUID_A):
            creator._template_to_envs(component, [inner_env], [], [])

        assert inner_env == original, "inner env dict was mutated by _template_to_envs"
