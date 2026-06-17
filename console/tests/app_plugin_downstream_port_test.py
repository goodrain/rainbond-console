# -*- coding: utf-8 -*-
import collections
import collections.abc
import os
import sys
from types import ModuleType
from types import SimpleNamespace
from unittest import TestCase, mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from console.services.plugin import app_plugin as app_plugin_module  # noqa: E402
from console.services.plugin.app_plugin import AppPluginService  # noqa: E402
from www.models.plugin import ServicePluginConfigVar  # noqa: E402


# capability_id: console.plugin.downstream-port-config
class CreatePluginCfg4MarketsvcDownstreamPortTest(TestCase):
    def setUp(self):
        self.svc = AppPluginService()
        self.service = SimpleNamespace(service_id="src-service-id")

    def test_downstream_port_reads_dest_service_attributes(self):
        # dest_service is an ORM model object: has .service_id / .service_alias
        # attributes but NO .get method (it is not a dict).
        dest_service = SimpleNamespace(service_id="dst-id", service_alias="dst-alias")

        components = [{"service_id": "dst-component-id", "service_share_uuid": "share-uuid"}]
        service_plugin_config_vars = [{
            "service_meta_type": "downstream_port",
            "injection": "auto",
            "dest_service_id": "dst-component-id",
            "container_port": 8080,
            "attrs": "{}",
            "protocol": "http",
        }]

        captured = {}

        def fake_bulk_create(config_list):
            captured["config_list"] = config_list

        with mock.patch.object(app_plugin_module, "app_service") as mock_app_service, \
                mock.patch.object(ServicePluginConfigVar.objects, "bulk_create", side_effect=fake_bulk_create):
            mock_app_service.get_service_by_service_key.return_value = dest_service
            self.svc.create_plugin_cfg_4marketsvc(
                tenant=mock.MagicMock(),
                service=self.service,
                version="v1",
                plugin_id="plugin-id",
                build_version="build-1",
                components=components,
                service_plugin_config_vars=service_plugin_config_vars,
            )

        config_list = captured["config_list"]
        self.assertEqual(len(config_list), 1)
        self.assertEqual(config_list[0].dest_service_id, "dst-id")
        self.assertEqual(config_list[0].dest_service_alias, "dst-alias")
