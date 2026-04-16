# -*- coding: utf-8 -*-
import collections
import json
import os
import sys
from datetime import datetime
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

from console.services.app_actions import app_manage as app_manage_module  # noqa: E402
from www.apiclient.regionapibaseclient import RegionApiBaseHttpClient  # noqa: E402


class AppManageMarketBuildPreferenceTests(TestCase):
    def test_deploy_services_info_prefers_image_payload_when_template_still_has_share_slug_path(self):
        tenant = mock.Mock(creater="creator", enterprise_id="eid", tenant_id="tenant-id")
        user = mock.Mock(user_id=7)
        service = mock.Mock(
            service_id="service-1",
            build_upgrade=False,
            language=None,
            tenant_id="tenant-id",
            arch="amd64",
            service_source="market",
            cmd="python app.py",
            image="goodrain.me/runner:latest-amd64",
        )
        service_source = mock.Mock(
            extend_info=json.dumps({
                "source_service_share_uuid": "svc-1+svc-1",
                "source_deploy_version": "snapshot-deploy-version",
            }),
        )
        template_apps = {
            "apps": [{
                "service_share_uuid": "svc-1+svc-1",
                "service_key": "svc-1",
                "share_image": "registry.example.com/demo/web:1.2.3",
                "share_slug_path": "/grdata/build/tenant/demo/stale-slug.tgz",
                "service_image": {
                    "hub_user": "hub-user",
                    "hub_password": "hub-password",
                },
                "service_slug": {
                    "slug_path": "/grdata/build/tenant/demo/stale-slug.tgz",
                    "namespace": "snapshot-space",
                },
            }],
            "update_time": datetime(2026, 4, 3, 0, 0, 0),
        }

        with mock.patch.object(app_manage_module, "check_account_quota", return_value=True), \
                mock.patch.object(app_manage_module.env_var_repo, "get_build_envs", return_value={}), \
                mock.patch.object(app_manage_module.service_source_repo, "get_service_source", return_value=service_source):
            service_manage = app_manage_module.AppManageService()
            code, body = service_manage.deploy_services_info({}, [service], tenant, user, None, template_apps, False, "demo-region")

        self.assertEqual(code, 200)
        build_info = body["build_infos"][0]
        self.assertEqual(build_info["kind"], "build_from_market_image")
        self.assertEqual(build_info["image_info"]["image_url"], "registry.example.com/demo/web:1.2.3")
        self.assertEqual(build_info["image_info"]["user"], "hub-user")
        self.assertEqual(build_info["image_info"]["password"], "hub-password")
        self.assertNotIn("slug_info", build_info)


class AppManageStartErrorTests(TestCase):
    def test_start_returns_region_error_reason_instead_of_generic_component_error(self):
        tenant = mock.Mock(creater="creator", enterprise_id="eid", tenant_name="demo-team")
        user = mock.Mock(nick_name="tester")
        service = mock.Mock(
            service_source="vm_run",
            service_region="demo-region",
            service_alias="demo-vm",
            create_status="complete",
            extend_method="vm",
        )
        region_error = RegionApiBaseHttpClient.CallApiError(
            "region api",
            "http://region/v2/tenants/demo/services/demo-vm/start",
            "POST",
            mock.Mock(status=500),
            {
                "msg": "vm start blocked: no schedulable node",
            },
        )

        with mock.patch.object(app_manage_module, "check_account_quota", return_value=True), \
                mock.patch.object(app_manage_module.region_api, "start_service", side_effect=region_error):
            service_manage = app_manage_module.AppManageService()
            code, msg = service_manage.start(tenant, service, user, oauth_instance=None)

        self.assertEqual(500, code)
        self.assertEqual("vm start blocked: no schedulable node", msg)
