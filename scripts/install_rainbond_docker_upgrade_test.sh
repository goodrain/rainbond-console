#!/usr/bin/env bash
# capability_id: script.install-rainbond.docker-old-version-upgrade
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

assert_line() {
  local haystack=$1
  local expected=$2
  if ! grep -Fxq -- "$expected" <<<"$haystack"; then
    fail "expected output line: ${expected}\noutput was:\n${haystack}"
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

extract_docker_version_functions() {
  local script=$1
  {
    grep -E '^DOCKER_(MIN|RECOMMENDED)_VERSION=' "${script}" || true
    grep -E '^DOCKER_UPGRADE_(BINARIES|REQUIRED_EXISTING_BINARIES)=' "${script}" || true
    awk '
      /^restore_previously_running_containers\(\)/ { capture = 1 }
      /^rollback_docker_upgrade\(\)/ { capture = 0 }
      capture { print }
    ' "${script}"
    awk '
      /^# Function to get the Docker daemon version/ { capture = 1 }
      /^set_cpu_mode\(\)/ { capture = 0 }
      capture { print }
    ' "${script}"
  }
}

extract_docker_bundle_upgrade_functions() {
  local script=$1
  {
    grep -E '^DOCKER_(RECOMMENDED_VERSION|UPGRADE_BINARIES)=' "${script}" || true
    awk '
      /^restore_docker_binaries\(\)/ { capture = 1 }
      /^# Function to install Docker on Linux/ { capture = 0 }
      capture { print }
    ' "${script}"
  }
}

write_docker_stub() {
  local path=$1
  local version=$2
  local marker=$3
  local docker_root=${4:-/var/lib/docker}
  {
    printf '%s\n' '#!/usr/bin/env bash'
    printf 'printf "%s docker %%s\\n" "$*" >>"${STUB_LOG}"\n' "${marker}"
    cat <<EOF
case "\${1:-}" in
  version)
    printf '%s\n' '${version}'
    ;;
  info)
    case "\$*" in
      *".DockerRootDir"*) printf '%s\n' '${docker_root}' ;;
      *".Driver"*) printf '%s\n' 'overlay2' ;;
      *) exit 0 ;;
    esac
    ;;
  inspect)
    if [ -f "\${STUB_LOG}.started.\${4:-}" ]; then
      printf 'true\n'
    else
      printf 'false\n'
    fi
    ;;
  ps)
    if [ "\${TEST_FAIL_SNAPSHOT:-false}" = "true" ]; then
      exit 1
    fi
    printf 'container-1\ncontainer-2\n'
    ;;
  start)
    touch "\${STUB_LOG}.started.\${2:-}"
    exit 0
    ;;
esac
EOF
  } >"${path}"
  chmod +x "${path}"
}

