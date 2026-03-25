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
from rest_framework.test import APIRequestFactory  # noqa: E402

django.setup()

from console.services.share_services import share_service as share_service_instance  # noqa: E402
from console.views import service_share  # noqa: E402
from console.views.service_share import ServiceShareInfoView, ServiceShareRecordView  # noqa: E402


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


class ServiceShareInfoViewTestCase(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = ServiceShareInfoView()
        self.view.team = mock.Mock(tenant_id=1, tenant_name="demo-team")

    def make_request(self):
        return self.view.initialize_request(
            self.factory.get("/console/teams/demo-team/share/30/info")
        )

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


class ShareServicePreferredAppTestCase(TestCase):
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
