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
from rest_framework.test import APIRequestFactory  # noqa: E402

django.setup()

from console.services.share_services import share_service as share_service_instance  # noqa: E402
from console.services import share_services as share_services_module  # noqa: E402
from console.views import service_share  # noqa: E402
from console.views.service_share import ServiceShareInfoView, ServiceShareRecordView  # noqa: E402
from console.repositories import share_repo as share_repo_module  # noqa: E402


# capability_id: console.service-share.create-record
class ServiceShareRecordViewTestCase(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = ServiceShareRecordView()
        self.view.team = mock.Mock(tenant_id=1, tenant_name="demo-team")
        self.view.tenant = mock.Mock(tenant_name="demo-team")
        self.view.user = mock.Mock(user_id=1)
        self.view.response_region = "demo-region"

    def make_request(self, payload):
        return self.view.initialize_request(
            self.factory.post("/console/teams/demo-team/groups/30/share/record", payload, format="json"))

    # capability_id: console.service-share.create-snapshot-record
    def test_post_snapshot_mode_uses_hidden_template_app_id(self):
        request = self.make_request({"scope": "team", "snapshot_mode": True, "snapshot_app_id": "origin-app-id"})
        share_record = mock.Mock()
        share_record.to_dict.return_value = {"group_share_id": "share-uuid"}
        hidden_template = mock.Mock(app_id="hidden-app-id")

        with mock.patch.object(
                service_share.group_repo, "get_group_count_by_team_id_and_group_id", return_value=1), \
                mock.patch.object(service_share.share_service, "check_service_source", return_value=None), \
                mock.patch("console.services.group_service.group_service.get_group_or_404",
                           return_value=mock.Mock()) as get_group_mock, \
                mock.patch.object(
                    service_share.app_version_service,
                    "get_or_create_hidden_template",
                    return_value=(mock.Mock(), hidden_template)), \
                mock.patch.object(
                    service_share.share_service,
                    "create_service_share_record",
                    return_value=share_record) as create_record_mock, \
                mock.patch.object(service_share, "make_uuid", return_value="share-uuid"):
            response = self.view.post(request, "demo-team", "30")

        self.assertEqual(response.status_code, 200)
        get_group_mock.assert_called_once_with(self.view.tenant, self.view.response_region, 30)
        _, kwargs = create_record_mock.call_args
        self.assertEqual(kwargs["app_id"], "hidden-app-id")
        self.assertEqual(kwargs["group_share_id"], "share-uuid")

    # capability_id: console.service-share.error-response
    def test_post_returns_500_response_for_unexpected_exception(self):
        request = self.make_request({"scope": "team"})

        with mock.patch.object(
                service_share.group_repo, "get_group_count_by_team_id_and_group_id", return_value=1), \
                mock.patch.object(service_share.share_service, "check_service_source", return_value=None), \
                mock.patch.object(
                    service_share.share_service,
                    "create_service_share_record",
                    side_effect=RuntimeError("boom")), \
                mock.patch.object(service_share, "make_uuid", return_value="share-uuid"):
            response = self.view.post(request, "demo-team", "30")

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data["msg"], "boom")
        self.assertEqual(response.data["msg_show"], "系统异常")


# capability_id: console.service-share.view-info
class ServiceShareInfoViewTestCase(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = ServiceShareInfoView()
        self.view.team = mock.Mock(tenant_id=1, tenant_name="demo-team")

    def make_request(self):
        return self.view.initialize_request(
            self.factory.get("/console/teams/demo-team/share/30/info")
        )

    # capability_id: console.service-share.view-snapshot-info
    def test_get_returns_snapshot_template_payload(self):
        request = self.make_request()
        share_record = mock.Mock(
            app_id="hidden-app-id",
            share_version="1.0.3",
            scope="team",
            is_success=False,
            step=1,
            group_id=30,
        )
        snapshot_version = mock.Mock(
            source="local",
            template_type="application_version",
            app_template=json.dumps(
                {
                    "apps": [{"service_cname": "web"}],
                    "plugins": [{"plugin_id": "demo-plugin"}],
                    "k8s_resources": [{"name": "demo-configmap"}],
                }
            ),
        )

        with mock.patch.object(
            service_share.share_service,
            "get_service_share_record_by_ID",
            return_value=share_record,
        ), mock.patch.object(
            service_share.rainbond_app_repo,
            "get_app_version",
            return_value=snapshot_version,
        ):
            response = self.view.get(request, "demo-team", "30")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["data"]["bean"]["share_service_list"],
            [{"service_cname": "web"}],
        )
        self.assertEqual(
            response.data["data"]["bean"]["share_plugin_list"],
            [{"plugin_id": "demo-plugin"}],
        )
        self.assertEqual(
            response.data["data"]["bean"]["share_k8s_resources"],
            [{"name": "demo-configmap"}],
        )
        self.assertEqual(response.data["data"]["bean"]["publish_mode"], "snapshot")


