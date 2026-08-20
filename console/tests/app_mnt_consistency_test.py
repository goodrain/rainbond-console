# -*- coding: utf-8 -*-
import collections
import importlib
import os
import sys
from types import ModuleType, SimpleNamespace
from unittest import TestCase, mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "src",
                     "openapi-client")))
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

from console.exception.main import ServiceHandleException  # noqa: E402
from console.services.app_config.mnt_service import AppMntService  # noqa: E402
from console.views.app_config.app_mnt import AppMntView  # noqa: E402

mnt_service_module = importlib.import_module(
    "console.services.app_config.mnt_service")


class AppMntViewConsistencyTests(TestCase):

    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = AppMntView()
        self.view.tenant = SimpleNamespace(tenant_id="tenant-1")
        self.view.service = SimpleNamespace(service_id="consumer-1")

    # capability_id: console.component.shared-config-mount-consistency
    def test_get_passes_mounted_pagination_to_service(self):
        request = self.factory.get(
            "/console/teams/team-1/apps/consumer-1/mnts", {
                "type": "mnt",
                "page": 3,
                "page_size": 7,
            })

        with mock.patch(
                "console.views.app_config.app_mnt.mnt_service.get_service_mnt_details",
                return_value=([{
                    "dep_vol_id": 9
                }], 21),
        ) as get_details:
            response = self.view.get(request)

        get_details.assert_called_once_with(
            self.view.tenant,
            self.view.service,
            None,
            page=3,
            page_size=7,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["list"], [{"dep_vol_id": 9}])
        self.assertEqual(response.data["data"]["total"], 21)


