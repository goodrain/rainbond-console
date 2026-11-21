# -*- coding: utf-8 -*-
import collections
import os
import sys
import typing
from types import ModuleType, SimpleNamespace
from unittest import TestCase
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
import six  # noqa: E402

django.setup()
sys.modules.setdefault("django.utils.six.moves", six.moves)
sys.modules.setdefault("django.utils.six.moves.http_client", six.moves.http_client)
sys.modules.setdefault("django.utils.six.moves.urllib", six.moves.urllib)
sys.modules.setdefault("django.utils.six.moves.urllib.parse", six.moves.urllib.parse)

from django.db.models.query import QuerySet  # noqa: E402

if not hasattr(QuerySet, "__class_getitem__"):
    QuerySet.__class_getitem__ = classmethod(lambda cls, item: cls)  # type: ignore[assignment]

from console.services.market_app.component import Component  # noqa: E402
from console.services.market_app.property_changes import PropertyChanges  # noqa: E402


def _component(service_alias="grabcd"):
    service = SimpleNamespace(
        component_id="svc-id",
        service_id="svc-id",
        service_alias=service_alias,
        tenant_id="tenant-id",
    )
    return Component(service, None, [], [], [], [], [], {}, [], [], [], support_labels=[])


class MarketAppComponentPortTests(TestCase):

    # capability_id: console.market-app.k8s-attribute-extra-fields
    def test_update_k8s_attribute_ignores_template_metadata_fields(self):
        component = _component()
        component.k8s_attributes = [SimpleNamespace(name="affinity", attribute_value="old")]

        component._update_component_k8s_attributes({
            "upd": [{
                "name": "affinity",
                "save_type": "json",
                "attribute_value": '{"nodeAffinity": {}}',
                "operator": "admin",
            }]
        })

        self.assertEqual(component.k8s_attributes[0].attribute_value, '{"nodeAffinity": {}}')

    def test_update_port_data_preserves_template_port_alias(self):
        component = _component()
        port = {
            "container_port": 8080,
            "protocol": "http",
            "port_alias": "HARBOR_CORE_8080",
            "is_inner_service": True,
            "is_outer_service": False,
            "k8s_service_name": "core",
        }

        with patch("console.services.market_app.component.port_repo.get_by_k8s_service_name", return_value=None):
            component._update_port_data(port)

        assert port["port_alias"] == "HARBOR_CORE_8080"
        assert port["k8s_service_name"] == "core"

    def test_update_port_data_keeps_legacy_alias_when_template_omits_alias(self):
        component = _component(service_alias="grlegacy")
        port = {
            "container_port": 8080,
            "protocol": "http",
            "is_inner_service": True,
            "is_outer_service": False,
            "k8s_service_name": "legacy",
        }

        with patch("console.services.market_app.component.port_repo.get_by_k8s_service_name", return_value=None):
            component._update_port_data(port)

        assert port["port_alias"] == "GRLEGACY"


class MarketAppUpgradePortTests(TestCase):

    def test_upgrade_enables_inner_service_when_template_opens_outer_service(self):
        component = _component()
        component.ports = [
            SimpleNamespace(
                container_port=8080,
                protocol="http",
                port_alias="WEB",
                is_inner_service=False,
                is_outer_service=False,
            )
        ]
        template_ports = [{
            "container_port": 8080,
            "protocol": "http",
            "port_alias": "WEB",
            "is_inner_service": False,
            "is_outer_service": True,
        }]

        changes = PropertyChanges._ports(component.ports, template_ports)
        component._update_ports(changes)

        self.assertTrue(component.ports[0].is_inner_service)
        self.assertTrue(component.ports[0].is_outer_service)

    def test_upgrade_does_not_close_existing_inner_service(self):
        component = _component()
        component.ports = [
            SimpleNamespace(
                container_port=8080,
                protocol="http",
                port_alias="WEB",
                is_inner_service=True,
                is_outer_service=False,
            )
        ]
        template_ports = [{
            "container_port": 8080,
            "protocol": "http",
            "port_alias": "WEB",
            "is_inner_service": False,
            "is_outer_service": False,
        }]

        component._update_ports(PropertyChanges._ports(component.ports, template_ports))

        self.assertTrue(component.ports[0].is_inner_service)

    def test_upgrade_keeps_existing_inner_service_when_protocol_changes(self):
        component = _component()
        component.ports = [
            SimpleNamespace(
                container_port=8080,
                protocol="http",
                port_alias="OLD_WEB",
                is_inner_service=True,
                is_outer_service=False,
            )
        ]
        template_ports = [{
            "container_port": 8080,
            "protocol": "tcp",
            "port_alias": "WEB",
            "is_inner_service": False,
            "is_outer_service": False,
        }]

        changes = PropertyChanges._ports(component.ports, template_ports)

        self.assertIn("upd", changes)
        self.assertIs(changes["upd"][0]["is_inner_service"], False)
        component._update_ports(changes)

        self.assertTrue(component.ports[0].is_inner_service)
        self.assertFalse(component.ports[0].is_outer_service)
        self.assertEqual("tcp", component.ports[0].protocol)

    def test_upgrade_does_not_recalculate_existing_port_k8s_service_name(self):
        component = _component()
        component.ports = [
            SimpleNamespace(
                container_port=8080,
                protocol="http",
                port_alias="WEB",
                k8s_service_name="web-ab12",
                is_inner_service=False,
                is_outer_service=True,
            )
        ]

        component._update_ports({
            "upd": [{
                "container_port": 8080,
                "protocol": "http",
                "port_alias": "WEB",
                "k8s_service_name": "web",
                "is_inner_service": True,
                "is_outer_service": True,
            }]
        })

        self.assertEqual("web-ab12", component.ports[0].k8s_service_name)

    def test_upgrade_port_flags_normalize_false_string_and_zero(self):
        component = _component()
        template_ports = [{
            "container_port": 8080,
            "protocol": "http",
            "port_alias": "WEB",
            "is_inner_service": "false",
            "is_outer_service": 0,
        }]

        changes = PropertyChanges._ports(component.ports, template_ports)
        with patch("console.services.market_app.component.port_repo.get_by_k8s_service_name", return_value=None):
            component._update_ports(changes)

        self.assertIs(component.ports[0].is_inner_service, False)
        self.assertIs(component.ports[0].is_outer_service, False)
