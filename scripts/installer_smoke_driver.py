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
SMOKE_BLOCK_IP = "192.0.2.1"


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


def terminate_process_group(process_group: int, signal_name: str) -> bool:
    try:
        result = run_sudo("kill", f"-{signal_name}", "--", f"-{process_group}", check=False)
    except (OSError, PermissionError):
        return False
    return result.returncode == 0


def run_command(command: list[str], env: dict[str, str], log_file: pathlib.Path, timeout: int) -> tuple[int, str, bool]:
    with log_file.open("w", encoding="utf-8") as output_file:
        process = subprocess.Popen(
            command,
            env=env,
            text=True,
            stdout=output_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            process.wait(timeout=timeout)
            code = process.returncode
            timed_out = False
        except subprocess.TimeoutExpired:
            terminated = terminate_process_group(process.pid, "TERM")
            try:
                process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                killed = terminate_process_group(process.pid, "KILL")
                if killed:
                    process.wait()
                elif not terminated:
                    output_file.write("\nsmoke driver could not terminate the sudo process group\n")
            code = 124
            timed_out = True
    return code, log_file.read_text(encoding="utf-8"), timed_out


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


def resolve_ipv6(host: str) -> list[str]:
    try:
        return sorted({entry[4][0] for entry in socket.getaddrinfo(host, 443, socket.AF_INET6, socket.SOCK_STREAM)})
    except socket.gaierror:
        return []


def run_sudo(*arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["sudo", *arguments], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=check)


def install_network_guard(results_dir: pathlib.Path, action: str) -> dict[str, list[str]]:
    addresses = {host: resolve_ipv4(host) for host in REPORT_HOSTS}
    addresses["smoke_blackhole"] = [SMOKE_BLOCK_IP]
    ipv6_addresses = {host: resolve_ipv6(host) for host in REPORT_HOSTS}
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
        for address in sorted({address for values in addresses.values() for address in values}):
                rule = [chain, "-d", address, "-j", action]
                run_sudo("iptables", "-I", *rule)
                rules.append(rule)
    for chain in ("OUTPUT", "FORWARD", "DOCKER-USER"):
        if run_sudo("ip6tables", "-S", chain, check=False).returncode != 0:
            continue
        for values in ipv6_addresses.values():
            for address in values:
                run_sudo("ip6tables", "-I", chain, "-d", address, "-j", action)
    (results_dir / "network-guard.json").write_text(
        json.dumps({"addresses": addresses, "ipv6_addresses": ipv6_addresses, "action": action}), encoding="utf-8"
    )
    return addresses


def verify_network_guard(results_dir: pathlib.Path) -> dict[str, Any]:
    guard = json.loads((results_dir / "network-guard.json").read_text(encoding="utf-8"))
    expected = {address for values in guard["addresses"].values() for address in values}
    chains = {}
    for chain in ("OUTPUT", "FORWARD", "DOCKER-USER"):
        result = run_sudo("iptables", "-S", chain, check=False)
        rules = result.stdout
        counters = run_sudo("iptables", "-L", chain, "-v", "-n", check=False).stdout
        chains[chain] = {
            "exists": result.returncode == 0,
            "blocked_addresses": sorted(address for address in expected if f"-d {address}/32 -j {guard['action']}" in rules),
            "packet_counters": counters,
        }
    valid = all(chain["exists"] and set(chain["blocked_addresses"]) == expected for chain in chains.values())
    return {"valid": valid, "chains": chains}


def destroy_rainbond_container() -> None:
    run_sudo("docker", "rm", "-f", "rainbond", check=False)


def probe_container_tcp(address: str) -> dict[str, Any]:
    result = run_sudo("docker", "exec", "rainbond", "bash", "-c", f"timeout 3 bash -c '</dev/tcp/{address}/443'", check=False)
    return {"exit_code": result.returncode, "blocked": result.returncode in {1, 124}, "valid": result.returncode not in {126, 127}}


def probe_container_network(addresses: dict[str, list[str]]) -> dict[str, Any]:
    blocked = {host: [probe_container_tcp(address) for address in values] for host, values in addresses.items() if host != "smoke_blackhole"}
    control = probe_container_tcp("registry.cn-hangzhou.aliyuncs.com")
    valid = control["exit_code"] == 0 and all(probe["valid"] and probe["blocked"] for probes in blocked.values() for probe in probes)
    return {"valid": valid, "blocked": blocked, "control": control}


def probe_report_endpoint() -> dict[str, Any]:
    result = subprocess.run(
        ["/usr/bin/curl", "--connect-timeout", "2", "--max-time", "2", "--silent", "--show-error", "https://log.rainbond.com/"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return {"reachable": result.returncode == 0, "exit_code": result.returncode, "output": result.stdout[-500:]}


def runner_eip_from_route(route: str) -> str:
    tokens = route.split()
    if "src" in tokens:
        index = tokens.index("src")
        if index + 1 < len(tokens):
            return tokens[index + 1]
    raise RuntimeError("could not determine the runner primary IPv4 address")


def runner_eip() -> str:
    result = subprocess.run(["ip", "route", "get", "1.1.1.1"], text=True, stdout=subprocess.PIPE, check=True)
    return runner_eip_from_route(result.stdout)


def main_script_uuid(main_script: pathlib.Path) -> str:
    lines = [(index, line.strip()) for index, line in enumerate(main_script.read_text(encoding="utf-8").splitlines())]
    os_info_index, os_info_line = next(((index, line) for index, line in lines if line.startswith("OS_INFO=")), (-1, ""))
    uuid_line = next((line for index, line in lines if index > os_info_index and line.startswith("UUID=")), "")
    if not os_info_line or not uuid_line:
        raise RuntimeError("main installer does not provide the UUID assignment segment")
    program = f'OS_TYPE=Linux; MD5_CMD="md5sum"; {os_info_line}; {uuid_line}; printf %s "$UUID"'
    return subprocess.check_output(["bash", "-c", program], text=True)


def collect_ready_components() -> list[dict[str, str]]:
    result = run_sudo("docker", "exec", "rainbond", "/bin/k3s", "kubectl", "get", "pods", "-n", "rbd-system", "--no-headers", check=False)
    return ready_components(result.stdout)


def wait_ready_components(timeout_seconds: int = 120) -> list[dict[str, str]]:
    deadline = time.monotonic() + timeout_seconds
    snapshot = []
    while time.monotonic() < deadline:
        snapshot = [component for component in collect_ready_components() if component["status"] not in {"Completed", "Succeeded"}]
        if snapshot and all(component["status"] == "Running" and component["ready"].split("/")[0] == component["ready"].split("/")[-1] for component in snapshot):
            return snapshot
        time.sleep(5)
    return snapshot


def resolve_public_ipv4(host: str) -> list[str]:
    result = subprocess.run(["dig", "@1.1.1.1", "+short", "A", host], text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
    return sorted({line.strip() for line in result.stdout.splitlines() if line.strip()})


def console_ready() -> bool:
    result = subprocess.run(["/usr/bin/curl", "--connect-timeout", "5", "--max-time", "10", "--silent", "--output", "/dev/null", "--write-out", "%{http_code}", "http://127.0.0.1:7070"], text=True, stdout=subprocess.PIPE, check=False)
    return result.returncode == 0 and result.stdout.isdigit() and result.stdout != "000"


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
    started_at = time.monotonic()
    code = 1
    output = ""
    timed_out = False
    connectivity = {}
    components = []
    console_is_ready = False
    gateway = {"pod": "", "containers": [], "logs": {}}
    guard_validation = {"valid": False, "chains": {}}
    container_probes = {"valid": False, "blocked": {}, "control": {}}
    expected_uuid = ""
    receiver = None
    setup_error = ""
    try:
        target_script = pathlib.Path(arguments.installer)
        main_script = pathlib.Path(arguments.main_installer)
        if not main_script.is_file() or not target_script.is_file():
            raise RuntimeError("target or main installer script is missing")
        receiver = start_receiver(results_dir)
        shim_dir = create_curl_shim(results_dir).resolve()
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
                "SMOKE_BLOCK_IP": SMOKE_BLOCK_IP,
                "SMOKE_SHIM_STATE": str((results_dir / "first-report-recorded").resolve()),
                "SMOKE_REPORT_ATTEMPTS": str((results_dir / "report-attempts.jsonl").resolve()),
            }
        )
        if arguments.scenario == "image_not_found":
            env["VERSION"] = "v0.0.0-installer-smoke-does-not-exist"
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
        components = wait_ready_components() if arguments.scenario == "normal_install" else collect_ready_components() if arguments.scenario != "image_not_found" else []
        console_is_ready = console_ready() if arguments.scenario == "normal_install" else False
        gateway = collect_gateway_logs(results_dir) if arguments.scenario != "image_not_found" else gateway
        guard_validation = verify_network_guard(results_dir)
        guard_validation["public_resolution"] = {host: resolve_public_ipv4(host) for host in REPORT_HOSTS}
        guard_validation["resolution_matches"] = all(set(guard_validation["public_resolution"][host]) == set(json.loads((results_dir / "network-guard.json").read_text(encoding="utf-8"))["addresses"][host]) for host in REPORT_HOSTS)
        container_probes = probe_container_network(json.loads((results_dir / "network-guard.json").read_text(encoding="utf-8"))["addresses"]) if arguments.scenario != "image_not_found" else container_probes
    except Exception as error:
        setup_error = str(error)
    finally:
        destroy_rainbond_container()
        if receiver is not None:
            stop_receiver(receiver)

    duration_seconds = round(time.monotonic() - started_at)
    report_lines = (results_dir / "reports.jsonl").read_text(encoding="utf-8").splitlines() if (results_dir / "reports.jsonl").exists() else []
    reports = extract_report_events(report_lines)
    target_uuid = next((event["uuid"] for event in reports if event.get("uuid")), "")
    success, reason = scenario_succeeded(arguments.scenario, code, timed_out, output, reports, expected_uuid)
    if setup_error:
        success = False
        reason = f"smoke setup failed: {setup_error}"
    elif not guard_validation["valid"]:
        success = False
        reason = "network guard rules are missing"
    elif not guard_validation.get("resolution_matches", False):
        success = False
        reason = "isolation is untrusted because public DNS addresses changed"
    elif arguments.scenario != "image_not_found" and not container_probes["valid"]:
        success = False
        reason = "container TCP isolation probe is invalid or not blocked"
    elif arguments.scenario == "normal_install" and (not console_is_ready or not components or any(component["ready"].split("/")[0] != component["ready"].split("/")[-1] or component["status"] != "Running" for component in components)):
        success = False
        reason = f"services are not ready (7070={console_is_ready}): {components}"
    if timed_out:
        reason = f"{reason} after {arguments.timeout}s"
    uuid_matches = validate_report_uuids(reports, expected_uuid)

    result = build_result(arguments.scenario, arguments.arch, success, duration_seconds, reason, components)
    result.update(
        {
            "exit_code": code,
            "timed_out": timed_out,
            "connectivity": connectivity,
            "network_guard": guard_validation,
            "container_tcp_probes": container_probes,
            "console_7070_ready": console_is_ready,
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
