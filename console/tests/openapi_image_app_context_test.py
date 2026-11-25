# -*- coding: utf-8 -*-
import os
from contextlib import ExitStack
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.test_settings")

import django  # noqa: E402

django.setup()

from django.test import TestCase  # noqa: E402
from django.utils import timezone  # noqa: E402
from rest_framework.test import APIRequestFactory  # noqa: E402

from console.exception.main import NoPermissionsError  # noqa: E402
from console.models.main import ServiceSourceInfo  # noqa: E402
from console.services import app as app_service_module  # noqa: E402
from openapi.views.apps import apps as app_views  # noqa: E402
from openapi.views.base import TeamAPIView  # noqa: E402
from www.models.main import ServiceGroup, Tenants, TenantServiceInfo  # noqa: E402


# capability_id: console.openapi.image-component-authorized-app-context
class OpenAPIImageAppContextTests(TestCase):
    def setUp(self):
        self.team = Tenants.objects.create(
            tenant_id="image-context-team", tenant_name="image-context-team", namespace="image-context-team",
            enterprise_id="image-context-enterprise")
        self.app = self.create_app(self.team, "region")
        self.user = SimpleNamespace(user_id=1, pk=1, nick_name="fixture-operator")
        self.component = SimpleNamespace(service_id="image-context-service")
        self.region_component = SimpleNamespace(service_id=self.component.service_id)
        self.factory = APIRequestFactory()
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.real_create = app_views.console_app_service.create_docker_run_app
        self.real_bind = app_views.group_service.add_service_to_group
        self.real_source = app_views.console_app_service.create_service_source_info
        self.create = self.stack.enter_context(mock.patch.object(
            app_views.console_app_service, "create_docker_run_app", return_value=(200, "success", self.component)))
        self.region_create = self.stack.enter_context(mock.patch.object(
            app_views.console_app_service, "create_region_service", return_value=self.region_component))
        self.bind = self.stack.enter_context(mock.patch.object(
            app_views.group_service, "add_service_to_group", return_value=(200, "success")))
        self.deploy = self.stack.enter_context(mock.patch.object(app_views.app_manage_service, "deploy"))
        self.source = self.stack.enter_context(mock.patch.object(app_views.console_app_service, "create_service_source_info"))

    def create_app(self, team, region):
        now = timezone.now()
        return ServiceGroup.objects.create(tenant_id=team.tenant_id, region_name=region, group_name="fixture-app",
                                           create_time=now, update_time=now)

    def post(self, body=None, app_id=None, denied=False):
        payload = {"image": "example.invalid/fixture:latest", "service_cname": "fixture", "is_deploy": False}
        if body:
            payload.update(body)
        request = self.factory.post("/openapi/image-component", payload, format="json")

        def authenticated_team_context(view, request, *args, **kwargs):
            if denied:
                raise NoPermissionsError()
            view.team = self.team
            view.user = self.user
            view.enterprise = SimpleNamespace(enterprise_id="image-context-enterprise")
            view.region_name = "region"

        with mock.patch.object(TeamAPIView, "initial", authenticated_team_context):
            return app_views.ListAppServicesView.as_view()(
                request, region_name="region", app_id=str(self.app.ID if app_id is None else app_id))

    def assert_no_creation(self):
        self.create.assert_not_called()
        self.bind.assert_not_called()
        self.region_create.assert_not_called()
        self.deploy.assert_not_called()
        self.source.assert_not_called()

    def test_omitted_group_uses_authorized_route_app(self):
        response = self.post()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["bean"], {"service_id": self.component.service_id})
        self.assertEqual(self.create.call_args.args[1].tenant_id, self.team.tenant_id)
        self.assertEqual(self.bind.call_args.args[2:], (self.app.ID, self.component.service_id))
        self.deploy.assert_not_called()

    def test_matching_legacy_group_id_is_accepted_as_string_or_integer(self):
        for value in (self.app.ID, str(self.app.ID), "0" + str(self.app.ID), " {} ".format(self.app.ID)):
            with self.subTest(value=value):
                self.assertEqual(self.post({"group_id": value}).status_code, 200)
        self.assertEqual(self.create.call_count, 4)

    def test_body_group_cannot_target_another_team(self):
        other_team = Tenants.objects.create(
            tenant_id="other-team", tenant_name="other-team", namespace="other-team", enterprise_id="other-enterprise")
        other_app = self.create_app(other_team, "region")
        response = self.post({"group_id": other_app.ID})
        self.assertEqual(response.status_code, 400)
        self.assert_no_creation()

    def test_body_group_cannot_target_another_app_in_same_team(self):
        other_app = self.create_app(self.team, "region")
        self.assertEqual(self.post({"group_id": other_app.ID}).status_code, 400)
        self.assert_no_creation()

    def test_invalid_group_values_return_400_before_side_effects(self):
        for value in (None, "", "invalid", -1, True, False, self.app.ID + 0.5, [], {}):
            with self.subTest(value=value):
                self.assertEqual(self.post({"group_id": value}).status_code, 400)
                self.assert_no_creation()

    def test_unknown_route_app_returns_404(self):
        self.assertEqual(self.post(app_id=self.app.ID + 10000).status_code, 404)
        self.assert_no_creation()

    def test_route_app_from_another_team_returns_404(self):
        other_app = self.create_app(SimpleNamespace(tenant_id="foreign-team"), "region")
        self.assertEqual(self.post(app_id=other_app.ID).status_code, 404)
        self.assert_no_creation()

    def test_route_app_from_another_region_returns_404(self):
        other_app = self.create_app(self.team, "other-region")
        self.assertEqual(self.post(app_id=other_app.ID).status_code, 404)
        self.assert_no_creation()

    def test_team_deleted_after_context_loading_returns_404(self):
        Tenants.objects.filter(pk=self.team.pk).delete()
        self.assertEqual(self.post({"group_id": self.app.ID}).status_code, 404)
        self.assert_no_creation()

    def test_missing_team_never_reaches_real_component_creation(self):
        Tenants.objects.filter(pk=self.team.pk).delete()
        self.create.side_effect = self.real_create
        self.assertEqual(self.post({"group_id": self.app.ID}).status_code, 404)
        self.assert_no_creation()

    def test_app_deleted_after_initial_validation_returns_404(self):
        lookup = app_views.group_service.get_app_by_id

        def lookup_then_delete(*args):
            app = lookup(*args)
            ServiceGroup.objects.filter(pk=self.app.pk).delete()
            return app

        with mock.patch.object(app_views.group_service, "get_app_by_id", side_effect=lookup_then_delete):
            self.assertEqual(self.post({"group_id": self.app.ID}).status_code, 404)
        self.assert_no_creation()

    def test_permission_denial_stops_creation(self):
        self.assertEqual(self.post({"group_id": self.app.ID}, denied=True).status_code, 403)
        self.assert_no_creation()

    def test_success_can_still_deploy_to_authorized_team(self):
        self.assertEqual(self.post({"group_id": self.app.ID, "is_deploy": True}).status_code, 200)
        self.deploy.assert_called_once_with(mock.ANY, self.region_component, self.user)
        self.assertEqual(self.deploy.call_args.args[0].tenant_id, self.team.tenant_id)

    def test_creation_failure_stops_binding_region_and_deployment(self):
        self.create.return_value = (409, "fixture conflict", None)
        response = self.post({"group_id": self.app.ID})
        self.assertEqual(response.status_code, 409)
        self.bind.assert_not_called()
        self.region_create.assert_not_called()
        self.deploy.assert_not_called()

    def test_registry_username_is_saved_for_the_authorized_team(self):
        self.assertEqual(self.post({"user_name": "fixture-user"}).status_code, 200)
        self.source.assert_called_once_with(mock.ANY, self.component, "fixture-user", None)
        self.assertEqual(self.source.call_args.args[0].tenant_id, self.team.tenant_id)

    def test_region_creation_failure_keeps_existing_failure_response(self):
        self.region_create.side_effect = RuntimeError("fixture region unavailable")
        response = self.post({"is_deploy": True})
        self.assertEqual(response.status_code, 400)
        self.deploy.assert_not_called()

    def test_deployment_failure_keeps_existing_failure_response(self):
        self.deploy.side_effect = RuntimeError("fixture build failed")
        self.assertEqual(self.post({"is_deploy": True}).status_code, 400)

    def test_duplicate_component_name_stops_before_creation(self):
        with mock.patch.object(app_views.console_app_service, "is_k8s_component_name_duplicate", return_value=True) as check:
            response = self.post({"k8s_component_name": "fixture-name"})
        self.assertEqual(response.status_code, 400)
        check.assert_called_once_with(self.app.ID, "fixture-name")
        self.assert_no_creation()

    def test_binding_failure_does_not_create_region_component_or_deploy(self):
        self.bind.return_value = (404, "应用不存在")
        self.assertEqual(self.post({"is_deploy": True}).status_code, 404)
        self.region_create.assert_not_called()
        self.deploy.assert_not_called()

    def test_app_disappearing_before_binding_rolls_back_local_component(self):
        def create_then_remove_app(*args):
            component = TenantServiceInfo.objects.create(
                tenant_id=self.team.tenant_id, service_id="rollback-image-context-service", service_region="region",
                service_key="application", service_alias="fixture", service_cname="fixture", category="application",
                version="1", image="example.invalid/fixture:latest", service_source="docker_image")
            ServiceGroup.objects.filter(pk=self.app.pk).delete()
            return 200, "success", component

        self.create.side_effect = create_then_remove_app
        self.bind.side_effect = self.real_bind
        self.assertEqual(self.post({"is_deploy": True}).status_code, 404)
        self.assertFalse(TenantServiceInfo.objects.filter(service_id="rollback-image-context-service").exists())
        self.region_create.assert_not_called()
        self.deploy.assert_not_called()

    def test_image_creation_telemetry_waits_for_successful_local_commit(self):
        self.create.side_effect = self.real_create
        self.bind.side_effect = self.real_bind
        with mock.patch.object(app_service_module.telemetry_service, "track_component_created") as track:
            with self.captureOnCommitCallbacks(execute=True) as callbacks:
                self.assertEqual(self.post().status_code, 200)
                track.assert_not_called()
            self.assertEqual(len(callbacks), 1)
            track.assert_called_once()
            self.assertEqual(track.call_args.kwargs["tenant"].tenant_id, self.team.tenant_id)
            component = track.call_args.kwargs["component"]
            self.assertTrue(TenantServiceInfo.objects.filter(service_id=component.service_id).exists())

    def test_image_creation_telemetry_is_discarded_when_binding_rolls_back(self):
        self.create.side_effect = self.real_create
        self.bind.return_value = (404, "应用不存在")
        self.source.side_effect = self.real_source
        with mock.patch.object(app_service_module.telemetry_service, "track_component_created") as track:
            with self.captureOnCommitCallbacks(execute=True) as callbacks:
                self.assertEqual(self.post({"is_deploy": True, "user_name": "fixture-user"}).status_code, 404)
            self.assertEqual(callbacks, [])
            track.assert_not_called()
        self.assertFalse(TenantServiceInfo.objects.filter(tenant_id=self.team.tenant_id).exists())
        self.assertFalse(ServiceSourceInfo.objects.filter(team_id=self.team.tenant_id).exists())
        self.region_create.assert_not_called()
        self.deploy.assert_not_called()