class ServiceShareRecordListViewTestCase(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = ServiceShareRecordView()
        self.view.tenant = mock.Mock(enterprise_id="eid")
        self.view.user = mock.Mock(user_id=1)

    def test_get_filters_pending_records_without_any_version(self):
        request = self.view.initialize_request(
            self.factory.get("/console/teams/demo-team/groups/30/share/record", {"page": 1, "page_size": 10})
        )
        invalid_pending_record = mock.Mock(
            share_app_model_name="",
            app_id="",
            share_version="",
            share_version_alias="",
            share_app_version_info="",
            share_store_name="demo-store",
            share_app_market_name="demo-store-id",
            scope="goodrain",
            create_time="2026-03-30 13:48:00",
            step=1,
            is_success=False,
            status=0,
            ID=12,
            save=mock.Mock(),
        )

        with mock.patch.object(
            service_share.share_repo,
            "get_service_share_records_by_groupid",
            return_value=(1, [invalid_pending_record]),
        ), mock.patch.object(
            service_share.rainbond_app_repo,
            "get_rainbond_app_version_by_record_id",
            return_value=None,
        ):
            response = self.view.get(request, "demo-team", "30")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["bean"]["total"], 0)
        self.assertEqual(response.data["data"]["list"], [])


class ShareRepoVMServiceSourceTestCase(TestCase):
    # capability_id: console.service-share.vm-qcow2-publish
    def test_get_service_list_keeps_vm_run_components_for_publish(self):
        query = mock.Mock()
        query.exclude.return_value = query
        team = mock.Mock(tenant_id=1)

        with mock.patch.object(
                share_repo_module.ServiceGroupRelation.objects,
                "filter",
                return_value=[mock.Mock(service_id="svc-vm")],
        ), mock.patch.object(
                share_repo_module.TenantServiceInfo.objects,
                "filter",
                return_value=query,
        ) as service_filter:
            result = share_repo_module.share_repo.get_service_list_by_group_id(team, 30)

        service_filter.assert_called_once_with(service_id__in=["svc-vm"])
        query.exclude.assert_called_once_with(service_source="third_party")
        self.assertIs(result, query)


# capability_id: console.service-share.stopped-component-publish
# capability_id: console.service-share.vm-shutdown-guard
class ShareServiceCheckServiceSourceTestCase(TestCase):
    def test_check_service_source_allows_stopped_non_vm_component_publish(self):
        team = mock.Mock(tenant_id=1, enterprise_id="eid")
        service = mock.Mock(service_id="svc-web", extend_method="docker", service_source="source_code")

        with mock.patch.object(share_services_module.share_repo, "get_service_list_by_group_id",
                               return_value=[service]), \
                mock.patch.object(share_services_module.k8s_resources_repo, "list_by_app_id", return_value=[]), \
                mock.patch.object(
                    share_services_module.base_service,
                    "status_multi_service",
                    return_value=[{"service_id": "svc-web", "status": "closed"}]):
            result = share_service_instance.check_service_source(
                team=team,
                team_name="demo-team",
                group_id=30,
                region_name="demo-region",
            )

        self.assertEqual(200, result["code"])
        self.assertTrue(result["success"])

    def test_check_service_source_rejects_running_vm_publish(self):
        team = mock.Mock(tenant_id=1, enterprise_id="eid")
        service = mock.Mock(service_id="svc-vm", extend_method="vm")

        with mock.patch.object(share_services_module.share_repo, "get_service_list_by_group_id",
                               return_value=[service]), \
                mock.patch.object(share_services_module.k8s_resources_repo, "list_by_app_id", return_value=[]), \
                mock.patch.object(
                    share_services_module.base_service,
                    "status_multi_service",
                    return_value=[{"service_id": "svc-vm", "status": "running"}]):
            result = share_service_instance.check_service_source(
                team=team,
                team_name="demo-team",
                group_id=30,
                region_name="demo-region",
            )

        self.assertEqual(400, result["code"])
        self.assertEqual("虚拟机发布前必须关机，请先关闭虚拟机组件后再发布。", result["msg_show"])

    def test_check_service_source_allows_closed_vm_publish(self):
        team = mock.Mock(tenant_id=1, enterprise_id="eid")
        service = mock.Mock(service_id="svc-vm", extend_method="vm")

        with mock.patch.object(share_services_module.share_repo, "get_service_list_by_group_id",
                               return_value=[service]), \
                mock.patch.object(share_services_module.k8s_resources_repo, "list_by_app_id", return_value=[]), \
                mock.patch.object(
                    share_services_module.base_service,
                    "status_multi_service",
                    return_value=[{"service_id": "svc-vm", "status": "closed"}]):
            result = share_service_instance.check_service_source(
                team=team,
                team_name="demo-team",
                group_id=30,
                region_name="demo-region",
            )

        self.assertEqual(200, result["code"])
        self.assertTrue(result["success"])

    def test_check_service_source_only_checks_vm_status_in_mixed_app(self):
        team = mock.Mock(tenant_id=1, enterprise_id="eid")
        vm_service = mock.Mock(service_id="svc-vm", extend_method="vm", service_source="")
        web_service = mock.Mock(service_id="svc-web", extend_method="docker", service_source="source_code")

        with mock.patch.object(share_services_module.share_repo, "get_service_list_by_group_id",
                               return_value=[vm_service, web_service]), \
                mock.patch.object(share_services_module.k8s_resources_repo, "list_by_app_id", return_value=[]), \
                mock.patch.object(
                    share_services_module.base_service,
                    "status_multi_service",
                    return_value=[{"service_id": "svc-vm", "status": "closed"}]) as status_multi_service_mock:
            result = share_service_instance.check_service_source(
                team=team,
                team_name="demo-team",
                group_id=30,
                region_name="demo-region",
            )

        self.assertEqual(200, result["code"])
        status_multi_service_mock.assert_called_once_with(
            region="demo-region", tenant_name="demo-team", service_ids=["svc-vm"], enterprise_id="eid")


