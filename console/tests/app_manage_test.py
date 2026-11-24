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
from console.enum.component_enum import ComponentType, is_support  # noqa: E402
from console.services.app_actions import app_manage as app_manage_module  # noqa: E402
from console.services import helm_app_yaml as helm_app_yaml_module  # noqa: E402
from www.apiclient.regionapibaseclient import RegionApiBaseHttpClient  # noqa: E402
from www.models.main import (TenantServiceEnvVar, TenantServiceInfo, TenantServiceInfoDelete,  # noqa: E402
                             TenantServicesPort, VirtualMachineImage)  # noqa: E402


class ComponentDaemonSetSupportTests(TestCase):
    # capability_id: console.component-type.daemonset
    def test_daemonset_component_type_is_supported(self):
        self.assertEqual("daemonset", ComponentType.daemonset.value)
        self.assertTrue(is_support("daemonset"))
        self.assertEqual("守护进程组件", ComponentType.to_zh("daemonset"))

    # capability_id: console.component-type.daemonset
    def test_extend_method_name_supports_daemonset(self):
        service_manage = app_manage_module.AppManageService()

        self.assertEqual("守护进程组件", service_manage.get_extend_method_name("daemonset"))


class AppManageLegacyPortTests(TestCase):
    def test_save_port_normalizes_legacy_market_service_flags(self):
        service_manage = app_manage_module.AppManageService()
        tenant = mock.Mock(tenant_id="tenant-1")
        service = mock.Mock(service_id="service-1", service_key="web")
        ports = [
            {"container_port": 8080, "protocol": "http", "port_alias": "WEB"},
            {
                "container_port": 8081,
                "protocol": "http",
                "port_alias": "FALSE",
                "is_inner_service": "false",
                "is_outer_service": 0,
            },
            {
                "container_port": 8082,
                "protocol": "http",
                "port_alias": "OUTER",
                "is_inner_service": "f",
                "is_outer_service": "t",
            },
        ]

        with mock.patch.object(
                app_manage_module.port_repo,
                "get_service_port_by_port",
                return_value=None), mock.patch.object(
                    app_manage_module.port_service,
                    "add_service_port",
                    return_value=(200, "success", None)) as add_service_port:
            code, message = service_manage._AppManageService__save_port(tenant, service, ports)

        self.assertEqual((200, "success"), (code, message))
        self.assertEqual([(False, False), (False, False), (True, True)], [
            (call.args[5], call.args[6]) for call in add_service_port.call_args_list
        ])

    # capability_id: console.component-type.daemonset
    def test_change_service_type_blocks_daemonset_transition(self):
        service = mock.Mock(
            extend_method="stateless_multiple",
            create_status="complete",
            min_node=1,
        )
        tenant = mock.Mock()

        with mock.patch.object(app_manage_module.volume_service, "get_service_volumes", return_value=[]), \
                mock.patch.object(app_manage_module.region_api, "update_service") as update_service:
            service_manage = app_manage_module.AppManageService()
            with self.assertRaises(app_manage_module.ServiceHandleException):
                service_manage.change_service_type(tenant, service, "daemonset", user_name="tester")

        update_service.assert_not_called()

    # capability_id: console.helm.daemonset-template
    def test_helm_template_maps_daemonset_resource_type(self):
        cvdata = {
            "kubernetes_resources": [],
            "convert_resource": [{
                "components_name": "node-agent",
                "basic_management": {
                    "resource_type": "DaemonSet",
                    "image": "registry.example.com/tools/agent:1.0.0",
                    "command": "",
                    "memory": 128,
                    "cpu": 100,
                    "replicas": 1,
                },
                "health_check_management": None,
                "port_management": [],
                "config_management": [],
                "env_management": [],
                "component_k8s_attributes_management": [],
            }],
        }
        app_model = mock.Mock(app_id="app-1", app_name="demo", details="", scope="team")
        tenant = mock.Mock(tenant_id="tenant-1", tenant_name="demo-team", namespace="demo-ns")

        with (
                mock.patch.object(helm_app_yaml_module.region_api,
                                  'get_cluster_nodes_arch',
                                  return_value=(200, {
                                      'list': ['amd64']
                                  })),
                mock.patch.object(helm_app_yaml_module, 'AppHelmOverrides') as overrides_cls,
                mock.patch.object(helm_app_yaml_module, 'RainbondCenterAppVersion') as version_cls,
        ):
            helm_app_yaml_module.helm_app_service.generate_template(cvdata, app_model, "1.0.0", tenant, "demo-chart",
                                                                    "region-a", "eid", 7, {}, "region-app-1")

        overrides_cls.return_value.save.assert_called_once()
        version_cls.return_value.save.assert_called_once()
        app_template = json.loads(version_cls.call_args.kwargs["app_template"])
        self.assertEqual("daemonset", app_template["apps"][0]["extend_method"])


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
        service_source = mock.Mock(extend_info=json.dumps({
            "source_service_share_uuid": "svc-1+svc-1",
            "source_deploy_version": "snapshot-deploy-version",
        }), )
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
            "update_time":
            datetime(2026, 4, 3, 0, 0, 0),
        }

        with mock.patch.object(app_manage_module, "check_account_quota", return_value=True), \
                mock.patch.object(app_manage_module.env_var_repo, "get_build_envs", return_value={}), \
                mock.patch.object(app_manage_module.service_source_repo, "get_service_source", return_value=service_source):
            service_manage = app_manage_module.AppManageService()
            code, body = service_manage.deploy_services_info({}, [service], tenant, user, None, template_apps, False,
                                                             "demo-region")

        self.assertEqual(code, 200)
        build_info = body["build_infos"][0]
        self.assertEqual(build_info["kind"], "build_from_market_image")
        self.assertEqual(build_info["image_info"]["image_url"], "registry.example.com/demo/web:1.2.3")
        self.assertEqual(build_info["image_info"]["user"], "hub-user")
        self.assertEqual(build_info["image_info"]["password"], "hub-password")
        self.assertNotIn("slug_info", build_info)

    # capability_id: console.market-build.template-update-time
    def test_deploy_market_component_uses_version_update_time_after_loading_template_json(self):
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
        service_two = mock.Mock(
            service_id="service-2",
            build_upgrade=False,
            language=None,
            tenant_id="tenant-id",
            arch="amd64",
            service_source="market",
            cmd="python app.py",
            image="goodrain.me/runner:latest-amd64",
        )

        def service_source():
            source = mock.Mock(
                extend_info=json.dumps({
                    "source_service_share_uuid": "svc-1+svc-1",
                    "source_deploy_version": "old-deploy-version",
                }),
                group_key="app-key",
                version="1.0.0",
            )
            source.is_install_from_cloud.return_value = False
            return source

        service_sources = [service_source(), service_source()]
        template = {
            "apps": [{
                "service_share_uuid": "svc-1+svc-1",
                "service_key": "svc-1",
                "share_image": "registry.example.com/demo/web:1.2.3",
                "deploy_version": "new-deploy-version",
                "service_image": {},
                "service_env_map_list": [],
                "service_connect_info_map_list": [],
                "service_volume_map_list": [],
                "port_map_list": [],
                "extend_method_map": {},
            }],
        }
        version_update_time = datetime(2026, 10, 6, 7, 25, 0)
        app_version = mock.Mock(app_template=json.dumps(template), update_time=version_update_time)
        service_manage = app_manage_module.AppManageService()

        with mock.patch.object(app_manage_module, "check_account_quota", return_value=True), \
                mock.patch.object(app_manage_module.env_var_repo, "get_build_envs", return_value={}), \
                mock.patch.object(
                    app_manage_module.service_source_repo,
                    "get_service_source",
                    side_effect=service_sources,
                ), \
                mock.patch.object(
                    app_manage_module.rainbond_app_repo,
                    "get_rainbond_app_and_version",
                    return_value=(mock.Mock(), app_version),
                ) as get_app_version, mock.patch.object(
                    service_manage,
                    "_AppManageService__save_env",
                    return_value=(200, "success"),
                ), \
                mock.patch.object(service_manage, "_AppManageService__save_volume"), \
                mock.patch.object(service_manage, "_AppManageService__save_port", return_value=(200, "success")), \
                mock.patch.object(service_manage, "_AppManageService__save_extend_info"), \
                mock.patch.object(app_manage_module.logger, "exception") as log_exception:
            code, _ = service_manage.deploy_services_info({}, [service, service_two],
                                                          tenant,
                                                          user,
                                                          None,
                                                          region_name="demo-region")

        self.assertEqual(code, 200)
        log_exception.assert_not_called()
        for source in service_sources:
            saved_extend_info = json.loads(source.extend_info)
            self.assertEqual(saved_extend_info["update_time"], "2026-10-06 07:25:00")
            self.assertEqual(saved_extend_info["source_deploy_version"], "new-deploy-version")
            source.save.assert_called_once_with()
        get_app_version.assert_called_once_with("eid", "app-key", "1.0.0")


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
            {"msg_show": "当前虚拟机不满足热更新条件，请停机后再修改规格。"},
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

    def test_vertical_upgrade_allows_memory_above_64g(self):
        tenant = mock.Mock(creater="creator", enterprise_id="eid", tenant_name="demo-team")
        user = mock.Mock(nick_name="tester")
        service = mock.Mock(
            min_memory=4096,
            service_region="demo-region",
            service_alias="demo-service",
            create_status="complete",
            container_gpu=0,
        )

        with mock.patch.object(app_manage_module, "check_account_quota", return_value=True), \
                mock.patch.object(app_manage_module.region_api, "vertical_upgrade") as vertical_upgrade:
            code, msg = app_manage_module.AppManageService().vertical_upgrade(
                tenant,
                service,
                user,
                131072,
                oauth_instance=None,
                new_cpu=8000,
            )

        self.assertEqual(200, code)
        self.assertEqual("操作成功", msg)
        self.assertEqual(131072, service.min_memory)
        service.save.assert_called_once()
        body = vertical_upgrade.call_args[0][3]
        self.assertEqual(131072, body["container_memory"])

    def test_vertical_upgrade_rejects_negative_memory_without_obsolete_upper_bound_message(self):
        tenant = mock.Mock()
        service = mock.Mock()
        user = mock.Mock()

        with mock.patch.object(app_manage_module.region_api, "vertical_upgrade") as vertical_upgrade:
            code, msg = app_manage_module.AppManageService().vertical_upgrade(
                tenant,
                service,
                user,
                -1,
                oauth_instance=None,
            )

        self.assertEqual(400, code)
        self.assertEqual("内存不能小于0M", msg)
        service.save.assert_not_called()
        vertical_upgrade.assert_not_called()


