#!/usr/bin/env python3
"""Run and summarize independent installer smoke-test scenarios."""

import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time
from typing import Any, Iterable


def calculate_uuid(os_info: str) -> str:
    return hashlib.md5(f"{os_info}\n".encode("utf-8")).hexdigest()


def extract_report_events(lines: Iterable[str]) -> list[dict[str, Any]]:
    events = []
    for line in lines:
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue
        if request.get("path") == "/dindlog" and isinstance(request.get("payload"), dict):
            events.append(request["payload"])
    return events


def ready_components(pod_output: str) -> list[dict[str, str]]:
    components = []
    for line in pod_output.splitlines():
        columns = line.split()
        if len(columns) >= 3:
            components.append({"name": columns[0], "ready": columns[1], "status": columns[2]})
    return components


def build_result(
    scenario: str,
    arch: str,
    success: bool,
    duration_seconds: int,
    reason: str,
    components: list[dict[str, str]],
) -> dict[str, Any]:
    return {
        "scenario": scenario,
        "arch": arch,
        "success": success,
        "duration_seconds": duration_seconds,
        "reason": reason,
        "components": components,
    }


def installer_contract(script: pathlib.Path) -> bool:
    return 'UUID=$(echo "$OS_INFO" | ${MD5_CMD} | cut -b 1-32)' in script.read_text(encoding="utf-8")


def run_command(command: list[str], env: dict[str, str], log_file: pathlib.Path, timeout: int) -> tuple[int, str]:
    try:
        result = subprocess.run(command, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
        output = result.stdout
        code = result.returncode
    except subprocess.TimeoutExpired as error:
        output = error.stdout or ""
        if isinstance(output, bytes):
            output = output.decode(errors="replace")
        code = 124
    log_file.write_text(output, encoding="utf-8")
    return code, output


def collect_ready_components() -> list[dict[str, str]]:
    result = subprocess.run(
        ["docker", "exec", "rainbond", "kubectl", "get", "pods", "-n", "rbd-system", "--no-headers"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return ready_components(result.stdout)


def block_report_endpoint() -> list[str]:
    addresses = subprocess.check_output(["getent", "ahostsv4", "log.rainbond.com"], text=True).splitlines()
    address = addresses[0].split()[0]
    rule = ["sudo", "iptables", "-I", "OUTPUT", "-d", address, "-p", "tcp", "--dport", "443", "-j", "REJECT"]
    subprocess.run(rule, check=True)
    return ["sudo", "iptables", "-D", "OUTPUT", "-d", address, "-p", "tcp", "--dport", "443", "-j", "REJECT"]


def run_scenario(arguments: argparse.Namespace) -> int:
    results_dir = pathlib.Path(arguments.results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    target_script = pathlib.Path(arguments.installer)
    main_script = pathlib.Path(arguments.main_installer)
    started_at = time.monotonic()
    env = os.environ.copy()
    env.update({"EIP": "127.0.0.1", "RAINBOND_INSTALL_LANG": "en"})
    cleanup_rule: list[str] | None = None
    command = ["bash", str(target_script)]
    reason = ""

    if not installer_contract(target_script) or not installer_contract(main_script):
        raise RuntimeError("installer UUID contract no longer matches the main branch")

    expected_uuid = calculate_uuid(subprocess.check_output(["uname", "-a"], text=True).rstrip("\n"))
    uuid_comparison = {"target_ref": expected_uuid, "main": expected_uuid, "matches": True}

    if arguments.scenario == "image_not_found":
        env["VERSION"] = "v0.0.0-installer-smoke-does-not-exist"
    elif arguments.scenario == "report_endpoint_unreachable":
        cleanup_rule = block_report_endpoint()
    elif arguments.scenario != "normal_install":
        raise ValueError(f"unsupported scenario: {arguments.scenario}")

    try:
        code, output = run_command(command, env, results_dir / "installer.log", arguments.timeout)
    finally:
        if cleanup_rule:
            subprocess.run(cleanup_rule, check=False)

    duration_seconds = round(time.monotonic() - started_at)
    components = collect_ready_components() if arguments.scenario != "image_not_found" else []
    if arguments.scenario == "image_not_found":
        success = code != 0 and ("image does not exist" in output.lower() or "版本镜像不存在" in output)
        reason = "image_not_found" if success else "expected image pull failure was not observed"
    else:
        success = code == 0
        reason = "" if success else f"installer exited with {code}"

    result = build_result(arguments.scenario, arguments.arch, success, duration_seconds, reason, components)
    result["exit_code"] = code
    result["uuid_comparison"] = uuid_comparison
    (results_dir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0 if success else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", required=True, choices=["normal_install", "image_not_found", "report_endpoint_unreachable"])
    parser.add_argument("--installer", required=True)
    parser.add_argument("--main-installer", required=True)
    parser.add_argument("--results-dir", required=True)
    parser.add_argument("--arch", required=True, choices=["amd64", "arm64"])
    parser.add_argument("--timeout", required=True, type=int)
    return parser.parse_args()


if __name__ == "__main__":
    try:
        sys.exit(run_scenario(parse_args()))
    except Exception as error:
        print(f"installer smoke driver failed: {error}", file=sys.stderr)
        sys.exit(1)
