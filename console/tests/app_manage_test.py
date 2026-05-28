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
if "openapi_client" not in sys.modules:
    openapi_client_module = ModuleType("openapi_client")
    configuration_module = ModuleType("openapi_client.configuration")
    rest_module = ModuleType("openapi_client.rest")

    class _DummyConfiguration(object):
        def __init__(self):
            self.client_side_validation = False
            self.host = ""
            self.api_key = {}

    class _DummyApiException(Exception):
        status = 500
        body = ""

    openapi_client_module.ApiClient = object
    openapi_client_module.MarketOpenapiApi = object
    configuration_module.Configuration = _DummyConfiguration
    rest_module.ApiException = _DummyApiException

    sys.modules["openapi_client"] = openapi_client_module
    sys.modules["openapi_client.configuration"] = configuration_module
    sys.modules["openapi_client.rest"] = rest_module

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from django.test import TestCase as DjangoTestCase  # noqa: E402
from console.services.app_actions import app_manage as app_manage_module  # noqa: E402
from www.apiclient.regionapibaseclient import RegionApiBaseHttpClient  # noqa: E402
from www.models.main import TenantServiceInfo, VirtualMachineImage  # noqa: E402


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

    def test_vertical_upgrade_returns_region_reason_instead_of_generic_component_error(self):
        tenant = mock.Mock(creater="creator", enterprise_id="eid", tenant_name="demo-team")
        user = mock.Mock(nick_name="tester")
        service = mock.Mock(
            min_memory=4096,
            service_region="demo-region",
            service_alias="demo-vm",
            create_status="complete",
            extend_method="vm",
        )
        region_error = RegionApiBaseHttpClient.CallApiError(
            "region api",
            "http://region/v2/tenants/demo/services/demo-vm/vertical",
            "PUT",
            mock.Mock(status=409),
            {
                "msg_show": "当前虚拟机不满足热更新条件，请停机后再修改规格。"
            },
        )

        with mock.patch.object(app_manage_module, "check_account_quota", return_value=True), \
                mock.patch.object(app_manage_module.region_api, "vertical_upgrade", side_effect=region_error):
            service_manage = app_manage_module.AppManageService()
            code, msg = service_manage.vertical_upgrade(
                tenant,
                service,
                user,
                8192,
                oauth_instance=None,
                new_cpu=6000,
            )

        self.assertEqual(409, code)
        self.assertEqual("当前虚拟机不满足热更新条件，请停机后再修改规格。", msg)


class AppManageVMRestoreDeleteTests(DjangoTestCase):

    # capability_id: console.vm-template-import.delete-restoring-vm
    def test_delete_allows_restoring_vm_to_skip_running_guard(self):
        tenant = mock.Mock(tenant_name="demo-team", enterprise_id="eid")
        user = mock.Mock()
        service = mock.Mock(
            service_id="service-vm",
            service_alias="service-vm",
            service_source="vm_run",
            service_region="demo-region",
            create_status="complete",
            extend_method="vm",
        )

        with mock.patch.object(
                app_manage_module.region_api,
                "check_service_status",
                return_value={"bean": {"cur_status": "restoring"}}), \
                mock.patch.object(
                    app_manage_module.AppManageService,
                    "_AppManageService__is_service_related",
                    return_value=(False, "")), \
                mock.patch.object(
                    app_manage_module.AppManageService,
                    "_AppManageService__is_service_mnt_related",
                    return_value=(False, "")), \
                mock.patch.object(app_manage_module.AppManageService, "get_app_by_service", return_value=None), \
                mock.patch.object(app_manage_module.AppManageService, "truncate_service", return_value=(200, "success")) as truncate_service:
            code, msg = app_manage_module.AppManageService().delete(user, tenant, service, True)

        self.assertEqual(200, code)
        self.assertEqual("success", msg)
        truncate_service.assert_called_once_with(tenant, service, user, None)

    # capability_id: console.vm-template-import.delete-restoring-vm
    def test_batch_delete_allows_restoring_vm_to_skip_running_guard(self):
        tenant = mock.Mock(tenant_name="demo-team", enterprise_id="eid")
        user = mock.Mock()
        service = mock.Mock(
            service_id="service-vm",
            service_alias="service-vm",
            service_source="vm_run",
            service_region="demo-region",
            create_status="complete",
            extend_method="vm",
        )

        with mock.patch.object(
                app_manage_module.region_api,
                "check_service_status",
                return_value={"bean": {"cur_status": "restoring"}}), \
                mock.patch.object(
                    app_manage_module.AppManageService,
                    "_AppManageService__is_service_mnt_related",
                    return_value=(False, "")), \
                mock.patch.object(
                    app_manage_module.AppManageService,
                    "_AppManageService__is_service_bind_domain",
                    return_value=False), \
                mock.patch.object(
                    app_manage_module.AppManageService,
                    "_AppManageService__is_service_has_plugins",
                    return_value=False), \
                mock.patch.object(
                    app_manage_module.AppManageService,
                    "_AppManageService__is_service_related_by_other_app_service",
                    return_value=False), \
                mock.patch.object(app_manage_module.AppManageService, "get_app_by_service", return_value=None), \
                mock.patch.object(app_manage_module.AppManageService, "truncate_service", return_value=(200, "success")) as truncate_service:
            code, msg = app_manage_module.AppManageService().batch_delete(user, tenant, service, is_force=True, is_del_app=False)

        self.assertEqual(200, code)
        self.assertEqual("success", msg)
        truncate_service.assert_called_once_with(tenant, service, user, None)


class AppManageIncompleteVMCleanupTests(DjangoTestCase):

    # capability_id: console.vm-asset.incomplete-service-cleanup-preserves-ready-assets
    def test_truncate_service_keeps_ready_uploaded_vm_asset(self):
        tenant = mock.Mock(tenant_id="tenant-a")
        asset = VirtualMachineImage.objects.create(
            tenant_id="tenant-a",
            name="win",
            image_url="default:win",
            source_type="upload",
            source_uri="/grdata/package_build/temp/events/demo-event",
            status="ready"
        )
        service = TenantServiceInfo.objects.create(
            service_id="service-vm-a",
            tenant_id="tenant-a",
            service_key="service-vm-a",
            service_alias="service-vm-a",
            service_cname="service-vm-a",
            service_region="demo-region",
            category="application",
            version="v1",
            image=asset.image_url,
            extend_method="vm",
            service_source="vm_run",
            create_status="creating",
            k8s_component_name="service-vm-a-k8s"
        )

        service_manage = app_manage_module.AppManageService()
        with mock.patch.object(app_manage_module.delete_service_repo, "create_delete_service"):
            service_manage._truncate_service(tenant, service)

        self.assertTrue(
            VirtualMachineImage.objects.filter(tenant_id="tenant-a", ID=asset.ID).exists()
        )