run_bundle_upgrade_case() {
  local fail_new_start=${1:-false}
  local changed_root=${2:-false}
  local new_version=${3:-28.3.1}
  local fail_stop=${4:-false}
  local fail_snapshot=${5:-false}
  local fail_rollback_stop=${6:-false}
  local tmp_dir bin_dir bundle_dir sys_bin functions_file output_file new_root
  tmp_dir=$(mktemp -d)
  bin_dir="${tmp_dir}/docker-bin"
  bundle_dir="${tmp_dir}/bundle"
  sys_bin="${tmp_dir}/system-bin"
  functions_file="${tmp_dir}/bundle-upgrade-functions.sh"
  output_file="${tmp_dir}/output"
  mkdir -p "${bin_dir}" "${bundle_dir}" "${sys_bin}"

  write_docker_stub "${bin_dir}/docker" "19.03.15" OLD
  write_docker_stub "${bundle_dir}/docker" "${new_version}" NEW "$([ "${changed_root}" = true ] && printf '/var/lib/docker-new' || printf '/var/lib/docker')"
  for binary in dockerd docker-init docker-proxy containerd containerd-shim-runc-v2 ctr runc; do
    printf 'OLD-%s\n' "${binary}" >"${bin_dir}/${binary}"
    printf 'NEW-%s\n' "${binary}" >"${bundle_dir}/${binary}"
    chmod +x "${bin_dir}/${binary}" "${bundle_dir}/${binary}"
  done

  write_stub "${sys_bin}" systemctl '
printf "systemctl %s\n" "$*" >>"${STUB_LOG}"
if [ "${1:-}" = "start" ] && [ "${2:-}" = "docker" ] && [ "${TEST_FAIL_NEW_START}" = "true" ] && grep -q "NEW" "${TEST_DOCKER_BIN_DIR}/docker"; then
  exit 1
fi
if [ "${1:-}" = "stop" ] && [ "${2:-}" = "docker" ] && [ "${TEST_FAIL_STOP}" = "true" ]; then
  exit 1
fi
if [ "${1:-}" = "stop" ] && [ "${2:-}" = "docker" ] && [ "${TEST_FAIL_ROLLBACK_STOP}" = "true" ] && grep -q "NEW" "${TEST_DOCKER_BIN_DIR}/docker"; then
  exit 1
fi
if [ "${1:-}" = "is-active" ]; then
  exit 3
fi
exit 0
'

  extract_docker_bundle_upgrade_functions "${INSTALL_SCRIPT}" >"${functions_file}"
  set +e
  PATH="${bin_dir}:${sys_bin}:/usr/bin:/bin" \
  STUB_LOG="${tmp_dir}/stub.log" \
  TEST_FAIL_NEW_START="${fail_new_start}" \
  TEST_FAIL_STOP="${fail_stop}" \
  TEST_FAIL_SNAPSHOT="${fail_snapshot}" \
  TEST_FAIL_ROLLBACK_STOP="${fail_rollback_stop}" \
  TEST_DOCKER_BIN_DIR="${bin_dir}" \
  RAINBOND_DOCKER_BIN_DIR="${bin_dir}" \
  RAINBOND_DOCKER_UPGRADE_BACKUP_ROOT="${tmp_dir}/backup" \
  bash -c '
    source "$1"
    rainbond_use_chinese_prompt() { return 1; }
    send_info() { printf "INFO: %s\n" "$*"; }
    send_warn() { printf "WARN: %s\n" "$*"; }
    send_error() { printf "ERROR: %s\n" "$*"; }
    get_docker_version() { docker version --format "{{.Server.Version}}" 2>/dev/null | head -n 1; }
    upgrade_docker_from_bundle "$2"
    status=$?
    printf "status=%s\n" "${status}"
    printf "installed_version=%s\n" "$(docker version --format "{{.Server.Version}}")"
    printf "dockerd_content=%s\n" "$(cat "${RAINBOND_DOCKER_BIN_DIR}/dockerd")"
    backup_dir=$(find "${RAINBOND_DOCKER_UPGRADE_BACKUP_ROOT}" -mindepth 1 -maxdepth 1 -type d | head -n 1)
    printf "backup_dockerd=%s\n" "$(cat "${backup_dir}/binaries/dockerd")"
    cat "${STUB_LOG}"
  ' bash "${functions_file}" "${bundle_dir}" >"${output_file}" 2>&1
  local command_status=$?
  set -e

  cat "${output_file}"
  printf 'case_status=%s\n' "${command_status}"
  rm -rf "${tmp_dir}"
}

run_package_upgrade_case() {
  local package_manager=${1:-apt}
  local upgraded_version=${2:-24.0.7}
  local package_failure=${3:-false}
  local changed_root=${4:-false}
  local exit_after_start=${5:-false}
  local tmp_dir bin_dir functions_file output_file
  tmp_dir=$(mktemp -d)
  bin_dir="${tmp_dir}/bin"
  functions_file="${tmp_dir}/docker-version-functions.sh"
  output_file="${tmp_dir}/output"
  mkdir -p "${bin_dir}"
  printf '19.03.15\n' >"${tmp_dir}/version"
  printf '19.03.15\n' >"${tmp_dir}/installed-version"

  write_stub "${bin_dir}" docker '
printf "docker %s\n" "$*" >>"${STUB_LOG}"
case "${1:-}" in
  version) cat "${TEST_VERSION_FILE}" ;;
  info)
    case "$*" in
      *".DockerRootDir"*)
        if [ "${TEST_CHANGED_ROOT}" = "true" ] && [ "$(cat "${TEST_VERSION_FILE}")" != "19.03.15" ]; then
          printf "/var/lib/docker-new\n"
        else
          printf "/var/lib/docker\n"
        fi
        ;;
      *".Driver"*) printf "overlay2\n" ;;
      *) exit 0 ;;
    esac
    ;;
  ps) printf "container-1\ncontainer-2\n" ;;
  inspect)
    if [ "${TEST_EXIT_AFTER_START}" != "true" ]; then
      printf "true\n"
    elif [ "${2:-}" = "container-1" ]; then
      printf "false\n"
    elif [ -f "${STUB_LOG}.started.${2:-}" ]; then
      printf "true\n"
    else
      printf "false\n"
    fi
    ;;
  start)
    touch "${STUB_LOG}.started.${2:-}"
    exit 0
    ;;