class ShareServiceCreateSnapshotPublishTestCase(TestCase):
    def setUp(self):
        self.tenant = mock.Mock(enterprise_id="eid", tenant_name="demo-team")
        self.team = mock.Mock(tenant_name="demo-team", tenant_id=1, enterprise_id="eid")
        self.user = mock.Mock(user_id=7)
        self.region_name = "demo-region"
        self.share_record = mock.Mock(
            ID=9,
            app_id="hidden-app-id",
            share_version="0.0.2",
            share_app_market_name="",
            group_id=30,
        )
        self.share_record.save = mock.Mock()
        self.runtime_app = mock.Mock(
            governance_mode="BUILD_IN_SERVICE_MESH",
        )
        self.target_template = mock.Mock(
            scope="enterprise",
            app_name="enterprise-template",
            arch="amd64",
            save=mock.Mock(),
        )
        self.snapshot_version = mock.Mock(
            template_type="application_version",
            app_template=json.dumps(
                {
                    "template_version": "v2",
                    "group_key": "hidden-app-id",
                    "group_name": "demo-app",
                    "group_version": "0.0.2",
                    "governance_mode": "BUILD_IN_SERVICE_MESH",
                    "k8s_resources": [{"name": "from-snapshot"}],
                    "app_config_groups": [{"name": "cg-snapshot"}],
                    "ingress_http_routes": [{"host": "demo.example.com"}],
                    "plugins": [{
                        "plugin_id": "snapshot-plugin",
                        "plugin_alias": "snapshot-plugin",
                        "plugin_key": "snapshot-plugin",
                        "build_version": "1.0.0",
                    }],
                    "apps": [{
                        "service_id": "svc-snapshot",
                        "service_key": "svc-snapshot",
                        "service_share_uuid": "svc-snapshot+svc-snapshot",
                        "service_alias": "svc-snapshot",
                        "service_cname": "svc-snapshot",
                        "need_share": True,
                        "arch": "amd64",
                        "service_related_plugin_config": [],
                    }],
                }
            )
        )
        self.share_info = {
            "app_version_info": {
                "app_model_id": "target-app-id",
                "version": "1.2.3",
                "version_alias": "stable",
                "describe": "publish from snapshot",
                "is_platform_plugin": False,
            },
            "share_service_list": [{
                "service_id": "svc-current",
                "service_key": "svc-current",
                "service_share_uuid": "svc-current+svc-current",
                "service_alias": "svc-current",
                "service_cname": "svc-current",
                "need_share": True,
                "arch": "amd64",
                "service_related_plugin_config": [],
            }],
            "share_plugin_list": [{
                "plugin_id": "current-plugin",
                "plugin_alias": "current-plugin",
                "build_version": "9.9.9",
                "origin_share_id": "current-plugin",
            }],
            "share_k8s_resources": [{"name": "from-current"}],
        }

    def test_create_share_info_uses_snapshot_template_payload_instead_of_request_component_payload(self):
        app_version_instance = mock.Mock(save=mock.Mock(), arch="amd64")
        snapshot_filter = mock.Mock()
        snapshot_filter.first.return_value = self.target_template

        with mock.patch.object(share_services_module.rainbond_app_repo, "get_app_version", return_value=self.snapshot_version), \
                mock.patch.object(share_services_module.RainbondCenterApp.objects, "filter", return_value=snapshot_filter), \
                mock.patch("console.services.group_service.group_service.get_app_by_id",
                           return_value=self.runtime_app), \
                mock.patch.object(share_services_module.ServiceSourceInfo.objects, "filter") as service_source_filter, \
                mock.patch.object(share_services_module.ServiceShareRecordEvent.objects, "filter") as service_events_filter, \
                mock.patch.object(share_services_module, "ServiceShareRecordEvent") as service_event_cls, \
                mock.patch.object(share_services_module, "PluginShareRecordEvent") as plugin_event_cls, \
                mock.patch.object(share_services_module, "RainbondCenterAppVersion",
                                  return_value=app_version_instance) as app_version_cls, \
                mock.patch.object(share_services_module.app_store, "get_app_hub_info", return_value={"hub": "demo"}), \
                mock.patch.object(share_services_module.app_store, "is_no_multiple_region_hub", return_value=False):
            service_source_filter.return_value.values_list.return_value = []
            service_events_filter.return_value.delete.return_value = None
            service_event_cls.return_value.save = mock.Mock()
            plugin_event_cls.return_value.save = mock.Mock()

            code, msg, bean = share_service_instance.create_share_info(
                tenant=self.tenant,
                region_name=self.region_name,
                share_record=self.share_record,
                share_team=self.team,
                share_user=self.user,
                share_info=self.share_info,
                use_force=True,
                user_id=None,
            )

        self.assertEqual(code, 200)
        self.assertEqual(msg, "分享信息处理成功")
        self.assertIsNotNone(bean)

        saved_template = json.loads(app_version_cls.call_args[1]["app_template"])
        self.assertEqual(saved_template["group_key"], "target-app-id")
        self.assertEqual(saved_template["group_name"], "enterprise-template")
        self.assertEqual(saved_template["group_version"], "1.2.3")
        self.assertEqual(saved_template["apps"][0]["service_id"], "svc-snapshot")
        self.assertEqual(saved_template["plugins"][0]["plugin_id"], "snapshot-plugin")
        self.assertEqual(saved_template["k8s_resources"][0]["name"], "from-snapshot")
        self.assertEqual(saved_template["app_config_groups"][0]["name"], "cg-snapshot")
        self.assertEqual(saved_template["ingress_http_routes"][0]["host"], "demo.example.com")

    def test_create_share_info_removes_stale_slug_fields_when_snapshot_component_is_published_as_image(self):
        self.snapshot_version.app_template = json.dumps(
            {
                "template_version": "v2",
                "group_key": "hidden-app-id",
                "group_name": "demo-app",
                "group_version": "0.0.2",
                "governance_mode": "BUILD_IN_SERVICE_MESH",
                "apps": [{
                    "service_id": "svc-snapshot",
                    "service_key": "svc-snapshot",
                    "service_share_uuid": "svc-snapshot+svc-snapshot",
                    "service_alias": "svc-snapshot",
                    "service_cname": "svc-snapshot",
                    "need_share": True,
                    "arch": "amd64",
                    "service_related_plugin_config": [],
                    "share_slug_path": "/grdata/build/tenant/demo/stale-slug.tgz",
                    "service_slug": {
                        "slug_path": "/grdata/build/tenant/demo/stale-slug.tgz",
                        "namespace": "snapshot-space",
                    },
                    "share_type": "slug",
                }],
                "plugins": [],
                "k8s_resources": [],
                "app_config_groups": [],
                "ingress_http_routes": [],
            }
        )
        app_version_instance = mock.Mock(save=mock.Mock(), arch="amd64")
        snapshot_filter = mock.Mock()
        snapshot_filter.first.return_value = self.target_template

        with mock.patch.object(share_services_module.rainbond_app_repo, "get_app_version", return_value=self.snapshot_version), \
                mock.patch.object(share_services_module.RainbondCenterApp.objects, "filter", return_value=snapshot_filter), \
                mock.patch("console.services.group_service.group_service.get_app_by_id",
                           return_value=self.runtime_app), \
                mock.patch.object(share_services_module.ServiceShareRecordEvent.objects, "filter") as service_events_filter, \
                mock.patch.object(share_services_module, "ServiceShareRecordEvent") as service_event_cls, \
                mock.patch.object(share_services_module, "PluginShareRecordEvent") as plugin_event_cls, \
                mock.patch.object(share_services_module, "RainbondCenterAppVersion",
                                  return_value=app_version_instance) as app_version_cls, \
                mock.patch.object(share_services_module.app_store, "get_app_hub_info",
                                  return_value={"hub": "demo-image-target"}), \
                mock.patch.object(share_services_module.app_store, "is_no_multiple_region_hub", return_value=False):
            service_events_filter.return_value.delete.return_value = None
            service_event_cls.return_value.save = mock.Mock()
            plugin_event_cls.return_value.save = mock.Mock()

            code, msg, bean = share_service_instance.create_share_info(
                tenant=self.tenant,
                region_name=self.region_name,
                share_record=self.share_record,
                share_team=self.team,
                share_user=self.user,
                share_info=self.share_info,
                use_force=True,
                user_id=None,
            )

        self.assertEqual(code, 200)
        self.assertEqual(msg, "分享信息处理成功")
        self.assertIsNotNone(bean)

        saved_template = json.loads(app_version_cls.call_args[1]["app_template"])
        saved_component = saved_template["apps"][0]
        self.assertEqual(saved_component["share_type"], "image")
        self.assertEqual(saved_component["service_image"], {"hub": "demo-image-target"})
        self.assertNotIn("share_slug_path", saved_component)
        self.assertNotIn("service_slug", saved_component)

    def test_sync_event_passes_vm_image_source_for_vm_publish(self):
        app_version = mock.Mock(
            template_type=share_service_instance.SNAPSHOT_TEMPLATE_TYPE,
            scope="team",
            version="1.2.3",
            update_time=None,
            save=mock.Mock(),
        )
        app_version.app_template = json.dumps(
            {
                "template_version": "v3",
                "group_key": "hidden-app-id",
                "group_name": "demo-app",
                "group_version": "0.0.2",
                "governance_mode": "BUILD_IN_SERVICE_MESH",
                "apps": [{
                    "service_id": "svc-snapshot",
                    "service_key": "svc-snapshot",
                    "service_share_uuid": "svc-snapshot+svc-snapshot",
                    "service_alias": "svc-snapshot",
                    "service_cname": "svc-snapshot",
                    "need_share": True,
                    "arch": "amd64",
                    "service_type": "vm",
                    "service_related_plugin_config": [],
                    "service_image": {"hub": "demo-image-target"},
                    "share_image": "registry.example.com/team/windows-root:v1",
                    "vm": {
                        "boot_mode": "bios",
                        "boot_source_format": "qcow2",
                        "disk_layout": [{
                            "disk_key": "disk",
                            "disk_role": "root",
                            "source_type": "registry",
                            "image": "registry.example.com/team/windows-root:v1",
                            "source_uri": "https://virt-export.example.com/volumes/manual22/disk.img.gz",
                        }]
                    },
                }],
                "plugins": [],
                "k8s_resources": [],
                "app_config_groups": [],
                "ingress_http_routes": [],
            }
        )
        record_event = mock.Mock(
            record_id=self.share_record.ID,
            service_key="svc-snapshot",
            service_id="svc-snapshot",
            service_alias="svc-snapshot",
            save=mock.Mock(),
        )
        self.user.nick_name = "demo-user"

        with mock.patch.object(
                share_services_module.rainbond_app_repo,
                "get_rainbond_app_version_by_record_id",
                return_value=app_version), \
                mock.patch.object(
                    share_service_instance,
                    "create_publish_event",
                    return_value=mock.Mock(event_id="event-id")), \
                mock.patch.object(share_services_module.region_api, "share_service", return_value=(None, {"bean": {"share_id": "sid", "event_id": "eid", "image_name": "registry.example.com/team/windows-root:v1"}})) as share_service_mock:
            share_service_instance.sync_event(
                self.user,
                self.region_name,
                self.team.tenant_name,
                record_event,
            )

        _, call_args, _ = share_service_mock.mock_calls[0]
        share_body = call_args[3]
        self.assertEqual("amd64", share_body["arch"])
        self.assertEqual(
            "https://virt-export.example.com/volumes/manual22/disk.img.gz",
            share_body["image_info"]["vm_image_source"],
        )

    def test_create_share_info_normalizes_no_inject_platform_plugin_positions_to_empty_list(self):
        self.share_info["app_version_info"].update({
            "is_platform_plugin": True,
            "plugin_id": "rainbond-demo-plugin",
            "plugin_name": "rainbond-demo-plugin",
            "plugin_type": "JSInject",
            "frontend_component": "svc-snapshot",
            "entry_path": "/static/main.js",
            "inject_position": ["NoInject"],
            "menu_title": "Demo Plugin",
            "route_path": "/plugins/demo-plugin",
        })
        app_version_instance = mock.Mock(save=mock.Mock(), arch="amd64")
        snapshot_filter = mock.Mock()
        snapshot_filter.first.return_value = self.target_template

        with mock.patch.object(share_services_module.rainbond_app_repo, "get_app_version", return_value=self.snapshot_version), \
                mock.patch.object(share_services_module.RainbondCenterApp.objects, "filter", return_value=snapshot_filter), \
                mock.patch("console.services.group_service.group_service.get_app_by_id",
                           return_value=self.runtime_app), \
                mock.patch.object(share_services_module.ServiceSourceInfo.objects, "filter") as service_source_filter, \
                mock.patch.object(share_services_module.ServiceShareRecordEvent.objects, "filter") as service_events_filter, \
                mock.patch.object(share_services_module, "ServiceShareRecordEvent") as service_event_cls, \
                mock.patch.object(share_services_module, "PluginShareRecordEvent") as plugin_event_cls, \
                mock.patch.object(share_services_module, "RainbondCenterAppVersion",
                                  return_value=app_version_instance) as app_version_cls, \
                mock.patch.object(share_services_module.app_store, "get_app_hub_info", return_value={"hub": "demo"}), \
                mock.patch.object(share_services_module.app_store, "is_no_multiple_region_hub", return_value=False):
            service_source_filter.return_value.values_list.return_value = []
            service_events_filter.return_value.delete.return_value = None
            service_event_cls.return_value.save = mock.Mock()
            plugin_event_cls.return_value.save = mock.Mock()

            code, msg, bean = share_service_instance.create_share_info(
                tenant=self.tenant,
                region_name=self.region_name,
                share_record=self.share_record,
                share_team=self.team,
                share_user=self.user,
                share_info=self.share_info,
                use_force=True,
                user_id=None,
            )

        self.assertEqual(code, 200)
        self.assertEqual(msg, "分享信息处理成功")
        self.assertIsNotNone(bean)

        saved_template = json.loads(app_version_cls.call_args[1]["app_template"])
        self.assertEqual(saved_template["platform_plugin"]["inject_position"], [])


