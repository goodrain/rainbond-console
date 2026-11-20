#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
INSTALL_SCRIPT="${SCRIPT_DIR}/../script/install-rainbond.sh"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
assert_equals() { [ "$2" = "$1" ] || fail "expected: ${1}; actual: ${2}"; }
assert_contains() { grep -Fq -- "$2" <<<"$1" || fail "expected output to contain: $2\noutput was:\n$1"; }
assert_not_contains() { if grep -Fq -- "$2" <<<"$1"; then fail "expected output not to contain: $2\noutput was:\n$1"; fi; }
extract_functions() {
  awk '
    /^function rainbond_normalize_arch\(\)/ { capture = 1 }
    /^function send_info\(\)/ { capture = 0 }
    capture { print }
  ' "${INSTALL_SCRIPT}"
}
functions_file=$(mktemp)
trap 'rm -f "${functions_file}"' EXIT
extract_functions >"${functions_file}"
source "${functions_file}"
assert_equals unknown_rainbond_timeout "$(rainbond_classify_timeout_reason '' 'rbd-app-ui-data Pending local-path')"
assert_equals storage_pvc_pending "$(rainbond_classify_timeout_reason '' 'data-volume Pending local-path')"
assert_equals storage_pvc_pending "$(rainbond_classify_timeout_reason 'Warning FailedScheduling: pod has unbound immediate PersistentVolumeClaims' '')"
assert_equals image_pull_failed "$(rainbond_classify_timeout_reason 'Status: Pending ImagePullBackOff' 'rbd-app-ui-data Pending 1m')"
assert_equals image_pull_failed "$(rainbond_classify_timeout_reason 'Reason: ImagePullBackOff' 'data-volume Pending local-path')"
assert_equals storage_pvc_pending "$(rainbond_classify_timeout_reason 'Warning FailedMount Unable to attach or mount volumes: timed out waiting for the condition' '')"
assert_equals unsupported "$(rainbond_normalize_arch armv7l)"
rainbond_diag_kubectl() {
  case "$*" in
    'get pods -n rbd-system --no-headers') printf '%s\n' 'helm-install-rainbond-cluster-x 0/1 Completed 0 2m' ;;
    'get pvc -n rbd-system --no-headers') printf '%s\n' 'rbd-app-ui-data Pending 1m' ;;
    'get nodes --no-headers') printf '%s\n' 'node Ready 3m' ;;
  esac
}
curl() { return 1; }
completed_job_diagnosis=$(rainbond_collect_timeout_diagnostics 600 test-attempt)
assert_contains "${completed_job_diagnosis}" '"root_cause_code":"unknown_rainbond_timeout"'
assert_not_contains "${completed_job_diagnosis}" 'helm-install-rainbond-cluster-x'
rainbond_diag_kubectl() {
  case "$*" in
    'get pods -n rbd-system --no-headers') printf '%s\n' 'rbd-api-abc 0/1 Pending 0 2m' ;;
    'get pvc -n rbd-system --no-headers') printf '%s\n' 'rbd-app-ui-data Pending 1m' ;;
    'get nodes --no-headers') printf '%s\n' 'node Ready 3m' ;;
    'describe pod rbd-api-abc -n rbd-system') printf '%s\n' 'Status: Pending' 'Reason: ImagePullBackOff' ;;
  esac
}
image_pull_diagnosis=$(rainbond_collect_timeout_diagnostics 600 test-attempt)
assert_contains "${image_pull_diagnosis}" '"root_cause_code":"image_pull_failed"'
pod_list=(local-path-provisioner minio rainbond-operator rbd-api rbd-app-ui rbd-chaos rbd-gateway rbd-hub rbd-monitor rbd-mq rbd-worker)
if rainbond_expected_pod_ready 'rbd-worker-abc 0/1 Running 0 2m' rbd-worker; then
  fail 'expected a Running but not Ready pod to remain unready'
