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
    /^function rainbond_json_escape\(\)/ { capture = 1 }
    /^function send_info\(\)/ { capture = 0 }
    capture { print }
  ' "${INSTALL_SCRIPT}"
}
functions_file=$(mktemp)
trap 'rm -f "${functions_file}"' EXIT
extract_functions >"${functions_file}"
source "${functions_file}"
assert_equals unknown_rainbond_timeout "$(rainbond_classify_timeout_reason 'rbd-app-ui-data Pending local-path')"
assert_equals storage_pvc_pending "$(rainbond_classify_timeout_reason 'data-volume Pending local-path')"
assert_equals storage_pvc_pending "$(rainbond_classify_timeout_reason 'Warning FailedScheduling: pod has unbound immediate PersistentVolumeClaims')"
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
    'get pods -n rbd-system --no-headers') printf '%s\n' 'rainbond-operator-abc 1/1 Running 0 2m' 'apisix-ingress-controller-abc 1/1 Running 0 2m' ;;
    'get pvc -n rbd-system --no-headers') printf '%s\n' 'rbd-app-ui-data Pending 1m' ;;
    'get nodes --no-headers') printf '%s\n' 'node Ready 3m' ;;
    'logs apisix-ingress-controller-abc -n rbd-system --tail=20') printf '%s\n' 'endpoint update failed' ;;
  esac
}
gateway_diagnosis=$(rainbond_collect_timeout_diagnostics 600 test-attempt)
assert_contains "${gateway_diagnosis}" '"root_cause_code":"gateway_unreachable"'
assert_contains "${gateway_diagnosis}" 'console_7070: unreachable'
assert_contains "${gateway_diagnosis}" 'gateway_controller: endpoint related entries detected'
RAINBOND_FINAL_EVENT_ENABLED=true
RAINBOND_FINAL_STATUS_SENT=false
RAINBOND_VERSION=v6.11.0-release
ARCH_TYPE=arm64
UUID=test-installation
send_msg() { printf '%s\n' "$1"; }
final_event=$(rainbond_send_final_event failed gateway_unreachable 1)
assert_contains "${final_event}" '"version":"v6.11.0-release"'
assert_contains "${final_event}" '"arch":"arm64"'
source "${functions_file}"
captured_payload=''
curl() {
  while [ "$#" -gt 0 ]; do
    [ "$1" = '-d' ] && { captured_payload=$2; return 0; }
    shift
  done
}
UUID=''
OS_INFO='Linux test-host 6.0'
send_msg 'early error'
assert_contains "${captured_payload}" '"eid":"'
assert_not_contains "${captured_payload}" '"eid":""'
printf 'PASS: install timeout diagnostics\n'
