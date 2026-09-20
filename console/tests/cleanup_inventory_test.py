import json
import hashlib
import hmac
import unittest

from console.services.cleanup_inventory import template_resource, verify_source_request, version_resources, deployment_resource


class CleanupInventoryProjectionTests(unittest.TestCase):
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

    def test_empty_payload_is_not_an_empty_successful_inventory(self):
        with self.assertRaises(ValueError):
            version_resources({"service_id": "s"}, {}, "r1")


if __name__ == "__main__":
    unittest.main()