class AppMntServiceConsistencyTests(TestCase):

    def setUp(self):
        self.mnt_service = AppMntService()
        self.tenant = SimpleNamespace(tenant_id="tenant-1",
                                      tenant_name="team-1",
                                      enterprise_id="enterprise-1")
        self.service = SimpleNamespace(
            service_id="consumer-1",
            service_region="region-1",
            service_alias="consumer",
            create_status="complete",
        )

    # capability_id: console.component.shared-config-mount-consistency
    def test_batch_mount_stops_and_propagates_first_failure(self):
        mounts = [{
            "id": 11,
            "path": "/etc/first.conf"
        }, {
            "id": 12,
            "path": "/etc/second.conf"
        }]
        dep_volumes = {
            11:
            SimpleNamespace(ID=11,
                            service_id="provider-1",
                            volume_name="first",
                            volume_type="config-file"),
            12:
            SimpleNamespace(ID=12,
                            service_id="provider-2",
                            volume_name="second",
                            volume_type="config-file"),
        }

        with mock.patch.object(mnt_service_module.volume_service, "get_service_volumes", return_value=[]), \
                mock.patch.object(mnt_service_module.volume_service, "check_volume_path"), \
                mock.patch.object(
                    mnt_service_module.volume_repo,
                    "get_service_volume_by_pk",
                    side_effect=lambda volume_id: dep_volumes[volume_id],
        ), \
                mock.patch.object(
                    self.mnt_service,
                    "add_service_mnt_relation",
                    side_effect=RuntimeError("region failed"),
        ) as add_relation:
            with self.assertRaisesRegex(RuntimeError, "region failed"):
                self.mnt_service.batch_mnt_serivce_volume(
                    self.tenant, self.service, mounts, "operator")

        add_relation.assert_called_once_with(
            self.tenant,
            self.service,
            "/etc/first.conf",
            dep_volumes[11],
            "operator",
        )

    # capability_id: console.component.shared-config-mount-consistency
    def test_batch_mount_rejects_missing_source_before_creating_any_relation(
            self):
        mounts = [{
            "id": 11,
            "path": "/etc/first.conf"
        }, {
            "id": 12,
            "path": "/etc/missing.conf"
        }]
        first_volume = SimpleNamespace(
            ID=11,
            service_id="provider-1",
            volume_name="first",
            volume_type="config-file",
        )

        with mock.patch.object(mnt_service_module.volume_service, "get_service_volumes", return_value=[]), \
                mock.patch.object(mnt_service_module.volume_service, "check_volume_path"), \
                mock.patch.object(
                    mnt_service_module.volume_repo,
                    "get_service_volume_by_pk",
                    side_effect=[first_volume, None],
        ), \
                mock.patch.object(self.mnt_service, "add_service_mnt_relation") as add_relation:
            with self.assertRaises(ServiceHandleException) as context:
                self.mnt_service.batch_mnt_serivce_volume(
                    self.tenant, self.service, mounts, "operator")

        self.assertEqual(context.exception.status_code, 404)
        self.assertEqual(context.exception.msg_show, "挂载的存储或配置文件不存在")
        add_relation.assert_not_called()

    # capability_id: console.component.shared-config-mount-consistency
    def test_batch_mount_rolls_back_first_relation_when_second_mount_fails(
            self):
        mounts = [{
            "id": 11,
            "path": "/mnt/first"
        }, {
            "id": 12,
            "path": "/mnt/second"
        }]
        dep_volumes = {
            11:
            SimpleNamespace(ID=11,
                            service_id="provider-1",
                            volume_name="first",
                            volume_type="share-file"),
            12:
            SimpleNamespace(ID=12,
                            service_id="provider-2",
                            volume_name="second",
                            volume_type="share-file"),
        }
        response = SimpleNamespace(status=200)
        persisted_relation = SimpleNamespace(service_id="consumer-1",
                                             dep_service_id="provider-1",
                                             mnt_dir="/mnt/first")

        with mock.patch.object(mnt_service_module.volume_service, "get_service_volumes", return_value=[]), \
                mock.patch.object(mnt_service_module.volume_service, "check_volume_path"), \
                mock.patch.object(
                    mnt_service_module.volume_repo,
                    "get_service_volume_by_pk",
                    side_effect=lambda volume_id: dep_volumes[int(volume_id)],
        ), \
                mock.patch.object(
                    mnt_service_module.region_api,
                    "add_service_dep_volumes",
                    side_effect=[(response, {}), RuntimeError("second region failed")],
        ) as add_region, \
                mock.patch.object(
                    mnt_service_module.mnt_repo,
                    "add_service_mnt_relation",
                    return_value=persisted_relation,
        ) as add_console, \
                mock.patch.object(
                    mnt_service_module.region_api,
                    "delete_service_dep_volumes",
                    return_value=(response, {}),
        ) as delete_region, \
                mock.patch.object(mnt_service_module.mnt_repo, "delete_mnt_relation") as delete_console:
            with self.assertRaisesRegex(RuntimeError, "second region failed"):
                self.mnt_service.batch_mnt_serivce_volume(
                    self.tenant, self.service, mounts, "operator")

        self.assertEqual(add_region.call_count, 2)
        add_console.assert_called_once()
        delete_region.assert_called_once_with(
            "region-1",
            "team-1",
            "consumer",
            {
                "depend_service_id": "provider-1",
                "volume_name": "first",
                "enterprise_id": "enterprise-1",
                "operator": "operator",
            },
        )
        delete_console.assert_called_once_with("consumer-1", "provider-1",
                                               "first")

    # capability_id: console.component.shared-config-mount-consistency
    def test_batch_mount_logs_rollback_failure_and_preserves_original_error(
            self):
        mounts = [
            {
                "id": 11,
                "path": "/mnt/first"
            },
            {
                "id": 12,
                "path": "/mnt/second"
            },
            {
                "id": 13,
                "path": "/mnt/third"
            },
        ]
        dep_volumes = {
            volume_id:
            SimpleNamespace(
                ID=volume_id,
                service_id="provider-{}".format(volume_id),
                volume_name="volume-{}".format(volume_id),
                volume_type="share-file",
            )
            for volume_id in (11, 12, 13)
        }

        with mock.patch.object(mnt_service_module.volume_service, "get_service_volumes", return_value=[]), \
                mock.patch.object(mnt_service_module.volume_service, "check_volume_path"), \
                mock.patch.object(
                    mnt_service_module.volume_repo,
                    "get_service_volume_by_pk",
                    side_effect=lambda volume_id: dep_volumes[volume_id],
        ), \
                mock.patch.object(
                    self.mnt_service,
                    "add_service_mnt_relation",
                    side_effect=[None, None, RuntimeError("third mount failed")],
        ), \
                mock.patch.object(
                    self.mnt_service,
                    "delete_service_mnt_relation",
                    side_effect=[RuntimeError("rollback second failed"), (200, "success")],
        ) as delete_relation:
            with self.assertLogs("default", level="ERROR") as logs:
                with self.assertRaisesRegex(RuntimeError,
                                            "third mount failed"):
                    self.mnt_service.batch_mnt_serivce_volume(
                        self.tenant, self.service, mounts, "operator")

        self.assertEqual(
            delete_relation.call_args_list,
            [
                mock.call(self.tenant, self.service, "12", "operator"),
                mock.call(self.tenant, self.service, "11", "operator"),
            ],
        )
        self.assertTrue(
            any("rollback second failed" in message
                for message in logs.output))

    # capability_id: console.component.shared-config-mount-consistency
    def test_batch_mount_logs_region_rollback_error_without_masking_mount_error(
            self):
        mounts = [{
            "id": 11,
            "path": "/mnt/first"
        }, {
            "id": 12,
            "path": "/mnt/second"
        }]
        dep_volumes = {
            11:
            SimpleNamespace(ID=11,
                            service_id="provider-1",
                            volume_name="first",
                            volume_type="share-file"),
            12:
            SimpleNamespace(ID=12,
                            service_id="provider-2",
                            volume_name="second",
                            volume_type="share-file"),
        }
        region_error = mnt_service_module.region_api.CallApiError(
            "region",
            "/depvolumes",
            "DELETE",
            SimpleNamespace(status=500),
            {"msg": "region delete failed"},
        )

        with mock.patch.object(mnt_service_module.volume_service, "get_service_volumes", return_value=[]), \
                mock.patch.object(mnt_service_module.volume_service, "check_volume_path"), \
                mock.patch.object(
                    mnt_service_module.volume_repo,
                    "get_service_volume_by_pk",
                    side_effect=lambda volume_id: dep_volumes[int(volume_id)],
        ), \
                mock.patch.object(
                    self.mnt_service,
                    "add_service_mnt_relation",
                    side_effect=[None, RuntimeError("second mount failed")],
        ), \
                mock.patch.object(
                    mnt_service_module.region_api,
                    "delete_service_dep_volumes",
                    side_effect=region_error,
        ), \
                mock.patch.object(mnt_service_module.mnt_repo, "delete_mnt_relation") as delete_console:
            with self.assertLogs("default", level="ERROR") as logs:
                with self.assertRaisesRegex(RuntimeError,
                                            "second mount failed"):
                    self.mnt_service.batch_mnt_serivce_volume(
                        self.tenant, self.service, mounts, "operator")

        delete_console.assert_not_called()
        self.assertTrue(
            any("failed to roll back batch mount relation 11" in message
                for message in logs.output))

    # capability_id: console.component.shared-config-mount-consistency
    def test_add_mount_compensates_region_when_console_persistence_fails(self):
        dep_volume = SimpleNamespace(
            ID=11,
            service_id="provider-1",
            volume_name="shared-data",
            volume_type="share-file",
        )
        region_response = SimpleNamespace(status=200)

        with mock.patch.object(
                mnt_service_module.region_api,
                "add_service_dep_volumes",
                return_value=(region_response, {}),
        ) as add_region, mock.patch.object(
                mnt_service_module.mnt_repo,
                "add_service_mnt_relation",
                side_effect=RuntimeError("console database failed"),
        ), mock.patch.object(
                mnt_service_module.region_api,
                "delete_service_dep_volumes",
                return_value=(region_response, {}),
        ) as delete_region:
            with self.assertRaisesRegex(RuntimeError,
                                        "console database failed"):
                self.mnt_service.add_service_mnt_relation(
                    self.tenant,
                    self.service,
                    "/mnt/shared-data",
                    dep_volume,
                    "operator",
                )

        add_region.assert_called_once()
        delete_region.assert_called_once_with(
            "region-1",
            "team-1",
            "consumer",
            {
                "depend_service_id": "provider-1",
                "volume_name": "shared-data",
                "enterprise_id": "enterprise-1",
                "operator": "operator",
            },
        )

    # capability_id: console.component.shared-config-mount-consistency
    def test_existing_config_mount_relation_remains_visible(self):
        relation = SimpleNamespace(
            dep_service_id="provider-1",
            mnt_name="shared-config",
            mnt_dir="/etc/app/test1.conf",
        )
        provider = SimpleNamespace(
            service_id="provider-1",
            service_cname="Provider",
            service_alias="provider",
        )
        volume = SimpleNamespace(
            ID=11,
            volume_name="shared-config",
            volume_path="/etc/provider/source.conf",
            volume_type="config-file",
        )

        with mock.patch.object(
                mnt_service_module.mnt_repo,
                "get_service_mnts_filter_volume_type",
                return_value=[relation],
        ), mock.patch.object(
                mnt_service_module.service_repo,
                "get_service_by_service_id",
                return_value=provider,
        ), mock.patch.object(
                mnt_service_module.group_service_relation_repo,
                "get_group_by_service_id",
                return_value=None,
        ), mock.patch.object(
                mnt_service_module.volume_repo,
                "get_service_volume_by_name",
                return_value=volume,
        ):
            mounted, total = self.mnt_service.get_service_mnt_details(
                self.tenant,
                self.service,
                ["config-file"],
                page=1,
                page_size=20,
            )

        self.assertEqual(total, 1)
        self.assertEqual(mounted[0]["local_vol_path"], "/etc/app/test1.conf")
        self.assertEqual(mounted[0]["dep_vol_id"], 11)
        self.assertEqual(mounted[0]["dep_vol_type"], "config-file")

    # capability_id: console.component.shared-config-mount-consistency
    def test_existing_config_mount_relation_can_be_cancelled(self):
        dep_volume = SimpleNamespace(service_id="provider-1",
                                     volume_name="shared-config")
        response = SimpleNamespace(status=200)

        with mock.patch.object(
                mnt_service_module.volume_repo,
                "get_service_volume_by_pk",
                return_value=dep_volume,
        ), mock.patch.object(
                mnt_service_module.region_api,
                "delete_service_dep_volumes",
                return_value=(response, {}),
        ) as delete_region, mock.patch.object(
                mnt_service_module.mnt_repo,
                "delete_mnt_relation",
        ) as delete_console:
            code, message = self.mnt_service.delete_service_mnt_relation(
                self.tenant,
                self.service,
                "11",
                "operator",
            )

        self.assertEqual((code, message), (200, "success"))
        delete_region.assert_called_once()
        delete_console.assert_called_once_with("consumer-1", "provider-1",
                                               "shared-config")

    # capability_id: console.component.shared-config-mount-consistency
    def test_cancel_mount_propagates_non_404_region_error(self):
        dep_volume = SimpleNamespace(service_id="provider-1",
                                     volume_name="shared-config")
        region_error = mnt_service_module.region_api.CallApiError(
            "region",
            "/depvolumes",
            "DELETE",
            SimpleNamespace(status=500),
            {"msg": "region delete failed"},
        )

        with mock.patch.object(
                mnt_service_module.volume_repo,
                "get_service_volume_by_pk",
                return_value=dep_volume,
        ), mock.patch.object(
                mnt_service_module.region_api,
                "delete_service_dep_volumes",
                side_effect=region_error,
        ), mock.patch.object(
                mnt_service_module.mnt_repo,
                "delete_mnt_relation",
        ) as delete_console:
            with self.assertRaises(
                    mnt_service_module.region_api.CallApiError) as context:
                self.mnt_service.delete_service_mnt_relation(
                    self.tenant,
                    self.service,
                    "11",
                    "operator",
                )

        self.assertIs(context.exception, region_error)
        delete_console.assert_not_called()

    # capability_id: console.component.shared-config-mount-consistency
    def test_cancel_mount_cleans_console_relation_when_region_returns_404(
            self):
        dep_volume = SimpleNamespace(service_id="provider-1",
                                     volume_name="shared-config")
        region_error = mnt_service_module.region_api.CallApiError(
            "region",
            "/depvolumes",
            "DELETE",
            SimpleNamespace(status=404),
            {"msg": "mount relation not found"},
        )

        with mock.patch.object(
                mnt_service_module.volume_repo,
                "get_service_volume_by_pk",
                return_value=dep_volume,
        ), mock.patch.object(
                mnt_service_module.region_api,
                "delete_service_dep_volumes",
                side_effect=region_error,
        ), mock.patch.object(
                mnt_service_module.mnt_repo,
                "delete_mnt_relation",
        ) as delete_console:
            code, message = self.mnt_service.delete_service_mnt_relation(
                self.tenant,
                self.service,
                "11",
                "operator",
            )

        self.assertEqual((code, message), (200, "success"))
        delete_console.assert_called_once_with("consumer-1", "provider-1",
                                               "shared-config")
