import json
import ipaddress
import os
import pathlib
import signal
import subprocess
import tempfile
import time
import unittest
from unittest import mock

from installer_smoke_driver import (
    build_result,
    calculate_uuid,
    extract_report_events,
    host_connectivity_valid,
    REPORT_SCENARIOS,
    scenario_succeeded,
    validate_report_uuids,
    ready_components,
    create_curl_shim,
    run_command,
    runner_eip_from_route,
    main_script_uuid,
    resolve_public_ipv4,
    resolve_ipv6,
    terminate_process_group,
)


class InstallerSmokeDriverTests(unittest.TestCase):
    def test_workflow_clears_credentials_after_each_checkout_without_checkout_cleanup(self):
        workflow = (pathlib.Path(__file__).parents[1] / ".github/workflows/installer-smoke.yml").read_text(encoding="utf-8")

        self.assertEqual(workflow.count("uses: actions/checkout@v4"), 3)
        self.assertNotIn("persist-credentials: false", workflow)
        run_scenario_position = workflow.index("- name: Run scenario")
        checkouts = (
            ("- name: Checkout smoke harness", "."),
            ("- name: Checkout requested installer ref", "under-test"),
            ("- name: Checkout main UUID reference", "main-reference"),
        )
        for checkout, directory in checkouts:
            cleanup = f"git -C {directory} config --local --unset-all http.https://github.com/.extraheader || true"
            self.assertLess(workflow.index(checkout), workflow.index(cleanup))
            self.assertLess(workflow.index(cleanup), run_scenario_position)

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
            with mock.patch(
                "installer_smoke_driver.terminate_process_group",
                side_effect=lambda process_group, _: os.killpg(process_group, signal.SIGTERM) is None,
            ):
                code, _, timed_out = run_command(["bash", "-c", "sleep 30"], os.environ.copy(), pathlib.Path(directory) / "timeout.log", 0.01)
        self.assertEqual(code, 124)
        self.assertTrue(timed_out)

    def test_runner_eip_uses_src_token_not_route_destination(self):
        route = "1.1.1.1 via 10.0.0.1 dev eth0 src 10.0.0.24 uid 1001\n"
        self.assertEqual(runner_eip_from_route(route), "10.0.0.24")

    def test_ipv6_resolution_returns_only_ipv6_addresses(self):
        with mock.patch("installer_smoke_driver.socket.getaddrinfo", return_value=[(None, None, None, None, ("2001:db8::1", 443, 0, 0))]):
            self.assertEqual(resolve_ipv6("log.rainbond.com"), ["2001:db8::1"])

    def test_public_dns_keeps_only_ipv4_records_and_reports_query_failure(self):
        completed = subprocess.CompletedProcess([], 0, "alb.example.net.\n203.0.113.8\n", "")
        with mock.patch("installer_smoke_driver.subprocess.run", return_value=completed):
            self.assertEqual(resolve_public_ipv4("log.rainbond.com"), {"addresses": ["203.0.113.8"], "error": ""})
        failed = subprocess.CompletedProcess([], 9, "", "timeout")
        with mock.patch("installer_smoke_driver.subprocess.run", return_value=failed):
            self.assertEqual(resolve_public_ipv4("log.rainbond.com")["error"], "DNS query failed")

    def test_main_script_uuid_matches_current_main_installer(self):
        installer = pathlib.Path(__file__).parents[1] / "script/install-rainbond.sh"
        expected = calculate_uuid(subprocess.check_output(["uname", "-a"], text=True).strip())
        self.assertEqual(main_script_uuid(installer), expected)

    def test_main_script_uuid_matches_2198_installer_fragment(self):
        fixture = pathlib.Path(__file__).parent / "fixtures/install-rainbond-2198-uuid.sh"
        expected = calculate_uuid(subprocess.check_output(["uname", "-a"], text=True).strip())
        self.assertEqual(main_script_uuid(fixture), expected)

    def test_host_connectivity_requires_reachable_baseline_and_blocked_guarded_probe(self):
        connectivity = {
            "before_guard": {"log.rainbond.com": [{"exit_code": 0, "valid": True, "blocked": False}]},
            "after_guard": {"log.rainbond.com": [{"exit_code": 124, "valid": True, "blocked": True}]},
        }
        self.assertTrue(host_connectivity_valid(connectivity))
        connectivity["before_guard"]["log.rainbond.com"][0]["exit_code"] = 124
        connectivity["before_guard"]["log.rainbond.com"][0]["blocked"] = True
        self.assertFalse(host_connectivity_valid(connectivity))

    def test_terminate_process_group_returns_false_when_sudo_kill_fails(self):
        with mock.patch("installer_smoke_driver.run_sudo", side_effect=PermissionError("denied")):
            self.assertFalse(terminate_process_group(123, "TERM"))

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
