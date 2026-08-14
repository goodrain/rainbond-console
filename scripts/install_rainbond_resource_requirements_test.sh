#!/usr/bin/env bash
# capability_id: script.install-rainbond.resource-requirements
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
INSTALL_SCRIPT="${REPO_ROOT}/script/install-rainbond.sh"

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

assert_contains() {
  local haystack=$1
  local needle=$2
  if ! grep -Fq -- "$needle" <<<"$haystack"; then
    fail "expected output to contain: ${needle}\noutput was:\n${haystack}"
  fi
}

assert_not_contains() {
  local haystack=$1
  local needle=$2
  if grep -Fq -- "$needle" <<<"$haystack"; then
    fail "expected output not to contain: ${needle}\noutput was:\n${haystack}"
  fi
}

extract_function() {
  local function_name=$1
  awk -v function_name="$function_name" '
    $0 == "function " function_name "() {" { capture = 1 }
    capture { print }
    /^}$/ && capture { capture = 0 }
  ' "${INSTALL_SCRIPT}"
}

extract_resource_checks() {
  grep -E '^MIN_(MEMORY_KB|DISK_AVAILABLE_KB)=' "${INSTALL_SCRIPT}" || true
  extract_function check_memory_requirement_linux
  extract_function check_disk_requirement
}

run_resource_case() {
  local resource=$1
  local value=$2
  local functions_file
  functions_file=$(mktemp)
  extract_resource_checks >"${functions_file}"

  TEST_RESOURCE="${resource}" TEST_VALUE="${value}" bash -c '
    source "$1"
    rainbond_use_chinese_prompt() { return 1; }
    send_info() { printf "INFO: %s\n" "$*"; }
    send_error() { printf "ERROR: %s\n" "$*"; }
    awk() { printf "%s\n" "${TEST_VALUE}"; }

    set +e
    case "${TEST_RESOURCE}" in
      memory) check_memory_requirement_linux ;;
      disk) check_disk_requirement "${TEST_VALUE}" ;;
      *) exit 99 ;;
    esac
    status=$?
    set -e
    printf "status=%s\n" "${status}"
  ' bash "${functions_file}"
}

requirements=$(extract_resource_checks)
assert_contains "${requirements}" 'MIN_MEMORY_KB=$((4 * 1024 * 1024))'
assert_contains "${requirements}" 'MIN_DISK_AVAILABLE_KB=$((10 * 1024 * 1024))'

script_content=$(sed -n '1,$p' "${INSTALL_SCRIPT}")
assert_not_contains "${script_content}" 'MIN_CPU_COUNT='
assert_not_contains "${script_content}" 'check_cpu_requirement_linux'

memory_below_output=$(run_resource_case memory 4194303)
assert_contains "${memory_below_output}" 'minimum required: 4GB'
assert_contains "${memory_below_output}" 'status=1'

memory_boundary_output=$(run_resource_case memory 4194304)
assert_contains "${memory_boundary_output}" 'Memory check passed, current: 4GB'
assert_contains "${memory_boundary_output}" 'status=0'

disk_below_output=$(run_resource_case disk 10485759)
assert_contains "${disk_below_output}" 'please reserve at least 10GB space and try again'
assert_contains "${disk_below_output}" 'status=1'

disk_boundary_output=$(run_resource_case disk 10485760)
assert_contains "${disk_boundary_output}" 'Disk space check passed, available space: 10GB'
assert_contains "${disk_boundary_output}" 'status=0'

printf 'PASS: install_rainbond_resource_requirements_test\n'
