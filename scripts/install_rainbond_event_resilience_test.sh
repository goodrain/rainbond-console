#!/usr/bin/env bash
# capability_id: script.install-rainbond.event-resilience
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

assert_equals() {
  local expected=$1
  local actual=$2
  if [ "$expected" != "$actual" ]; then
    fail "expected: ${expected}; actual: ${actual}"
  fi
}

assert_less_than() {
  local upper_bound=$1
  local actual=$2
  if [ "$actual" -ge "$upper_bound" ]; then
    fail "expected value below ${upper_bound}; actual: ${actual}"
  fi
}

extract_functions() {
  awk '
    /^function rainbond_json_escape\(\)/ { capture = 1 }
    /^function send_info\(\)/ { capture = 0 }
    capture { print }
  ' "${INSTALL_SCRIPT}"
}

extract_docker_install_function() {
  awk '
    /^# Function to install Docker on Linux using binary installation/ { capture = 1 }
    /^manage_docker\(\)/ { capture = 0 }
    capture { print }
  ' "${INSTALL_SCRIPT}"
}

extract_pull_loop() {
  awk '
    /^# Pull image with retry mechanism/ { capture = 1 }
    /^if ! check_docker_network_preflight/ { capture = 0 }
    capture { print }
  ' "${INSTALL_SCRIPT}"
}

functions_file=$(mktemp)
trap 'rm -f "${functions_file}"' EXIT
extract_functions >"${functions_file}"
# shellcheck disable=SC1090
source "${functions_file}"

RAINBOND_FINAL_EVENT_ENABLED=true
UUID=test-installation
for signal_name in INT HUP TERM; do
  RAINBOND_FINAL_STATUS_SENT=false
  captured_message=''
  send_msg() { captured_message=$1; }
  set +e
  rainbond_handle_signal "${signal_name}" >/dev/null
  signal_status=$?
  set -e
  case "${signal_name}" in
    INT)
      assert_equals 130 "${signal_status}"
      assert_contains "${captured_message}" '"reason":"user_interrupted"'
      ;;
    HUP)
      assert_equals 129 "${signal_status}"
      assert_contains "${captured_message}" '"reason":"session_disconnected"'
      ;;
    TERM)
      assert_equals 143 "${signal_status}"
      assert_contains "${captured_message}" '"reason":"process_terminated"'
      ;;
  esac
done

tmp_dir=$(mktemp -d)
set +e
RAINBOND_FINAL_EVENT_ENABLED=true \
UUID=test-installation \
TEST_SIGNAL_LOG="${tmp_dir}/signal.log" \
bash -c '
  source "$1"
  send_msg() { printf "%s\n" "$1" >>"${TEST_SIGNAL_LOG}"; }
  trap "rainbond_handle_signal HUP; exit \$?" HUP
  kill -HUP $$
  sleep 1
' bash "${functions_file}"
signal_status=$?
set -e
assert_equals 129 "${signal_status}"
assert_contains "$(cat "${tmp_dir}/signal.log")" '"reason":"session_disconnected"'
assert_equals 1 "$(grep -Fc 'install_final' "${tmp_dir}/signal.log")"
rm -rf "${tmp_dir}"

RAINBOND_FINAL_STATUS_SENT=false
captured_message=''
send_msg() { captured_message=$1; }
rainbond_send_progress_event image_pull running '"attempt":1,"elapsed_seconds":30'
assert_contains "${captured_message}" '"event_type":"install_progress"'
assert_contains "${captured_message}" '"stage":"image_pull"'
assert_contains "${captured_message}" '"elapsed_seconds":30'
assert_equals 4xx "$(rainbond_http_status_class 404)"
assert_equals 5xx "$(rainbond_http_status_class 503)"
assert_equals 2xx "$(rainbond_http_status_class 200)"
assert_equals none "$(rainbond_http_status_class 000)"

RAINBOND_FINAL_STATUS_SENT=false
captured_message=''
send_msg() { captured_message=$1; }
rainbond_send_progress_event preflight running
assert_contains "${captured_message}" '"stage":"preflight"'
assert_contains "${captured_message}" '"status":"running"'

missing_command=''
command() {
  if [ "$1" = "-v" ] && [ "${2:-}" = "${missing_command}" ]; then
    return 1
  fi
  builtin command "$@"
}