esac
'
  write_stub "${bin_dir}" apt-get '
printf "apt-get %s\n" "$*" >>"${STUB_LOG}"
if [ "${1:-}" = "install" ]; then
  [ "${TEST_PACKAGE_FAILURE}" != "true" ] || exit 1
  printf "%s\n" "${TEST_UPGRADED_VERSION}" >"${TEST_INSTALLED_VERSION_FILE}"
fi
'
  write_stub "${bin_dir}" dnf '
printf "dnf %s\n" "$*" >>"${STUB_LOG}"
if [ "${1:-}" = "upgrade" ]; then
  [ "${TEST_PACKAGE_FAILURE}" != "true" ] || exit 1
  printf "%s\n" "${TEST_UPGRADED_VERSION}" >"${TEST_INSTALLED_VERSION_FILE}"
fi
'
  write_stub "${bin_dir}" yum '
printf "yum %s\n" "$*" >>"${STUB_LOG}"
if [ "${1:-}" = "upgrade" ]; then
  [ "${TEST_PACKAGE_FAILURE}" != "true" ] || exit 1
  printf "%s\n" "${TEST_UPGRADED_VERSION}" >"${TEST_INSTALLED_VERSION_FILE}"
fi
'
  write_stub "${bin_dir}" dpkg-query '
if [ "${1:-}" = "-W" ]; then
  case "${@: -1}" in
    docker-ce-cli|containerd.io) printf "install ok installed\n" ;;
    *) exit 1 ;;
  esac
fi
'
  write_stub "${bin_dir}" rpm '
if [ "${1:-}" = "-q" ]; then
  case "${2:-}" in
    docker-ce-cli|containerd.io) exit 0 ;;
    *) exit 1 ;;
  esac
fi
'
  write_stub "${bin_dir}" systemctl '
printf "systemctl %s\n" "$*" >>"${STUB_LOG}"
if [ "${1:-}" = "restart" ] && [ "${2:-}" = "docker" ]; then
  cp "${TEST_INSTALLED_VERSION_FILE}" "${TEST_VERSION_FILE}"
fi
exit 0
'
  write_stub "${bin_dir}" service 'exit 0'

  extract_docker_version_functions "${INSTALL_SCRIPT}" >"${functions_file}"
  set +e
  PATH="${bin_dir}:/usr/bin:/bin" \
  STUB_LOG="${tmp_dir}/stub.log" \
  TEST_VERSION_FILE="${tmp_dir}/version" \
  TEST_INSTALLED_VERSION_FILE="${tmp_dir}/installed-version" \
  TEST_UPGRADED_VERSION="${upgraded_version}" \
  TEST_PACKAGE_FAILURE="${package_failure}" \
  TEST_CHANGED_ROOT="${changed_root}" \
  TEST_EXIT_AFTER_START="${exit_after_start}" \
  bash -c '
    source "$1"
    rainbond_use_chinese_prompt() { return 1; }
    send_info() { printf "INFO: %s\n" "$*"; }
    send_warn() { printf "WARN: %s\n" "$*"; }
    send_error() { printf "ERROR: %s\n" "$*"; }
    upgrade_docker_with_package_manager "$2" "$3"
    status=$?
    printf "status=%s\n" "${status}"
    printf "installed_version=%s\n" "$(get_docker_version)"
    cat "${STUB_LOG}"
    exit "${status}"
  ' bash "${functions_file}" "${package_manager}" docker-ce >"${output_file}" 2>&1
  local status=$?
  set -e

  cat "${output_file}"
  printf 'case_status=%s\n' "${status}"
  rm -rf "${tmp_dir}"
}

