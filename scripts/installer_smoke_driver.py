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


def validate_report_uuids(events: list[dict[str, Any]], expected_uuid: str) -> bool:
    return bool(events) and all(event.get("uuid") == expected_uuid for event in events)


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


def start_receiver(results_dir: pathlib.Path) -> subprocess.Popen[str]:
    ready_file = results_dir / "receiver-port"
    receiver = pathlib.Path(__file__).with_name("installer_smoke_receiver.py")
    process = subprocess.Popen(
        [sys.executable, str(receiver), "--output", str(results_dir / "reports.jsonl"), "--ready-file", str(ready_file)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    for _ in range(50):
        if ready_file.exists():
            return process
        if process.poll() is not None:
            raise RuntimeError(process.stderr.read())
        time.sleep(0.1)
    process.terminate()
    raise RuntimeError("fake report receiver did not start")


def create_curl_shim(results_dir: pathlib.Path) -> pathlib.Path:
    shim_dir = results_dir / "bin"
    shim_dir.mkdir()
    (shim_dir / "curl").write_text(
        """#!/usr/bin/env bash
set -euo pipefail
url=""
payload=""
args=("$@")
for ((index=0; index < ${#args[@]}; index++)); do
  case "${args[$index]}" in
    http://*|https://*) url="${args[$index]}" ;;
    -d|--data|--data-raw|--data-binary) payload="${args[$((index + 1))]:-}" ;;
  esac
done
if [[ "$url" =~ ^https://log\.rainbond\.com/(dindlog|logCollect)$ ]]; then
  if [ "${SMOKE_REPORT_MODE:-receiver}" = "unreachable" ]; then
    exit 7
  fi
  /usr/bin/curl --silent --show-error --max-time 5 -X POST \
    "http://127.0.0.1:${SMOKE_RECEIVER_PORT}${BASH_REMATCH[1]/#/\/}" \
    -H 'Content-Type: application/json' --data-binary "$payload" >/dev/null
  exit 0
fi
exec /usr/bin/curl "$@"
""",
        encoding="utf-8",
    )
    (shim_dir / "curl").chmod(0o755)
    return shim_dir


def collect_ready_components() -> list[dict[str, str]]:
    result = subprocess.run(
        ["docker", "exec", "rainbond", "kubectl", "get", "pods", "-n", "rbd-system", "--no-headers"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return ready_components(result.stdout)


def collect_gateway_logs(results_dir: pathlib.Path) -> dict[str, list[str]]:
    pods = subprocess.run(
        ["docker", "exec", "rainbond", "kubectl", "get", "pods", "-n", "rbd-system", "--no-headers"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    ).stdout
    gateway_pod = next((line.split()[0] for line in pods.splitlines() if line.startswith("rbd-gateway")), "")
    logs = {}
    if not gateway_pod:
        return logs
    for container in ("ingress-apisix", "apisix"):
        result = subprocess.run(
            ["docker", "exec", "rainbond", "kubectl", "logs", gateway_pod, "-n", "rbd-system", "-c", container, "--tail=80"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        lines = result.stdout.splitlines()
        (results_dir / f"rbd-gateway-{container}.log").write_text(result.stdout, encoding="utf-8")
        logs[container] = lines[-20:]
    return logs


def run_scenario(arguments: argparse.Namespace) -> int:
    results_dir = pathlib.Path(arguments.results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    target_script = pathlib.Path(arguments.installer)
    main_script = pathlib.Path(arguments.main_installer)
    started_at = time.monotonic()
    env = os.environ.copy()
    env.update({"EIP": "127.0.0.1", "RAINBOND_INSTALL_LANG": "en"})
    command = ["bash", str(target_script)]
    reason = ""

    if not installer_contract(target_script) or not installer_contract(main_script):
        raise RuntimeError("installer UUID contract no longer matches the main branch")

    expected_uuid = calculate_uuid(subprocess.check_output(["uname", "-a"], text=True).rstrip("\n"))
    uuid_comparison = {"target_ref": expected_uuid, "main": expected_uuid, "matches": True}

    receiver = start_receiver(results_dir)
    shim_dir = create_curl_shim(results_dir)
    env["PATH"] = f"{shim_dir}:{env['PATH']}"
    env["SMOKE_RECEIVER_PORT"] = (results_dir / "receiver-port").read_text(encoding="utf-8")

    if arguments.scenario == "image_not_found":
        env["VERSION"] = "v0.0.0-installer-smoke-does-not-exist"
    elif arguments.scenario == "report_endpoint_unreachable":
        env["SMOKE_REPORT_MODE"] = "unreachable"
    elif arguments.scenario != "normal_install":
        raise ValueError(f"unsupported scenario: {arguments.scenario}")

    try:
        code, output = run_command(command, env, results_dir / "installer.log", arguments.timeout)
    finally:
        receiver.terminate()
        receiver.wait(timeout=5)

    duration_seconds = round(time.monotonic() - started_at)
    components = collect_ready_components() if arguments.scenario != "image_not_found" else []
    gateway_logs = collect_gateway_logs(results_dir) if arguments.scenario != "image_not_found" else {}
    report_lines = (results_dir / "reports.jsonl").read_text(encoding="utf-8").splitlines() if (results_dir / "reports.jsonl").exists() else []
    reports = extract_report_events(report_lines)
    if arguments.scenario == "image_not_found":
        success = code != 0 and ("image does not exist" in output.lower() or "版本镜像不存在" in output)
        reason = "image_not_found" if success else "expected image pull failure was not observed"
    else:
        reports_valid = arguments.scenario == "report_endpoint_unreachable" or validate_report_uuids(reports, expected_uuid)
        success = code == 0 and reports_valid
        reason = "" if success else f"installer exited with {code}"

    result = build_result(arguments.scenario, arguments.arch, success, duration_seconds, reason, components)
    result["exit_code"] = code
    result["uuid_comparison"] = uuid_comparison
    result["report_count"] = len(reports)
    result["gateway_logs"] = gateway_logs
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
