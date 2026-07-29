#!/usr/bin/env bash
# capability_id: script.install-rainbond.gpu-auto-detection
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
  if ! printf '%s' "$haystack" | grep -Fq -- "$needle"; then
    fail "expected output to contain: ${needle}\noutput was:\n${haystack}"
  fi
}

assert_not_contains() {
  local haystack=$1
  local needle=$2
  if printf '%s' "$haystack" | grep -Fq -- "$needle"; then
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

extract_gpu_functions() {
  awk '
    /^set_cpu_mode\(\) \{/ { capture = 1 }
    /^# Main Docker management function/ { capture = 0 }
    capture { print }
  ' "${INSTALL_SCRIPT}"
}

run_gpu_case() {
  local setup_name=$1
  local tmp_dir
  tmp_dir=$(mktemp -d)
  local bin_dir="${tmp_dir}/bin"
  local functions_file="${tmp_dir}/gpu-functions.sh"
  local output_file="${tmp_dir}/output"
  mkdir -p "${bin_dir}"

  write_stub "${bin_dir}" docker '
printf "docker %s\n" "$*" >>"${STUB_LOG}"
if [ "${1:-}" = "run" ]; then
  if [ -f "${TEST_TMP}/docker-gpu-ready" ]; then
    exit 0
  fi
  exit "${DOCKER_RUN_STATUS:-0}"
fi
exit 0
'
  write_stub "${bin_dir}" systemctl '
printf "systemctl %s\n" "$*" >>"${STUB_LOG}"
exit 0
'
  write_stub "${bin_dir}" service '
printf "service %s\n" "$*" >>"${STUB_LOG}"
exit 0
'
  write_stub "${bin_dir}" modprobe '
printf "modprobe %s\n" "$*" >>"${STUB_LOG}"
exit 0
'
  write_stub "${bin_dir}" sleep 'exit 0'

  case "${setup_name}" in
    driver-missing)
      write_stub "${bin_dir}" lspci '
printf "lspci %s\n" "$*" >>"${STUB_LOG}"
printf "03:00.0 VGA compatible controller: NVIDIA Corporation Device 2684\n"
'
      write_stub "${bin_dir}" apt-get '
printf "apt-get %s\n" "$*" >>"${STUB_LOG}"
exit 0
'
      ;;
    driver-fails)
      write_stub "${bin_dir}" lspci '
printf "lspci %s\n" "$*" >>"${STUB_LOG}"
printf "03:00.0 VGA compatible controller: NVIDIA Corporation Device 2684\n"
'
      write_stub "${bin_dir}" nvidia-smi '
printf "nvidia-smi %s\n" "$*" >>"${STUB_LOG}"
exit 1
'
      write_stub "${bin_dir}" apt-get '
printf "apt-get %s\n" "$*" >>"${STUB_LOG}"
exit 0
'
      ;;
    driver-ready)
      write_stub "${bin_dir}" lspci '
printf "lspci %s\n" "$*" >>"${STUB_LOG}"
printf "03:00.0 VGA compatible controller: NVIDIA Corporation Device 2684\n"
'
      write_stub "${bin_dir}" nvidia-smi '
printf "nvidia-smi %s\n" "$*" >>"${STUB_LOG}"
printf "NVIDIA-SMI test output\n"
'
      write_stub "${bin_dir}" nvidia-ctk '