class ShareServicePlatformPluginConfigTestCase(TestCase):
    def test_normalize_platform_plugin_positions_drops_no_inject_marker(self):
        positions = share_service_instance.normalize_platform_plugin_positions(
            ["Platform", "NoInject", "Team"]
        )

        self.assertEqual(positions, [])

    def test_normalize_platform_plugin_positions_preserves_regular_views(self):
        positions = share_service_instance.normalize_platform_plugin_positions(
            ["Platform", "Application", "Platform"]
        )

        self.assertEqual(positions, ["Platform", "Application"])


class ShareServiceVMPublishMetadataTestCase(TestCase):
    # capability_id: console.service-share.vm-qcow2-publish

    def test_build_vm_publish_metadata_from_runtime_attrs(self):
        service = {
            "extend_method": "vm",
            "image": "registry.example.com/team/windows-root:staging",
            "git_url": "https://virt-export.example.com/volumes/manual22/disk.img.gz",
            "service_volume_map_list": [{
                "volume_name": "disk",
                "volume_capacity": 80,
            }],
            "component_k8s_attributes": [
                {"name": "vm_boot_mode", "save_type": "string", "attribute_value": "bios"},
                {"name": "vm_boot_source_format", "save_type": "string", "attribute_value": "qcow2"},
                {
                    "name": "vm_disk_layout",
                    "save_type": "json",
                    "attribute_value": json.dumps([{
                        "disk_key": "disk",
                        "disk_name": "system-disk",
                        "disk_role": "root",
                        "device_type": "disk",
                        "order_index": 0,
                        "volume_name": "disk",
                    }]),
                },
            ],
        }

        payload = share_service_instance._build_vm_publish_metadata(service)

        self.assertEqual("bios", payload["boot_mode"])
        self.assertEqual("qcow2", payload["boot_source_format"])
        self.assertEqual("registry", payload["disk_layout"][0]["source_type"])
        self.assertEqual("registry.example.com/team/windows-root:staging", payload["disk_layout"][0]["image"])
        self.assertEqual("80Gi", payload["disk_layout"][0]["request_size"])
        self.assertEqual("https://virt-export.example.com/volumes/manual22/disk.img.gz", payload["disk_layout"][0]["source_uri"])

    def test_sync_vm_root_disk_image_updates_root_disk_only(self):
        service = {
            "vm": {
                "disk_layout": [
                    {"disk_role": "root", "image": "registry.example.com/old/root:v1"},
                    {"disk_role": "data", "image": "registry.example.com/old/data:v1"},
                ]
            }
        }

        share_service_instance._sync_vm_root_disk_image(
            service, "registry.example.com/new/root:v2")

        self.assertEqual("registry.example.com/new/root:v2", service["vm"]["disk_layout"][0]["image"])
        self.assertEqual("registry.example.com/old/data:v1", service["vm"]["disk_layout"][1]["image"])

    def test_resolve_publish_template_version_uses_v3_for_vm_components(self):
        version = share_service_instance._resolve_publish_template_version([
            {
                "service_type": "vm",
                "extend_method": "vm",
                "vm": {"boot_source_format": "qcow2"},
            }
        ])

        self.assertEqual("v3", version)

    def test_extract_vm_root_source_uri_falls_back_to_git_url(self):
        service = {
            "git_url": "https://virt-export.example.com/disk.img.gz",
            "vm": {
                "disk_layout": [{
                    "disk_role": "root",
                    "source_uri": "",
                }]
            }
        }

        source_uri = share_service_instance._extract_vm_root_source_uri(service)

        self.assertEqual("https://virt-export.example.com/disk.img.gz", source_uri)

    def test_prepare_vm_publish_image_source_creates_live_export_when_source_missing(self):
        service = {
            "service_id": "svc-vm",
            "service_alias": "vm-demo",
            "service_type": "vm",
            "vm": {
                "disk_layout": [{
                    "disk_role": "root",
                    "source_type": "registry",
                    "image": "registry.example.com/team/windows-root:v1",
                }]
            },
        }
        record_event = mock.Mock(service_id="svc-vm", service_alias="vm-demo")

        with mock.patch.object(
                share_services_module.region_api,
                "create_vm_export",
                return_value=(None, {"bean": {
                    "phase": "Ready",
                    "download_url": "https://virt-export.default.svc/volumes/manual22/disk.img.gz",
                }}),
        ) as create_export:
            source = share_service_instance._prepare_vm_publish_image_source(
                "demo-region", "demo-team", service, record_event, wait_seconds=0)

        self.assertEqual("https://virt-export.default.svc/volumes/manual22/disk.img.gz", source)
        create_export.assert_called_once()
        self.assertEqual(
            "https://virt-export.default.svc/volumes/manual22/disk.img.gz",
            service["vm"]["disk_layout"][0]["source_uri"],
        )

    def test_prepare_vm_publish_image_source_reuses_existing_export_url(self):
        service = {
            "service_type": "vm",
            "vm": {
                "disk_layout": [{
                    "disk_role": "root",
                    "source_uri": "https://virt-export.default.svc/volumes/manual22/disk.img.gz",
                }]
            },
        }
        record_event = mock.Mock(service_id="svc-vm", service_alias="vm-demo")

        with mock.patch.object(share_services_module.region_api, "create_vm_export") as create_export:
            source = share_service_instance._prepare_vm_publish_image_source(
                "demo-region", "demo-team", service, record_event, wait_seconds=0)

        self.assertEqual("https://virt-export.default.svc/volumes/manual22/disk.img.gz", source)
        create_export.assert_not_called()

    def test_prepare_vm_publish_image_source_refreshes_existing_export_url_when_forced(self):
        service = {
            "service_id": "svc-vm",
            "service_alias": "vm-demo",
            "service_type": "vm",
            "vm": {
                "disk_layout": [{
                    "disk_role": "root",
                    "source_uri": "https://virt-export.default.svc/volumes/manual22/old-disk.img.gz",
                }]
            },
        }
        record_event = mock.Mock(service_id="svc-vm", service_alias="vm-demo")

        with mock.patch.object(
                share_services_module.region_api,
                "create_vm_export",
                return_value=(None, {"bean": {
                    "phase": "Ready",
                    "download_url": "https://virt-export.default.svc/volumes/manual22/new-disk.img.gz",
                }}),
        ) as create_export:
            source = share_service_instance._prepare_vm_publish_image_source(
                "demo-region", "demo-team", service, record_event, wait_seconds=0, force_export=True)

        self.assertEqual("https://virt-export.default.svc/volumes/manual22/new-disk.img.gz", source)
        create_export.assert_called_once()
        self.assertEqual(
            "https://virt-export.default.svc/volumes/manual22/new-disk.img.gz",
            service["vm"]["disk_layout"][0]["source_uri"],
        )


