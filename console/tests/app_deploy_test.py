# -*- coding: utf-8 -*-
import collections
import json
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

from console.services.app_actions import app_deploy as app_deploy_module  # noqa: E402


class MarketServiceSourceUpdateTestCase(TestCase):
    def test_update_service_source_prefers_share_image_when_stale_share_slug_path_exists(self):
        tenant = mock.Mock(tenant_id="tenant-1")
        service = mock.Mock(service_id="service-1")
        service_source = mock.Mock(
            version="1.0.0",
            group_key="group-key",
        )
        service_source.is_install_from_cloud.return_value = False
        service_source.get_market_name.return_value = None

        with mock.patch.object(
                app_deploy_module.service_source_repo,
                "get_service_source",
                return_value=service_source), mock.patch.object(
                    app_deploy_module.service_source_repo,
                    "update_service_source") as update_service_source:
            market_service = app_deploy_module.MarketService(tenant, service, version="1.2.3")
            market_service._update_service_source(
                {
                    "share_image": "registry.example.com/demo/web:1.2.3",
                    "share_slug_path": "/grdata/build/tenant/demo/stale-slug.tgz",
                    "service_image": {
                        "image_url": "registry.example.com/demo/web:1.2.3",
                        "cmd": "",
                    },
                    "service_slug": {
                        "slug_path": "/grdata/build/tenant/demo/stale-slug.tgz",
                        "namespace": "demo-space",
                    },
                    "service_share_uuid": "svc-1+svc-1",
                    "deploy_version": "snapshot-deploy-version",
                },
                version="1.2.3",
                template_updatetime=None,
            )

        kwargs = update_service_source.call_args[1]
        extend_info = json.loads(kwargs["extend_info"])
        self.assertEqual(extend_info["image_url"], "registry.example.com/demo/web:1.2.3")
        self.assertEqual(extend_info["source_service_share_uuid"], "svc-1+svc-1")
        self.assertEqual(extend_info["source_deploy_version"], "snapshot-deploy-version")
        self.assertNotIn("slug_path", extend_info)
