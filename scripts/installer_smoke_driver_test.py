import json
import os
import pathlib
import subprocess
import tempfile
import time
import unittest

from installer_smoke_driver import (
    build_result,
    calculate_uuid,
    extract_report_events,
    REPORT_SCENARIOS,
    scenario_succeeded,
    validate_report_uuids,
    ready_components,
    create_curl_shim,
    run_command,
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

    def test_validate_report_uuids_requires_one_non_empty_uuid(self):
        self.assertTrue(validate_report_uuids([{"uuid": ""}, {"uuid": "same-id"}], "same-id"))
        self.assertFalse(validate_report_uuids([{"uuid": ""}], "same-id"))
        self.assertFalse(validate_report_uuids([{"uuid": "other-id"}], "same-id"))

    def test_report_outage_scenarios_use_network_drop_and_reject(self):
        self.assertEqual(REPORT_SCENARIOS["report_endpoint_drop"], "DROP")
        self.assertEqual(REPORT_SCENARIOS["report_endpoint_reject"], "REJECT")

    def test_scenario_failure_reason_distinguishes_missing_reports_and_uuid(self):
        self.assertEqual(scenario_succeeded("normal_install", 0, False, "", [], "main-id")[1], "fake receiver did not receive /dindlog")
        self.assertIn("uuid mismatch", scenario_succeeded("normal_install", 0, False, "", [{"uuid": "other"}], "main-id")[1])

    def test_scenario_timeout_is_not_reported_as_installer_exit(self):
        self.assertEqual(scenario_succeeded("normal_install", 124, True, "", [{"uuid": "main-id"}], "main-id")[1], "driver timeout")

    def test_run_command_terminates_process_group_after_timeout(self):
        with tempfile.TemporaryDirectory() as directory:
            code, _, timed_out = run_command(["bash", "-c", "sleep 30"], os.environ.copy(), pathlib.Path(directory) / "timeout.log", 0.01)
        self.assertEqual(code, 124)
        self.assertTrue(timed_out)

    def test_curl_shim_maps_report_path_to_receiver_without_external_request(self):
        with tempfile.TemporaryDirectory() as directory:
            result_dir = pathlib.Path(directory)
            shim = create_curl_shim(result_dir) / "curl"
            receiver = subprocess.Popen(
                ["python3", "-m", "http.server", "18080", "--bind", "127.0.0.1"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            try:
                time.sleep(0.1)
                environment = {
                    "PATH": f"{shim.parent}:{os.environ['PATH']}",
                    "SMOKE_RECEIVER_PORT": "18080",
                    "SMOKE_REPORT_MODE": "receiver",
                    "SMOKE_SHIM_STATE": str(result_dir / "state"),
                    "SMOKE_REPORT_ATTEMPTS": str(result_dir / "attempts.jsonl"),
                }
                result = subprocess.run(
                    [str(shim), "-X", "POST", "https://log.rainbond.com/dindlog", "-d", '{"uuid":"test"}'],
                    env=environment,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr.decode())
            finally:
                receiver.terminate()
                receiver.wait()

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
