#!/usr/bin/env python3
"""Run and summarize independent installer smoke-test scenarios."""

import argparse
import hashlib
import ipaddress
import json
import os
import pathlib
import re
import shlex
import signal
import socket
import subprocess
import sys
import threading
import time
from typing import Any, Iterable

REPORT_HOSTS = ("log.rainbond.com", "posthog.goodrain.com", "sentry.goodrain.com")
REPORT_SCENARIOS = {"report_endpoint_drop": "DROP", "report_endpoint_reject": "REJECT"}
DOCKER_SCENARIOS = (
    "no_docker_install",
    "no_docker_tuna_fallback",
    "no_docker_all_sources_unavailable",
)
NETWORK_GUARD_CHAINS = ("OUTPUT", "FORWARD", "DOCKER-USER")
RAW_GUARD_CHAINS = ("PREROUTING", "OUTPUT")
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
    elif scenario == "no_docker_all_sources_unavailable":
        if code == 0:
            return False, "expected Docker download failure was not observed"
    elif code != 0:
        return False, f"installer exited with {code}"
    if not reports_received:
        return False, "fake receiver did not receive /dindlog"
    if not validate_report_uuids(reports, expected_uuid):
        return False, f"uuid mismatch: target={target_uuid or 'empty'}, main={expected_uuid}"
    return True, ""


def docker_scenario_assertions(scenario: str, reports: list[dict[str, Any]]) -> str:
    if scenario == "no_docker_tuna_fallback":
        if not any(event.get("event_type") == "install_progress" and event.get("stage") == "docker_download" and event.get("status") == "failed" and event.get("source") == "tuna" for event in reports):
            return "Docker download fallback event for tuna was not received"
    if scenario == "no_docker_all_sources_unavailable":
        failed_sources = {
            event.get("source")
            for event in reports
            if event.get("event_type") == "install_progress" and event.get("stage") == "docker_download" and event.get("status") == "failed"
        }
        if failed_sources != {"tuna", "aliyun", "official"}:
            return f"unexpected Docker download failure sources: {sorted(failed_sources)}"
        final_events = [event for event in reports if event.get("event_type") == "install_final"]
        if len(final_events) != 1:
            return f"expected exactly one final event, received {len(final_events)}"
        final_event = final_events[0]
        if final_event.get("final_status") != "failed" or final_event.get("reason") != "docker_download_failed":
            return f"unexpected Docker download final event: {final_event}"
    return ""


def docker_recommended_version(installer: pathlib.Path) -> str:
    for line in installer.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("DOCKER_RECOMMENDED_VERSION="):
            value = stripped.split("=", 1)[1].strip().strip("\"'")
            if value:
                return value
    raise RuntimeError("installer does not define DOCKER_RECOMMENDED_VERSION")


def docker_download_urls(installer: pathlib.Path, arch: str) -> list[str]:
    docker_architectures = {"amd64": "x86_64", "arm64": "aarch64"}
    if arch not in docker_architectures:
        raise RuntimeError(f"unsupported Docker smoke architecture: {arch}")
    templates = []
    inside_urls = False
    for line in installer.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped == "docker_urls=(":
            inside_urls = True
            continue
        if inside_urls and stripped == ")":
            break
        if inside_urls:
            templates.extend(re.findall(r'"(https://[^"]+)"', stripped))
    if len(templates) != 3:
        raise RuntimeError("installer does not provide exactly three Docker download URLs")
    version = docker_recommended_version(installer)
    return [template.replace("${docker_arch}", docker_architectures[arch]).replace("${DOCKER_RECOMMENDED_VERSION}", version) for template in templates]


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
docker_download_host=""
docker_download_match=false
if [ -n "${SMOKE_DOCKER_DOWNLOAD_URLS_FILE:-}" ] && [ -f "${SMOKE_DOCKER_DOWNLOAD_URLS_FILE}" ]; then
  while IFS= read -r expected_url; do
    if [ "$url" = "$expected_url" ]; then
      docker_download_match=true
      docker_download_host="${url#https://}"
      docker_download_host="${docker_download_host%%/*}"
      break
    fi
  done <"${SMOKE_DOCKER_DOWNLOAD_URLS_FILE}"