fi
rainbond_diag_kubectl() {
  case "$*" in
    'get pods -n rbd-system --no-headers') printf '%s\n' 'local-path-provisioner-abc 1/1 Running 0 2m' 'rainbond-operator-abc 1/1 Running 0 2m' ;;
    'get pvc -n rbd-system --no-headers') printf '%s\n' 'rbd-app-ui-data Pending 1m' ;;
    'get nodes --no-headers') printf '%s\n' 'node Ready 3m' ;;
  esac
}
not_created_diagnosis=$(rainbond_collect_timeout_diagnostics 600 test-attempt)
assert_not_contains "${not_created_diagnosis}" '"root_cause_code":"gateway_unreachable"'
rainbond_diag_kubectl() {
  case "$*" in
    'get pods -n rbd-system --no-headers') printf '%s\n' 'local-path-provisioner-abc 1/1 Running 0 2m' 'minio-abc 1/1 Running 0 2m' 'rainbond-operator-abc 1/1 Running 0 2m' 'rbd-api-abc 1/1 Running 0 2m' 'rbd-app-ui-abc 1/1 Running 0 2m' 'rbd-chaos-abc 1/1 Running 0 2m' 'rbd-gateway-abc 2/2 Running 0 2m' 'rbd-hub-abc 1/1 Running 0 2m' 'rbd-monitor-abc 1/1 Running 0 2m' 'rbd-mq-abc 1/1 Running 0 2m' 'rbd-worker-abc 1/1 Running 0 2m' ;;
    'get pvc -n rbd-system --no-headers') printf '%s\n' 'rbd-app-ui-data Pending 1m' ;;
    'get nodes --no-headers') printf '%s\n' 'node Ready 3m' ;;
    'logs rbd-gateway-abc -n rbd-system -c apisix --tail=200') printf '%s\n' 'no valid upstream node for service default/rbd-api' ;;
    'logs rbd-gateway-abc -n rbd-system -c ingress-apisix --tail=200') printf '%s\n' "upstream doesn't exist: default/rbd-api" ;;
  esac
}
gateway_diagnosis=$(rainbond_collect_timeout_diagnostics 600 test-attempt)
assert_contains "${gateway_diagnosis}" '"root_cause_code":"gateway_unreachable"'
assert_contains "${gateway_diagnosis}" 'console_7070: unreachable'
assert_contains "${gateway_diagnosis}" 'gateway_controller: upstream routing errors detected'
EIP=console.example
curl() { for argument in "$@"; do [ "$argument" = 'http://console.example:7070' ] && { printf 200; return 0; }; done; return 1; }
assert_contains "$(rainbond_probe_console_7070)" 'reachable via external'
external_console_diagnosis=$(rainbond_collect_timeout_diagnostics 600 test-attempt)
assert_not_contains "${external_console_diagnosis}" '"root_cause_code":"gateway_unreachable"'
rainbond_diag_kubectl() {
  case "$*" in
    'get pods -n rbd-system --no-headers') printf '%s\n' 'rbd-gateway-abc 2/2 Running 0 2m' ;;
    'logs rbd-gateway-abc -n rbd-system -c apisix --tail=200') printf '%s\n' 'endpoint sync completed' ;;
    'logs rbd-gateway-abc -n rbd-system -c ingress-apisix --tail=200') printf '%s\n' 'endpoint sync completed' ;;
  esac
}
assert_contains "$(rainbond_gateway_controller_log_summary)" 'no relevant recent log entries'
rainbond_diag_kubectl() {
  case "$*" in
    'get pods -n rbd-system --no-headers') printf '%s\n' 'rbd-gateway-abc 2/2 Running 0 2m' ;;
    'logs rbd-gateway-abc -n rbd-system -c apisix --tail=200') printf '%s\n' 'container apisix is not valid for pod rbd-gateway-abc' >&2; return 1 ;;
    'logs rbd-gateway-abc -n rbd-system -c ingress-apisix --tail=200') printf '%s\n' 'endpoint sync completed' ;;
  esac
}
assert_contains "$(rainbond_gateway_controller_log_summary)" 'log collection failed'
RAINBOND_VERSION=v6.11.0-release
RAINBOND_FINAL_EVENT_ENABLED=true
RAINBOND_FINAL_STATUS_SENT=false
UUID=test-installation
ARCH_TYPE=amd64
send_msg() { printf '%s\n' "$1"; }
final_event=$(rainbond_send_final_event failed gateway_unreachable 1)
assert_contains "${final_event}" '"version":"v6.11.0-release"'
assert_contains "${final_event}" '"arch":"amd64"'
source "${functions_file}"
UUID=''
OS_INFO=''
ARCH_TYPE=''
arch() { printf 'x86_64'; }
rainbond_initialize_report_identity
first_uuid=$UUID
legacy_uuid=$(echo "$OS_INFO" | "$MD5_CMD" | cut -b 1-32)
assert_equals "${legacy_uuid}" "${first_uuid}"
captured_payloads=''
curl() {
  while [ "$#" -gt 0 ]; do
    [ "$1" = '-d' ] && { captured_payloads="${captured_payloads}${2}\n"; return 0; }
    shift
  done
}
send_msg 'early error'
send_msg 'later error'
assert_not_contains "${captured_payloads}" '"eid":'
assert_contains "${captured_payloads}" "\"uuid\":\"${first_uuid}\""
assert_contains "${captured_payloads}" '"version":"v6.11.0-release"'
assert_contains "${captured_payloads}" '"arch":"amd64"'
curl() { return 28; }
if ! send_msg 'report endpoint dropped'; then
  fail 'expected report timeout not to interrupt installation flow'
