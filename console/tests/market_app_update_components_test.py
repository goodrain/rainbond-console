# -*- coding: utf-8 -*-
import collections
import json
import os
import sys
import typing
from types import ModuleType
from unittest import TestCase

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))
if not hasattr(typing, "NotRequired"):
    try:
        from typing_extensions import NotRequired
        typing.NotRequired = NotRequired
    except ImportError:
        typing.NotRequired = lambda item: item

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from django.db.models.query import QuerySet  # noqa: E402

if not hasattr(QuerySet, "__class_getitem__"):
    QuerySet.__class_getitem__ = classmethod(lambda cls, item: cls)

from console.services.market_app.update_components import UpdateComponents  # noqa: E402
from console.services.market_app.new_components import NewComponents  # noqa: E402


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


class MarketAppNewComponentsVMK8sAttrsTests(TestCase):
    # capability_id: console.market-app.vm-disk-imports-from-template
    def test_template_to_k8s_attributes_backfills_vm_runtime_attrs_from_vm_block(self):
        creator = NewComponents.__new__(NewComponents)
        component = type("FakeComponent", (), {"tenant_id": "tenant-a", "service_id": "service-a", "service_key": "service-1"})()
        component_tmpl = {
            "vm": {
                "boot_mode": "bios",
                "boot_source_format": "qcow2",
                "disk_layout": [{
                    "disk_key": "disk",
                    "disk_role": "root",
                    "image": "registry.example.com/team/windows-root:v1",
                    "source_type": "registry",
                    "format": "qcow2",
                }]
            }
        }

        attrs = creator._template_to_k8s_attributes(component, [], component_tmpl)
        attr_map = {attr.name: attr.attribute_value for attr in attrs}

        self.assertEqual("bios", attr_map["vm_boot_mode"])
        self.assertEqual("qcow2", attr_map["vm_boot_source_format"])
        self.assertIn('"disk_key": "disk"', attr_map["vm_disk_layout"])
        imports = json.loads(attr_map["vm_disk_imports"])
        self.assertEqual("registry.example.com/team/windows-root:v1", imports["disk"]["image_url"])
        self.assertEqual("registry", imports["disk"]["source_type"])

    def test_template_to_k8s_attributes_uses_http_artifact_for_published_vm_root(self):
        creator = NewComponents.__new__(NewComponents)
        component = type("FakeComponent", (), {"tenant_id": "tenant-a", "service_id": "service-a", "service_key": "service-1"})()
        component_tmpl = {
            "vm": {
                "boot_mode": "bios",
                "boot_source_format": "raw.gz",
                "disk_layout": [{
                    "disk_key": "disk",
                    "disk_role": "root",
                    "image": "goodrain.me/team/windows-root:v1",
                    "source_type": "registry",
                    "source_uri": "https://virt-export.default.svc/volumes/manual22/disk.img.gz",
                    "format": "raw.gz",
                }]
            }
        }

        attrs = creator._template_to_k8s_attributes(component, [], component_tmpl)
        attr_map = {attr.name: attr.attribute_value for attr in attrs}
        imports = json.loads(attr_map["vm_disk_imports"])

        self.assertEqual("goodrain.me/team/windows-root:v1", imports["disk"]["image_url"])
        self.assertEqual("http-artifact", imports["disk"]["source_type"])

    def test_template_to_component_marks_vm_service_type(self):
        creator = NewComponents.__new__(NewComponents)
        creator.user = type("FakeUser", (), {"pk": 1})()
        creator.region_name = "demo-region"
        creator.original_app = type("FakeApp", (), {"upgrade_group_id": 1})()
        creator.is_deploy = False
        template = {
            "service_cname": "vm-root",
            "service_key": "service-1",
            "version": "1.0.0",
            "deploy_version": "20260521",
            "arch": "amd64",
            "share_image": "registry.example.com/team/windows-root:v1",
            "extend_method": "vm",
            "service_type": "vm",
            "extend_method_map": {"min_node": 1},
            "vm": {
                "boot_mode": "bios",
                "boot_source_format": "qcow2",
                "disk_layout": [{"disk_key": "disk", "disk_role": "root"}],
            },
        }

        component = creator._template_to_component("tenant-a", template)

        self.assertEqual("vm", component.service_type)


class MarketAppNewComponentsResourceLimitTests(TestCase):
    # capability_id: console.market-app.install-unlimited-resources
    def test_template_to_component_preserves_explicit_unlimited_cpu_and_memory(self):
        creator = NewComponents.__new__(NewComponents)
        creator.user = type("FakeUser", (), {"pk": 1})()
        creator.region_name = "demo-region"
        creator.original_app = type("FakeApp", (), {"upgrade_group_id": 1})()
        creator.is_deploy = False
        template = {
            "service_cname": "nginx",
            "service_key": "service-1",
            "version": "alpine",
            "deploy_version": "20260622152758",
            "arch": "amd64",
            "share_image": "goodrain.me/nginx:20260622152758",
            "image": "registry.example.com/nginx:alpine",
            "extend_method": "stateless_multiple",
            "service_type": "application",
            "memory": 0,
            "cpu": 0,
            "extend_method_map": {
                "min_node": 1,
                "min_memory": 64,
                "init_memory": 0,
                "max_memory": 65536,
                "step_memory": 64,
            },
        }

        component = creator._template_to_component("tenant-a", template)

        self.assertEqual(0, component.min_memory)
        self.assertEqual(0, component.min_cpu)
        self.assertEqual(0, component.total_memory)

    def test_template_to_component_defaults_daemonset_node_when_node_scaling_is_absent(self):
        creator = NewComponents.__new__(NewComponents)
        creator.user = type("FakeUser", (), {"pk": 1})()
        creator.region_name = "demo-region"
        creator.original_app = type("FakeApp", (), {"upgrade_group_id": 1})()
        creator.is_deploy = False
        template = {
            "service_cname": "agent",
            "service_key": "service-1",
            "version": "alpine",
            "deploy_version": "20260622152758",
            "arch": "amd64",
            "share_image": "goodrain.me/agent:20260622152758",
            "image": "registry.example.com/agent:alpine",
            "extend_method": "daemonset",
            "service_type": "application",
            "extend_method_map": {
                "min_memory": 64,
                "init_memory": 1024,
                "max_memory": 65536,
                "step_memory": 64,
                "container_cpu": 600,
            },
        }

        component = creator._template_to_component("tenant-a", template)

        self.assertEqual(1, component.min_node)
        self.assertEqual(1024, component.min_memory)
        self.assertEqual(600, component.min_cpu)
        self.assertEqual(1024, component.total_memory)
