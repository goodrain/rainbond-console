# -*- coding: utf-8 -*-
import importlib.util
import os
from pathlib import Path
from unittest import TestCase, mock


def load_initializer():
    repository_root = Path(__file__).resolve().parents[2]
    initializer_path = repository_root / "scripts" / "init_default_region.py"
    spec = importlib.util.spec_from_file_location("init_default_region", str(initializer_path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# capability_id: console.region.default-initialization
class DefaultRegionInitializerTest(TestCase):
    def setUp(self):
        self.initializer = load_initializer()
        self.region_model = mock.Mock()
        self.region_manager = self.region_model.objects
        self.environment = {
            "DB_TYPE": "dm",
            "REGION_URL": "https://api.example.invalid",
            "REGION_HTTP_DOMAIN": "apps.example.invalid",
            "REGION_TCP_DOMAIN": "tcp.example.invalid",
        }

    def test_creates_default_region_for_empty_database(self):
        self.region_manager.exists.return_value = False
        self.region_manager.get_or_create.return_value = (mock.Mock(), True)

        with mock.patch.dict(os.environ, self.environment, clear=False), \
                mock.patch.object(self.initializer, "make_uuid", return_value="region-id"), \
                mock.patch.object(self.initializer, "read_required_file", side_effect=["content-a", "content-b", "content-c"]):
            created = self.initializer.initialize_default_region(self.region_model)

        self.assertTrue(created)
        self.region_manager.get_or_create.assert_called_once_with(
            region_name="rainbond",
            defaults={
                "region_id": "region-id",
                "region_alias": "Built-in Cluster",
                "url": "https://api.example.invalid",
                "status": "1",
                "desc": "The current cluster is the default built-in cluster",
                "wsurl": "ws://rbd-api-websocket:6060",
                "httpdomain": "apps.example.invalid",
                "tcpdomain": "tcp.example.invalid",
                "scope": "default",
                "ssl_ca_cert": "content-a",
                "cert_file": "content-b",
                "key_file": "content-c",
            },
        )

    def test_skips_creation_when_a_region_already_exists(self):
        self.region_manager.exists.return_value = True

        with mock.patch.object(self.initializer, "read_required_file") as read_required_file:
            created = self.initializer.initialize_default_region(self.region_model)

        self.assertFalse(created)
        self.region_manager.create.assert_not_called()
        self.region_manager.get_or_create.assert_not_called()
        read_required_file.assert_not_called()

    def test_handles_a_region_created_by_a_concurrent_startup(self):
        self.region_manager.exists.return_value = False
        self.region_manager.get_or_create.return_value = (mock.Mock(), False)

        with mock.patch.object(self.initializer, "read_required_file", side_effect=["content-a", "content-b", "content-c"]):
            created = self.initializer.initialize_default_region(self.region_model)

        self.assertFalse(created)
        self.region_manager.get_or_create.assert_called_once()