fi
init_line=$(grep -n '^rainbond_initialize_report_identity$' "${INSTALL_SCRIPT}" | cut -d: -f1)
parse_line=$(grep -n '^parse_cli_args "\$@"$' "${INSTALL_SCRIPT}" | cut -d: -f1)
[ "${init_line}" -lt "${parse_line}" ] || fail 'expected report identity initialization before argument parsing'
show_command_line=$(grep -n '^if \[ "\$CLI_COMMAND" = "show-command" \]; then$' "${INSTALL_SCRIPT}" | cut -d: -f1)
port_forward_line=$(grep -n '^if \[ "\$CLI_COMMAND" = "port-forward" \]; then$' "${INSTALL_SCRIPT}" | cut -d: -f1)
unsupported_arch_line=$(grep -n '^if \[ "\$ARCH_TYPE" = "unsupported" \]; then$' "${INSTALL_SCRIPT}" | cut -d: -f1)
[ "${show_command_line}" -lt "${unsupported_arch_line}" ] || fail 'expected show-command before unsupported architecture check'
[ "${port_forward_line}" -lt "${unsupported_arch_line}" ] || fail 'expected port-forward before unsupported architecture check'
assert_contains "$(grep -F -- '-e UUID=${UUID}' "${INSTALL_SCRIPT}")" '-e UUID=${UUID}'
log_collect_report=$(awk '/^function rainbond_send_operator_log_collect\(\)/,/^}/' "${INSTALL_SCRIPT}")
dindlog_report=$(awk '/^function send_msg\(\)/,/^}/' "${INSTALL_SCRIPT}")
assert_contains "${log_collect_report}" '--connect-timeout 3 --max-time 5'
assert_contains "${dindlog_report}" '--connect-timeout 3 --max-time 5'
main_running_check=$(grep -F 'if echo "$pod_status" | grep "^${prefix}" | grep '\''Running'\'' >/dev/null 2>&1; then' "${INSTALL_SCRIPT}" || true)
assert_contains "${main_running_check}" "grep 'Running'"
set +e
(arch() { printf armv7l; }; rainbond_initialize_report_identity) >/dev/null 2>&1
unknown_arch_status=$?
set -e
assert_equals 0 "${unknown_arch_status}"
unknown_arch=$(arch() { printf armv7l; }; rainbond_initialize_report_identity; printf '%s' "$ARCH_TYPE")
assert_equals unsupported "${unknown_arch}"
printf 'PASS: install timeout diagnostics\n'