class AppManageBatchActionDeployEventTests(DjangoTestCase):

    # capability_id: console.oauth.missing-access-key-fallback
    def test_deploy_info_falls_back_without_error_log_when_oauth_access_key_is_missing(self):
        tenant = mock.Mock(tenant_id="tenant-id", enterprise_id="enterprise-id", creater="creator")
        user = mock.Mock(user_id=1)
        service = mock.Mock(
            service_id="service-1",
            service_alias="grsvc1",
            service_cname="api",
            service_source="source_code",
            create_status="complete",
            build_upgrade=False,
            language="python",
            build_strategy="dockerfile",
            git_url="https://git.example.com/demo/api.git",
            code_version="main",
            arch="amd64",
            oauth_service_id=7,
        )
        oauth_service = mock.Mock(oauth_type="gitea")
        oauth_instance = mock.Mock()
        oauth_instance.is_git_oauth.return_value = True
        oauth_instance.get_clone_url.side_effect = app_manage_module.NoAccessKeyErr("expired")

        with (
                mock.patch.object(app_manage_module, 'check_account_quota', return_value=True),
                mock.patch.object(app_manage_module.env_var_repo, 'get_build_envs', return_value=[]),
                mock.patch.object(app_manage_module.AppManageService,
                                  '_AppManageService__get_service_kind',
                                  return_value='build_from_source_code'),
                mock.patch.object(app_manage_module, 'compose_source_code_info', return_value={}),
                mock.patch.object(app_manage_module.service_source_repo, 'get_service_source', return_value=None),
                mock.patch.object(app_manage_module.oauth_repo, 'get_oauth_services_by_service_id', return_value=oauth_service),
                mock.patch.object(app_manage_module.oauth_user_repo, 'get_user_oauth_by_user_id', return_value=mock.Mock()),
                mock.patch.object(app_manage_module, 'get_oauth_instance', return_value=oauth_instance),
                mock.patch.object(app_manage_module.logger, 'exception') as log_exception,
                mock.patch.object(app_manage_module.logger, 'warning') as log_warning,
        ):
            code, body = app_manage_module.AppManageService().deploy_services_info({}, [service],
                                                                                   tenant,
                                                                                   user,
                                                                                   None,
                                                                                   region_name="region-a")

        self.assertEqual(code, 200)
        self.assertEqual(body["build_infos"][0]["code_info"]["repo_url"], service.git_url)
        log_exception.assert_not_called()
        log_warning.assert_called_once()

    def test_batch_action_keeps_return_contract_and_records_deploy_event_on_service(self):
        tenant = mock.Mock()
        user = mock.Mock()
        service = mock.Mock(
            service_id="service-1",
            service_alias="grsvc1",
            service_cname="api",
            service_source="source_code",
            arch="amd64",
            update_time=None,
        )
        service.save = mock.Mock()

        with mock.patch.object(app_manage_module.service_repo, "get_services_by_service_ids", return_value=[service]), \
                mock.patch.object(app_manage_module.region_api, "get_cluster_nodes_arch",
                                  return_value=(200, {"list": ["amd64"]})), \
                mock.patch.object(app_manage_module.AppManageService, "deploy",
                                  return_value=(200, "success", "event-1")) as deploy:
            code, msg, services = app_manage_module.AppManageService().batch_action("region-a", tenant, user, "deploy",
                                                                                    ["service-1"], None, None)

        self.assertEqual(code, 200)
        self.assertEqual(msg, "success")
        self.assertEqual(services, [service])
        deploy.assert_called_once()
        self.assertEqual(service._last_deploy_event_id, "event-1")
        self.assertEqual(service._last_deploy_result, {"code": 200, "msg": "success"})


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

        with (
                mock.patch.object(app_manage_module.region_api,
                                  'check_service_status',
                                  return_value={'bean': {
                                      'cur_status': 'restoring'
                                  }}),
                mock.patch.object(app_manage_module.AppManageService,
                                  '_AppManageService__is_service_related',
                                  return_value=(False, '')),
                mock.patch.object(app_manage_module.AppManageService,
                                  '_AppManageService__is_service_mnt_related',
                                  return_value=(False, '')),
                mock.patch.object(app_manage_module.AppManageService, 'get_app_by_service', return_value=None),
                mock.patch.object(app_manage_module.AppManageService, 'truncate_service', return_value=(200, 'success')) as
                truncate_service,
        ):
            code, msg = app_manage_module.AppManageService().delete(user, tenant, service, True)

        self.assertEqual(200, code)
        self.assertEqual("success", msg)
        truncate_service.assert_called_once_with(tenant, service, user, None)

    # capability_id: console.vm-template-import.delete-abnormal-vm
    def test_delete_allows_abnormal_vm_to_skip_running_guard(self):
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

        with (
                mock.patch.object(app_manage_module.region_api,
                                  'check_service_status',
                                  return_value={'bean': {
                                      'cur_status': 'abnormal'
                                  }}),
                mock.patch.object(app_manage_module.AppManageService,
                                  '_AppManageService__is_service_related',
                                  return_value=(False, '')),
                mock.patch.object(app_manage_module.AppManageService,
                                  '_AppManageService__is_service_mnt_related',
                                  return_value=(False, '')),
                mock.patch.object(app_manage_module.AppManageService, 'get_app_by_service', return_value=None),
                mock.patch.object(app_manage_module.AppManageService, 'truncate_service', return_value=(200, 'success')) as
                truncate_service,
        ):
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

        with (
                mock.patch.object(app_manage_module.region_api,
                                  'check_service_status',
                                  return_value={'bean': {
                                      'cur_status': 'restoring'
                                  }}),
                mock.patch.object(app_manage_module.AppManageService,
                                  '_AppManageService__is_service_mnt_related',
                                  return_value=(False, '')),
                mock.patch.object(app_manage_module.AppManageService,
                                  '_AppManageService__is_service_bind_domain',
                                  return_value=False),
                mock.patch.object(app_manage_module.AppManageService,
                                  '_AppManageService__is_service_has_plugins',
                                  return_value=False),
                mock.patch.object(app_manage_module.AppManageService,
                                  '_AppManageService__is_service_related_by_other_app_service',
                                  return_value=False),
                mock.patch.object(app_manage_module.AppManageService, 'get_app_by_service', return_value=None),
                mock.patch.object(app_manage_module.AppManageService, 'truncate_service', return_value=(200, 'success')) as
                truncate_service,
        ):
            code, msg = app_manage_module.AppManageService().batch_delete(user,
                                                                          tenant,
                                                                          service,
                                                                          is_force=True,
                                                                          is_del_app=False)

        self.assertEqual(200, code)
        self.assertEqual("success", msg)
        truncate_service.assert_called_once_with(tenant, service, user, None)


