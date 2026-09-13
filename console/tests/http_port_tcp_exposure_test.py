"""HTTP component ports may also have independently created TCP mappings."""
import importlib
import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.test_settings")
import django  # noqa: E402

django.setup()

from django.test import RequestFactory  # noqa: E402
from www.models.main import TenantServicesPort  # noqa: E402

view_module = importlib.import_module("console.views.app_config.app_port")
service_module = importlib.import_module("console.services.app_config.port_service")


class HTTPPortTCPExposureTests(unittest.TestCase):
    def setUp(self):
        self.tenant = SimpleNamespace(tenant_id="tenant", tenant_name="team", enterprise_id="enterprise")
        self.service = SimpleNamespace(service_id="component", service_alias="demo", service_region="region",
                                       service_cname="Demo", create_status="complete")
        self.region = SimpleNamespace(region_id="region", region_name="region")
        self.port = TenantServicesPort(ID=1, tenant_id="tenant", service_id="component", container_port=8080,
                                       protocol="http", is_inner_service=True, is_outer_service=False)
        self.port.save = MagicMock()
        self.http_domains = []
        self.stream_rules = [{"service_name": "original-name-30000", "nodePort": 30000, "protocol": "TCP"}]
        self.api = MagicMock()
        self.api.api_gateway_get_proxy.side_effect = self.gateway_response
        self.patch(view_module, "region_api", self.api)
        self.patch(service_module, "region_api", self.api)
        self.patch(service_module.AppPortService, "get_service_ports", return_value=[self.port])
        self.patch(service_module.AppPortService, "get_port_variables", return_value={"environment": []})
        self.patch(service_module.group_repo, "get_by_service_id", return_value=SimpleNamespace(app_id=7))
        self.patch(service_module.domain_repo, "get_service_domain_by_container_port", return_value=[])
        self.local_delete = self.patch(service_module.tcp_domain, "delete_by_component_port")
        self.patch(importlib.import_module("console.services.plugin").app_plugin_service,
                   "update_config_if_have_entrance_plugin")

    def patch(self, target, name, *args, **kwargs):
        patcher = patch.object(target, name, *args, **kwargs)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def gateway_response(self, region, tenant_id, path, app_id):
        if "/http/domains?" in path:
            return {"list": self.http_domains}
        if "/tcp/domains?" in path:
            return {"list": self.stream_rules}
        if "/http/port?act=close" in path:
            return {"bean": {}}
        raise AssertionError("unexpected gateway request: " + path)

    def get_port(self):
        view = view_module.AppPortView()
        view.tenant = self.tenant
        view.tenant_name = self.tenant.tenant_name
        view.service = self.service
        view.region = self.region
        return view.get(RequestFactory().get("/ports")).data["data"]["list"][0]

    def close_port(self):
        return service_module.AppPortService()._AppPortService__close_outer(
            self.tenant, self.service, self.region, self.port, "operator")

    def test_http_port_shows_tcp_mapping_and_updates_only_exposure_flag(self):
        result = self.get_port()
        self.assertEqual(result["protocol"], "http")
        self.assertEqual(result["bind_domains"], [])
        self.assertTrue(result["is_outer_service"])
        self.assertEqual(result["bind_tcp_domains"][0]["end_point"], "0.0.0.0:30000")
        self.assertEqual(result["bind_tcp_domains"][0]["protocol"], "tcp")
        self.assertEqual(result["bind_tcp_domains"][0]["service_name"], "demo")
        self.assertTrue(self.port.is_outer_service)
        self.assertEqual(self.port.protocol, "http")
        self.port.save.assert_called_once_with(update_fields=["is_outer_service"])

    def test_http_domains_and_tcp_mappings_are_both_returned(self):
        self.http_domains = ["demo.example"]
        result = self.get_port()
        self.assertEqual(result["bind_domains"][0]["domain_name"], "demo.example")
        self.assertEqual(len(result["bind_tcp_domains"]), 1)
        self.assertTrue(result["is_outer_service"])

    def test_http_only_port_stays_open(self):
        self.http_domains = ["demo.example"]
        self.stream_rules = []
        self.assertTrue(self.get_port()["is_outer_service"])

    def test_no_mappings_marks_port_closed(self):
        self.port.is_outer_service = True
        self.stream_rules = []
        self.assertFalse(self.get_port()["is_outer_service"])
        self.assertFalse(self.port.is_outer_service)

    def test_failed_tcp_query_does_not_write_a_false_closed_state(self):
        self.port.is_outer_service = True
        self.api.api_gateway_get_proxy.side_effect = [{"list": []}, RuntimeError("gateway unavailable")]
        with self.assertRaisesRegex(RuntimeError, "gateway unavailable"):
            self.get_port()
        self.assertTrue(self.port.is_outer_service)
        self.port.save.assert_not_called()

    def test_close_http_port_deletes_tcp_by_actual_service_name(self):
        self.port.is_outer_service = True
        self.http_domains = ["demo.example"]
        self.assertEqual(self.close_port()[0], 200)
        self.api.delete_proxy.assert_called_once_with(
            "region", "/v2/proxy-pass/gateway/team/routes/tcp/original-name-30000?service_id=component")
        self.assertTrue(any("/http/port?act=close" in call.args[2]
                            for call in self.api.api_gateway_get_proxy.call_args_list))
        self.assertFalse(self.port.is_outer_service)
        self.api.manage_outer_port.assert_called_once()

    def test_close_third_party_port_resolves_region_name(self):
        self.service.service_region = "region-name"
        self.port.is_outer_service = True
        self.api.CallApiError = service_module.RegionApiBaseHttpClient.CallApiError
        region_lookup = self.patch(service_module.region_repo, "get_region_by_region_name", return_value=self.region)

        def gateway_response(region, tenant_id, path, app_id):
            self.assertEqual(region.region_name, self.region.region_name)
            return self.gateway_response(region, tenant_id, path, app_id)

        self.api.api_gateway_get_proxy.side_effect = gateway_response
        service_module.AppPortService().close_thirdpart_outer(self.tenant, self.service, self.service.service_region,
                                                              self.port)

        region_lookup.assert_called_once_with(self.service.service_region)
        self.api.delete_proxy.assert_called_once_with(
            self.region.region_name, "/v2/proxy-pass/gateway/team/routes/tcp/original-name-30000?service_id=component")
        self.api.manage_outer_port.assert_called_once()
        self.assertFalse(self.port.is_outer_service)

    def test_close_third_party_port_rejects_missing_region(self):
        self.port.is_outer_service = True
        self.api.CallApiError = service_module.RegionApiBaseHttpClient.CallApiError
        region_lookup = self.patch(service_module.region_repo, "get_region_by_region_name", return_value=None)

        with self.assertRaises(service_module.ServiceHandleException) as context:
            service_module.AppPortService().close_thirdpart_outer(self.tenant, self.service,
                                                                  self.service.service_region, self.port)

        self.assertEqual(context.exception.status_code, 404)
        region_lookup.assert_called_once_with(self.service.service_region)
        self.api.api_gateway_get_proxy.assert_not_called()
        self.api.delete_proxy.assert_not_called()
        self.api.manage_outer_port.assert_not_called()
        self.port.save.assert_not_called()
        self.assertTrue(self.port.is_outer_service)

    def test_close_third_party_port_preserves_gateway_failure(self):
        self.port.is_outer_service = True
        self.api.CallApiError = service_module.RegionApiBaseHttpClient.CallApiError
        self.patch(service_module.region_repo, "get_region_by_region_name", return_value=self.region)
        self.api.api_gateway_get_proxy.side_effect = RuntimeError("gateway unavailable")

        with self.assertRaisesRegex(RuntimeError, "gateway unavailable"):
            service_module.AppPortService().close_thirdpart_outer(self.tenant, self.service,
                                                                  self.service.service_region, self.port)

        self.api.manage_outer_port.assert_not_called()
        self.port.save.assert_not_called()
        self.assertTrue(self.port.is_outer_service)

    def test_failed_delete_keeps_port_open_and_saved_mappings(self):
        self.port.is_outer_service = True
        self.api.delete_proxy.side_effect = RuntimeError("delete failed")
        with self.assertRaisesRegex(RuntimeError, "delete failed"):
            self.close_port()
        self.assertTrue(self.port.is_outer_service)
        self.port.save.assert_not_called()
        self.local_delete.assert_not_called()
        self.api.manage_outer_port.assert_not_called()

    def test_close_attempts_other_mappings_after_one_delete_fails(self):
        self.port.is_outer_service = True
        self.stream_rules.append({"service_name": "another-name-30001", "nodePort": 30001, "protocol": "TCP"})
        self.api.delete_proxy.side_effect = [RuntimeError("delete failed"), None]
        with self.assertRaisesRegex(RuntimeError, "delete failed"):
            self.close_port()
        self.assertEqual(self.api.delete_proxy.call_count, 2)
        self.assertTrue(self.port.is_outer_service)

    def test_incomplete_query_response_does_not_write_closed_state(self):
        self.port.is_outer_service = True
        self.api.api_gateway_get_proxy.side_effect = [{"list": []}, None]
        with self.assertRaises(view_module.AbortRequest):
            self.get_port()
        self.port.save.assert_not_called()
        self.assertTrue(self.port.is_outer_service)

    def test_http_close_failure_still_attempts_tcp_without_saving_closed_state(self):
        self.port.is_outer_service = True
        self.http_domains = ["demo.example"]

        def fail_http_close(region, tenant_id, path, app_id):
            if "/http/port?act=close" in path:
                raise RuntimeError("HTTP close failed")
            return self.gateway_response(region, tenant_id, path, app_id)

        self.api.api_gateway_get_proxy.side_effect = fail_http_close
        with self.assertRaisesRegex(RuntimeError, "HTTP close failed"):
            self.close_port()
        self.api.delete_proxy.assert_called_once()
        self.port.save.assert_not_called()
        self.local_delete.assert_not_called()
        self.assertTrue(self.port.is_outer_service)

    def test_repeated_query_keeps_existing_state_without_extra_writes(self):
        self.port.is_outer_service = True
        self.assertTrue(self.get_port()["is_outer_service"])
        self.port.save.assert_not_called()


if __name__ == "__main__":
    unittest.main()
