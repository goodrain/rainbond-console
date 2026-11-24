# -*- coding: utf-8 -*-
import copy
import json
import os
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.test_settings")

import django  # noqa: E402

django.setup()

from django.test import TestCase  # noqa: E402
from rest_framework.test import APIRequestFactory  # noqa: E402

from console.exception.main import ServiceHandleException  # noqa: E402
from console.models.main import ComponentK8sAttributes  # noqa: E402
from console.services import k8s_attribute as attribute_module  # noqa: E402
from console.views.app_config.base import AppBaseView  # noqa: E402
from console.views.k8s_attribute import ComponentK8sAttributeListView  # noqa: E402
from www.models.main import TenantServiceInfo, Tenants  # noqa: E402


# capability_id: console.k8s-attribute.create-payload-validation
class K8sAttributeInputValidationTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.team = Tenants.objects.create(
            tenant_id="attribute-input-team", tenant_name="attribute-input-team", namespace="attribute-input-team")
        self.component = TenantServiceInfo.objects.create(
            tenant_id=self.team.tenant_id, service_id="attribute-input-component", service_region="fixture-region",
            service_key="application", service_alias="fixture-component", service_cname="fixture-component",
            category="application", version="1", image="", service_source="docker_image")
        self.region_create = mock.patch.object(attribute_module.region_api, "create_component_k8s_attribute").start()
        self.region_update = mock.patch.object(attribute_module.region_api, "update_component_k8s_attribute").start()
        self.addCleanup(mock.patch.stopall)

    def post(self, payload):
        def authorized_component_context(view, request, *args, **kwargs):
            view.tenant = self.team
            view.service = self.component
            view.region_name = "fixture-region"
            view.user = SimpleNamespace(nick_name="fixture-operator")

        with mock.patch.object(AppBaseView, "initial", new=authorized_component_context):
            return ComponentK8sAttributeListView.as_view()(
                self.factory.post("/component/attributes", payload, format="json"))

    def assert_invalid(self, payload):
        response = self.post(payload)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], 400)
        self.assertFalse(ComponentK8sAttributes.objects.filter(component_id=self.component.service_id).exists())
        self.region_create.assert_not_called()
        self.region_update.assert_not_called()

    def test_omitted_attribute_is_rejected_before_side_effects(self):
        self.assert_invalid({})

    def test_non_mapping_attribute_is_rejected_before_side_effects(self):
        for value in (None, [], ["labels"], True, 7, "labels"):
            with self.subTest(value=value):
                self.assert_invalid({"attribute": value})

    def test_missing_save_type_for_regular_attribute_returns_400(self):
        self.assert_invalid({"attribute": {"name": "labels", "attribute_value": {"role": "web"}}})

    def test_invalid_save_types_are_rejected_before_serialization(self):
        for value in (None, "", "unknown", "JSON", [], {}, True, 7):
            with self.subTest(value=value):
                self.assert_invalid({"attribute": {"name": "labels", "save_type": value,
                                                   "attribute_value": {"role": "web"}}})

    def test_invalid_attribute_names_are_rejected(self):
        for value in (None, "", [], {}, True, 7):
            with self.subTest(value=value):
                self.assert_invalid({"attribute": {"name": value, "save_type": "json", "attribute_value": {}}})

    def test_sequence_attributes_still_infer_yaml_when_type_is_omitted(self):
        for name in ("cmd", "args"):
            with self.subTest(name=name):
                response = self.post({"attribute": {"name": name, "attribute_value": ["sh", "-c", "echo fixture"]}})
                self.assertEqual(response.status_code, 200)
                saved = ComponentK8sAttributes.objects.get(component_id=self.component.service_id, name=name)
                self.assertEqual(saved.save_type, "yaml")
                self.assertEqual(saved.attribute_value, "- sh\n- -c\n- echo fixture\n")
                self.assertEqual(self.region_create.call_args.args[3]["save_type"], "yaml")

    def test_sequence_attributes_keep_supported_legacy_json_conversion(self):
        response = self.post({"attribute": {"name": "cmd", "save_type": "json", "attribute_value": ["/bin/sh"]}})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ComponentK8sAttributes.objects.get(name="cmd").save_type, "yaml")

    def test_sequence_attribute_with_explicit_invalid_type_returns_400(self):
        self.assert_invalid({"attribute": {"name": "cmd", "save_type": [], "attribute_value": ["/bin/sh"]}})

    def test_valid_json_attribute_preserves_serialization_and_region_request(self):
        response = self.post({"attribute": {"name": "labels", "save_type": "json",
                                            "attribute_value": [{"key": "role", "value": "web"}]}})
        self.assertEqual(response.status_code, 200)
        saved = ComponentK8sAttributes.objects.get(name="labels")
        self.assertEqual(saved.attribute_value, json.dumps({"role": "web"}))
        self.region_create.assert_called_once_with(
            self.team.tenant_name, "fixture-region", self.component.service_alias,
            {"name": "labels", "save_type": "json", "attribute_value": saved.attribute_value,
             "operator": "fixture-operator"})

    def test_valid_yaml_attribute_is_saved_unchanged(self):
        value = "runAsNonRoot: true\n"
        self.assertEqual(self.post({"attribute": {"name": "securityContext", "save_type": "yaml",
                                                  "attribute_value": value}}).status_code, 200)
        self.assertEqual(ComponentK8sAttributes.objects.get(name="securityContext").attribute_value, value)

    def test_valid_string_attribute_is_saved_unchanged(self):
        self.assertEqual(self.post({"attribute": {"name": "workingDir", "save_type": "string",
                                                  "attribute_value": "/workspace"}}).status_code, 200)
        self.assertEqual(ComponentK8sAttributes.objects.get(name="workingDir").attribute_value, "/workspace")

    def test_direct_service_call_gets_business_error_before_any_write(self):
        attribute = {"name": "workingDir", "attribute_value": "/workspace"}
        with self.assertRaises(ServiceHandleException) as raised:
            attribute_module.k8s_attribute_service.create_k8s_attribute(
                self.team, self.component, "fixture-region", copy.deepcopy(attribute), "fixture-operator")
        self.assertEqual(raised.exception.status_code, 400)
        self.assertFalse(ComponentK8sAttributes.objects.exists())
        self.region_create.assert_not_called()

    def test_external_failure_remains_failure_and_rolls_back_local_record(self):
        self.region_create.side_effect = RuntimeError("fixture region unavailable")
        attribute = {"name": "workingDir", "save_type": "string", "attribute_value": "/workspace"}
        with self.assertRaises(RuntimeError):
            attribute_module.k8s_attribute_service.create_k8s_attribute(
                self.team, self.component, "fixture-region", attribute, "fixture-operator")
        self.assertFalse(ComponentK8sAttributes.objects.exists())
        self.region_update.assert_not_called()
