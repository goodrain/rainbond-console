import json
import hashlib
import hmac
import unittest

from console.services.cleanup_inventory import (template_resource, verify_source_request, version_resources,
                                                deployment_resource, failed_scope_label)


class CleanupInventoryProjectionTests(unittest.TestCase):
    def test_failed_component_keeps_identifier_and_readable_context(self):
        self.assertEqual(failed_scope_label({"service_id": "s1", "service_cname": "支付接口", "owner_name": "研发 / 商城"}),
                         "研发 / 商城 / 支付接口 (s1)")
        self.assertEqual(failed_scope_label({"service_id": "s1"}), "s1")

    def test_version_owner_uses_team_and_application_label(self):
        component = {"service_id": "component-id", "service_cname": "订单接口", "owner_name": "研发团队 / 订单系统"}
        result = version_resources(component, {"list": [{"build_version": "v1"}]}, "r")[0]
        self.assertEqual(result["name"], "订单接口 / v1")
        self.assertEqual(result["owner"], "研发团队 / 订单系统")
        self.assertEqual(result["id"], "version:r:component-id:v1")

    def test_deployment_reference_is_readable_without_changing_key(self):
        row = {"ID": 1, "service_id": "component-id", "service_cname": "订单接口", "owner_name": "研发团队 / 订单系统",
               "app_upgrade_record_id": 9, "app_upgrade_record__group_name": "订单系统",
               "app_upgrade_record__old_version": "v1", "app_upgrade_record__version": "v2"}
        result = deployment_resource(row, "r")
        self.assertEqual(result["owner"], "研发团队 / 订单系统")
        self.assertEqual(result["references"][0]["key"], "app-record:9")
        self.assertIn("订单系统", result["references"][0]["name"])

    def test_template_uses_published_chinese_name_and_keeps_stable_id(self):
        row = {"ID": 3, "app_id": "opaque-id", "version": "v2",
               "share_team": "team-id", "owner_name": "研发团队 / 订单系统",
               "app_template": json.dumps({"group_name": "订单管理系统", "apps": []})}
        result = template_resource(row, "r", False)
        self.assertEqual(result["name"], "订单管理系统 / v2")
        self.assertEqual(result["id"], "template:r:3")
        self.assertEqual(result["owner"], "")
        self.assertEqual(result["protection"], "reference_unknown")

    def test_snapshot_name_and_legacy_name_fallback(self):
        for template, expected in [({"group_name": "数据库备份"}, "数据库备份"),
                                   ({"group_name": " ", "app_name": "旧版模板"}, "旧版模板"),
                                   ({"group_name": {}}, "opaque-id"), ({}, "opaque-id")]:
            result = template_resource({"ID": 4, "app_id": "opaque-id", "version": "v1",
                                        "app_template": json.dumps(template)}, "r", True)
            self.assertEqual(result["name"], expected + " / v1")
            self.assertEqual(result["resourceType"], "application_snapshot")
            self.assertEqual(result["owner"], "")

    def test_deployment_record_is_read_only_evidence_not_a_rollback_guarantee(self):
        row = {"ID": 8, "service_id": "s", "service_cname": "web", "status": 3,
               "app_upgrade_record__version": "v2", "app_upgrade_record__old_version": "v1",
               "app_upgrade_record__record_type": "upgrade", "app_upgrade_record_id": 4,
               "update": "do-not-export"}
        result = deployment_resource(row, "r")
        self.assertEqual(result["resourceType"], "recorded_upgrade")
        self.assertEqual(result["usageStatus"], "history_unverified")
        self.assertEqual(result["recordStatus"], "upgraded")
        self.assertIsNone(result["unusedSince"])
        self.assertNotIn("do-not-export", json.dumps(result))
        row["status"] = 4
        row["app_upgrade_record__record_type"] = "rollback"
        self.assertEqual(deployment_resource(row, "r")["usageStatus"], "referenced")

    def test_template_schema_failure_does_not_crash_or_claim_observation(self):
        for section in (None, {}, "bad", [None]):
            result = template_resource({"ID": 1, "app_template": json.dumps({"apps": section})}, "r", False)
            self.assertFalse(result["observed"])

    def test_source_signature_binds_method_path_scope_and_time(self):
        key = bytes(range(32))
        path = "/console/cleanup/internal/inventory/e/r?kind=templates"
        raw = "\n".join(["cleanup-inventory-v1", "GET", path, "e", "r", "1000"])
        signature = hmac.new(key, raw.encode("utf-8"), hashlib.sha256).hexdigest()
        self.assertTrue(verify_source_request("GET", path, "e", "r", "1000", signature, key, now=1000))
        for method, target, enterprise, region, timestamp, signed, now in [
                ("POST", path, "e", "r", "1000", signature, 1000),
                ("GET", path + "&cursor=1", "e", "r", "1000", signature, 1000),
                ("GET", path, "other", "r", "1000", signature, 1000),
                ("GET", path, "e", "other", "1000", signature, 1000),
                ("GET", path, "e", "r", "1000", signature, 1201),
                ("GET", path, "e", "r", "invalid", signature, 1000),
                ("GET", path, "e", "r", "1000", "invalid", 1000)]:
            self.assertFalse(verify_source_request(method, target, enterprise, region, timestamp, signed, key, now=now))

    def test_template_projection_keeps_images_but_excludes_configuration(self):
        row = {"ID": 3, "app_id": "app", "version": "v1", "app_template": json.dumps({
            "apps": [{"share_image": "registry/app:v1", "envs": [{"name": "PRIVATE", "value": "do-not-export"}]}],
            "plugins": [{"image": "registry/sidecar:v1"}], "opaque_configuration": "do-not-export"})}
        result = template_resource(row, "r1", False)
        self.assertEqual(result["images"], ["registry/app:v1", "registry/sidecar:v1"])
        self.assertFalse(result["sizeKnown"])
        self.assertIsNone(result["unusedSince"])
        self.assertNotIn("do-not-export", json.dumps(result))
        self.assertEqual(template_resource(row, "r1", True)["resourceType"], "application_snapshot")

    def test_invalid_template_is_visible_and_never_claims_complete_references(self):
        result = template_resource({"ID": 1, "app_id": "app", "version": "v", "app_template": "bad-json"}, "r1", False)
        self.assertEqual(result["protection"], "reference_unknown")
        self.assertEqual(result["usageStatus"], "unknown")

    def test_build_history_does_not_claim_successful_deployment_or_idle_time(self):
        component = {"service_id": "s", "service_cname": "backend", "service_alias": "svc"}
        payload = {"deploy_version": "v2", "list": [
            {"build_version": "v1", "image_name": "registry/app:v1", "final_status": "success", "repo_url": "do-not-export"},
            {"build_version": "v2", "image_name": "registry/app:v2", "final_status": "success"}]}
        rows = version_resources(component, payload, "r1")
        self.assertEqual(rows[0]["usageStatus"], "history_unverified")
        self.assertEqual(rows[1]["usageStatus"], "current_deployment")
        self.assertIsNone(rows[0]["unusedSince"])
        self.assertNotIn("do-not-export", json.dumps(rows))

    def test_retirement_requires_complete_fresh_reference_evidence(self):
        component = {"service_id": "s", "retirement_references_complete": True, "snapshot_referenced": False}
        version = {"build_version": "v1", "event_id": "event1", "final_status": "success",
                   "delivered_type": "image", "image_name": "registry/app:v1"}
        inspection = {"protocol": 1, "current_version": "v2", "active_operation": False,
                      "checkpoints": {"event1": "activation1"}}
        payload = {"deploy_version": "v2", "list": [version], "retirement": inspection}
        result = version_resources(component, payload, "r")[0]
        self.assertEqual(result["retirement"]["expected"]["activation_revision"], "activation1")
        self.assertIsNone(result["unusedSince"])
        for changes in ({"snapshot_referenced": True}, {"retirement_references_complete": False}):
            with self.subTest(changes=changes):
                self.assertNotIn("retirement", version_resources(dict(component, **changes), payload, "r")[0])
        for changes in ({"current_version": "v3"}, {"active_operation": True}, {"checkpoints": {}}, {"protocol": 0}):
            with self.subTest(changes=changes):
                stale = dict(payload, retirement=dict(inspection, **changes))
                self.assertNotIn("retirement", version_resources(component, stale, "r")[0])
        current = dict(payload, deploy_version="v1", retirement=dict(inspection, current_version="v1"))
        self.assertNotIn("retirement", version_resources(component, current, "r")[0])

    def test_empty_payload_is_not_an_empty_successful_inventory(self):
        with self.assertRaises(ValueError):
            version_resources({"service_id": "s"}, {}, "r1")


if __name__ == "__main__":
    unittest.main()
