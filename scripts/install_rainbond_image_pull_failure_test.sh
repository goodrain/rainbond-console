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
    /^function rainbond_handle_exit\(\)/ { capture = 0 }
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

zh_message=$(RAINBOND_INSTALL_LANG=zh rainbond_image_pull_failure_message image_not_found 'registry.example/rainbond:v0-k3s')
assert_contains "${zh_message}" '版本镜像问题，不是网络问题'
assert_contains "${zh_message}" 'VERSION=<可用版本> bash install-rainbond.sh'

en_message=$(RAINBOND_INSTALL_LANG=en rainbond_image_pull_failure_message image_not_found 'registry.example/rainbond:v0-k3s')
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

assert_contains "$(cat "${INSTALL_SCRIPT}")" 'docker pull "${RBD_IMAGE}" 2>&1 | tee "${pull_output_file}"'
assert_contains "$(cat "${INSTALL_SCRIPT}")" '"${RAINBOND_FINAL_FAILURE_REASON:-exit_nonzero}"'

printf 'PASS: image pull failure classification\n'