run_version_case() {
  local server_version=$1
  local upgrade_mode=$2
  local driver=${3:-overlay2}
  local swarm_state=${4:-inactive}
  local endpoint=${5:-unix:///var/run/docker.sock}
  local ctr_namespaces=${6:-moby}
  local unit_layout=${7:-standard}
  local security_options=${8:-[]}
  local active_service=${9:-none}
  local missing_unit=${10:-none}
  local package_manager=${11:-none}
  local package_name=${12:-docker.io}
  local docker_context=${13:-}
  local upgraded_version=${14:-28.3.1}
  local upgrade_failure=${15:-false}
  local package_owner_output=${16:-}
  local mixed_package_binary=${17:-none}
  local tmp_dir bin_dir functions_file output_file
  tmp_dir=$(mktemp -d)
  bin_dir="${tmp_dir}/bin"
  functions_file="${tmp_dir}/docker-version-functions.sh"
  output_file="${tmp_dir}/output"
  mkdir -p "${bin_dir}"

  write_stub "${bin_dir}" docker '
case "${1:-}" in
  version)
    printf "%s\n" "${TEST_DOCKER_SERVER_VERSION}"
    ;;
  context)
    printf "%s\n" "${TEST_DOCKER_ENDPOINT}"
    ;;
  info)
    case "$*" in
      *".DockerRootDir"*) printf "%s\n" "/var/lib/docker" ;;
      *".Driver"*) printf "%s\n" "${TEST_DOCKER_DRIVER}" ;;
      *".Swarm.LocalNodeState"*) printf "%s\n" "${TEST_DOCKER_SWARM_STATE}" ;;
      *".SecurityOptions"*) printf "%s\n" "${TEST_DOCKER_SECURITY_OPTIONS}" ;;
      *) exit 0 ;;
    esac
    ;;
  ps)
    case "$*" in
      *"{{.Names}}"*) printf "mysql\nnginx\n" ;;
      *"-q"*) printf "container-1\ncontainer-2\n" ;;
    esac
    ;;
esac
'
  write_stub "${bin_dir}" systemctl '
case "${1:-}" in
  cat)
    [ "${2:-}" != "${TEST_MISSING_UNIT}" ]
    exit $?
    ;;
  show)
    if [ "${TEST_UNIT_LAYOUT}" = "wrapper" ]; then
      if [ "$2" = "docker" ]; then
        printf "{ path=/opt/wrapper ; argv[]=/opt/wrapper %s/dockerd -H fd:// ; }\n" "${TEST_BIN_DIR}"
      else
        printf "{ path=/opt/wrapper ; argv[]=/opt/wrapper %s/containerd ; }\n" "${TEST_BIN_DIR}"
      fi
    elif [ "${TEST_UNIT_LAYOUT}" = "custom" ]; then
      printf "{ path=/opt/custom/%s ; argv[]=/opt/custom/%s ; }\n" "$2" "$2"
    elif [ "$2" = "docker" ]; then
      printf "{ path=%s/dockerd ; argv[]=%s/dockerd -H fd:// ; }\n" "${TEST_BIN_DIR}" "${TEST_BIN_DIR}"
    else
      printf "{ path=%s/containerd ; argv[]=%s/containerd ; }\n" "${TEST_BIN_DIR}" "${TEST_BIN_DIR}"
    fi
    ;;
  is-active)
    if [ "${3:-${2:-}}" = "docker" ] && [ "${TEST_PACKAGE_MANAGER}" != "none" ]; then
      exit 0
    fi
    [ "${3:-${2:-}}" = "${TEST_ACTIVE_SERVICE}" ]
    exit $?
    ;;
esac
exit 0
'
  write_stub "${bin_dir}" ctr '
if [ "${TEST_CTR_NAMESPACES}" = "ERROR" ]; then
  exit 1
fi
printf "%s\n" "${TEST_CTR_NAMESPACES}"
'
  write_stub "${bin_dir}" readlink '
if [ "${1:-}" = "-f" ]; then
  printf "%s\n" "$2"
else
  /usr/bin/readlink "$@"
fi
'
  write_stub "${bin_dir}" dpkg-query '
case "${1:-}" in
  -S)
    if [ "${TEST_MIXED_PACKAGE_BINARY}" != "none" ] && [ "${2:-}" = "${TEST_BIN_DIR}/${TEST_MIXED_PACKAGE_BINARY}" ]; then
      printf "containerd: %s\n" "${2:-}"
    elif [ "${TEST_PACKAGE_MANAGER}" != "apt" ]; then
      exit 1
    elif [ -n "${TEST_PACKAGE_OWNER_OUTPUT}" ]; then
      printf "%s\n" "${TEST_PACKAGE_OWNER_OUTPUT}"
    else
      printf "%s: %s\n" "${TEST_PACKAGE_NAME}" "${2:-}"
    fi
    ;;
  -W)
    printf "install ok installed\n"
    ;;
esac
'
  write_stub "${bin_dir}" rpm '
if [ "${TEST_PACKAGE_MANAGER}" != "dnf" ] && [ "${TEST_PACKAGE_MANAGER}" != "yum" ]; then
  exit 1
fi
case "${1:-}" in
  -qf)
    printf "%s\n" "${TEST_PACKAGE_NAME}"
    ;;
