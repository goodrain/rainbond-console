#!/usr/bin/env bash
# capability_id: script.install-rainbond.orbstack-download-recovery
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
INSTALL_SCRIPTS=(
  "${REPO_ROOT}/script/install-rainbond.sh"
  "${REPO_ROOT}/script/install-rainbond-gpu.sh"
)

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

write_stub() {
  local bin_dir=$1
  local name=$2
  local body=$3
  {
    printf '%s\n' '#!/usr/bin/env bash'
    printf '%s\n' "$body"
  } >"${bin_dir}/${name}"
  chmod +x "${bin_dir}/${name}"
}

extract_truthy_helper() {
  local script=$1
  awk '
    /^function is_truthy\(\) \{/ { capture = 1 }
    capture { print }
    /^}$/ && capture { capture = 0 }
  ' "${script}"
}

extract_orbstack_functions() {
  local script=$1
  {
    extract_truthy_helper "${script}"
    awk '
      /^# Function to check if OrbStack is installed/ { capture = 1 }
      /^# Function to handle Docker Desktop on macOS/ { capture = 0 }
      capture { print }
    ' "${script}"
  }
}

extract_docker_install_functions() {
  local script=$1
  local docker_file=$2
  awk '
    /^# Function to create containerd systemd service file/ { capture = 1 }
    /^# Function to handle Docker installation requirement on macOS/ { capture = 0 }
    capture { print }
  ' "${script}" | sed "s|local docker_file=\"/tmp/docker.tgz\"|local docker_file=\"${docker_file}\"|"
}

run_orbstack_start_case() {
  local script=$1
  local tmp_dir bin_dir functions_file output_file
  tmp_dir=$(mktemp -d)
  bin_dir="${tmp_dir}/bin"
  functions_file="${tmp_dir}/orbstack-functions.sh"
  output_file="${tmp_dir}/output"
  mkdir -p "${bin_dir}"

write_stub "${bin_dir}" orb '
if [ "$#" -eq 0 ]; then
  printf "orb <no-args>\n" >>"${STUB_LOG}"
  touch "${TEST_TMP}/orbstack-ready"
  exit 0
fi
printf "orb %s\n" "$*" >>"${STUB_LOG}"
case "${1:-}" in
  status)
    [ -f "${TEST_TMP}/orbstack-ready" ]
    exit $?
    ;;
esac
exit 1
'
  write_stub "${bin_dir}" docker '
printf "docker %s\n" "$*" >>"${STUB_LOG}"
if [ "${1:-}" = "info" ]; then
  [ -f "${TEST_TMP}/orbstack-ready" ]
  exit $?
fi
exit 0
'
  write_stub "${bin_dir}" open '
printf "open %s\n" "$*" >>"${STUB_LOG}"
touch "${TEST_TMP}/orbstack-ready"
exit 0
'
  write_stub "${bin_dir}" pgrep 'exit 1'
  write_stub "${bin_dir}" sleep 'exit 0'

  extract_orbstack_functions "${script}" >"${functions_file}"
  set +e
  STUB_LOG="${tmp_dir}/stub.log" \
  TEST_TMP="${tmp_dir}" \
  PATH="${bin_dir}:/usr/bin:/bin" \
  LANG=C \
  RAINBOND_ORBSTACK_WAIT_SECONDS=3 \
  bash -c '
    source "$1"
    rainbond_use_chinese_prompt() { return 1; }
    send_info() { printf "INFO: %s\n" "$*" >>"${STUB_LOG}"; }
    send_warn() { printf "WARN: %s\n" "$*" >>"${STUB_LOG}"; }
    send_error() { printf "ERROR: %s\n" "$*" >>"${STUB_LOG}"; }
    check_orbstack_installed() { command -v orb >/dev/null 2>&1; }
    handle_orbstack_macos
    status=$?
    printf "status=%s\n" "${status}"
    cat "${STUB_LOG}"
  ' bash "${functions_file}" >"${output_file}" 2>&1
  local status=$?
  set -e

  cat "${output_file}"
  printf "case_status=%s\n" "${status}"
}

