# -*- coding: utf-8 -*-
import os
from unittest import TestCase, mock

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.test_settings")

import django  # noqa: E402

django.setup()

from rest_framework.test import APIRequestFactory  # noqa: E402

from console.views import enterprise as enterprise_views  # noqa: E402


# capability_id: console.enterprise.resource-category-ordering
class ResourceCategoriesMixin:
    def get_response(self, bean, query=None):
        request = APIRequestFactory().get("/resource-categories", query or {})
        view = self.view_class()
        with mock.patch.object(enterprise_views.region_resource, self.service_method,
                               return_value={"bean": bean}) as get_resources:
            response = view.get(request, enterprise_id="fixture-enterprise", region_id="fixture-region")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["code"], 200)
        return response.data["data"]["bean"], get_resources

    def test_missing_unclassified_category_keeps_existing_categories(self):
        bean = {"deployment": [{"name": "web"}], "service": [{"name": "web-service"}]}
        result, _ = self.get_response(bean)
        self.assertEqual(result, bean)
        self.assertEqual(list(result), ["deployment", "service"])
        self.assertNotIn("unclassified", result)

    def test_empty_resource_mapping_is_success(self):
        result, _ = self.get_response({})
        self.assertEqual(result, {})

    def test_existing_unclassified_category_moves_last_without_losing_resources(self):
        resource = {"kind": "FixtureResource", "metadata": {"name": "external"}}
        bean = {"unclassified": [resource], "deployment": [{"name": "web"}], "service": []}
        result, _ = self.get_response(bean)
        self.assertEqual(list(result), ["deployment", "service", "unclassified"])
        self.assertEqual(result["unclassified"], [resource])
        self.assertEqual(result["deployment"], [{"name": "web"}])
        self.assertEqual(result["service"], [])

    def test_empty_unclassified_category_remains_present(self):
        result, _ = self.get_response({"unclassified": [], "deployment": []})
        self.assertEqual(list(result), ["deployment", "unclassified"])
        self.assertEqual(result["unclassified"], [])

    def test_null_unclassified_value_is_preserved(self):
        result, _ = self.get_response({"unclassified": None, "deployment": []})
        self.assertEqual(list(result), ["deployment", "unclassified"])
        self.assertIsNone(result["unclassified"])

    def test_content_and_namespace_query_are_forwarded_unchanged(self):
        result, get_resources = self.get_response({"unclassified": []}, {"content": "pod", "namespace": "fixture-ns"})
        self.assertEqual(result, {"unclassified": []})
        get_resources.assert_called_once_with(*self.query_arguments)

    def test_downstream_failure_is_not_converted_to_empty_success(self):
        request = APIRequestFactory().get("/resource-categories")
        view = self.view_class()
        failure = RuntimeError("fixture region request failed")
        with mock.patch.object(enterprise_views.region_resource, self.service_method, side_effect=failure):
            with self.assertRaises(RuntimeError) as raised:
                view.get(request, enterprise_id="fixture-enterprise", region_id="fixture-region")
        self.assertIs(raised.exception, failure)


class EnterpriseNamespaceResourceCategoriesTests(ResourceCategoriesMixin, TestCase):
    view_class = enterprise_views.EnterpriseNamespaceResource
    service_method = "get_namespaces_resource"
    query_arguments = ("fixture-enterprise", "fixture-region", "pod", "fixture-ns")


class EnterpriseConvertResourceCategoriesTests(ResourceCategoriesMixin, TestCase):
    view_class = enterprise_views.EnterpriseConvertResource
    service_method = "convert_resource"
    query_arguments = ("fixture-enterprise", "fixture-region", "fixture-ns", "pod")