esac
'
  write_stub "${bin_dir}" apt-get 'exit 0'
  write_stub "${bin_dir}" apt-cache 'printf "  Candidate: 24.0.7-test\n"'
  write_stub "${bin_dir}" dnf 'exit 0'
  write_stub "${bin_dir}" yum 'exit 0'
  for binary in dockerd containerd containerd-shim-runc-v2 runc docker-init docker-proxy; do
    write_stub "${bin_dir}" "${binary}" 'exit 0'
  done

  extract_docker_version_functions "${INSTALL_SCRIPT}" >"${functions_file}"
  set +e
  PATH="${bin_dir}:/usr/bin:/bin" \
  TEST_DOCKER_SERVER_VERSION="${server_version}" \
  TEST_DOCKER_DRIVER="${driver}" \
  TEST_DOCKER_SWARM_STATE="${swarm_state}" \
  TEST_DOCKER_ENDPOINT="${endpoint}" \
  TEST_CTR_NAMESPACES="${ctr_namespaces}" \
  TEST_UNIT_LAYOUT="${unit_layout}" \
  TEST_DOCKER_SECURITY_OPTIONS="${security_options}" \
  TEST_ACTIVE_SERVICE="${active_service}" \
  TEST_MISSING_UNIT="${missing_unit}" \
  TEST_PACKAGE_MANAGER="${package_manager}" \
  TEST_PACKAGE_NAME="${package_name}" \
  TEST_PACKAGE_OWNER_OUTPUT="${package_owner_output//PLACEHOLDER/${bin_dir}\/dockerd}" \
  TEST_MIXED_PACKAGE_BINARY="${mixed_package_binary}" \
  DOCKER_CONTEXT="${docker_context}" \
  TEST_BIN_DIR="${bin_dir}" \
  TEST_DOCKER_UPGRADED_VERSION="${upgraded_version}" \
  TEST_DOCKER_UPGRADE_FAILURE="${upgrade_failure}" \
  RAINBOND_DOCKER_UPGRADE="${upgrade_mode}" \
  bash -c '
    source "$1"
    rainbond_use_chinese_prompt() { return 1; }
    rainbond_tty_available() { return 1; }
    send_info() { printf "INFO: %s\n" "$*"; }
    send_warn() { printf "WARN: %s\n" "$*"; }
    send_error() { printf "ERROR: %s\n" "$*"; }
    upgrade_docker_with_package_manager() {
      printf "PACKAGE_UPGRADE manager=%s package=%s\n" "$1" "$2"
      [ "${TEST_DOCKER_UPGRADE_FAILURE}" != "true" ] || return 1
      TEST_DOCKER_SERVER_VERSION="${TEST_DOCKER_UPGRADED_VERSION}"
      export TEST_DOCKER_SERVER_VERSION
    }
    install_docker_linux() {
      printf "STATIC_UPGRADE target=%s mode=%s\n" "${DOCKER_RECOMMENDED_VERSION}" "$1"
      [ "${TEST_DOCKER_UPGRADE_FAILURE}" != "true" ] || return 1
      TEST_DOCKER_SERVER_VERSION="${TEST_DOCKER_UPGRADED_VERSION}"
      export TEST_DOCKER_SERVER_VERSION
    }
    ensure_docker_version_linux
  ' bash "${functions_file}" >"${output_file}" 2>&1
  local status=$?
  set -e

  cat "${output_file}"
  printf 'case_status=%s\n' "${status}"
  rm -rf "${tmp_dir}"
}

script_content=$(sed -n '1,$p' "${INSTALL_SCRIPT}")
assert_contains "${script_content}" 'DOCKER_RECOMMENDED_VERSION="28.3.1"'
assert_contains "${script_content}" 'docker version --format'
assert_contains "${script_content}" 'read -r answer </dev/tty'

supported_output=$(run_version_case "20.10.24" auto)
assert_contains "${supported_output}" "case_status=0"
assert_not_contains "${supported_output}" "UPGRADE_CALLED"

upgrade_output=$(run_version_case "19.03.15" auto)
assert_contains "${upgrade_output}" "case_status=0"
assert_contains "${upgrade_output}" "STATIC_UPGRADE target=28.3.1 mode=upgrade"
assert_contains "${upgrade_output}" "19.03.15"
assert_contains "${upgrade_output}" "28.3.1"

decline_output=$(run_version_case "19.03.15" never)
assert_contains "${decline_output}" "case_status=1"
assert_not_contains "${decline_output}" "STATIC_UPGRADE"