run_orbstack_install_case() {
  local script=$1
  local tmp_dir bin_dir functions_file output_file install_dir
  tmp_dir=$(mktemp -d)
  bin_dir="${tmp_dir}/bin"
  functions_file="${tmp_dir}/orbstack-functions.sh"
  output_file="${tmp_dir}/output"
  install_dir="${tmp_dir}/apps"
  mkdir -p "${bin_dir}" "${install_dir}"

  write_stub "${bin_dir}" brew '
printf "brew %s\n" "$*" >>"${STUB_LOG}"
exit 99
'
  write_stub "${bin_dir}" curl '
printf "curl %s\n" "$*" >>"${STUB_LOG}"
out=""
while [ "$#" -gt 0 ]; do
  if [ "$1" = "-o" ]; then
    shift
    out=$1
  fi
  shift || break
done
[ -n "${out}" ] || exit 2
printf "fake-dmg" >"${out}"
exit 0
'
  write_stub "${bin_dir}" hdiutil '
printf "hdiutil %s\n" "$*" >>"${STUB_LOG}"
if [ "${1:-}" = "attach" ]; then
  mountpoint=""
  while [ "$#" -gt 0 ]; do
    if [ "$1" = "-mountpoint" ]; then
      shift
      mountpoint=$1
    fi
    shift || break
  done
  mkdir -p "${mountpoint}/OrbStack.app"
fi
exit 0
'
  write_stub "${bin_dir}" ditto '
printf "ditto %s\n" "$*" >>"${STUB_LOG}"
mkdir -p "$2"
exit 0
'
  write_stub "${bin_dir}" docker '
printf "docker %s\n" "$*" >>"${STUB_LOG}"
if [ "${1:-}" = "info" ]; then
  [ -f "${TEST_TMP}/orbstack-ready" ]
  exit $?
fi
exit 0
'
  write_stub "${bin_dir}" open '
printf "open %s\n" "$*" >>"${STUB_LOG}"
touch "${TEST_TMP}/orbstack-ready"
exit 0
'
  write_stub "${bin_dir}" pgrep 'exit 1'
  write_stub "${bin_dir}" sleep 'exit 0'

  extract_orbstack_functions "${script}" >"${functions_file}"
  set +e
  STUB_LOG="${tmp_dir}/stub.log" \
  TEST_TMP="${tmp_dir}" \
  PATH="${bin_dir}:/usr/bin:/bin" \
  HOME="${tmp_dir}/home" \
  LANG=C \
  RAINBOND_AUTO_INSTALL_ORBSTACK=true \
  RAINBOND_ORBSTACK_INSTALL_DIR="${install_dir}" \
  RAINBOND_ORBSTACK_WAIT_SECONDS=3 \
  bash -c '
    source "$1"
    rainbond_use_chinese_prompt() { return 1; }
    send_info() { printf "INFO: %s\n" "$*" >>"${STUB_LOG}"; }
    send_warn() { printf "WARN: %s\n" "$*" >>"${STUB_LOG}"; }
    send_error() { printf "ERROR: %s\n" "$*" >>"${STUB_LOG}"; }
    check_orbstack_installed() { command -v orb >/dev/null 2>&1 || [ -d "${RAINBOND_ORBSTACK_INSTALL_DIR}/OrbStack.app" ]; }
    handle_orbstack_macos
    status=$?
    printf "status=%s\n" "${status}"
    cat "${STUB_LOG}"
  ' bash "${functions_file}" >"${output_file}" 2>&1
  local status=$?
  set -e

  cat "${output_file}"
  printf "case_status=%s\n" "${status}"
}