fi
if [ "$docker_download_match" = true ]; then
  case "${SMOKE_DOCKER_DOWNLOAD_MODE:-}" in
    tuna_partial_archive)
      if [ "$docker_download_host" = "mirrors.tuna.tsinghua.edu.cn" ]; then
        for ((index=0; index < ${#args[@]}; index++)); do
          if [ "${args[$index]}" = "-o" ] || [ "${args[$index]}" = "--output" ]; then
            printf 'partial Docker archive' >"${args[$((index + 1))]:-}"
            break
          fi
        done
        status=0
      else
        /usr/bin/curl "$@" || status=$?
      fi
      ;;
    all_sources_connect_failure)
      status=7
      ;;
    *)
      /usr/bin/curl "$@" || status=$?
      ;;
  esac
elif [[ "$url" =~ ^https?://(log\.rainbond\.com|posthog\.goodrain\.com|sentry\.goodrain\.com)([:/?]|$) ]]; then
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
if [ -n "$docker_download_host" ]; then
  printf '{"url":"%s","duration_ms":%s,"exit_code":%s,"kind":"docker_download","mode":"%s"}\n' "$url" "$((finished - started))" "$status" "${SMOKE_DOCKER_DOWNLOAD_MODE:-none}" >>"${SMOKE_DOCKER_DOWNLOAD_ATTEMPTS}"
else
  printf '{"url":"%s","duration_ms":%s,"exit_code":%s}\n' "$url" "$((finished - started))" "$status" >>"${SMOKE_REPORT_ATTEMPTS}"
fi
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


def address_with_prefix(address: str) -> str:
    return f"{address}/{128 if ':' in address else 32}"


def guard_rule_prefix_valid(rules: str, chain: str, addresses: list[str], action: str) -> bool:
    expected = {f"-A {chain} -d {address_with_prefix(address)} -j {action}" for address in addresses}
    if not expected:
        return True
    entries = [line.strip() for line in rules.splitlines() if line.startswith(f"-A {chain} ")]
    prefixes = entries[: len(expected)]
    return len(prefixes) == len(expected) and all(any(line == expected_rule or line.startswith(f"{expected_rule} ") for line in prefixes) for expected_rule in expected)


def guard_packet_counts(counters: str, addresses: Iterable[str]) -> dict[str, int]:
    counts = {address: 0 for address in addresses}
    for line in counters.splitlines():
        columns = line.split()
        if len(columns) < 2:
            continue
        for address in counts:
            if address_with_prefix(address) in columns or address in columns:
                if not columns[0].isdigit():
                    raise ValueError(f"iptables packet counter is not exact: {columns[0]}")
                counts[address] += int(columns[0])
    return counts


def insert_guard_rules(command: str, table: str, chain: str, addresses: Iterable[str], action: str) -> None:
    for address in sorted(set(addresses)):
        run_sudo(command, "-t", table, "-I", chain, "-d", address, "-j", action)


def guard_addresses(guard: dict[str, Any], version: int, include_smoke_blackhole: bool = True) -> list[str]:
    source = guard["ipv6_addresses"] if version == 6 else guard["addresses"]
    return sorted({address for host, values in source.items() if include_smoke_blackhole or host != "smoke_blackhole" for address in values})


def read_guard_rules(command: str, table: str, chain: str) -> subprocess.CompletedProcess[str]:
    return run_sudo(command, "-t", table, "-S", chain, check=False)


def reconcile_network_guard(results_dir: pathlib.Path) -> list[dict[str, Any]]:
    guard = json.loads((results_dir / "network-guard.json").read_text(encoding="utf-8"))
    changes = []
    for command, version in (("iptables", 4), ("ip6tables", 6)):
        filter_addresses = guard_addresses(guard, version)
        raw_addresses = guard_addresses(guard, version, include_smoke_blackhole=False)
        if not filter_addresses:
            continue
        for chain in RAW_GUARD_CHAINS:
            state = read_guard_rules(command, "raw", chain)
            if raw_addresses and state.returncode == 0 and not guard_rule_prefix_valid(state.stdout, chain, raw_addresses, "DROP"):
                insert_guard_rules(command, "raw", chain, raw_addresses, "DROP")
                changes.append({"table": "raw", "chain": chain, "ip_version": version, "at_monotonic_seconds": time.monotonic()})
        for chain in NETWORK_GUARD_CHAINS:
            state = read_guard_rules(command, "filter", chain)
            if state.returncode == 0 and not guard_rule_prefix_valid(state.stdout, chain, filter_addresses, guard["action"]):
                insert_guard_rules(command, "filter", chain, filter_addresses, guard["action"])
                changes.append({"table": "filter", "chain": chain, "ip_version": version, "at_monotonic_seconds": time.monotonic()})
    return changes


class NetworkGuardMonitor:
    def __init__(self, results_dir: pathlib.Path):
        self.results_dir = results_dir
        self.reinsertions: list[dict[str, Any]] = []
        self.errors: list[str] = []
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=5)

    def _run(self) -> None:
        while not self._stop.wait(1):
            try:
                self.reinsertions.extend(reconcile_network_guard(self.results_dir))
            except subprocess.CalledProcessError as error:
                self.errors.append(f"{error}: {error.stderr.strip()}")
            except Exception as error:
                self.errors.append(str(error))


def summarize_guard_reinsertions(reinsertions: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "table": entry["table"],
            "chain": entry["chain"],
            "ip_version": entry["ip_version"],
            "at_monotonic_seconds": entry["at_monotonic_seconds"],
        }
        for entry in reinsertions
    ]


def install_network_guard(results_dir: pathlib.Path, action: str) -> dict[str, list[str]]:
    addresses = {host: resolve_ipv4(host) for host in REPORT_HOSTS}
    addresses["smoke_blackhole"] = [SMOKE_BLOCK_IP]
    ipv6_addresses = {host: resolve_ipv6(host) for host in REPORT_HOSTS}
    hosts_backup = results_dir / "hosts.before"
    hosts_backup.write_text(pathlib.Path("/etc/hosts").read_text(encoding="utf-8"), encoding="utf-8")
    with (results_dir / "hosts.append").open("w", encoding="utf-8") as output:
        for host in REPORT_HOSTS:
            output.write(f"127.0.0.1 {host}\n")
    run_sudo("sh", "-c", f"cat {results_dir / 'hosts.append'} >> /etc/hosts")
    guard = {"addresses": addresses, "ipv6_addresses": ipv6_addresses, "action": action, "raw_action": "DROP"}
    (results_dir / "network-guard.json").write_text(
        json.dumps(guard, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    reconcile_network_guard(results_dir)
    return addresses


def verify_network_guard(results_dir: pathlib.Path, require_docker_user: bool = True) -> dict[str, Any]:
    guard = json.loads((results_dir / "network-guard.json").read_text(encoding="utf-8"))
    tables = {}
    for command, version in (("iptables", 4), ("ip6tables", 6)):
        filter_addresses = guard_addresses(guard, version)
        raw_addresses = guard_addresses(guard, version, include_smoke_blackhole=False)
        if not filter_addresses:
            tables[f"ipv{version}"] = {"skipped": True, "filter": {}, "raw": {}}
            continue
        result = {"skipped": False, "filter": {}, "raw": {}}
        for table, chains, action in (("filter", NETWORK_GUARD_CHAINS, guard["action"]), ("raw", RAW_GUARD_CHAINS, "DROP")):
            addresses = raw_addresses if table == "raw" else filter_addresses
            for chain in chains:
                rules = read_guard_rules(command, table, chain)
                counters = run_sudo(command, "-t", table, "-L", chain, "-v", "-n", "-x", check=False).stdout
                result[table][chain] = {
                    "exists": rules.returncode == 0,
                    "prefix_valid": rules.returncode == 0 and guard_rule_prefix_valid(rules.stdout, chain, addresses, action),
                    "packet_counters": counters,
                    "drop_packets": guard_packet_counts(counters, addresses),
                    "real_report_drop_packets": guard_packet_counts(counters, raw_addresses),
                }
        tables[f"ipv{version}"] = result
    required_filter_chains = NETWORK_GUARD_CHAINS if require_docker_user else tuple(chain for chain in NETWORK_GUARD_CHAINS if chain != "DOCKER-USER")
    valid = all(
        table[rule_table][chain]["exists"] and table[rule_table][chain]["prefix_valid"]
        for table in tables.values()
        if not table["skipped"]
        for rule_table, chains in (("filter", required_filter_chains), ("raw", RAW_GUARD_CHAINS))
        for chain in chains
    )
    raw_packets = sum(sum(chain["real_report_drop_packets"].values()) for table in tables.values() if not table["skipped"] for chain in table["raw"].values())
    filter_real_packets = sum(sum(chain["real_report_drop_packets"].values()) for table in tables.values() if not table["skipped"] for chain in table["filter"].values())
    filter_blackhole_packets = sum(sum(chain["drop_packets"].values()) - sum(chain["real_report_drop_packets"].values()) for table in tables.values() if not table["skipped"] for chain in table["filter"].values())
    counter_consistent = filter_real_packets == 0
    return {
        "valid": valid and counter_consistent,
        "tables": tables,
        "docker_user_required": require_docker_user,
        "drop_packet_totals": {"raw": raw_packets, "filter_real_report_ips": filter_real_packets, "filter_smoke_blackhole": filter_blackhole_packets},
        "counter_consistent": counter_consistent,
    }


def destroy_rainbond_container() -> None:
    run_sudo("docker", "rm", "-f", "rainbond", check=False)


def installed_docker_packages() -> list[str]:
    result = run_sudo("dpkg-query", "-W", "-f=${binary:Package}\t${db:Status-Abbrev}\n", check=False)
    package_prefixes = ("moby-", "docker-ce", "docker.io", "containerd.io", "containerd")
    packages = []
    for line in result.stdout.splitlines():
        columns = line.split("\t", 1)
        if len(columns) != 2 or not columns[1].startswith("ii "):
            continue
        package = columns[0]
        if package.split(":", 1)[0].startswith(package_prefixes):
            packages.append(package)
    return sorted(packages)


def remove_docker_chains() -> dict[str, Any]:
    chains = ("DOCKER", "DOCKER-USER", "DOCKER-FORWARD", "DOCKER-BRIDGE", "DOCKER-INTERNAL", "DOCKER-CT", "DOCKER-ISOLATION-STAGE-1", "DOCKER-ISOLATION-STAGE-2")
    removed = []
    for table in ("filter", "nat"):
        parents = ("INPUT", "OUTPUT", "FORWARD", "PREROUTING", "POSTROUTING")
        for parent in parents:
            rules = run_sudo("iptables", "-t", table, "-S", parent, check=False)
            for line in rules.stdout.splitlines():
                fields = shlex.split(line)
                if fields and fields[0] == "-A" and any(f"-j {chain}" in line for chain in chains):
                    fields[0] = "-D"
                    run_sudo("iptables", "-t", table, *fields, check=False)
        for chain in chains:
            if run_sudo("iptables", "-t", table, "-S", chain, check=False).returncode == 0:
                run_sudo("iptables", "-t", table, "-F", chain, check=False)
                run_sudo("iptables", "-t", table, "-X", chain, check=False)
                removed.append(f"{table}/{chain}")
    return {"removed_chains": removed}


def remove_preinstalled_docker(results_dir: pathlib.Path) -> dict[str, Any]:
    result: dict[str, Any] = {"packages_before": installed_docker_packages(), "actions": []}
    for unit in ("docker.service", "docker.socket", "containerd.service"):
        command = ("systemctl", "disable", "--now", unit)
        completed = run_sudo(*command, check=False)
        result["actions"].append({"command": list(command), "exit_code": completed.returncode})
    if result["packages_before"]:
        completed = run_sudo("apt-get", "purge", "-y", *result["packages_before"], check=False)
        result["actions"].append({"command": ["apt-get", "purge", "-y", *result["packages_before"]], "exit_code": completed.returncode})
        if completed.returncode != 0:
            raise RuntimeError("Docker package purge failed")
    for path in (
        "/usr/bin/docker", "/usr/bin/dockerd", "/usr/bin/containerd", "/usr/bin/containerd-shim-runc-v2", "/usr/bin/ctr", "/usr/bin/runc", "/usr/bin/docker-init", "/usr/bin/docker-proxy",
        "/usr/local/bin/docker", "/usr/local/bin/dockerd", "/etc/systemd/system/docker.service", "/etc/systemd/system/docker.socket", "/etc/systemd/system/containerd.service",
    ):
        run_sudo("rm", "-f", path, check=False)
    run_sudo("systemctl", "daemon-reload", check=False)
    run_sudo("ip", "link", "set", "docker0", "down", check=False)
    run_sudo("ip", "link", "delete", "docker0", check=False)
    result.update(remove_docker_chains())
    for path in ("/var/lib/docker", "/var/lib/containerd", "/etc/docker"):
        run_sudo("rm", "-rf", path, check=False)
    command = subprocess.run(["bash", "-c", "command -v docker"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    result["docker_command_after"] = command.stdout.strip()
    result["packages_after"] = installed_docker_packages()
    result["docker0_exists_after"] = run_sudo("ip", "link", "show", "docker0", check=False).returncode == 0
    result["verified_absent"] = not result["docker_command_after"] and not result["packages_after"] and not result["docker0_exists_after"]
    (results_dir / "docker-cleanup.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if not result["verified_absent"]:
        raise RuntimeError("docker cleanup incomplete")
    return result


def docker_installation_evidence(installer: pathlib.Path, cleanup: dict[str, Any]) -> dict[str, Any]:
    expected = docker_recommended_version(installer)
    version = run_sudo("docker", "version", "--format", "{{.Server.Version}}", check=False)
    info = run_sudo("docker", "info", "--format", "{{.DockerRootDir}}", check=False)
    service = run_sudo("systemctl", "is-active", "docker.service", check=False)
    actual = version.stdout.strip()
    return {
        "expected_version": expected,
        "actual_server_version": actual,
        "version_matches": version.returncode == 0 and actual == expected,
        "docker_root": info.stdout.strip(),
        "service_active": service.returncode == 0 and service.stdout.strip() == "active",
        "cleanup_verified_absent": cleanup.get("verified_absent", False),
    }


def probe_container_tcp(address: str) -> dict[str, Any]:
    result = run_sudo("docker", "exec", "rainbond", "bash", "-c", f"timeout 3 bash -c '</dev/tcp/{address}/443'", check=False)
    return {"exit_code": result.returncode, "blocked": result.returncode in {1, 124}, "valid": result.returncode not in {126, 127}}


def probe_container_network(addresses: dict[str, list[str]]) -> dict[str, Any]:
    blocked = {host: [probe_container_tcp(address) for address in values] for host, values in addresses.items() if host != "smoke_blackhole"}
    control = probe_container_tcp("registry.cn-hangzhou.aliyuncs.com")
    valid = control["exit_code"] == 0 and all(probe["valid"] and probe["blocked"] for probes in blocked.values() for probe in probes)
    return {"valid": valid, "blocked": blocked, "control": control}


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


def resolve_public_ipv4(host: str) -> dict[str, Any]:
    result = subprocess.run(["dig", "@1.1.1.1", "+short", "A", host], text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
    if result.returncode != 0:
        return {"addresses": [], "error": "DNS query failed"}
    addresses = []
    for line in result.stdout.splitlines():
        try:
            addresses.append(str(ipaddress.IPv4Address(line.strip())))
        except ipaddress.AddressValueError:
            continue
    if not addresses:
        return {"addresses": [], "error": "DNS query returned no IPv4 address"}
    return {"addresses": sorted(set(addresses)), "error": ""}


def probe_host_tcp(address: str) -> dict[str, Any]:
    result = subprocess.run(["timeout", "3", "bash", "-c", f"</dev/tcp/{address}/443"], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    return {"exit_code": result.returncode, "blocked": result.returncode in {1, 124}, "valid": result.returncode not in {126, 127}}


def host_connectivity_valid(connectivity: dict[str, dict[str, list[dict[str, Any]]]]) -> bool:
    baseline = connectivity.get("before_guard", {})
    guarded = connectivity.get("after_guard", {})
    return (
        bool(baseline)
        and bool(guarded)
        and all(probe["valid"] and probe["exit_code"] == 0 for probes in baseline.values() for probe in probes)
        and all(probe["valid"] and probe["blocked"] for probes in guarded.values() for probe in probes)
    )


def console_ready() -> bool:
    result = subprocess.run(["/usr/bin/curl", "--connect-timeout", "5", "--max-time", "10", "--silent", "--output", "/dev/null", "--write-out", "%{http_code}", "http://127.0.0.1:7070"], text=True, stdout=subprocess.PIPE, check=False)
    return result.returncode == 0 and result.stdout.isdigit() and result.stdout != "000"


def collect_gateway_logs(results_dir: pathlib.Path) -> dict[str, Any]:
    pods = run_sudo("docker", "exec", "rainbond", "/bin/k3s", "kubectl", "get", "pods", "-n", "rbd-system", "--no-headers", check=False).stdout
    gateway_pod = next((line.split()[0] for line in pods.splitlines() if line.startswith("rbd-gateway")), "")
    if not gateway_pod:
        return {"pod": "", "containers": [], "logs": {}}
    names = run_sudo(
        "docker", "exec", "rainbond", "/bin/k3s", "kubectl", "get", "pod", gateway_pod, "-n", "rbd-system", "-o", "jsonpath={.spec.containers[*].name}", check=False
    ).stdout.split()
    logs = {}
    for container in ("ingress-apisix", "apisix"):
        if container not in names:
            continue
        result = run_sudo(
            "docker", "exec", "rainbond", "/bin/k3s", "kubectl", "logs", gateway_pod, "-n", "rbd-system", "-c", container, "--tail=80", check=False
        )
        (results_dir / f"rbd-gateway-{container}.log").write_text(result.stdout, encoding="utf-8")
        logs[container] = result.stdout.splitlines()[-20:]
    return {"pod": gateway_pod, "containers": names, "logs": logs}


def read_json_lines(path: pathlib.Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def docker_guard_snapshot(results_dir: pathlib.Path) -> dict[str, Any]:
    raw_rules = run_sudo("iptables", "-t", "raw", "-S", check=False).stdout
    (results_dir / "docker-raw-rules.txt").write_text(raw_rules, encoding="utf-8")
    started = run_sudo("systemctl", "show", "docker.service", "--property=ActiveEnterTimestampMonotonic", "--value", check=False)
    try:
        docker_started_at_monotonic_seconds = int(started.stdout.strip()) / 1_000_000
    except ValueError:
        docker_started_at_monotonic_seconds = None
    return {"docker_started_at_monotonic_seconds": docker_started_at_monotonic_seconds, "raw_rules_captured": bool(raw_rules)}


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
    docker_cleanup: dict[str, Any] = {}
    docker_evidence: dict[str, Any] = {}
    docker_guard: dict[str, Any] = {}
    expected_uuid = ""
    receiver = None
    guard_monitor = None
    setup_error = ""
    try:
        target_script = pathlib.Path(arguments.installer)
        main_script = pathlib.Path(arguments.main_installer)
        if not main_script.is_file() or not target_script.is_file():
            raise RuntimeError("target or main installer script is missing")
        receiver = start_receiver(results_dir)
        shim_dir = create_curl_shim(results_dir).resolve()
        action = REPORT_SCENARIOS.get(arguments.scenario, "DROP")
        report_mode = "receiver" if arguments.scenario in {"normal_install", "image_not_found", *DOCKER_SCENARIOS} else arguments.scenario.removeprefix("report_endpoint_")
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
                "SMOKE_DOCKER_DOWNLOAD_ATTEMPTS": str((results_dir / "docker-download-attempts.jsonl").resolve()),
            }
        )
        if arguments.scenario == "image_not_found":
            env["VERSION"] = "v0.0.0-installer-smoke-does-not-exist"
        baseline_addresses = {host: resolve_ipv4(host) for host in REPORT_HOSTS}
        connectivity["before_guard"] = {
            host: [probe_host_tcp(address) for address in values]
            for host, values in baseline_addresses.items()
        }
        install_network_guard(results_dir, action)
        guard_addresses = json.loads((results_dir / "network-guard.json").read_text(encoding="utf-8"))["addresses"]
        guard_validation = verify_network_guard(results_dir)
        if not guard_validation["valid"]:
            raise RuntimeError("network guard preflight failed")
        if arguments.scenario in DOCKER_SCENARIOS:
            docker_urls_file = results_dir / "docker-download-urls"
            docker_urls_file.write_text("\n".join(docker_download_urls(target_script, arguments.arch)) + "\n", encoding="utf-8")
            env["SMOKE_DOCKER_DOWNLOAD_URLS_FILE"] = str(docker_urls_file.resolve())
            docker_cleanup = remove_preinstalled_docker(results_dir)
        if arguments.scenario == "no_docker_tuna_fallback":
            env["SMOKE_DOCKER_DOWNLOAD_MODE"] = "tuna_partial_archive"
        elif arguments.scenario == "no_docker_all_sources_unavailable":
            env["SMOKE_DOCKER_DOWNLOAD_MODE"] = "all_sources_connect_failure"
        guard_monitor = NetworkGuardMonitor(results_dir)
        guard_monitor.start()
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
            f"SMOKE_DOCKER_DOWNLOAD_ATTEMPTS={env['SMOKE_DOCKER_DOWNLOAD_ATTEMPTS']}",
        ]
        if "VERSION" in env:
            command.append(f"VERSION={env['VERSION']}")
        if "SMOKE_DOCKER_DOWNLOAD_MODE" in env:
            command.append(f"SMOKE_DOCKER_DOWNLOAD_MODE={env['SMOKE_DOCKER_DOWNLOAD_MODE']}")
        if "SMOKE_DOCKER_DOWNLOAD_URLS_FILE" in env:
            command.append(f"SMOKE_DOCKER_DOWNLOAD_URLS_FILE={env['SMOKE_DOCKER_DOWNLOAD_URLS_FILE']}")
        command.extend(["bash", str(target_script)])
        code, output, timed_out = run_command(command, env, results_dir / "installer.log", arguments.timeout)
        if guard_monitor is not None:
            guard_monitor.stop()
            guard_state = json.loads((results_dir / "network-guard.json").read_text(encoding="utf-8"))
            guard_state["reinsertions"] = guard_monitor.reinsertions
            guard_state["monitor_errors"] = guard_monitor.errors
            (results_dir / "network-guard.json").write_text(json.dumps(guard_state, ensure_ascii=False, indent=2), encoding="utf-8")
        connectivity["after_guard"] = {
            host: [probe_host_tcp(address) for address in values]
            for host, values in guard_addresses.items()
            if host != "smoke_blackhole"
        }
        ready_scenarios = {"normal_install", "no_docker_install", "no_docker_tuna_fallback"}
        components = wait_ready_components() if arguments.scenario in ready_scenarios else collect_ready_components() if arguments.scenario not in {"image_not_found", "no_docker_all_sources_unavailable"} else []
        console_is_ready = console_ready() if arguments.scenario in ready_scenarios else False
        gateway = collect_gateway_logs(results_dir) if arguments.scenario not in {"image_not_found", "no_docker_all_sources_unavailable"} else gateway
        if arguments.scenario in DOCKER_SCENARIOS and arguments.scenario != "no_docker_all_sources_unavailable":
            docker_evidence = docker_installation_evidence(target_script, docker_cleanup)
            docker_guard = docker_guard_snapshot(results_dir)
        guard_validation = verify_network_guard(results_dir, require_docker_user=arguments.scenario != "no_docker_all_sources_unavailable")
        guard_validation["public_resolution"] = {host: resolve_public_ipv4(host) for host in REPORT_HOSTS}
        guard_validation["resolution_query_failed"] = any(result["error"] for result in guard_validation["public_resolution"].values())
        guard_validation["resolution_matches"] = not guard_validation["resolution_query_failed"] and all(set(guard_validation["public_resolution"][host]["addresses"]) == set(guard_addresses[host]) for host in REPORT_HOSTS)
        container_probes = probe_container_network(json.loads((results_dir / "network-guard.json").read_text(encoding="utf-8"))["addresses"]) if arguments.scenario != "image_not_found" else container_probes
    except Exception as error:
        setup_error = str(error)
    finally:
        if guard_monitor is not None:
            guard_monitor.stop()
        destroy_rainbond_container()
        if receiver is not None:
            stop_receiver(receiver)

    duration_seconds = round(time.monotonic() - started_at)
    report_lines = (results_dir / "reports.jsonl").read_text(encoding="utf-8").splitlines() if (results_dir / "reports.jsonl").exists() else []
    reports = extract_report_events(report_lines)
    target_uuid = next((event["uuid"] for event in reports if event.get("uuid")), "")
    success, reason = scenario_succeeded(arguments.scenario, code, timed_out, output, reports, expected_uuid)
    docker_assertion_error = docker_scenario_assertions(arguments.scenario, reports)
    if setup_error:
        success = False
        reason = f"smoke setup failed: {setup_error}"
    elif not guard_validation["valid"]:
        success = False
        reason = "raw table did not observe filter-blocked traffic" if not guard_validation.get("counter_consistent", True) else "network guard rules are missing"
    elif not guard_validation.get("resolution_matches", False):
        success = False
        reason = "isolation is untrusted because public DNS query failed" if guard_validation.get("resolution_query_failed") else "isolation is untrusted because public DNS addresses changed"
    elif not host_connectivity_valid(connectivity):
        success = False
        reason = (
            "host TCP isolation baseline is unreachable or guarded probe is invalid or not blocked"
        )
    elif arguments.scenario not in {"image_not_found", "no_docker_all_sources_unavailable"} and not container_probes["valid"]:
        success = False
        reason = "container TCP isolation probe is invalid or not blocked"
    elif guard_monitor is not None and guard_monitor.errors:
        success = False
        reason = f"network guard monitor failed: {guard_monitor.errors}"
    elif docker_assertion_error:
        success = False
        reason = docker_assertion_error
    elif arguments.scenario in {"normal_install", "no_docker_install", "no_docker_tuna_fallback"} and (not console_is_ready or not components or any(component["ready"].split("/")[0] != component["ready"].split("/")[-1] or component["status"] != "Running" for component in components)):
        success = False
        reason = f"services are not ready (7070={console_is_ready}): {components}"
    elif arguments.scenario in {"no_docker_install", "no_docker_tuna_fallback"} and (not docker_evidence.get("version_matches", False) or not docker_evidence.get("service_active", False)):
        success = False
        reason = f"installer Docker version mismatch: {docker_evidence}"
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
            "network_guard_reinsertions": summarize_guard_reinsertions(guard_monitor.reinsertions if guard_monitor is not None else []),
            "container_tcp_probes": container_probes,
            "console_7070_ready": console_is_ready,
            "uuid_comparison": {"target_ref": target_uuid, "main": expected_uuid, "matches": uuid_matches},
            "report_count": len(reports),
            "report_attempts": read_json_lines(results_dir / "report-attempts.jsonl"),
            "docker_download_attempts": read_json_lines(results_dir / "docker-download-attempts.jsonl"),
            "docker_cleanup": docker_cleanup,
            "docker_installation": docker_evidence,
            "docker_guard": docker_guard,
            "gateway": gateway,
        }
    )
    (results_dir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0 if success else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", required=True, choices=["normal_install", "image_not_found", *REPORT_SCENARIOS, *DOCKER_SCENARIOS])
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