for missing_command in awk sed grep tar; do
  RAINBOND_FINAL_EVENT_ENABLED=false
  RAINBOND_FINAL_STATUS_SENT=false
  RAINBOND_FINAL_FAILURE_REASON=preflight_required_command_missing
  captured_message=''
  send_msg() { captured_message=$1; }
  rainbond_enable_preflight_events
  assert_contains "${captured_message}" '"stage":"preflight"'
  set +e
  rainbond_handle_exit 1
  exit_status=$?
  set -e
  assert_equals 1 "${exit_status}"
  assert_contains "${captured_message}" '"final_status":"failed"'
  assert_contains "${captured_message}" '"reason":"preflight_required_command_missing"'
done

missing_command=curl
RAINBOND_FINAL_EVENT_ENABLED=false
RAINBOND_FINAL_STATUS_SENT=false
captured_message=''
send_msg() { captured_message=$1; }
rainbond_enable_preflight_events
assert_equals false "${RAINBOND_FINAL_EVENT_ENABLED}"
assert_equals '' "${captured_message}"

missing_command=''

tmp_dir=$(mktemp -d)
bin_dir="${tmp_dir}/bin"
command_override_file="${tmp_dir}/command-override.sh"
mkdir -p "${bin_dir}"
cat >"${bin_dir}/curl" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" >>"${TEST_CURL_LOG}"
EOF
chmod +x "${bin_dir}/curl"
cat >"${command_override_file}" <<'EOF'
command() {
  if [ "$1" = '-v' ] && [ "${2:-}" = "${TEST_MISSING_COMMAND:-}" ]; then
    return 1
  fi
  builtin command "$@"
}
EOF

for missing_command in awk sed grep tar; do
  : >"${tmp_dir}/curl.log"
  set +e
  PATH="${bin_dir}:${PATH}" \
  BASH_ENV="${command_override_file}" \
  TEST_CURL_LOG="${tmp_dir}/curl.log" \
  TEST_MISSING_COMMAND="${missing_command}" \
  bash "${INSTALL_SCRIPT}" >/dev/null 2>&1
  exit_status=$?
  set -e
  assert_equals 1 "${exit_status}"
  assert_contains "$(cat "${tmp_dir}/curl.log")" '\"stage\":\"preflight\"'
  assert_contains "$(cat "${tmp_dir}/curl.log")" '\"final_status\":\"failed\"'
  assert_contains "$(cat "${tmp_dir}/curl.log")" '\"reason\":\"preflight_required_command_missing\"'
  final_event=$(grep 'Rainbond install final event' "${tmp_dir}/curl.log")
  assert_not_contains "${final_event}" '"os_info":"Linux '
done

: >"${tmp_dir}/curl.log"
set +e
PATH="${bin_dir}:${PATH}" \
BASH_ENV="${command_override_file}" \
TEST_CURL_LOG="${tmp_dir}/curl.log" \
TEST_MISSING_COMMAND=curl \
bash "${INSTALL_SCRIPT}" >/dev/null 2>&1
exit_status=$?
set -e
assert_equals 1 "${exit_status}"
assert_equals '' "$(cat "${tmp_dir}/curl.log")"
rm -rf "${tmp_dir}"

RAINBOND_FINAL_EVENT_ENABLED=true
for preflight_reason in preflight_iptables_missing preflight_memory_insufficient preflight_disk_insufficient preflight_port_in_use preflight_docker_iptables_chain_unavailable containerd_start_failed; do
  RAINBOND_FINAL_STATUS_SENT=false
  RAINBOND_FINAL_FAILURE_REASON="${preflight_reason}"
  captured_message=''
  send_msg() { captured_message=$1; }
  set +e
  rainbond_handle_exit 1
  exit_status=$?
  set -e
  assert_equals 1 "${exit_status}"
  assert_contains "${captured_message}" '"final_status":"failed"'
  assert_contains "${captured_message}" "\"reason\":\"${preflight_reason}\""
done

sleep 30 &
RAINBOND_PULL_COMMAND_PID=$!
pull_command_pid=$RAINBOND_PULL_COMMAND_PID
rainbond_cleanup_pull_output
if kill -0 "${pull_command_pid}" 2>/dev/null; then
  fail 'expected pull cleanup to terminate the active docker pull process'
fi

bash -c 'trap "" TERM; while :; do :; done' &
RAINBOND_PULL_COMMAND_PID=$!
pull_command_pid=$RAINBOND_PULL_COMMAND_PID
start_time=$(date +%s)
rainbond_cleanup_pull_output
elapsed_seconds=$(( $(date +%s) - start_time ))
if kill -0 "${pull_command_pid}" 2>/dev/null; then
  fail 'expected pull cleanup watchdog to terminate a TERM-ignoring process'
