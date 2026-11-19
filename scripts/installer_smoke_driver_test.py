import json
import unittest

from installer_smoke_driver import (
    build_result,
    calculate_uuid,
    extract_report_events,
    ready_components,
)


class InstallerSmokeDriverTests(unittest.TestCase):
    def test_calculate_uuid_matches_installer_md5_contract(self):
        self.assertEqual(calculate_uuid("Linux test-host 6.8.0"), "a119547c0f77a5ecbbe0c5bb0c1dcb21")

    def test_extract_report_events_reads_dindlog_payloads(self):
        lines = [
            json.dumps({"path": "/dindlog", "payload": {"uuid": "same-id", "message": "started"}}),
            json.dumps({"path": "/logCollect", "payload": {"eid": "same-id"}}),
        ]

        self.assertEqual(extract_report_events(lines), [{"uuid": "same-id", "message": "started"}])

    def test_ready_components_records_each_component_without_failing_unready(self):
        pods = """rainbond-operator-1 1/1 Running 0 1m
rbd-app-ui-data-1 0/1 Pending 0 1m
"""

        self.assertEqual(
            ready_components(pods),
            [
                {"name": "rainbond-operator-1", "ready": "1/1", "status": "Running"},
                {"name": "rbd-app-ui-data-1", "ready": "0/1", "status": "Pending"},
            ],
        )

    def test_build_result_contains_duration_and_non_fatal_ready_snapshot(self):
        result = build_result(
            scenario="normal_install",
            arch="amd64",
            success=True,
            duration_seconds=123,
            reason="",
            components=[{"name": "rainbond-operator-1", "ready": "1/1", "status": "Running"}],
        )

        self.assertEqual(result["duration_seconds"], 123)
        self.assertTrue(result["success"])
        self.assertEqual(result["components"][0]["status"], "Running")


if __name__ == "__main__":
    unittest.main()