class AppManageIncompleteVMCleanupTests(DjangoTestCase):

    # capability_id: console.component-delete.skip-incomplete-backup
    def test_incomplete_cleanup_skips_backup_and_removes_component_relations(self):
        for status in ("creating", "checking", "failed"):
            with self.subTest(status=status):
                service_id = "incomplete-" + status
                service = TenantServiceInfo.objects.create(
                    service_id=service_id, tenant_id="cleanup-team", service_key=service_id,
                    service_alias=service_id, service_cname=service_id, service_region="region",
                    category="application", version="v1", image="nginx:latest",
                    create_status=status, k8s_component_name=service_id)
                TenantServiceEnvVar.objects.create(
                    tenant_id="cleanup-team", service_id=service_id, attr_name="FIXTURE", attr_value="value")
                TenantServicesPort.objects.create(
                    tenant_id="cleanup-team", service_id=service_id, container_port=8080)
                manager = app_manage_module.AppManageService()
                tenant = mock.Mock(tenant_id="cleanup-team")
                user = mock.Mock(nick_name="operator")
                with mock.patch.object(app_manage_module, "_create_delete_service_with_retry",
                                       wraps=app_manage_module._create_delete_service_with_retry) as backup, \
                        mock.patch.object(app_manage_module.logger, "exception") as log_exception, \
                        mock.patch.object(app_manage_module.event_repo, "create_event") as create_event:
                    manager._truncate_service(tenant, service, user)
                backup.assert_not_called()
                log_exception.assert_not_called()
                create_event.assert_called_once()
                self.assertEqual(create_event.call_args.kwargs["service_id"], service_id)
                self.assertFalse(TenantServiceInfo.objects.filter(service_id=service_id).exists())
                self.assertFalse(TenantServiceEnvVar.objects.filter(service_id=service_id).exists())
                self.assertFalse(TenantServicesPort.objects.filter(service_id=service_id).exists())
                self.assertFalse(TenantServiceInfoDelete.objects.filter(service_id=service_id).exists())

    # capability_id: console.component-delete.skip-incomplete-backup
    def test_complete_cleanup_preserves_backup_and_transient_lock_retry(self):
        service = TenantServiceInfo.objects.create(
            service_id="complete-cleanup", tenant_id="cleanup-team", service_key="complete-cleanup",
            service_alias="complete-cleanup", service_cname="complete-cleanup", service_region="region",
            category="application", version="v1", image="nginx:latest", create_status="complete",
            k8s_component_name="complete-cleanup")
        original_create = app_manage_module.delete_service_repo.create_delete_service
        attempts = []

        def transient_then_create(**data):
            attempts.append(data)
            if len(attempts) == 1:
                raise app_manage_module.OperationalError("database is locked")
            return original_create(**data)

        with mock.patch.object(app_manage_module.delete_service_repo, "create_delete_service",
                               side_effect=transient_then_create), \
                mock.patch.object(app_manage_module.time, "sleep") as sleep:
            app_manage_module.AppManageService()._truncate_service(mock.Mock(tenant_id="cleanup-team"), service)
        self.assertEqual(len(attempts), 2)
        self.assertEqual(attempts[0]["service_id"], "complete-cleanup")
        sleep.assert_called_once_with(app_manage_module._DB_LOCK_RETRY_DELAY)
        self.assertEqual(TenantServiceInfoDelete.objects.filter(service_id="complete-cleanup").count(), 1)
        self.assertFalse(TenantServiceInfo.objects.filter(service_id="complete-cleanup").exists())

    # capability_id: console.vm-asset.incomplete-service-cleanup-preserves-ready-assets
    def test_truncate_service_keeps_ready_uploaded_vm_asset(self):
        tenant = mock.Mock(tenant_id="tenant-a")
        asset = VirtualMachineImage.objects.create(tenant_id="tenant-a",
                                                   name="win",
                                                   image_url="default:win",
                                                   source_type="upload",
                                                   source_uri="/grdata/package_build/temp/events/demo-event",
                                                   status="ready")
        service = TenantServiceInfo.objects.create(service_id="service-vm-a",
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
                                                   k8s_component_name="service-vm-a-k8s")

        service_manage = app_manage_module.AppManageService()
        with mock.patch.object(app_manage_module.delete_service_repo, "create_delete_service"):
            service_manage._truncate_service(tenant, service)

        self.assertTrue(VirtualMachineImage.objects.filter(tenant_id="tenant-a", ID=asset.ID).exists())

    def test_truncate_service_strips_build_strategy_for_delete_record(self):
        """Regression: _truncate_service must not pass build_strategy to TenantServiceInfoDelete."""
        tenant = mock.Mock(tenant_id="tenant-b")
        service = TenantServiceInfo.objects.create(service_id="service-bs-1",
                                                   tenant_id="tenant-b",
                                                   service_key="service-bs-1",
                                                   service_alias="service-bs-1",
                                                   service_cname="service-bs-1",
                                                   service_region="demo-region",
                                                   category="application",
                                                   version="v1",
                                                   image="nginx:latest",
                                                   build_strategy="dockerfile",
                                                   inner_port=0,
                                                   container_gpu=0,
                                                   create_status="complete",
                                                   k8s_component_name="service-bs-1-k8s")

        service_manage = app_manage_module.AppManageService()
        captured_data = {}

        def fake_create(**kwargs):
            captured_data.update(kwargs)
            return mock.Mock()

        with mock.patch.object(app_manage_module.delete_service_repo, "create_delete_service", side_effect=fake_create):
            service_manage._truncate_service(tenant, service)

        self.assertNotIn("build_strategy", captured_data)
        self.assertEqual(captured_data.get("inner_port", 0), 0)


