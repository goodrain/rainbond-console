#!/usr/bin/env python3
"""Run and summarize independent installer smoke-test scenarios."""

import argparse
import hashlib
import json
import os
import pathlib
import signal
import socket
import subprocess
import sys
import time
from typing import Any, Iterable

REPORT_HOSTS = ("log.rainbond.com", "posthog.goodrain.com", "sentry.goodrain.com")
REPORT_SCENARIOS = {"report_endpoint_drop": "DROP", "report_endpoint_reject": "REJECT"}


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
    reported_uuids = [event["uuid"] for event in events if event.get("uuid")]
    return bool(reported_uuids) and all(value == expected_uuid for value in reported_uuids)


def scenario_succeeded(scenario: str, code: int, timed_out: bool, output: str, reports: list[dict[str, Any]], expected_uuid: str) -> tuple[bool, str]:
    reports_received = bool(reports)
    target_uuid = next((event["uuid"] for event in reports if event.get("uuid")), "")
    if timed_out:
        return False, "driver timeout"
    if scenario == "image_not_found":
        image_failure = "image does not exist" in output.lower() or "版本镜像不存在" in output
        if code == 0 or not image_failure:
            return False, "expected image pull failure was not observed"
    elif code != 0:
        return False, f"installer exited with {code}"
    if not reports_received:
        return False, "fake receiver did not receive /dindlog"
    if not validate_report_uuids(reports, expected_uuid):
        return False, f"uuid mismatch: target={target_uuid or 'empty'}, main={expected_uuid}"
    return True, ""


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