fi
assert_less_than 7 "${elapsed_seconds}"

tmp_dir=$(mktemp -d)
bin_dir="${tmp_dir}/bin"
docker_function_file="${tmp_dir}/docker-install.sh"
mkdir -p "${bin_dir}"
extract_docker_install_function >"${docker_function_file}"
cat >"${bin_dir}/curl" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" >>"${TEST_CURL_LOG}"
output_file=''
for argument in "$@"; do
  if [ "${previous:-}" = '-o' ]; then
    output_file=$argument
    break
  fi
  previous=$argument
done
case "$*" in
  *mirrors.tuna.tsinghua.edu.cn*)
    printf '000'
    exit 6
    ;;
  *mirrors.aliyun.com*)
    printf '503'
    exit 22
    ;;
  *download.docker.com*)
    : >"${output_file}"
    printf '200'
    exit 0
    ;;
  *)
    exit 1
    ;;
esac
EOF
cat >"${bin_dir}/tar" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
chmod +x "${bin_dir}/curl" "${bin_dir}/tar"
PATH="${bin_dir}:/usr/bin:/bin" \
TEST_CURL_LOG="${tmp_dir}/curl.log" \
TEST_PROGRESS_LOG="${tmp_dir}/progress.log" \
RAINBOND_DOCKER_DOWNLOAD_RETRIES=3 \
bash -c '
  source "$1"
  rainbond_use_chinese_prompt() { return 1; }
  send_info() { :; }
  send_warn() { :; }
  send_error() { :; }
  rainbond_send_progress_event() { printf "%s\n" "$*" >>"${TEST_PROGRESS_LOG}"; }
  rainbond_http_status_class() { printf none; }
  verify_docker_archive() { return 0; }
  upgrade_docker_from_bundle() { return 0; }
  ARCH_TYPE=amd64
  install_docker_linux upgrade
' bash "${docker_function_file}"
assert_contains "$(cat "${tmp_dir}/curl.log")" 'mirrors.tuna.tsinghua.edu.cn'
assert_contains "$(cat "${tmp_dir}/curl.log")" 'mirrors.aliyun.com'
assert_contains "$(cat "${tmp_dir}/curl.log")" 'download.docker.com'
assert_contains "$(cat "${tmp_dir}/curl.log")" '--speed-limit 1024 --speed-time 60'
assert_equals 3 "$(wc -l <"${tmp_dir}/curl.log" | tr -d ' ')"
assert_contains "$(cat "${tmp_dir}/progress.log")" 'docker_download failed "source":"tuna","curl_exit_code":6,"http_status_class":"none"'
rm -rf "${tmp_dir}"

tmp_dir=$(mktemp -d)
bin_dir="${tmp_dir}/bin"
pull_loop_file="${tmp_dir}/pull-loop.sh"
mkdir -p "${bin_dir}"
extract_pull_loop >"${pull_loop_file}"
cat >"${bin_dir}/docker" <<'EOF'
#!/usr/bin/env bash
if [ "$1" = pull ]; then
  printf 'manifest unknown\n' >&2
  exit 1
fi
exit 0
EOF
cat >"${bin_dir}/sleep" <<'EOF'
#!/usr/bin/env bash
if [ "$1" = 1 ]; then
  exec /bin/sleep 1
fi
exit 0
EOF
chmod +x "${bin_dir}/docker" "${bin_dir}/sleep"
start_time=$(date +%s)
set +e
PATH="${bin_dir}:/usr/bin:/bin" \
TMPDIR="${tmp_dir}" \
RBD_IMAGE='registry.example/rainbond:test-k3s' \
RAINBOND_VERSION=test \
bash -c '
  source "$1"
  rainbond_use_chinese_prompt() { return 1; }
  send_info() { :; }
  send_warn() { :; }
  send_error() { :; }
  send_msg() { :; }
  rainbond_image_pull_failure_message() { printf "Image pull failed"; }
  source "$2"
' bash "${functions_file}" "${pull_loop_file}" | cat >/dev/null
pull_status=${PIPESTATUS[0]}
set -e
elapsed_seconds=$(( $(date +%s) - start_time ))
assert_equals 1 "${pull_status}"
assert_less_than 5 "${elapsed_seconds}"
rm -rf "${tmp_dir}"

printf 'PASS: install_rainbond_event_resilience_test\n'