class AppManageDeleteRecordIdempotencyTests(DjangoTestCase):
    # capability_id: console.component-delete.missing-app-relation
    def test_get_app_by_service_returns_none_when_group_relation_is_missing(self):
        service = mock.Mock(service_id="service-without-app")

        with mock.patch.object(
                app_manage_module.group_service_relation_repo,
                "get_group_by_service_id",
                return_value=None,
        ), mock.patch.object(app_manage_module.group_repo, "get_group_by_id") as get_group:
            app = app_manage_module.AppManageService().get_app_by_service(service)

        self.assertIsNone(app)
        get_group.assert_not_called()

    # capability_id: console.component-delete.region-payload-isolation
    def test_delete_record_payload_excludes_region_only_fields_for_incomplete_service(self):
        service = mock.Mock(create_status="creating")
        user = mock.Mock(nick_name="operator")

        data = app_manage_module.AppManageService()._build_delete_record_data(service, app=None, user=user)

        self.assertEqual(data, {"exec_user": "operator"})
        self.assertNotIn("etcd_keys", data)

    # capability_id: console.component-delete.idempotent-record
    def test_create_delete_service_updates_existing_record_for_repeated_delete(self):
        data = {
            "service_id": "service-delete-1",
            "tenant_id": "tenant-a",
            "service_key": "service-delete-1",
            "service_alias": "service-delete-1",
            "service_cname": "old name",
            "service_region": "demo-region",
            "category": "application",
            "version": "v1",
            "image": "nginx:1",
        }
        first = app_manage_module.delete_service_repo.create_delete_service(**data)

        second = app_manage_module.delete_service_repo.create_delete_service(
            **dict(data, service_cname="new name", version="v2", image="nginx:2"))

        self.assertEqual(first.ID, second.ID)
        self.assertEqual(
            TenantServiceInfoDelete.objects.filter(service_id="service-delete-1").count(),
            1,
        )
        second.refresh_from_db()
        self.assertEqual(second.service_cname, "new name")
        self.assertEqual(second.version, "v2")
        self.assertEqual(second.image, "nginx:2")