class ShareServicePreferredAppTestCase(TestCase):
    # capability_id: console.service-share.local-app-versions
    def test_get_team_local_apps_versions_keeps_team_apps_when_preferred_app_is_hidden_snapshot(self):
        preferred_app = mock.Mock(
            app_name="hidden-snapshot",
            app_id="hidden-app",
            pic="hidden-pic",
            describe="hidden describe",
            dev_status="",
            scope="team",
        )
        team_app = mock.Mock(
            app_name="team-template",
            app_id="team-app",
            pic="team-pic",
            describe="team describe",
            dev_status="",
            scope="team",
        )

        with mock.patch.object(
                service_share.rainbond_app_repo,
                "get_rainbond_app_by_app_id",
                return_value=preferred_app), \
                mock.patch.object(
                    service_share.rainbond_app_repo,
                    "get_enterprise_team_apps",
                    return_value=[team_app]), \
                mock.patch.object(
                    service_share.share_repo,
                    "get_last_app_versions_by_app_id",
                    side_effect=lambda app_id: [{"version": "1.0.0"}] if app_id == "team-app" else []):
            app_list = share_service_instance.get_team_local_apps_versions(
                enterprise_id="eid",
                team_name="demo-team",
                preferred_app_id="hidden-app",
            )

        self.assertEqual([item["app_id"] for item in app_list], ["hidden-app", "team-app"])
        self.assertEqual(app_list[0]["versions"], [])

    # capability_id: console.service-share.local-app-versions
    def test_get_team_local_apps_versions_filters_by_template_scope(self):
        preferred_app = mock.Mock(
            app_name="hidden-snapshot",
            app_id="hidden-app",
            pic="hidden-pic",
            describe="hidden describe",
            dev_status="",
            scope="team",
        )
        enterprise_app = mock.Mock(
            app_name="enterprise-template",
            app_id="enterprise-app",
            pic="enterprise-pic",
            describe="enterprise describe",
            dev_status="release",
            scope="enterprise",
        )

        with mock.patch.object(
                service_share.rainbond_app_repo,
                "get_rainbond_app_by_app_id",
                return_value=preferred_app), \
                mock.patch.object(
                    share_services_module.team_repo,
                    "get_teams_by_enterprise_id",
                    return_value=[
                        mock.Mock(tenant_name="demo-team"),
                        mock.Mock(tenant_name="test-team"),
                    ],
                ), \
                mock.patch.object(
                    service_share.rainbond_app_repo,
                    "get_enterprise_team_apps",
                    return_value=[enterprise_app]) as list_apps_mock, \
                mock.patch.object(
                    service_share.share_repo,
                    "get_last_app_versions_by_app_id",
                    side_effect=lambda app_id: [{"version": "2.0.0"}] if app_id == "enterprise-app" else []):
            app_list = share_service_instance.get_team_local_apps_versions(
                enterprise_id="eid",
                team_name="demo-team",
                preferred_app_id="hidden-app",
                template_scope="enterprise",
            )

        list_apps_mock.assert_called_once_with(
            "eid",
            "demo-team",
            scope="enterprise",
            visible_team_names=["demo-team", "test-team"],
        )
        self.assertEqual([item["app_id"] for item in app_list], ["enterprise-app"])

    # capability_id: console.service-share.resolve-last-shared-app
    def test_get_last_shared_app_ignores_missing_versions_for_preferred_local_app(self):
        tenant = mock.Mock(tenant_name="demo-team")
        app_list = [{
            "app_name": "demo-app",
            "app_id": "app-1",
            "versions": [],
            "pic": "demo-pic",
            "app_describe": "demo describe",
            "dev_status": "complete",
            "scope": "team",
            "tags": [],
        }]

        with mock.patch.object(
                service_share.share_repo, "get_last_shared_app_version_by_group_id", return_value=None), \
                mock.patch.object(
                    share_service_instance, "get_team_local_apps_versions", return_value=app_list), \
                mock.patch.object(share_service_instance, "_patch_rainbond_apps_tag", return_value=None):
            data = share_service_instance.get_last_shared_app_and_app_list(
                enterprise_id="eid",
                tenant=tenant,
                group_id=27,
                scope="local",
                market_name=None,
                user_id=None,
                preferred_app_id="app-1",
                preferred_version=None,
            )

        self.assertEqual(data["last_shared_app"]["app_id"], "app-1")
        self.assertIsNone(data["last_shared_app"]["version"])

    # capability_id: console.service-share.resolve-last-shared-app
    def test_snapshot_publish_lists_only_enterprise_templates_and_ignores_team_default(self):
        tenant = mock.Mock(tenant_name="demo-team")
        last_shared = mock.Mock(app_id="team-app", share_version="1.0.0")
        team_app = mock.Mock(
            app_name="team-template",
            app_id="team-app",
            pic="team-pic",
            describe="team describe",
            dev_status="release",
            scope="team",
        )
        snapshot_version = mock.Mock(template_type=share_service_instance.SNAPSHOT_TEMPLATE_TYPE)
        enterprise_app_list = [{
            "app_name": "enterprise-template",
            "app_id": "enterprise-app",
            "versions": [{"version": "2.0.0"}],
            "pic": "enterprise-pic",
            "app_describe": "enterprise describe",
            "dev_status": "release",
            "scope": "enterprise",
            "tags": [],
        }]

        with mock.patch.object(
                service_share.share_repo, "get_last_shared_app_version_by_group_id", return_value=last_shared), \
                mock.patch.object(
                    service_share.rainbond_app_repo, "get_app_version", return_value=snapshot_version), \
                mock.patch.object(
                    service_share.rainbond_app_repo, "get_rainbond_app_by_app_id", return_value=team_app), \
                mock.patch.object(
                    share_service_instance,
                    "get_team_local_apps_versions",
                    return_value=enterprise_app_list) as list_apps_mock, \
                mock.patch.object(share_service_instance, "_patch_rainbond_app_tag", return_value=None), \
                mock.patch.object(share_service_instance, "_patch_rainbond_apps_tag", return_value=None):
            data = share_service_instance.get_last_shared_app_and_app_list(
                enterprise_id="eid",
                tenant=tenant,
                group_id=27,
                scope="local",
                market_name=None,
                user_id=None,
                preferred_app_id="hidden-snapshot-app",
                preferred_version="1.0.0",
            )

        list_apps_mock.assert_called_once_with(
            "eid",
            "demo-team",
            None,
            template_scope="enterprise",
        )
        self.assertEqual([item["app_id"] for item in data["app_model_list"]], ["enterprise-app"])
        self.assertEqual(data["last_shared_app"], {})