printf "nvidia-ctk %s\n" "$*" >>"${STUB_LOG}"
touch "${TEST_TMP}/docker-gpu-ready"
exit 0
'
      ;;
    *)
      fail "unknown setup: ${setup_name}"
      ;;
  esac

  extract_gpu_functions >"${functions_file}"
  set +e
  STUB_LOG="${tmp_dir}/stub.log" \
  TEST_TMP="${tmp_dir}" \
  TEST_BIN="${bin_dir}" \
  PATH="${bin_dir}:/usr/bin:/bin" \
  LANG=C \
  OS_TYPE=Linux \
  ENABLE_GPU=true \
  DOCKER_RUN_STATUS=0 \
  bash -c '
    set +e
    source "$1"
    rainbond_use_chinese_prompt() { return 1; }
    send_msg() { :; }
    send_info() { printf "INFO: %s\n" "$*" >>"${STUB_LOG}"; }
    send_warn() { printf "WARN: %s\n" "$*" >>"${STUB_LOG}"; }
    send_error() { printf "ERROR: %s\n" "$*" >>"${STUB_LOG}"; }
    if [ "$2" = "driver-ready" ]; then
      export DOCKER_RUN_STATUS=1
    fi
    validate_gpu_support_linux
    status=$?
    printf "status=%s\n" "${status}"
    printf "ENABLE_GPU=%s\n" "${ENABLE_GPU:-}"
    printf "GPU_DOCKER_ARGS=%s\n" "${GPU_DOCKER_ARGS:-}"
    printf "GPU_ENV_ARGS=%s\n" "${GPU_ENV_ARGS:-}"
    if declare -F build_docker_run_cmd >/dev/null 2>&1; then
      VOLUME_OPTS="-v /opt/rainbond:/opt/rainbond"
      EIP="192.0.2.10"
      UUID="test-uuid"
      RBD_IMAGE="registry.example/rainbond:test"
      build_docker_run_cmd
      printf "docker_run_cmd=%s\n" "${docker_run_cmd}"
    fi
    printf "%s\n" "--- log ---"
    if [ -f "${STUB_LOG}" ]; then
      cat "${STUB_LOG}"
    fi
  ' bash "${functions_file}" "${setup_name}" >"${output_file}" 2>&1
  local case_status=$?
  set -e

  cat "${output_file}"
  printf "case_status=%s\n" "${case_status}"
}

missing_driver_output=$(run_gpu_case driver-missing)
assert_contains "${missing_driver_output}" "status=0"
assert_contains "${missing_driver_output}" "ENABLE_GPU=false"
assert_contains "${missing_driver_output}" "GPU_DOCKER_ARGS="
assert_not_contains "${missing_driver_output}" "--gpus all"
assert_contains "${missing_driver_output}" "docker_run_cmd=docker run"
assert_not_contains "${missing_driver_output}" "docker_run_cmd=docker run --privileged -d --gpus all"
assert_not_contains "${missing_driver_output}" "lspci"
assert_not_contains "${missing_driver_output}" "apt-get"
assert_not_contains "${missing_driver_output}" "docker run --rm --gpus all"

failed_driver_output=$(run_gpu_case driver-fails)
assert_contains "${failed_driver_output}" "status=0"
assert_contains "${failed_driver_output}" "ENABLE_GPU=false"
assert_contains "${failed_driver_output}" "GPU_DOCKER_ARGS="
assert_not_contains "${failed_driver_output}" "--gpus all"
assert_not_contains "${failed_driver_output}" "lspci"
assert_not_contains "${failed_driver_output}" "apt-get"
assert_not_contains "${failed_driver_output}" "docker run --rm --gpus all"

ready_driver_output=$(run_gpu_case driver-ready)
assert_contains "${ready_driver_output}" "status=0"
assert_contains "${ready_driver_output}" "ENABLE_GPU=true"
assert_contains "${ready_driver_output}" "GPU_DOCKER_ARGS=--gpus all"
assert_contains "${ready_driver_output}" "docker_run_cmd=docker run --privileged -d --gpus all"
assert_not_contains "${ready_driver_output}" "lspci"
assert_not_contains "${ready_driver_output}" "apt-get"
assert_not_contains "${ready_driver_output}" "nvidia-ctk"
assert_not_contains "${ready_driver_output}" "systemctl restart docker"
assert_not_contains "${ready_driver_output}" "docker run --rm --gpus all"

printf 'PASS: install_rainbond_gpu_detection_test\n'
