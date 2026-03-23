from unittest import TestCase

from console.services.gray_release_route_utils import (
    extract_actual_route_name,
    extract_region_app_id,
    route_name_candidates,
)


class GrayReleaseRouteNameTests(TestCase):
    def test_extract_actual_route_name_from_original_name(self):
        route = {
            "name": "312345.comp-ps-s-graf6613",
            "original_name": "3|12345.comp-ps-s|-graf6613",
        }

        self.assertEqual(extract_actual_route_name(route), "12345.comp-ps-s")

    def test_extract_actual_route_name_falls_back_to_name(self):
        route = {
            "name": "12345.comp-ps-s",
        }

        self.assertEqual(extract_actual_route_name(route), "12345.comp-ps-s")

    def test_extract_region_app_id_prefers_explicit_field(self):
        route = {
            "region_app_id": 12,
            "original_name": "3|12345.comp-ps-s|-graf6613",
        }

        self.assertEqual(extract_region_app_id(route), "12")

    def test_extract_region_app_id_from_original_name(self):
        route = {
            "name": "312345.comp-ps-s-graf6613",
            "original_name": "3|12345.comp-ps-s|-graf6613",
        }

        self.assertEqual(extract_region_app_id(route), "3")

    def test_route_name_candidates_contains_display_original_and_actual_names(self):
        route = {
            "name": "312345.comp-ps-s-graf6613",
            "original_name": "3|12345.comp-ps-s|-graf6613",
            "region_app_id": "3",
        }

        self.assertEqual(
            route_name_candidates(route),
            [
                "312345.comp-ps-s-graf6613",
                "3|12345.comp-ps-s|-graf6613",
                "12345.comp-ps-s",
            ],
        )
