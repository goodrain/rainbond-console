# -*- coding: utf-8 -*-
from unittest import mock

from django.test import SimpleTestCase

from console.views.rbd_plugin import (
    _enrich_gateway_monitoring_app_items,
    _is_gateway_monitoring_app_top_path,
)


class FakeValuesQuerySet(list):
    def values(self, *args):
        return self


class GatewayMonitoringPluginProxyTests(SimpleTestCase):
    def test_gateway_monitoring_app_top_path_detection(self):
        self.assertTrue(_is_gateway_monitoring_app_top_path(
            "rainbond-gateway-monitoring",
            "api/v1/platform/apps/top-latency",
        ))
        self.assertTrue(_is_gateway_monitoring_app_top_path(
            "rainbond-gateway-monitoring",
            "api/v1/teams/rbd-prd/apps/top-throughput",
        ))
        self.assertFalse(_is_gateway_monitoring_app_top_path(
            "rainbond-gateway-monitoring",
            "api/v1/apps/3/components/summary",
        ))
        self.assertFalse(_is_gateway_monitoring_app_top_path(
            "other-plugin",
            "api/v1/platform/apps/top-latency",
        ))

    @mock.patch("console.views.rbd_plugin.Tenants.objects.filter")
    @mock.patch("console.views.rbd_plugin.ServiceGroup.objects.filter")
    @mock.patch("console.views.rbd_plugin.RegionApp.objects.filter")
    def test_enriches_app_and_team_names_from_console_models(
            self,
            region_app_filter,
            service_group_filter,
            tenant_filter,
    ):
        region_app_filter.return_value = FakeValuesQuerySet([
            {
                "region_app_id": "6cf2bf3464d74f3da0a612c5917b2957",
                "app_id": 3,
            },
        ])
        service_group_filter.return_value = FakeValuesQuerySet([
            {
                "ID": 3,
                "tenant_id": "team-id-1",
                "group_name": "订单系统",
                "region_name": "rainbond",
            },
        ])
        tenant_filter.return_value = FakeValuesQuerySet([
            {
                "tenant_id": "team-id-1",
                "tenant_name": "rbd-prd",
                "tenant_alias": "生产团队",
                "namespace": "rbd-prd",
            },
        ])

        payload = {
            "data": [
                {
                    "app_id": "3",
                    "team_id": "unknown_team",
                    "namespace": "rbd-prd",
                    "region_app_id": "6cf2bf3464d74f3da0a612c5917b2957",
                    "name": "3",
                    "request_count": 280,
                },
            ],
        }

        _enrich_gateway_monitoring_app_items(payload, "rainbond")

        self.assertEqual(payload["data"][0]["app_id"], "3")
        self.assertEqual(payload["data"][0]["name"], "订单系统")
        self.assertEqual(payload["data"][0]["app_name"], "订单系统")
        self.assertEqual(payload["data"][0]["team_id"], "team-id-1")
        self.assertEqual(payload["data"][0]["team_name"], "rbd-prd")
        self.assertEqual(payload["data"][0]["team_alias"], "生产团队")