run_orbstack_dmg_failure_brew_failure_case() {
  local script=$1
  local tmp_dir bin_dir functions_file output_file
  tmp_dir=$(mktemp -d)
  bin_dir="${tmp_dir}/bin"
  functions_file="${tmp_dir}/orbstack-functions.sh"
  output_file="${tmp_dir}/output"
  mkdir -p "${bin_dir}"

  write_stub "${bin_dir}" brew '
printf "brew %s\n" "$*" >>"${STUB_LOG}"
printf "/opt/homebrew/Library/Homebrew/macos_version.rb:43:in initialize: unknown or unsupported macOS version: \"26.2\" (MacOSVersion::Error)\n" >&2
exit 1
'
  write_stub "${bin_dir}" curl '
printf "curl %s\n" "$*" >>"${STUB_LOG}"
exit 1
'

  extract_orbstack_functions "${script}" >"${functions_file}"
  set +e
  STUB_LOG="${tmp_dir}/stub.log" \
  TEST_TMP="${tmp_dir}" \
  PATH="${bin_dir}:/usr/bin:/bin" \
  HOME="${tmp_dir}/home" \
  LANG=C \
  RAINBOND_AUTO_INSTALL_ORBSTACK=true \
  bash -c '
    source "$1"
    rainbond_use_chinese_prompt() { return 1; }
    send_info() { printf "INFO: %s\n" "$*" >>"${STUB_LOG}"; }
    send_warn() { printf "WARN: %s\n" "$*" >>"${STUB_LOG}"; }
    send_error() { printf "ERROR: %s\n" "$*" >>"${STUB_LOG}"; }
    install_orbstack_macos
    status=$?
    printf "status=%s\n" "${status}"
    cat "${STUB_LOG}"
  ' bash "${functions_file}" >"${output_file}" 2>&1
  local status=$?
  set -e

  cat "${output_file}"
  printf "case_status=%s\n" "${status}"
}

run_orbstack_download_resume_case() {
  local script=$1
  local tmp_dir bin_dir functions_file output_file install_dir
  tmp_dir=$(mktemp -d)
  bin_dir="${tmp_dir}/bin"
  functions_file="${tmp_dir}/orbstack-functions.sh"
  output_file="${tmp_dir}/output"
  install_dir="${tmp_dir}/apps"
  mkdir -p "${bin_dir}" "${install_dir}"

  write_stub "${bin_dir}" curl '
printf "curl %s\n" "$*" >>"${STUB_LOG}"
count=0
[ -f "${TEST_TMP}/curl-count" ] && count=$(cat "${TEST_TMP}/curl-count")
count=$((count + 1))
printf "%s" "${count}" >"${TEST_TMP}/curl-count"
out=""
while [ "$#" -gt 0 ]; do
  if [ "$1" = "-o" ]; then
    shift
    out=$1
  fi
  shift || break
done
[ -n "${out}" ] || exit 2
if [ "${count}" -eq 1 ]; then
  printf "partial-dmg" >"${out}"
  exit 28
fi
printf "fake-dmg" >>"${out}"
exit 0
'
  write_stub "${bin_dir}" hdiutil '
printf "hdiutil %s\n" "$*" >>"${STUB_LOG}"
if [ "${1:-}" = "attach" ]; then
  mountpoint=""
  while [ "$#" -gt 0 ]; do
    if [ "$1" = "-mountpoint" ]; then
      shift
      mountpoint=$1
    fi
    shift || break
  done
  mkdir -p "${mountpoint}/OrbStack.app"
fi
exit 0
'
  write_stub "${bin_dir}" ditto '
printf "ditto %s\n" "$*" >>"${STUB_LOG}"
mkdir -p "$2"
exit 0
'
  write_stub "${bin_dir}" sleep 'exit 0'

  extract_orbstack_functions "${script}" >"${functions_file}"
  set +e
  STUB_LOG="${tmp_dir}/stub.log" \
  TEST_TMP="${tmp_dir}" \
  PATH="${bin_dir}:/usr/bin:/bin" \
  HOME="${tmp_dir}/home" \
  LANG=C \
  RAINBOND_ORBSTACK_INSTALL_DIR="${install_dir}" \
  RAINBOND_ORBSTACK_DOWNLOAD_RETRIES=2 \
  bash -c '
    source "$1"
    rainbond_use_chinese_prompt() { return 1; }
    send_info() { printf "INFO: %s\n" "$*" >>"${STUB_LOG}"; }
    send_warn() { printf "WARN: %s\n" "$*" >>"${STUB_LOG}"; }
    send_error() { printf "ERROR: %s\n" "$*" >>"${STUB_LOG}"; }
    install_orbstack_from_dmg_macos
    status=$?
    printf "status=%s\n" "${status}"
    printf "curl_calls=%s\n" "$(cat "${TEST_TMP}/curl-count")"
    cat "${STUB_LOG}"
  ' bash "${functions_file}" >"${output_file}" 2>&1
  local status=$?
  set -e

  cat "${output_file}"
  printf "case_status=%s\n" "${status}"
}