def run_command(command: list[str], env: dict[str, str], log_file: pathlib.Path, timeout: int) -> tuple[int, str, bool]:
    process = subprocess.Popen(
        command,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    try:
        output, _ = process.communicate(timeout=timeout)
        code = process.returncode
        timed_out = False
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            output, _ = process.communicate(timeout=20)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            output, _ = process.communicate()
        code = 124
        timed_out = True
    log_file.write_text(output or "", encoding="utf-8")
    return code, output or "", timed_out


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


def stop_receiver(process: subprocess.Popen[str]) -> None:
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def create_curl_shim(results_dir: pathlib.Path) -> pathlib.Path:
    shim_dir = results_dir / "bin"
    shim_dir.mkdir()
    (shim_dir / "curl").write_text(
        r"""#!/usr/bin/env bash
set -u
url=""
payload=""
args=("$@")
for ((index=0; index < ${#args[@]}; index++)); do
  case "${args[$index]}" in
    http://*|https://*) url="${args[$index]}" ;;
    -d|--data|--data-raw|--data-binary) payload="${args[$((index + 1))]:-}" ;;
  esac
done
started=$(date +%s%3N)
status=0
if [[ "$url" =~ ^https?://(log\.rainbond\.com|posthog\.goodrain\.com|sentry\.goodrain\.com)([:/?]|$) ]]; then
  host="${BASH_REMATCH[1]}"
  if [ "$host" = "log.rainbond.com" ] && [[ "$url" =~ ^https?://log\.rainbond\.com/?(.*)$ ]]; then
    if [ ! -e "${SMOKE_SHIM_STATE}" ]; then
      : >"${SMOKE_SHIM_STATE}"
      /usr/bin/curl --silent --show-error --max-time 5 -X POST \
        "http://127.0.0.1:${SMOKE_RECEIVER_PORT}/${BASH_REMATCH[1]}" \
        -H 'Content-Type: application/json' --data-binary "$payload" >/dev/null || status=$?
    elif [ "${SMOKE_REPORT_MODE}" = "receiver" ]; then
      /usr/bin/curl --silent --show-error --max-time 5 -X POST \
        "http://127.0.0.1:${SMOKE_RECEIVER_PORT}/${BASH_REMATCH[1]}" \
        -H 'Content-Type: application/json' --data-binary "$payload" >/dev/null || status=$?
    else
      /usr/bin/curl --connect-to "log.rainbond.com:443:${SMOKE_BLOCK_IP}:443" "$@" >/dev/null 2>&1 || status=$?
    fi
  else
    /usr/bin/curl "$@" >/dev/null 2>&1 || status=$?
  fi
else
  /usr/bin/curl "$@" || status=$?
fi
finished=$(date +%s%3N)
printf '{"url":"%s","duration_ms":%s,"exit_code":%s}\n' "$url" "$((finished - started))" "$status" >>"${SMOKE_REPORT_ATTEMPTS}"
exit "$status"
""",
        encoding="utf-8",
    )
    (shim_dir / "curl").chmod(0o755)
    return shim_dir


def resolve_ipv4(host: str) -> list[str]:
    return sorted({entry[4][0] for entry in socket.getaddrinfo(host, 443, socket.AF_INET, socket.SOCK_STREAM)})


def run_sudo(*arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["sudo", *arguments], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=check)


def install_network_guard(results_dir: pathlib.Path, action: str) -> dict[str, list[str]]:
    addresses = {host: resolve_ipv4(host) for host in REPORT_HOSTS}
    hosts_backup = results_dir / "hosts.before"
    hosts_backup.write_text(pathlib.Path("/etc/hosts").read_text(encoding="utf-8"), encoding="utf-8")
    run_sudo("cp", "/etc/hosts", str(results_dir / "hosts.root.before"))
    with (results_dir / "hosts.append").open("w", encoding="utf-8") as output:
        for host in REPORT_HOSTS:
            output.write(f"127.0.0.1 {host}\n")
    run_sudo("sh", "-c", f"cat {results_dir / 'hosts.append'} >> /etc/hosts")
    rules = []
    for chain in ("OUTPUT", "FORWARD", "DOCKER-USER"):
        if run_sudo("iptables", "-S", chain, check=False).returncode != 0:
            continue
        for values in addresses.values():
            for address in values:
                rule = [chain, "-d", address, "-j", action]
                run_sudo("iptables", "-I", *rule)
                rules.append(rule)
    (results_dir / "network-guard.json").write_text(json.dumps({"addresses": addresses, "action": action}), encoding="utf-8")
    return addresses


def remove_network_guard(results_dir: pathlib.Path) -> None:
    guard_file = results_dir / "network-guard.json"
    if guard_file.exists():
        guard = json.loads(guard_file.read_text(encoding="utf-8"))
        for chain in ("OUTPUT", "FORWARD", "DOCKER-USER"):
            for values in guard["addresses"].values():
                for address in values:
                    run_sudo("iptables", "-D", chain, "-d", address, "-j", guard["action"], check=False)
    backup = results_dir / "hosts.root.before"
    if backup.exists():
        run_sudo("cp", str(backup), "/etc/hosts", check=False)


def probe_report_endpoint() -> dict[str, Any]:
    result = subprocess.run(
        ["/usr/bin/curl", "--connect-timeout", "2", "--max-time", "2", "--silent", "--show-error", "https://log.rainbond.com/"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return {"reachable": result.returncode == 0, "exit_code": result.returncode, "output": result.stdout[-500:]}


def runner_eip() -> str:
    result = subprocess.run(["ip", "route", "get", "1.1.1.1"], text=True, stdout=subprocess.PIPE, check=True)
    for token in result.stdout.split():
        if token.count(".") == 3 and not token.startswith("127."):
            return token
    raise RuntimeError("could not determine the runner primary IPv4 address")


def main_script_uuid(main_script: pathlib.Path) -> str:
    uuid_line = next((line for line in main_script.read_text(encoding="utf-8").splitlines() if line.startswith("UUID=")), "")
    if not uuid_line:
        raise RuntimeError("main installer does not assign UUID")
    program = f'OS_INFO=$(uname -a); MD5_CMD=$(command -v md5sum); {uuid_line}; printf %s "$UUID"'
    return subprocess.check_output(["bash", "-c", program], text=True)


def collect_ready_components() -> list[dict[str, str]]:
    result = run_sudo("docker", "exec", "rainbond", "kubectl", "get", "pods", "-n", "rbd-system", "--no-headers", check=False)
    return ready_components(result.stdout)


def collect_gateway_logs(results_dir: pathlib.Path) -> dict[str, Any]:
    pods = run_sudo("docker", "exec", "rainbond", "kubectl", "get", "pods", "-n", "rbd-system", "--no-headers", check=False).stdout
    gateway_pod = next((line.split()[0] for line in pods.splitlines() if line.startswith("rbd-gateway")), "")
    if not gateway_pod:
        return {"pod": "", "containers": [], "logs": {}}
    names = run_sudo(
        "docker", "exec", "rainbond", "kubectl", "get", "pod", gateway_pod, "-n", "rbd-system", "-o", "jsonpath={.spec.containers[*].name}", check=False
    ).stdout.split()
    logs = {}
    for container in ("ingress-apisix", "apisix"):
        if container not in names:
            continue
        result = run_sudo(
            "docker", "exec", "rainbond", "kubectl", "logs", gateway_pod, "-n", "rbd-system", "-c", container, "--tail=80", check=False
        )
        (results_dir / f"rbd-gateway-{container}.log").write_text(result.stdout, encoding="utf-8")
        logs[container] = result.stdout.splitlines()[-20:]
    return {"pod": gateway_pod, "containers": names, "logs": logs}


def read_json_lines(path: pathlib.Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def run_scenario(arguments: argparse.Namespace) -> int:
    results_dir = pathlib.Path(arguments.results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    target_script = pathlib.Path(arguments.installer)
    main_script = pathlib.Path(arguments.main_installer)
    if not main_script.is_file() or not target_script.is_file():
        raise RuntimeError("target or main installer script is missing")

    started_at = time.monotonic()
    receiver = start_receiver(results_dir)
    shim_dir = create_curl_shim(results_dir)
    action = REPORT_SCENARIOS.get(arguments.scenario, "DROP")
    report_mode = "receiver" if arguments.scenario in {"normal_install", "image_not_found"} else arguments.scenario.removeprefix("report_endpoint_")
    expected_uuid = main_script_uuid(main_script)
    env = os.environ.copy()
    env.update(
        {
            "EIP": runner_eip(),
            "RAINBOND_INSTALL_LANG": "en",
            "PATH": f"{shim_dir}:{env['PATH']}",
            "SMOKE_RECEIVER_PORT": (results_dir / "receiver-port").read_text(encoding="utf-8"),
            "SMOKE_REPORT_MODE": report_mode,
            "SMOKE_BLOCK_IP": resolve_ipv4("log.rainbond.com")[0],
            "SMOKE_SHIM_STATE": str(results_dir / "first-report-recorded"),
            "SMOKE_REPORT_ATTEMPTS": str(results_dir / "report-attempts.jsonl"),
        }
    )
    if arguments.scenario == "image_not_found":
        env["VERSION"] = "v0.0.0-installer-smoke-does-not-exist"

    code = 1
    output = ""
    timed_out = False
    connectivity = {}
    try:
        install_network_guard(results_dir, action)
        connectivity["before"] = probe_report_endpoint()
        command = [
            "sudo",
            "env",
            f"PATH={env['PATH']}",
            f"EIP={env['EIP']}",
            f"RAINBOND_INSTALL_LANG={env['RAINBOND_INSTALL_LANG']}",
            f"SMOKE_RECEIVER_PORT={env['SMOKE_RECEIVER_PORT']}",
            f"SMOKE_REPORT_MODE={env['SMOKE_REPORT_MODE']}",
            f"SMOKE_BLOCK_IP={env['SMOKE_BLOCK_IP']}",
            f"SMOKE_SHIM_STATE={env['SMOKE_SHIM_STATE']}",
            f"SMOKE_REPORT_ATTEMPTS={env['SMOKE_REPORT_ATTEMPTS']}",
        ]
        if "VERSION" in env:
            command.append(f"VERSION={env['VERSION']}")
        command.extend(["bash", str(target_script)])
        code, output, timed_out = run_command(command, env, results_dir / "installer.log", arguments.timeout)
        connectivity["after"] = probe_report_endpoint()
        components = collect_ready_components() if arguments.scenario != "image_not_found" else []
        gateway = collect_gateway_logs(results_dir) if arguments.scenario != "image_not_found" else {"pod": "", "containers": [], "logs": {}}
    finally:
        remove_network_guard(results_dir)
        stop_receiver(receiver)

    duration_seconds = round(time.monotonic() - started_at)
    report_lines = (results_dir / "reports.jsonl").read_text(encoding="utf-8").splitlines() if (results_dir / "reports.jsonl").exists() else []
    reports = extract_report_events(report_lines)
    target_uuid = next((event["uuid"] for event in reports if event.get("uuid")), "")
    success, reason = scenario_succeeded(arguments.scenario, code, timed_out, output, reports, expected_uuid)
    if timed_out:
        reason = f"{reason} after {arguments.timeout}s"
    uuid_matches = validate_report_uuids(reports, expected_uuid)

    result = build_result(arguments.scenario, arguments.arch, success, duration_seconds, reason, components)
    result.update(
        {
            "exit_code": code,
            "timed_out": timed_out,
            "connectivity": connectivity,
            "uuid_comparison": {"target_ref": target_uuid, "main": expected_uuid, "matches": uuid_matches},
            "report_count": len(reports),
            "report_attempts": read_json_lines(results_dir / "report-attempts.jsonl"),
            "gateway": gateway,
        }
    )
    (results_dir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0 if success else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", required=True, choices=["normal_install", "image_not_found", *REPORT_SCENARIOS])
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
