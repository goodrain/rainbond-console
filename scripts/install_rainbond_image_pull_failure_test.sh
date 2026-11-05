#!/usr/bin/env bash
# capability_id: script.install-rainbond.image-pull-failure-classification
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
INSTALL_SCRIPT="${REPO_ROOT}/script/install-rainbond.sh"

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

assert_equals() {
  local expected=$1
  local actual=$2
  if [ "$actual" != "$expected" ]; then
    fail "expected: ${expected}; actual: ${actual}"
  fi
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

extract_functions() {
  awk '
    /^function rainbond_use_chinese_prompt\(\)/ { capture = 1 }
    /^function rainbond_classify_image_pull_failure\(\)/ { capture = 1 }
    /^function rainbond_image_pull_failure_message\(\)/ { capture = 1 }
    /^function rainbond_json_escape\(\)/ { capture = 1 }
    /^function rainbond_send_final_event\(\)/ { capture = 1 }
    /^function send_info\(\)/ { capture = 0 }
    capture { print }
  ' "${INSTALL_SCRIPT}"
}

extract_pull_loop() {
  awk '
    /^# Try to pull image with retries/ { capture = 1 }
    /^if ! check_docker_network_preflight/ { capture = 0 }
    capture { print }
  ' "${INSTALL_SCRIPT}"
}

functions_file=$(mktemp)
trap 'rm -f "${functions_file}"' EXIT
extract_functions >"${functions_file}"

# shellcheck disable=SC1090
source "${functions_file}"

assert_equals image_not_found "$(rainbond_classify_image_pull_failure 'manifest unknown: manifest unknown')"
assert_equals image_not_found "$(rainbond_classify_image_pull_failure 'pull access denied: repository not found')"
assert_equals registry_unreachable "$(rainbond_classify_image_pull_failure 'dial tcp: lookup registry.example: no such host')"
assert_equals registry_denied "$(rainbond_classify_image_pull_failure 'unauthorized: authentication required')"
assert_equals disk_full "$(rainbond_classify_image_pull_failure 'write /var/lib/docker: no space left on device')"
assert_equals pull_failed_other "$(rainbond_classify_image_pull_failure 'unexpected pull failure')"

zh_message=$(RAINBOND_INSTALL_LANG=zh rainbond_image_pull_failure_message image_not_found)
assert_contains "${zh_message}" '版本镜像问题，不是网络问题'
assert_contains "${zh_message}" 'VERSION=<可用版本> bash install-rainbond.sh'

en_message=$(RAINBOND_INSTALL_LANG=en rainbond_image_pull_failure_message image_not_found)
assert_contains "${en_message}" 'version image issue, not a network issue'
assert_contains "${en_message}" 'VERSION=<available-version> bash install-rainbond.sh'

RAINBOND_FINAL_EVENT_ENABLED=true
RAINBOND_FINAL_STATUS_SENT=false
UUID=test-installation
send_msg() {
  printf '%s\n' "$1"
}
event_output=$(rainbond_send_final_event failed image_not_found 1)
assert_contains "${event_output}" '"reason":"image_not_found"'
assert_not_contains "${event_output}" 'manifest unknown'

signal_tmp_file=$(mktemp)
printf 'manifest unknown: registry.private.example\n' >"${signal_tmp_file}"
RAINBOND_PULL_OUTPUT_FILE="${signal_tmp_file}"
RAINBOND_FINAL_STATUS_SENT=false
set +e
rainbond_handle_signal INT >/dev/null
signal_status=$?
set -e
assert_equals 130 "${signal_status}"
if [ -e "${signal_tmp_file}" ]; then
  fail 'expected signal handler to remove the pull output file'
fi

IMGHUB_MIRROR='registry.private.example:5000/team'
captured_message=''
send_msg() {
  captured_message=$1
}
send_error() {
  send_msg "$1"
}
send_error "$(rainbond_image_pull_failure_message image_not_found "${IMGHUB_MIRROR}/rainbond:v0-k3s")"
assert_not_contains "${captured_message}" "${IMGHUB_MIRROR}"
assert_contains "${captured_message}" 'VERSION=<可用版本> bash install-rainbond.sh'

assert_contains "$(cat "${INSTALL_SCRIPT}")" 'docker pull "${RBD_IMAGE}" 2>"${pull_output_file}"'
assert_contains "$(cat "${INSTALL_SCRIPT}")" 'cat "${pull_output_file}" >&2'
assert_not_contains "$(cat "${INSTALL_SCRIPT}")" 'tee "${pull_output_file}"'
assert_contains "$(cat "${INSTALL_SCRIPT}")" '"${RAINBOND_FINAL_FAILURE_REASON:-exit_nonzero}"'

tmp_dir=$(mktemp -d)
pull_loop_file="${tmp_dir}/pull-loop.sh"
extract_pull_loop >"${pull_loop_file}"
set +e
TMPDIR="${tmp_dir}" \
RBD_IMAGE='registry.private.example:5000/team/rainbond:v0-k3s' \
RAINBOND_VERSION='v0' \
TEST_DOCKER_LOG="${tmp_dir}/docker.log" \
TEST_MESSAGE_LOG="${tmp_dir}/messages.log" \
bash -c '
  source "$1"
  rainbond_use_chinese_prompt() { return 0; }
  send_info() { :; }
  send_warn() { :; }
  send_msg() { printf "%s\n" "$1" >>"${TEST_MESSAGE_LOG}"; }
  send_error() { send_msg "$1"; }
  sleep() { :; }
  docker() {
    printf "%s\n" "$*" >>"${TEST_DOCKER_LOG}"
    if [ "$1" = pull ]; then
      printf "Downloading layer\n"
      printf "manifest unknown: registry.private.example:5000/team/rainbond:v0-k3s\n" >&2
      return 1
    fi
    return 0
  }
  source "$2"
' bash "${functions_file}" "${pull_loop_file}" >"${tmp_dir}/stdout" 2>"${tmp_dir}/stderr"
pull_status=$?
set -e
assert_equals 1 "${pull_status}"
assert_contains "$(cat "${tmp_dir}/stdout")" 'Downloading layer'
assert_contains "$(cat "${tmp_dir}/stderr")" 'manifest unknown'
assert_equals 3 "$(grep -Fc 'pull registry.private.example:5000/team/rainbond:v0-k3s' "${tmp_dir}/docker.log")"
assert_not_contains "$(cat "${tmp_dir}/messages.log")" 'registry.private.example:5000/team'
if find "${tmp_dir}" -name 'rainbond-image-pull.*' -print -quit | grep -q .; then
  fail 'expected the pull output file to be removed after failure'
fi
rm -rf "${tmp_dir}"

printf 'PASS: image pull failure classification\n'