class AppManageRecycleFieldProjectionTests(DjangoTestCase):
    def setUp(self):
        from console.models.main import ServiceRecycleBin

        self.recycle_model = ServiceRecycleBin
        self.service = TenantServiceInfo.objects.create(
            service_id="recycle-field-fixture",
            tenant_id="recycle-field-tenant",
            service_key="recycle-field-fixture",
            service_alias="recycle-field-fixture",
            service_cname="recycle field fixture",
            service_region="demo-region",
            category="application",
            version="v1",
            image="busybox:1.36.1",
            service_source="docker_run",
            create_status="complete",
            min_cpu=50,
            min_memory=64,
            inner_port=0,
            container_gpu=0,
            build_strategy="dockerfile",
            arch="arm64",
            k8s_component_name="recycle-field-fixture-k8s",
        )
        self.original_id = self.service.ID
        self.manager = app_manage_module.AppManageService()

    # capability_id: console.component-recycle.field-projection
    def test_recycle_preserves_declared_fields_and_removes_original_after_insert(self):
        trash = self.manager.move_service_into_recycle_bin(self.service)

        self.assertEqual(trash.service_id, "recycle-field-fixture")
        self.assertEqual(trash.min_cpu, 50)
        self.assertEqual(trash.min_memory, 64)
        self.assertEqual(trash.image, "busybox:1.36.1")
        self.assertEqual(self.recycle_model.objects.filter(service_id=trash.service_id).count(), 1)
        self.assertFalse(TenantServiceInfo.objects.filter(ID=self.original_id).exists())

    # capability_id: console.component-recycle.field-projection
    def test_recycle_failure_before_insert_preserves_original_for_retry(self):
        with mock.patch.object(app_manage_module.recycle_bin_repo,
                               "create_trash_service",
                               side_effect=RuntimeError("insert failed")):
            with self.assertRaisesRegex(RuntimeError, "insert failed"):
                self.manager.move_service_into_recycle_bin(self.service)

        self.assertTrue(TenantServiceInfo.objects.filter(ID=self.original_id).exists())
        self.assertFalse(self.recycle_model.objects.filter(service_id=self.service.service_id).exists())
        self.manager.move_service_into_recycle_bin(self.service)
        self.assertEqual(self.recycle_model.objects.filter(service_id=self.service.service_id).count(), 1)

    # capability_id: console.component-recycle.atomic-retry
    def test_recycle_failure_deleting_original_rolls_back_and_can_retry(self):
        with mock.patch.object(self.service, "delete", side_effect=RuntimeError("original delete failed")):
            with self.assertRaisesRegex(RuntimeError, "original delete failed"):
                self.manager.move_service_into_recycle_bin(self.service)

        self.assertTrue(TenantServiceInfo.objects.filter(ID=self.original_id).exists())
        self.assertFalse(self.recycle_model.objects.filter(service_id=self.service.service_id).exists())
        self.manager.move_service_into_recycle_bin(self.service)
        self.assertEqual(self.recycle_model.objects.filter(service_id=self.service.service_id).count(), 1)

    # capability_id: console.component-recycle.atomic-retry
    def test_relation_move_failure_rolls_back_single_and_batch_delete_and_can_retry(self):
        from console.models.main import ServiceRelationRecycleBin
        from www.models.main import TenantServiceRelation

        tenant = mock.Mock(tenant_id=self.service.tenant_id)
        for index in range(2):
            TenantServiceRelation.objects.create(
                tenant_id=self.service.tenant_id,
                service_id=self.service.service_id,
                dep_service_id="dependency-{}".format(index),
                dep_service_type="v",
                dep_order=index,
            )

        def insert_first_relation_then_fail(**params):
            if ServiceRelationRecycleBin.objects.filter(service_id=self.service.service_id).exists():
                raise RuntimeError("relations failed")
            ServiceRelationRecycleBin.objects.create(**params)

        for method_name in ("delete", "batch_delete"):
            with self.subTest(method=method_name):
                service = TenantServiceInfo.objects.get(ID=self.original_id)
                with mock.patch.object(self.manager, "_AppManageService__is_service_running", return_value=False), \
                        mock.patch.object(self.manager, "_AppManageService__is_service_related", return_value=(False, "")), \
                        mock.patch.object(self.manager, "_AppManageService__is_service_mnt_related", return_value=(False, "")), \
                        mock.patch.object(self.manager, "get_app_by_service", return_value=None), \
                        mock.patch.object(
                            app_manage_module.relation_recycle_bin_repo,
                            "create_trash_service_relation",
                            side_effect=insert_first_relation_then_fail):
                    with self.assertRaisesRegex(RuntimeError, "relations failed"):
                        getattr(self.manager, method_name)(mock.Mock(), tenant, service, False)

                self.assertTrue(TenantServiceInfo.objects.filter(ID=self.original_id).exists())
                self.assertFalse(self.recycle_model.objects.filter(service_id=self.service.service_id).exists())
                self.assertEqual(TenantServiceRelation.objects.filter(service_id=self.service.service_id).count(), 2)
                self.assertFalse(ServiceRelationRecycleBin.objects.filter(service_id=self.service.service_id).exists())

        service = TenantServiceInfo.objects.get(ID=self.original_id)
        with mock.patch.object(self.manager, "_AppManageService__is_service_running", return_value=False), \
                mock.patch.object(self.manager, "_AppManageService__is_service_related", return_value=(False, "")), \
                mock.patch.object(self.manager, "_AppManageService__is_service_mnt_related", return_value=(False, "")), \
                mock.patch.object(self.manager, "get_app_by_service", return_value=None):
            code, _ = self.manager.delete(mock.Mock(), tenant, service, False)
        self.assertEqual(code, 200)
        self.assertEqual(self.recycle_model.objects.filter(service_id=self.service.service_id).count(), 1)
        self.assertFalse(TenantServiceRelation.objects.filter(service_id=self.service.service_id).exists())
        self.assertEqual(ServiceRelationRecycleBin.objects.filter(service_id=self.service.service_id).count(), 2)


