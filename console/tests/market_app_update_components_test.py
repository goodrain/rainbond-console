# -*- coding: utf-8 -*-
import collections
import json
import os
import sys
from types import ModuleType
from unittest import TestCase

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from console.services.market_app.update_components import UpdateComponents  # noqa: E402


class FakeService(object):
    def __init__(self):
        self.service_key = "service-1"
        self.component_id = "component-1"
        self.image = "registry.example.com/demo/web:1.0.0"
        self.cmd = "old-cmd"
        self.version = "1.0.0"


class FakeServiceSource(object):
    def __init__(self):
        self.version = "1.0.0"
        self.service_share_uuid = "service-1+component-1"
        self.extend_info = json.dumps({})


class FakeComponent(object):
    def __init__(self):
        self.component = FakeService()
        self.component_source = FakeServiceSource()
        self.changes = []

    def set_changes(self, tenant, region, changes, governance_mode):
        self.changes.append({
            "tenant": tenant,
            "region": region,
            "changes": changes,
            "governance_mode": governance_mode,
        })


class FakeOriginalApp(object):
    def __init__(self, component):
        self._component = component
        self.tenant = "tenant-1"
        self.region = "demo-region"
        self.governance_mode = "KUBERNETES_NATIVE_SERVICE"

    def components(self):
        return [self._component]


class MarketAppUpdateComponentsCompatibilityTests(TestCase):
    # capability_id: console.market-app.upgrade-share-image-fallback
    def test_create_update_components_falls_back_to_image_when_share_image_missing(self):
        original_component = FakeComponent()
        app_template = {
            "apps": [
                {
                    "service_key": "service-1",
                    "service_share_uuid": "service-1+component-1",
                    "image": "registry.example.com/demo/web:2.0.0",
                    "version": "2.0.0",
                }
            ]
        }
        property_changes = type("PropertyChanges", (), {"changes": [{"component_id": "component-1"}]})()

        update_components = UpdateComponents(
            FakeOriginalApp(original_component),
            "app-model-key",
            app_template,
            "2.0.0",
            None,
            property_changes,
        )

        updated_component = update_components.components[0]
        self.assertEqual(updated_component.component.image, app_template["apps"][0]["image"])
        self.assertEqual(updated_component.component.version, "2.0.0")
        self.assertEqual(len(updated_component.changes), 1)
