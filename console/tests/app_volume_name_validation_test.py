# -*- coding: utf-8 -*-
import os
from contextlib import ExitStack
from types import SimpleNamespace
from unittest import TestCase, mock

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.test_settings")

import django  # noqa: E402

django.setup()

from rest_framework.test import APIRequestFactory  # noqa: E402

from console.exception.main import NoPermissionsError  # noqa: E402
from console.views.app_config import app_volume  # noqa: E402
from console.views.app_config.base import AppBaseView  # noqa: E402


# capability_id: console.component.volume-name-input-validation
class AppVolumeNameValidationTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.team = SimpleNamespace(tenant_id="volume-input-team", tenant_name="volume-input-team")
        self.component = SimpleNamespace(service_id="volume-input-component", service_alias="fixture-component",
                                         service_cname="Fixture", service_region="fixture-region", extend_method="stateless")
        self.user = SimpleNamespace(nick_name="fixture-operator", enterprise_id="fixture-enterprise")
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.describe = self.stack.enter_context(mock.patch.object(app_volume.volume_service, "json_service_volume"))
        self.add_volume = self.stack.enter_context(mock.patch.object(
            app_volume.volume_service, "add_service_volume", return_value=SimpleNamespace(to_dict=lambda: {"ID": 1})))
        self.comment = self.stack.enter_context(mock.patch.object(
            app_volume.operation_log_service, "generate_component_comment", return_value="fixture log"))
        self.log = self.stack.enter_context(mock.patch.object(app_volume.operation_log_service, "create_component_log"))

    def post(self, payload, denied=False):
        def authorized_component_context(view, request, *args, **kwargs):
            if denied:
                raise NoPermissionsError()
            view.tenant = self.team
            view.service = self.component
            view.user = self.user
            view.app = SimpleNamespace(ID=1)

        data = {"volume_type": "share-file", "volume_path": "/fixture", "volume_capacity": 1}
        data.update(payload)
        with mock.patch.object(AppBaseView, "initial", new=authorized_component_context):
            return app_volume.AppVolumeView.as_view()(self.factory.post("/component/volumes", data, format="json"))

    def assert_invalid(self, payload):
        response = self.post(payload)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], 400)
        self.assertEqual(response.data["msg"], "volume name illegal")
        self.describe.assert_not_called()
        self.add_volume.assert_not_called()
        self.comment.assert_not_called()
        self.log.assert_not_called()

    def test_omitted_volume_name_returns_400_before_side_effects(self):
        self.assert_invalid({})

    def test_non_string_volume_names_return_400(self):
        for value in (None, [], {}, 7, 0, True, False):
            with self.subTest(value=value):
                self.assert_invalid({"volume_name": value})

    def test_invalid_string_names_keep_existing_rejection(self):
        for value in ("", ".fixture", "-fixture", "fixture.", "fixture_", "with space", "fixture/path"):
            with self.subTest(value=value):
                self.assert_invalid({"volume_name": value})

    def test_valid_names_keep_existing_creation_and_log_flow(self):
        for value in ("db", "volume-1", "volume.one", "Volume_1", "0"):
            with self.subTest(value=value):
                response = self.post({"volume_name": value})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data["data"]["bean"], {"ID": 1})
                self.assertEqual(self.add_volume.call_args.args[4], value)
                self.assertEqual(self.describe.call_args.kwargs["volume_name"], value)
        self.assertEqual(self.add_volume.call_count, 5)
        self.assertEqual(self.log.call_count, 5)

    def test_valid_name_still_preserves_existing_mode_validation(self):
        response = self.post({"volume_name": "fixture", "mode": 888})
        self.assertEqual(response.status_code, 400)
        self.add_volume.assert_not_called()
        self.log.assert_not_called()

    def test_valid_name_preserves_settings_and_operator_arguments(self):
        response = self.post({"volume_name": "fixture", "mode": 644, "access_mode": "ReadWriteMany",
                              "volume_provider_name": "fixture-provider"})
        self.assertEqual(response.status_code, 200)
        args = self.add_volume.call_args.args
        self.assertEqual(args[:5], (self.team, self.component, "/fixture", "share-file", "fixture"))
        self.assertEqual(args[6]["provider_name"], "fixture-provider")
        self.assertEqual(args[6]["access_mode"], "ReadWriteMany")
        self.assertEqual(args[7], "fixture-operator")
        self.assertEqual(self.add_volume.call_args.kwargs, {"mode": 644})

    def test_permission_failure_remains_before_validation_and_creation(self):
        response = self.post({}, denied=True)
        self.assertEqual(response.status_code, 403)
        self.add_volume.assert_not_called()
        self.log.assert_not_called()

    def test_downstream_failure_is_not_disguised_as_invalid_name(self):
        self.add_volume.side_effect = RuntimeError("fixture region unavailable")
        self.assertEqual(self.post({"volume_name": "fixture"}).status_code, 500)
        self.log.assert_not_called()
