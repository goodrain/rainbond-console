#!/usr/bin/env bash
# capability_id: script.install-rainbond.operator-log-collect
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

assert_file_missing_or_empty() {
  local file=$1
  if [ -s "$file" ]; then
    fail "expected ${file} to be empty, got:\n$(cat "$file")"
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

extract_log_collect_functions() {
  awk '
    /^function rainbond_json_escape\(\) \{/ { capture = 1 }
    /^function docker_network_repair_message\(\) \{/ { capture = 0 }
    capture { print }
  ' "${INSTALL_SCRIPT}"
}

tmp_dir=$(mktemp -d)
bin_dir="${tmp_dir}/bin"
functions_file="${tmp_dir}/log-collect-functions.sh"
payload_file="${tmp_dir}/payload.json"
url_file="${tmp_dir}/url.txt"
mkdir -p "$bin_dir"

write_stub "$bin_dir" curl '
while [ "$#" -gt 0 ]; do
  case "$1" in
    -d)
      shift
      printf "%s" "${1:-}" >"${CURL_PAYLOAD_FILE}"
      ;;
    http*)
      printf "%s" "$1" >"${CURL_URL_FILE}"
      ;;
  esac
  shift || break
done
exit 0
'

extract_log_collect_functions >"$functions_file"

PATH="${bin_dir}:/usr/bin:/bin" \
CURL_PAYLOAD_FILE="$payload_file" \
CURL_URL_FILE="$url_file" \
bash -c '
  set -euo pipefail
  source "$1"

  rainbond_diag_kubectl() {
    case "$*" in
      "get namespace kube-system -o jsonpath={.metadata.uid}")
        printf "kube-uid-1"
        ;;
      "get pod -n rbd-system --no-headers")
        if [ "${OPERATOR_READY:-false}" = "true" ]; then
          printf "rainbond-operator-abc 1/1 Running 0 10m\n"
        else
          printf "rainbond-operator-abc 0/1 ImagePullBackOff 0 10m\n"
        fi
        ;;
      "get pod rainbond-operator-abc -n rbd-system -o jsonpath={range .status.containerStatuses[*]}{.state.waiting.reason}{\" \"}{.lastState.terminated.reason}{\" \"}{end}")
        printf "ImagePullBackOff "
        ;;
      "describe pod rainbond-operator-abc -n rbd-system")
        printf "Warning Failed Failed to pull image registry.example/rainbond-operator:test\n"
        ;;
      "logs rainbond-operator-abc -n rbd-system --all-containers --tail=80")
        printf "container is waiting to start: ImagePullBackOff\n"
        ;;
      "get nodes --no-headers")
        printf "node1 Ready control-plane 1h v1.30.4+k3s1\n"
        ;;
      *)
        return 1
        ;;
    esac
  }

  OS_TYPE=Linux \
  ARCH_TYPE=amd64 \
  RAINBOND_VERSION=v6.9.3-dev \
  EIP=192.0.2.10 \
  RAINBOND_INSTALL_METHOD=single_node \
  RAINBOND_LOG_COLLECT_URL=https://log.rainbond.com/logCollect \
  rainbond_send_operator_log_collect "{\"root_cause_code\":\"image_pull_failed\"}" 600
' bash "$functions_file"

payload=$(cat "$payload_file")
url=$(cat "$url_file")
if command -v sha256sum >/dev/null 2>&1; then
  expected_eid=$(printf 'kube-uid-1' | sha256sum | awk '{print $1}' | cut -c 1-32)
else
  expected_eid=$(printf 'kube-uid-1' | shasum -a 256 | awk '{print $1}' | cut -c 1-32)
fi

assert_contains "$url" "https://log.rainbond.com/logCollect"
assert_contains "$payload" "\"eid\":\"${expected_eid}\""
assert_contains "$payload" "\"enable_cluster\":\"standalone\""
assert_contains "$payload" "\"status\":\"RegionFailed-operator_not_ready\""
assert_contains "$payload" "\"name\":\"rainbond-operator-abc\""
assert_contains "$payload" "ImagePullBackOff"
assert_contains "$payload" "rainbond-operator did not become ready before timeout (600s)"

: >"$payload_file"
: >"$url_file"

PATH="${bin_dir}:/usr/bin:/bin" \
CURL_PAYLOAD_FILE="$payload_file" \
CURL_URL_FILE="$url_file" \
OPERATOR_READY=true \
bash -c '
  set -euo pipefail
  source "$1"

  rainbond_diag_kubectl() {
    case "$*" in
      "get pod -n rbd-system --no-headers")
        printf "rainbond-operator-abc 1/1 Running 0 10m\n"
        ;;
      *)
        printf "unused"
        ;;
    esac
  }

  UUID=fallback-eid rainbond_send_operator_log_collect "{\"root_cause_code\":\"image_pull_failed\"}" 600
' bash "$functions_file"

assert_file_missing_or_empty "$payload_file"
assert_file_missing_or_empty "$url_file"

printf 'PASS: install_rainbond_operator_log_collect_test\n'
