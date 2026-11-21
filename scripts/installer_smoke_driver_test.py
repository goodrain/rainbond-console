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
    docker_download_urls,
    docker_recommended_version,
    docker_scenario_assertions,
    guard_rule_prefix_valid,
    guard_packet_counts,
    guard_addresses,
    NETWORK_GUARD_CHAINS,
    RAW_GUARD_CHAINS,
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
        self.assertNotIn("|| true", workflow)
        self.assertEqual(workflow.count('case "$status" in'), 3)
        run_scenario_position = workflow.index("- name: Run scenario")
        checkouts = (
            ("- name: Checkout smoke harness", "."),
            ("- name: Checkout requested installer ref", "under-test"),
            ("- name: Checkout main UUID reference", "main-reference"),
        )
        for checkout, directory in checkouts:
            cleanup = f"git -C {directory} config --local --unset-all http.https://github.com/.extraheader"
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

    def test_workflow_exposes_no_docker_scenarios(self):
        workflow = (pathlib.Path(__file__).parents[1] / ".github/workflows/installer-smoke.yml").read_text(encoding="utf-8")

        for scenario in ("no_docker_install", "no_docker_tuna_fallback", "no_docker_all_sources_unavailable"):
            self.assertIn(f"- {scenario}", workflow)
            self.assertIn(f'"{scenario}"', workflow)
        self.assertIn("max-parallel: 4", workflow)

    def test_docker_version_is_read_from_the_tested_installer(self):
        with tempfile.TemporaryDirectory() as directory:
            installer = pathlib.Path(directory) / "install-rainbond.sh"
            installer.write_text("DOCKER_RECOMMENDED_VERSION='28.3.1'\n", encoding="utf-8")

            self.assertEqual(docker_recommended_version(installer), "28.3.1")

    def test_docker_download_urls_are_extracted_from_the_tested_installer(self):
        installer = pathlib.Path(__file__).parents[1] / "script/install-rainbond.sh"

        self.assertEqual(
            docker_download_urls(installer, "amd64"),
            [
                "https://mirrors.tuna.tsinghua.edu.cn/docker-ce/linux/static/stable/x86_64/docker-28.3.1.tgz",
                "https://mirrors.aliyun.com/docker-ce/linux/static/stable/x86_64/docker-28.3.1.tgz",
                "https://download.docker.com/linux/static/stable/x86_64/docker-28.3.1.tgz",
            ],
        )

    def test_docker_download_scenario_events_are_checked(self):
        fallback_reports = [
            {"event_type": "install_progress", "stage": "docker_download", "status": "failed", "source": "tuna"},
            {"event_type": "install_final", "final_status": "success"},
        ]
        self.assertEqual(docker_scenario_assertions("no_docker_tuna_fallback", fallback_reports), "")

        failed_reports = [
            {"event_type": "install_progress", "stage": "docker_download", "status": "failed", "source": "tuna"},
            {"event_type": "install_progress", "stage": "docker_download", "status": "failed", "source": "aliyun"},
            {"event_type": "install_progress", "stage": "docker_download", "status": "failed", "source": "official"},
            {"event_type": "install_final", "final_status": "failed", "reason": "docker_download_failed"},
        ]
        self.assertEqual(docker_scenario_assertions("no_docker_all_sources_unavailable", failed_reports), "")
        self.assertIn("failure sources", docker_scenario_assertions("no_docker_all_sources_unavailable", failed_reports[1:]))

    def test_guard_requires_raw_and_filter_prefix_rules(self):
        self.assertEqual(NETWORK_GUARD_CHAINS, ("OUTPUT", "FORWARD", "DOCKER-USER"))
        self.assertEqual(RAW_GUARD_CHAINS, ("PREROUTING", "OUTPUT"))
        rules = "-A FORWARD -d 203.0.113.10/32 -j DROP\n-A FORWARD -d 203.0.113.11/32 -j DROP\n-A FORWARD -j DOCKER-USER\n"
        self.assertTrue(guard_rule_prefix_valid(rules, "FORWARD", ["203.0.113.10", "203.0.113.11"], "DROP"))
        self.assertFalse(guard_rule_prefix_valid(rules.replace("-A FORWARD -j DOCKER-USER\n", "", 1).replace("-A FORWARD -d 203.0.113.10/32 -j DROP\n", "-A FORWARD -j DOCKER-USER\n-A FORWARD -d 203.0.113.10/32 -j DROP\n"), "FORWARD", ["203.0.113.10", "203.0.113.11"], "DROP"))
        self.assertTrue(guard_rule_prefix_valid("-A OUTPUT -d 203.0.113.10/32 -j REJECT --reject-with icmp-port-unreachable\n", "OUTPUT", ["203.0.113.10"], "REJECT"))

    def test_raw_guard_excludes_the_local_blackhole(self):
        guard = {"addresses": {"log.rainbond.com": ["203.0.113.10"], "smoke_blackhole": ["192.0.2.1"]}, "ipv6_addresses": {}}
        self.assertEqual(guard_addresses(guard, 4, include_smoke_blackhole=False), ["203.0.113.10"])

    def test_guard_packet_counts_are_recorded_per_destination(self):
        counters = "  12   720 DROP all -- * * 0.0.0.0/0 203.0.113.10\n   3   180 DROP all -- * * 0.0.0.0/0 203.0.113.11\n"
        self.assertEqual(guard_packet_counts(counters, ["203.0.113.10", "203.0.113.11"]), {"203.0.113.10": 12, "203.0.113.11": 3})

    def test_guard_packet_counts_reject_abbreviated_iptables_output(self):
        counters = " 123K  12M DROP all -- * * 0.0.0.0/0 203.0.113.10\n"
        with self.assertRaisesRegex(ValueError, "not exact"):
            guard_packet_counts(counters, ["203.0.113.10"])

    def test_docker_download_shim_injects_a_truncated_tuna_archive_without_following_redirects(self):
        with tempfile.TemporaryDirectory() as directory:
            result_dir = pathlib.Path(directory)
            shim = create_curl_shim(result_dir) / "curl"
            archive = result_dir / "docker.tgz"
            installer = pathlib.Path(__file__).parents[1] / "script/install-rainbond.sh"
            url_file = result_dir / "docker-urls"
            url_file.write_text("\n".join(docker_download_urls(installer, "amd64")) + "\n", encoding="utf-8")
            environment = {
                "SMOKE_REPORT_ATTEMPTS": str(result_dir / "report-attempts.jsonl"),
                "SMOKE_DOCKER_DOWNLOAD_ATTEMPTS": str(result_dir / "docker-download-attempts.jsonl"),
                "SMOKE_DOCKER_DOWNLOAD_MODE": "tuna_partial_archive",
                "SMOKE_DOCKER_DOWNLOAD_URLS_FILE": str(url_file),
            }
            result = subprocess.run(
                [str(shim), "-L", "https://mirrors.tuna.tsinghua.edu.cn/docker-ce/linux/static/stable/x86_64/docker-28.3.1.tgz", "-o", str(archive)],
                env={**os.environ, **environment},
                check=False,
            )

            self.assertEqual(result.returncode, 0)
            self.assertEqual(archive.read_text(encoding="utf-8"), "partial Docker archive")
            attempt = json.loads((result_dir / "docker-download-attempts.jsonl").read_text(encoding="utf-8"))
            self.assertEqual(attempt["mode"], "tuna_partial_archive")

    def test_docker_download_shim_blocks_all_three_installer_urls(self):
        with tempfile.TemporaryDirectory() as directory:
            result_dir = pathlib.Path(directory)
            installer = pathlib.Path(__file__).parents[1] / "script/install-rainbond.sh"
            urls = docker_download_urls(installer, "amd64")
            url_file = result_dir / "docker-urls"
            url_file.write_text("\n".join(urls) + "\n", encoding="utf-8")
            shim = create_curl_shim(result_dir) / "curl"
            environment = {
                "SMOKE_REPORT_ATTEMPTS": str(result_dir / "report-attempts.jsonl"),
                "SMOKE_DOCKER_DOWNLOAD_ATTEMPTS": str(result_dir / "docker-download-attempts.jsonl"),
                "SMOKE_DOCKER_DOWNLOAD_MODE": "all_sources_connect_failure",
                "SMOKE_DOCKER_DOWNLOAD_URLS_FILE": str(url_file),
            }

            for index, url in enumerate(urls):
                archive = result_dir / f"docker-{index}.tgz"
                result = subprocess.run([str(shim), "-L", url, "-o", str(archive)], env={**os.environ, **environment}, check=False)
                self.assertEqual(result.returncode, 7)
                self.assertFalse(archive.exists())

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