driver_output=$(run_version_case "19.03.15" auto devicemapper)
assert_contains "${driver_output}" "case_status=1"
assert_contains "${driver_output}" "devicemapper"
assert_not_contains "${driver_output}" "STATIC_UPGRADE"

swarm_output=$(run_version_case "19.03.15" auto overlay2 active)
assert_contains "${swarm_output}" "case_status=1"
assert_contains "${swarm_output}" "Swarm"
assert_not_contains "${swarm_output}" "STATIC_UPGRADE"

bundle_output=$(run_bundle_upgrade_case false false)
assert_contains "${bundle_output}" "status=0"
assert_contains "${bundle_output}" "installed_version=28.3.1"
assert_contains "${bundle_output}" "dockerd_content=NEW-dockerd"
assert_contains "${bundle_output}" "backup_dockerd=OLD-dockerd"
assert_contains "${bundle_output}" "NEW docker start container-1"
assert_contains "${bundle_output}" "NEW docker start container-2"

rollback_output=$(run_bundle_upgrade_case true false)
assert_contains "${rollback_output}" "status=1"
assert_contains "${rollback_output}" "installed_version=19.03.15"
assert_contains "${rollback_output}" "dockerd_content=OLD-dockerd"
assert_contains "${rollback_output}" "backup_dockerd=OLD-dockerd"
assert_contains "${rollback_output}" "Docker 19.03.15 was restored"

root_mismatch_output=$(run_bundle_upgrade_case false true)
assert_contains "${root_mismatch_output}" "status=1"
assert_contains "${root_mismatch_output}" "installed_version=19.03.15"
assert_contains "${root_mismatch_output}" "dockerd_content=OLD-dockerd"
assert_contains "${root_mismatch_output}" "Docker 19.03.15 was restored"

wrong_version_output=$(run_bundle_upgrade_case false false 20.10.24)
assert_contains "${wrong_version_output}" "status=1"
assert_contains "${wrong_version_output}" "installed_version=19.03.15"
assert_contains "${wrong_version_output}" "dockerd_content=OLD-dockerd"
assert_contains "${wrong_version_output}" "Docker 19.03.15 was restored"

rollback_stop_failure_output=$(run_bundle_upgrade_case true false 28.3.1 false false true)
assert_contains "${rollback_stop_failure_output}" "status=1"
assert_contains "${rollback_stop_failure_output}" "installed_version=28.3.1"
assert_contains "${rollback_stop_failure_output}" "dockerd_content=NEW-dockerd"
assert_contains "${rollback_stop_failure_output}" "No files were overwritten during rollback"

stop_failure_output=$(run_bundle_upgrade_case false false 28.3.1 true)
assert_contains "${stop_failure_output}" "status=1"
assert_contains "${stop_failure_output}" "installed_version=19.03.15"
assert_contains "${stop_failure_output}" "dockerd_content=OLD-dockerd"
assert_contains "${stop_failure_output}" "no upgrade was performed"

snapshot_failure_output=$(run_bundle_upgrade_case false false 28.3.1 false true)
assert_contains "${snapshot_failure_output}" "status=1"
assert_contains "${snapshot_failure_output}" "dockerd_content=OLD-dockerd"
assert_contains "${snapshot_failure_output}" "runtime state could not be read"
assert_not_contains "${snapshot_failure_output}" "systemctl stop"

