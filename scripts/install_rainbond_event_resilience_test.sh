#!/usr/bin/env bash
# capability_id: script.install-rainbond.event-resilience
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
INSTALL_SCRIPT="${REPO_ROOT}/script/install-rainbond.sh"
WINDOWS_SCRIPT="${REPO_ROOT}/script/install-rainbond.ps1"
WSL_SCRIPT="${REPO_ROOT}/script/install-rainbond-wsl.ps1"

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

assert_equals() {
  local expected=$1
  local actual=$2
  if [ "$expected" != "$actual" ]; then
    fail "expected: ${expected}; actual: ${actual}"
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

sleep 1 &
RAINBOND_PULL_COMMAND_PID=$!
pull_command_pid=$RAINBOND_PULL_COMMAND_PID
RAINBOND_PULL_PROGRESS_PID=''
rainbond_cleanup_pull_output
if kill -0 "${pull_command_pid}" 2>/dev/null; then
  fail 'expected pull cleanup to terminate the active docker pull process'
fi

script_content=$(cat "${INSTALL_SCRIPT}")
assert_contains "${script_content}" 'rainbond_handle_signal HUP'
assert_contains "${script_content}" 'rainbond_send_progress_event image_pull running'
assert_contains "${script_content}" 'docker_download_failed'
assert_contains "${script_content}" 'curl_exit_code'
assert_contains "${script_content}" 'http_status_class'
assert_contains "${script_content}" 'include_environment_info'
assert_contains "${script_content}" 'mirrors.aliyun.com/docker-ce/linux/static/stable'
assert_contains "${script_content}" 'download.docker.com/linux/static/stable'

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
    : >"${output_file}"
    printf '200'
    exit 0
    ;;
  *)
    printf '500'
    exit 22
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
RAINBOND_DOCKER_DOWNLOAD_RETRIES=1 \
bash -c '
  source "$1"
  rainbond_use_chinese_prompt() { return 1; }
  send_info() { :; }
  send_warn() { :; }
  send_error() { :; }
  rainbond_send_progress_event() { printf "%s\n" "$*" >>"${TEST_PROGRESS_LOG}"; }
  rainbond_http_status_class() { printf none; }
  verify_docker_upgrade_archive() { return 0; }
  upgrade_docker_from_bundle() { return 0; }
  ARCH_TYPE=amd64
  install_docker_linux upgrade
' bash "${docker_function_file}"
assert_contains "$(cat "${tmp_dir}/curl.log")" 'mirrors.tuna.tsinghua.edu.cn'
assert_contains "$(cat "${tmp_dir}/curl.log")" 'mirrors.aliyun.com'
assert_contains "$(cat "${tmp_dir}/progress.log")" 'docker_download failed "source":"tuna","curl_exit_code":6,"http_status_class":"none"'
rm -rf "${tmp_dir}"

windows_content=$(cat "${WINDOWS_SCRIPT}")
assert_contains "${windows_content}" 'function Send-FinalEvent'
assert_contains "${windows_content}" 'TimeoutSec = 5'
assert_contains "${windows_content}" 'windows_container_ready'
assert_contains "${windows_content}" 'windows_container_start_failed'
assert_contains "${windows_content}" 'windows_prerequisites_failed'
assert_contains "${windows_content}" 'windows_eip_invalid'
assert_contains "${windows_content}" 'windows_eip_unavailable'
assert_contains "${windows_content}" $'MD5\n\ncheck_docker'

wsl_content=$(cat "${WSL_SCRIPT}")
assert_contains "${wsl_content}" 'function Send-FinalEvent'
assert_contains "${wsl_content}" 'TimeoutSec  = 5'
assert_contains "${wsl_content}" 'wsl_services_ready'
assert_contains "${wsl_content}" 'wsl_install_failed'
assert_contains "${wsl_content}" '[int]$ExitCode = 1'

printf 'PASS: install_rainbond_event_resilience_test\n'