run_download_retry_case() {
  local script=$1
  local tmp_dir bin_dir functions_file output_file docker_file
  tmp_dir=$(mktemp -d)
  bin_dir="${tmp_dir}/bin"
  functions_file="${tmp_dir}/docker-functions.sh"
  output_file="${tmp_dir}/output"
  docker_file="${tmp_dir}/docker.tgz"
  mkdir -p "${bin_dir}"

  write_stub "${bin_dir}" curl '
printf "curl %s\n" "$*" >>"${STUB_LOG}"
count=0
[ -f "${TEST_TMP}/curl-count" ] && count=$(cat "${TEST_TMP}/curl-count")
count=$((count + 1))
printf "%s" "${count}" >"${TEST_TMP}/curl-count"
out=""
while [ "$#" -gt 0 ]; do
  if [ "$1" = "-o" ]; then
    shift
    out=$1
  fi
  shift || break
done
[ -n "${out}" ] || exit 2
if [ "${count}" -eq 1 ]; then
  printf "not-a-tarball" >"${out}"
else
  printf "valid-tarball" >"${out}"
fi
exit 0
'
  write_stub "${bin_dir}" tar '
printf "tar %s\n" "$*" >>"${STUB_LOG}"
case "${1:-}" in
  -tzf)
    grep -q "valid-tarball" "$2"
    exit $?
    ;;
  -xzf)
    exit 0
    ;;
esac
exit 0
'
  write_stub "${bin_dir}" cp 'printf "cp %s\n" "$*" >>"${STUB_LOG}"; exit 0'
  write_stub "${bin_dir}" chmod 'printf "chmod %s\n" "$*" >>"${STUB_LOG}"; exit 0'
  write_stub "${bin_dir}" groupadd 'printf "groupadd %s\n" "$*" >>"${STUB_LOG}"; exit 0'
  write_stub "${bin_dir}" systemctl 'printf "systemctl %s\n" "$*" >>"${STUB_LOG}"; exit 0'
  write_stub "${bin_dir}" sleep 'exit 0'
  write_stub "${bin_dir}" rm '