class VMBatchPowerSafetyTests(TestCase):
    # capability_id: console.vm-batch-power.preserve-disks
    def setUp(self):
        self.manage = app_manage_module.AppManageService()
        self.tenant = mock.Mock(tenant_id='team-a', tenant_name='team', enterprise_id='ent', creater=1)
        self.user = mock.Mock(nick_name='operator')
        self.vm = mock.Mock(service_id='vm-a',
                            service_alias='grvm',
                            extend_method='vm',
                            service_region='region-a',
                            tenant_id='team-a',
                            create_status='complete',
                            service_source='vm_run')
        self.container = mock.Mock(service_id='web-a',
                                   service_alias='grweb',
                                   extend_method='stateless_multiple',
                                   service_region='region-a',
                                   tenant_id='team-a',
                                   create_status='complete',
                                   service_source='docker_run')

    def test_vm_only_stop_uses_single_service_and_never_legacy_batch(self):
        with mock.patch.object(app_manage_module.service_repo, 'get_services_by_service_ids', return_value=[self.vm]), \
                mock.patch.object(app_manage_module.region_api, 'stop_service',
                                  return_value={'bean': {'event_id': 'ev-vm'}}) as stop, \
                mock.patch.object(app_manage_module.region_api, 'batch_operation_service') as batch:
            result = self.manage.batch_operations(self.tenant, 'region-a', self.user, 'stop', ['vm-a'])
        stop.assert_called_once()
        batch.assert_not_called()
        self.assertEqual(result, [{'service_id': 'vm-a', 'operation': 'stop', 'event_id': 'ev-vm', 'status': 'success'}])

    def test_mixed_start_sends_only_containers_to_region_batch(self):
        container_events = [{'service_id': 'web-a', 'event_id': 'ev-web', 'operation': 'start', 'status': 'success'}]
        with mock.patch.object(app_manage_module.service_repo, 'get_services_by_service_ids',
                               return_value=[self.vm, self.container]), \
                mock.patch.object(app_manage_module, 'check_account_quota', return_value=True), \
                mock.patch.object(app_manage_module.region_api, 'start_service',
                                  return_value={'bean': {'event_id': 'ev-vm'}}) as start, \
                mock.patch.object(app_manage_module.region_api, 'batch_operation_service',
                                  return_value=({}, {'bean': {'batch_result': container_events}})) as batch:
            result = self.manage.batch_operations(self.tenant, 'region-a', self.user, 'start', ['vm-a', 'web-a'])
        start.assert_called_once()
        self.assertEqual(batch.call_args.args[2]['start_infos'], [{'service_id': 'web-a'}])
        self.assertEqual({item['service_id'] for item in result}, {'vm-a', 'web-a'})
        self.assertEqual({item['event_id'] for item in result}, {'ev-vm', 'ev-web'})

    def test_container_only_keeps_batch_result_contract(self):
        events = {'existing-event': 'web-a'}
        with mock.patch.object(app_manage_module.service_repo, 'get_services_by_service_ids', return_value=[self.container]), \
                mock.patch.object(app_manage_module.region_api, 'batch_operation_service',
                                  return_value=({}, {'bean': {'batch_result': events}})) as batch, \
                mock.patch.object(self.manage, 'stop') as stop:
            result = self.manage.batch_operations(self.tenant, 'region-a', self.user, 'stop', ['web-a'])
        self.assertIs(result, events)
        stop.assert_not_called()
        self.assertEqual(batch.call_args.args[2]['stop_infos'], [{'service_id': 'web-a'}])

    def test_vm_start_failure_is_not_reported_as_success(self):
        with mock.patch.object(app_manage_module.service_repo, 'get_services_by_service_ids', return_value=[self.vm]), \
                mock.patch.object(self.manage, 'start', return_value=(409, 'busy')), \
                mock.patch.object(app_manage_module.region_api, 'batch_operation_service') as batch:
            with self.assertRaises(app_manage_module.ServiceHandleException):
                self.manage.batch_operations(self.tenant, 'region-a', self.user, 'start', ['vm-a'])
        batch.assert_not_called()

    def test_invalid_scope_blocks_all_power_operations_before_mutation(self):
        self.vm.tenant_id = 'another-team'
        with mock.patch.object(app_manage_module.service_repo, 'get_services_by_service_ids', return_value=[self.vm]), \
                mock.patch.object(self.manage, 'stop') as stop, \
                mock.patch.object(app_manage_module.region_api, 'batch_operation_service') as batch:
            with self.assertRaises(app_manage_module.ServiceHandleException):
                self.manage.batch_operations(self.tenant, 'region-a', self.user, 'stop', ['vm-a'])
        stop.assert_not_called()
        batch.assert_not_called()

    def test_vm_stop_failure_is_not_reported_as_success(self):
        with mock.patch.object(app_manage_module.service_repo, 'get_services_by_service_ids', return_value=[self.vm]), \
                mock.patch.object(self.manage, 'stop', side_effect=app_manage_module.ServiceHandleException(
                    msg='stop failed', msg_show='stop failed', status_code=500)), \
                mock.patch.object(app_manage_module.region_api, 'batch_operation_service') as batch:
            with self.assertRaises(app_manage_module.ServiceHandleException):
                self.manage.batch_operations(self.tenant, 'region-a', self.user, 'stop', ['vm-a'])
        batch.assert_not_called()

    def test_incomplete_vm_is_not_started(self):
        self.vm.create_status = 'checking'
        with mock.patch.object(app_manage_module.service_repo, 'get_services_by_service_ids', return_value=[self.vm]), \
                mock.patch.object(self.manage, 'start') as start, \
                mock.patch.object(app_manage_module.region_api, 'batch_operation_service') as batch:
            self.assertEqual([], self.manage.batch_operations(self.tenant, 'region-a', self.user, 'start', ['vm-a']))
        start.assert_not_called()
        batch.assert_not_called()

    def test_mcp_uses_the_safe_vm_power_path_and_keeps_event_ids(self):
        from console.services.mcp_query_service import mcp_query_service
        app = mock.Mock(ID=68, region_name='region-a')
        with mock.patch.object(mcp_query_service, '_get_team_app_context', return_value=(self.tenant, app)), \
                mock.patch.object(app_manage_module.service_repo, 'get_services_by_service_ids', return_value=[self.vm]), \
                mock.patch.object(app_manage_module.region_api, 'stop_service',
                                  return_value={'bean': {'event_id': 'ev-safe'}}) as single, \
                mock.patch.object(app_manage_module.region_api, 'batch_operation_service') as batch:
            result = mcp_query_service.operate_app(self.user, {
                'team_name': 'team',
                'region_name': 'region-a',
                'app_id': 68,
                'action': 'stop',
                'service_ids': ['vm-a']
            })
        single.assert_called_once()
        batch.assert_not_called()
        self.assertEqual(result['event_ids'][0]['event_id'], 'ev-safe')

    def test_ui_application_operation_uses_the_safe_vm_power_path(self):
        from console.views.group import TenantGroupCommonOperationView
        from rest_framework.test import APIRequestFactory
        from console.views import group as group_view
        view = TenantGroupCommonOperationView()
        view.tenant, view.region_name, view.user = self.tenant, 'region-a', self.user
        view.oauth_instance = None
        view.team_name = 'team'
        view.has_perms = mock.Mock()
        request = view.initialize_request(APIRequestFactory().post('/group/68/operations', {'action': 'stop'}, format='json'))
        with mock.patch.object(group_view.group_service_relation_repo, 'list_service_groups', return_value=[self.vm]), \
                mock.patch.object(app_manage_module.service_repo, 'get_services_by_service_ids', return_value=[self.vm]), \
                mock.patch.object(app_manage_module.region_api, 'stop_service', return_value={}) as single, \
                mock.patch.object(app_manage_module.region_api, 'batch_operation_service') as batch, \
                mock.patch.object(group_view.operation_log_service, 'create_app_log'):
            # Unrelated operation-log repositories are mocked; the power service
            # itself is the same implementation reached by the application UI.
            view.app = mock.Mock(ID=68, group_name='app')
            response = view.post(request, group_id='68')
        self.assertEqual(response.status_code, 200)
        single.assert_called_once()
        batch.assert_not_called()