remote_output=$(run_version_case "19.03.15" auto overlay2 inactive tcp://192.0.2.10:2375)
assert_contains "${remote_output}" "case_status=1"
assert_contains "${remote_output}" "endpoint"
assert_not_contains "${remote_output}" "STATIC_UPGRADE"

shared_containerd_output=$(run_version_case "19.03.15" auto overlay2 inactive unix:///var/run/docker.sock k8s.io)
assert_contains "${shared_containerd_output}" "case_status=1"
assert_contains "${shared_containerd_output}" "k8s.io"
assert_not_contains "${shared_containerd_output}" "STATIC_UPGRADE"

ctr_failure_output=$(run_version_case "19.03.15" auto overlay2 inactive unix:///var/run/docker.sock ERROR)
assert_contains "${ctr_failure_output}" "case_status=1"
assert_contains "${ctr_failure_output}" "could not determine whether containerd is shared"
assert_not_contains "${ctr_failure_output}" "STATIC_UPGRADE"

custom_unit_output=$(run_version_case "19.03.15" auto overlay2 inactive unix:///var/run/docker.sock moby custom)
assert_contains "${custom_unit_output}" "case_status=1"
assert_contains "${custom_unit_output}" "ExecStart"
assert_not_contains "${custom_unit_output}" "STATIC_UPGRADE"

wrapper_unit_output=$(run_version_case "19.03.15" auto overlay2 inactive unix:///var/run/docker.sock moby wrapper)
assert_contains "${wrapper_unit_output}" "case_status=1"
assert_contains "${wrapper_unit_output}" "ExecStart"
assert_not_contains "${wrapper_unit_output}" "STATIC_UPGRADE"

rootless_output=$(run_version_case "19.03.15" auto overlay2 inactive unix:///var/run/docker.sock moby standard '["name=rootless"]')
assert_contains "${rootless_output}" "case_status=1"
assert_contains "${rootless_output}" "Rootless"
assert_not_contains "${rootless_output}" "STATIC_UPGRADE"

kubernetes_output=$(run_version_case "19.03.15" auto overlay2 inactive unix:///var/run/docker.sock moby standard '[]' kubelet)
assert_contains "${kubernetes_output}" "case_status=1"
assert_contains "${kubernetes_output}" "kubelet"
assert_not_contains "${kubernetes_output}" "STATIC_UPGRADE"

nomad_output=$(run_version_case "19.03.15" auto overlay2 inactive unix:///var/run/docker.sock moby standard '[]' nomad)
assert_contains "${nomad_output}" "case_status=1"
assert_contains "${nomad_output}" "nomad"
assert_not_contains "${nomad_output}" "STATIC_UPGRADE"

missing_socket_output=$(run_version_case "19.03.15" auto overlay2 inactive unix:///var/run/docker.sock moby standard '[]' none docker.socket)
assert_contains "${missing_socket_output}" "case_status=1"
assert_contains "${missing_socket_output}" "docker.socket"
assert_not_contains "${missing_socket_output}" "STATIC_UPGRADE"

mixed_static_output=$(run_version_case "19.03.15" auto overlay2 inactive unix:///var/run/docker.sock moby standard '[]' none none none docker.io '' 28.3.1 false '' containerd)
assert_contains "${mixed_static_output}" "case_status=1"
assert_contains "${mixed_static_output}" "package-managed files"
assert_not_contains "${mixed_static_output}" "STATIC_UPGRADE"

package_managed_output=$(run_version_case "19.03.15" auto overlay2 inactive unix:///var/run/docker.sock moby standard '[]' none docker.socket apt docker.io '' 24.0.7)
assert_contains "${package_managed_output}" "case_status=0"
assert_contains "${package_managed_output}" "PACKAGE_UPGRADE manager=apt package=docker.io"
assert_contains "${package_managed_output}" "original apt repository"
assert_contains "${package_managed_output}" "minimum 20.0.0"
assert_not_contains "${package_managed_output}" "STATIC_UPGRADE"

package_ctr_failure_output=$(run_version_case "19.03.15" auto overlay2 inactive unix:///var/run/docker.sock ERROR standard '[]' none none apt docker.io '' 24.0.7)
assert_contains "${package_ctr_failure_output}" "case_status=0"
assert_contains "${package_ctr_failure_output}" "could not be enumerated with ctr"
assert_contains "${package_ctr_failure_output}" "PACKAGE_UPGRADE manager=apt package=docker.io"

package_wrapper_output=$(run_version_case "19.03.15" auto overlay2 inactive unix:///var/run/docker.sock moby wrapper '[]' none none apt docker.io '' 24.0.7)
assert_contains "${package_wrapper_output}" "case_status=1"
assert_contains "${package_wrapper_output}" "ExecStart"
assert_not_contains "${package_wrapper_output}" "PACKAGE_UPGRADE"

dnf_managed_output=$(run_version_case "19.03.15" auto overlay2 inactive unix:///var/run/docker.sock moby standard '[]' none none dnf docker-ce '' 26.1.4)
assert_contains "${dnf_managed_output}" "case_status=0"
assert_contains "${dnf_managed_output}" "PACKAGE_UPGRADE manager=dnf package=docker-ce"
assert_contains "${dnf_managed_output}" "original dnf repository"
assert_not_contains "${dnf_managed_output}" "STATIC_UPGRADE"

package_too_old_output=$(run_version_case "19.03.15" auto overlay2 inactive unix:///var/run/docker.sock moby standard '[]' none none apt docker.io '' 19.03.15)
assert_contains "${package_too_old_output}" "case_status=1"
assert_contains "${package_too_old_output}" "PACKAGE_UPGRADE manager=apt package=docker.io"
assert_contains "${package_too_old_output}" "version verification failed"

package_failure_output=$(run_version_case "19.03.15" auto overlay2 inactive unix:///var/run/docker.sock moby standard '[]' none none apt docker.io '' 24.0.7 true)
assert_contains "${package_failure_output}" "case_status=1"
assert_contains "${package_failure_output}" "PACKAGE_UPGRADE manager=apt package=docker.io"

malicious_package_output=$(run_version_case "19.03.15" auto overlay2 inactive unix:///var/run/docker.sock moby standard '[]' none none apt docker.io '' 24.0.7 false 'docker.io;touch /tmp/pwned: PLACEHOLDER')
assert_contains "${malicious_package_output}" "case_status=1"
assert_contains "${malicious_package_output}" "could not be identified"
assert_not_contains "${malicious_package_output}" "PACKAGE_UPGRADE"

apt_upgrade_output=$(run_package_upgrade_case apt 24.0.7)
assert_line "${apt_upgrade_output}" "status=0"
assert_line "${apt_upgrade_output}" "case_status=0"
assert_contains "${apt_upgrade_output}" "installed_version=24.0.7"
assert_contains "${apt_upgrade_output}" "apt-get update"
assert_contains "${apt_upgrade_output}" "apt-get install"
assert_contains "${apt_upgrade_output}" "docker-ce"
assert_not_contains "${apt_upgrade_output}" "docker-ce-cli"
assert_not_contains "${apt_upgrade_output}" "containerd.io"
assert_contains "${apt_upgrade_output}" "systemctl restart docker"

dnf_upgrade_output=$(run_package_upgrade_case dnf 26.1.4)
assert_line "${dnf_upgrade_output}" "status=0"
assert_line "${dnf_upgrade_output}" "case_status=0"
assert_contains "${dnf_upgrade_output}" "installed_version=26.1.4"
assert_contains "${dnf_upgrade_output}" "dnf upgrade"

package_command_failure_output=$(run_package_upgrade_case apt 24.0.7 true)
assert_line "${package_command_failure_output}" "status=1"
assert_line "${package_command_failure_output}" "case_status=1"
assert_contains "${package_command_failure_output}" "installed_version=19.03.15"
assert_contains "${package_command_failure_output}" "package-manager upgrade failed"
assert_contains "${package_command_failure_output}" "docker inspect --format {{.State.Running}} container-1"
assert_contains "${package_command_failure_output}" "docker inspect --format {{.State.Running}} container-2"

package_still_old_output=$(run_package_upgrade_case apt 19.03.15)
assert_line "${package_still_old_output}" "status=1"
assert_line "${package_still_old_output}" "case_status=1"
assert_contains "${package_still_old_output}" "version verification failed"
assert_contains "${package_still_old_output}" "docker inspect --format {{.State.Running}} container-1"
assert_contains "${package_still_old_output}" "docker inspect --format {{.State.Running}} container-2"

package_root_mismatch_output=$(run_package_upgrade_case apt 24.0.7 false true)
assert_line "${package_root_mismatch_output}" "status=1"
assert_line "${package_root_mismatch_output}" "case_status=1"
assert_contains "${package_root_mismatch_output}" "root directory or storage driver changed"

container_exit_output=$(run_package_upgrade_case apt 24.0.7 false false true)
assert_line "${container_exit_output}" "status=1"
assert_line "${container_exit_output}" "case_status=1"
assert_contains "${container_exit_output}" "some previously running containers could not be restored"
assert_contains "${container_exit_output}" "docker start container-1"
assert_contains "${container_exit_output}" "docker start container-2"

remote_context_output=$(run_version_case "19.03.15" auto overlay2 inactive unix:///var/run/docker.sock moby standard '[]' none none none docker.io remote)
assert_contains "${remote_context_output}" "case_status=1"
assert_contains "${remote_context_output}" "DOCKER_CONTEXT=remote"
assert_not_contains "${remote_context_output}" "STATIC_UPGRADE"

supported_suffix_output=$(run_version_case "20.10.24+dfsg1" auto)
assert_contains "${supported_suffix_output}" "case_status=0"
assert_not_contains "${supported_suffix_output}" "STATIC_UPGRADE"

prerelease_output=$(run_version_case "20.0.0-rc1" never)
assert_contains "${prerelease_output}" "case_status=1"
assert_contains "${prerelease_output}" "20.0.0-rc1"

printf 'PASS: install_rainbond_docker_upgrade_test\n'
