# -*- coding: utf-8 -*-
import collections
import os
import sys
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

from console.services import enterprise_services as enterprise_module  # noqa: E402


class EnterpriseNodeDiskTest(TestCase):
    def test_get_nodes_includes_container_filesystem_usage(self):
        gib = 1024 * 1024 * 1024
        region_response = {
            "list": [{
                "name": "worker-1",
                "conditions": [{"type": "Ready", "status": "True"}],
                "unschedulable": False,
                "roles": ["worker"],
                "architecture": "amd64",
                "resource": {
                    "req_cpu": 1,
                    "cap_cpu": 4,
                    "req_memory": 2048,
                    "cap_memory": 8192,
                    "req_container_disk": 75 * gib,
                    "cap_container_disk": 100 * gib,
                },
            }]
        }

        with mock.patch.object(
                enterprise_module.region_api,
                "get_cluster_nodes",
                return_value=({}, region_response)):
            nodes, _ = enterprise_module.enterprise_services.get_nodes("test-region")

        self.assertEqual(nodes[0]["req_docker_partition"], 75)
        self.assertEqual(nodes[0]["cap_docker_partition"], 100)