for arg in "$@"; do
  case "${arg}" in
    "${TEST_TMP}"/*)
      /bin/rm -rf "${arg}"
      ;;
  esac
done
exit 0
'

  extract_docker_install_functions "${script}" "${docker_file}" >"${functions_file}"
  set +e
  STUB_LOG="${tmp_dir}/stub.log" \
  TEST_TMP="${tmp_dir}" \
  PATH="${bin_dir}:/usr/bin:/bin" \
  LANG=C \
  ARCH_TYPE=amd64 \
  RAINBOND_DOCKER_DOWNLOAD_RETRIES=2 \
  bash -c '
    source "$1"
    rainbond_use_chinese_prompt() { return 1; }
    send_info() { printf "INFO: %s\n" "$*" >>"${STUB_LOG}"; }
    send_warn() { printf "WARN: %s\n" "$*" >>"${STUB_LOG}"; }
    send_error() { printf "ERROR: %s\n" "$*" >>"${STUB_LOG}"; }
    create_containerd_service() { printf "create_containerd_service\n" >>"${STUB_LOG}"; }
    create_docker_service() { printf "create_docker_service\n" >>"${STUB_LOG}"; }
    install_docker_linux
    status=$?
    printf "status=%s\n" "${status}"
    printf "curl_calls=%s\n" "$(cat "${TEST_TMP}/curl-count")"
    cat "${STUB_LOG}"
  ' bash "${functions_file}" >"${output_file}" 2>&1
  local status=$?
  set -e

  cat "${output_file}"
  printf "case_status=%s\n" "${status}"
}

for install_script in "${INSTALL_SCRIPTS[@]}"; do
  script_content=$(sed -n '1,$p' "${install_script}")
  assert_contains "${script_content}" "RAINBOND_AUTO_INSTALL_ORBSTACK=true bash ./install.sh"
  assert_not_contains "${script_content}" "curl -o install.sh https://get.rainbond.com && RAINBOND_AUTO_INSTALL_ORBSTACK=true bash ./install.sh"
  assert_not_contains "${script_content}" "--platform linux/amd64"
  assert_not_contains "${script_content}" 'docker pull ${RAINBOND_IMAGE_PLATFORM_ARGS} ${RBD_IMAGE}'

  start_output=$(run_orbstack_start_case "${install_script}")
  assert_contains "${start_output}" "status=0"
  assert_contains "${start_output}" "orb <no-args>"
  assert_contains "${start_output}" "docker info"

  install_output=$(run_orbstack_install_case "${install_script}")
  assert_contains "${install_output}" "status=0"
  assert_contains "${install_output}" "curl --fail --location"
  assert_contains "${install_output}" "-C -"
  assert_contains "${install_output}" "--progress-bar"
  assert_contains "${install_output}" "hdiutil attach"
  assert_contains "${install_output}" "ditto"
  assert_contains "${install_output}" "open"
  assert_contains "${install_output}" "docker info"
  assert_not_contains "${install_output}" "brew install --cask orbstack"

  brew_failure_output=$(run_orbstack_dmg_failure_brew_failure_case "${install_script}")
  assert_contains "${brew_failure_output}" "status=1"
  assert_contains "${brew_failure_output}" "curl --fail --location"
  assert_contains "${brew_failure_output}" "-C -"
  assert_contains "${brew_failure_output}" "--progress-bar"
  assert_contains "${brew_failure_output}" "Failed to download OrbStack installer"
  assert_contains "${brew_failure_output}" "Official OrbStack installer failed, trying Homebrew"
  assert_contains "${brew_failure_output}" "brew install --cask orbstack"
  assert_contains "${brew_failure_output}" "Homebrew cannot run on this macOS version"
  assert_not_contains "${brew_failure_output}" "macos_version.rb"

  resume_output=$(run_orbstack_download_resume_case "${install_script}")
  assert_contains "${resume_output}" "status=0"
  assert_contains "${resume_output}" "curl_calls=2"
  assert_contains "${resume_output}" "-C -"
  assert_contains "${resume_output}" "--max-time 1800"
  assert_contains "${resume_output}" "OrbStack installer download failed, retrying (1/2)"
  assert_contains "${resume_output}" "OrbStack installed to"

  download_output=$(run_download_retry_case "${install_script}")
  assert_contains "${download_output}" "status=0"
  assert_contains "${download_output}" "curl_calls=2"
  assert_contains "${download_output}" "Downloaded Docker binary is corrupted, retrying (1/2)"
  assert_not_contains "${download_output}" "Downloaded file is corrupted, please re-run the script"
done

printf 'PASS: install_rainbond_orbstack_download_test\n'
