#!/bin/bash

# This script is used to install Rainbond standalone on Linux and MacOS

# Basic environment variables
RAINBOND_VERSION=${VERSION:-'v6.9.4-release'}
IMGHUB_MIRROR=${IMGHUB_MIRROR:-'registry.cn-hangzhou.aliyuncs.com/goodrain'}
ENABLE_GPU=${ENABLE_GPU:-auto}
DOCKER_MIN_VERSION="20.0.0"
DOCKER_RECOMMENDED_VERSION="28.3.1"
DOCKER_INSTALL_SHA256_AMD64="ac80f9cdec0a465ad180236127a6a23fc7dc88d2f006c74615bad55ddb515739"
DOCKER_INSTALL_SHA256_ARM64="056e8d5d764866add932396441a063e67abb51c3ce11e258a9fa5062e52c6e89"
DOCKER_UPGRADE_BINARIES="docker dockerd containerd containerd-shim-runc-v2 ctr runc docker-init docker-proxy"
DOCKER_UPGRADE_REQUIRED_EXISTING_BINARIES="docker dockerd containerd ctr runc docker-init docker-proxy"

# Define colorful stdout
RED='\033[0;31m'
GREEN='\033[32;1m'
YELLOW='\033[33;1m'
NC='\033[0m'
TIME="+%Y-%m-%d %H:%M:%S"
INSTALL_ATTEMPT_ID=${INSTALL_ATTEMPT_ID:-"single-$(date +%Y%m%d%H%M%S)-$$"}
RAINBOND_INSTALL_METHOD=${RAINBOND_INSTALL_METHOD:-"single_node"}
RAINBOND_FINAL_EVENT_ENABLED=false
RAINBOND_FINAL_STATUS_SENT=false

function rainbond_use_chinese_prompt() {
    case "${RAINBOND_INSTALL_LANG:-zh}" in
        en | en_US | en-US | en_US.UTF-8 | en-US.UTF-8 | english | English | EN)
            return 1
            ;;
        *)
            return 0
            ;;
    esac
}

########################################
# Information collection
# Automatically collect the install details.
# Help us improve the success rate of installation.
########################################

# Rainbond startup diagnostics
# Collects a compact snapshot when the installer times out waiting for services.
function rainbond_json_escape() {
    printf '%s' "${1:-}" | awk '
        BEGIN { ORS = "" }
        {
            gsub(/\\/,"\\\\")
            gsub(/"/,"\\\"")
            gsub(/\t/,"\\t")
            gsub(/\r/,"\\r")
            if (NR > 1) {
                printf "\\n"
            }
            printf "%s", $0
        }
    '
}

function rainbond_diag_kubectl() {
    if [ -n "${RAINBOND_DIAG_KUBECTL:-}" ]; then
        "$RAINBOND_DIAG_KUBECTL" "$@"
    else
        docker exec rainbond /bin/k3s kubectl "$@"
    fi
}

function rainbond_diag_compact() {
    printf '%s' "${1:-}" | tr '\r\n' '  ' | sed 's/[[:space:]][[:space:]]*/ /g' | cut -c 1-500
}

function rainbond_diag_append_json_string() {
    local current="${1:-}"
    local value
    value=$(rainbond_json_escape "$(rainbond_diag_compact "${2:-}")")
    if [ -n "$current" ]; then
        printf '%s,"%s"' "$current" "$value"
    else
        printf '"%s"' "$value"
    fi
}

function rainbond_classify_timeout_reason() {
    local raw="${1:-}"

    if printf '%s' "$raw" | grep -Eqi 'unbound immediate PersistentVolumeClaims|PersistentVolumeClaim|FailedMount|MountVolume|storageclass|provisioner|PVC|Pending.*local-path'; then
        printf 'storage_pvc_pending'
    elif printf '%s' "$raw" | grep -Eqi 'NodeNotReady|Node is not ready|NotReady'; then
        printf 'node_not_ready'
    elif printf '%s' "$raw" | grep -Eqi 'ImagePullBackOff|ErrImagePull|pull image|failed to pull'; then
        printf 'image_pull_failed'
    elif printf '%s' "$raw" | grep -Eqi 'CrashLoopBackOff|Back-off restarting failed container|BackOff'; then
        printf 'container_backoff'
    elif printf '%s' "$raw" | grep -Eqi 'Startup probe failed'; then
        printf 'startup_probe_failed'
    elif printf '%s' "$raw" | grep -Eqi 'Readiness probe failed'; then
        printf 'readiness_probe_failed'
    elif printf '%s' "$raw" | grep -Eqi 'mysql.sock|Can.t connect to local MySQL|rbd-db|database'; then
        printf 'database_not_ready'
    elif printf '%s' "$raw" | grep -Eqi 'Get pod log error|try resolving symlinks|no such file or directory'; then
        printf 'component_log_collect_failed'
    else
        printf 'unknown_rainbond_timeout'
    fi
}

function rainbond_timeout_reason_summary() {
    case "${1:-}" in
        storage_pvc_pending)
            printf 'PVC or storage provisioning is not ready'
            ;;
        node_not_ready)
            printf 'Kubernetes node is NotReady'
            ;;
        image_pull_failed)
            printf 'Container image pull failed'
            ;;
        container_backoff)
            printf 'Container is restarting or backed off'
            ;;
        startup_probe_failed)
            printf 'Startup probe failed'
            ;;
        readiness_probe_failed)
            printf 'Readiness probe failed'
            ;;
        database_not_ready)
            printf 'Database component is not ready'
            ;;
        component_log_collect_failed)
            printf 'Failed to collect component logs'
            ;;
        *)
            printf 'Rainbond services did not become ready before timeout'
            ;;
    esac
}

function rainbond_collect_timeout_diagnostics() {
    local wait_seconds="${1:-600}"
    local attempt_id="${2:-${INSTALL_ATTEMPT_ID:-}}"
    local pod_status pvc_status node_status raw root_cause_code root_cause_summary
    local failed_components="" evidence_items="" pod_count=0

    pod_status=$(rainbond_diag_kubectl get pods -n rbd-system --no-headers 2>&1 || true)
    pvc_status=$(rainbond_diag_kubectl get pvc -n rbd-system --no-headers 2>&1 || true)
    node_status=$(rainbond_diag_kubectl get nodes --no-headers 2>&1 || true)
    raw="$pod_status
$pvc_status
$node_status"

    while read -r pod_name ready status rest; do
        [ -n "$pod_name" ] || continue
        [ "$status" = "Succeeded" ] && continue
        local current_ready="${ready%/*}"
        local expected_ready="${ready#*/}"
        local is_failed="false"
        local pod_describe pod_log pod_evidence

        if [ "$ready" = "$expected_ready" ] || [ "$current_ready" != "$expected_ready" ] || [ "$status" != "Running" ]; then
            is_failed="true"
        fi

        if [ "$is_failed" = "true" ]; then
            failed_components=$(rainbond_diag_append_json_string "$failed_components" "$pod_name")
            pod_count=$((pod_count + 1))
            pod_describe=$(rainbond_diag_kubectl describe pod "$pod_name" -n rbd-system 2>&1 || true)
            pod_log=$(rainbond_diag_kubectl logs "$pod_name" -n rbd-system --all-containers --tail=80 2>&1 || true)
            pod_evidence=$(printf '%s\n' "$pod_describe" | grep -E 'Warning|Failed|BackOff|Unhealthy|FailedScheduling|FailedMount|ImagePull|ErrImagePull|NodeNotReady|PersistentVolumeClaim' | head -n 8)
            if [ -n "$pod_evidence" ]; then
                evidence_items=$(rainbond_diag_append_json_string "$evidence_items" "$pod_name: $pod_evidence")
            fi
            if [ -n "$pod_log" ]; then
                evidence_items=$(rainbond_diag_append_json_string "$evidence_items" "$pod_name log: $pod_log")
            fi
            raw="$raw
$pod_describe
$pod_log"
        fi

        if [ "$pod_count" -ge 8 ]; then
            break
        fi
    done <<EOF
$pod_status
EOF

    if [ -n "$pvc_status" ]; then
        evidence_items=$(rainbond_diag_append_json_string "$evidence_items" "pvc: $pvc_status")
    fi
    if [ -n "$node_status" ]; then
        evidence_items=$(rainbond_diag_append_json_string "$evidence_items" "nodes: $node_status")
    fi

    root_cause_code=$(rainbond_classify_timeout_reason "$raw")
    root_cause_summary=$(rainbond_timeout_reason_summary "$root_cause_code")

    printf '{"diagnosis_version":"v1","install_method":"%s","install_attempt_id":"%s","wait_seconds":%s,"root_cause_code":"%s","root_cause_summary":"%s","failed_components":[%s],"evidence":[%s]}' \
        "$(rainbond_json_escape "${RAINBOND_INSTALL_METHOD:-single_node}")" \
        "$(rainbond_json_escape "$attempt_id")" \
        "$wait_seconds" \
        "$(rainbond_json_escape "$root_cause_code")" \
        "$(rainbond_json_escape "$root_cause_summary")" \
        "$failed_components" \
        "$evidence_items"
}

function rainbond_sha256_32() {
    local input="${1:-}" digest

    if command -v sha256sum >/dev/null 2>&1; then
        digest=$(printf '%s' "$input" | sha256sum | awk '{print $1}')
    elif command -v shasum >/dev/null 2>&1; then
        digest=$(printf '%s' "$input" | shasum -a 256 | awk '{print $1}')
    else
        digest="${UUID:-}"
    fi
    printf '%s' "$digest" | cut -c 1-32
}

function rainbond_log_collect_eid() {
    local kube_system_uid

    kube_system_uid=$(rainbond_diag_kubectl get namespace kube-system -o jsonpath='{.metadata.uid}' 2>/dev/null || true)
    if [ -n "$kube_system_uid" ]; then
        rainbond_sha256_32 "$kube_system_uid"
        return
    fi
    printf '%s' "${UUID:-}"
}

function rainbond_log_collect_enable_cluster() {
    case "${RAINBOND_INSTALL_METHOD:-standalone}" in
        single_node)
            printf 'standalone'
            ;;
        *)
            printf '%s' "${RAINBOND_INSTALL_METHOD:-standalone}"
            ;;
    esac
}

function rainbond_host_cpu_count() {
    local ncpu

    ncpu=$(getconf _NPROCESSORS_ONLN 2>/dev/null || true)
    if ! echo "$ncpu" | grep -Eq '^[0-9]+$'; then
        ncpu=$(sysctl -n hw.ncpu 2>/dev/null || true)
    fi
    if ! echo "$ncpu" | grep -Eq '^[0-9]+$'; then
        ncpu=0
    fi
    printf '%s' "$ncpu"
}

function rainbond_host_mem_mb() {
    local mem_kb mem_bytes

    mem_kb=$(awk '/MemTotal/ {print $2; exit}' /proc/meminfo 2>/dev/null || true)
    if echo "$mem_kb" | grep -Eq '^[0-9]+$'; then
        printf '%s' $((mem_kb / 1024))
        return
    fi
    mem_bytes=$(sysctl -n hw.memsize 2>/dev/null || true)
    if echo "$mem_bytes" | grep -Eq '^[0-9]+$'; then
        printf '%s' $((mem_bytes / 1024 / 1024))
        return
    fi
    printf '0'
}

function rainbond_log_collect_docker_info_json() {
    printf '{"client_version":"docker","server":{"os":"%s","os_arch":"%s","kernel_version":"%s","ncpu":%s,"mem_total":%s}}' \
        "$(rainbond_json_escape "${OS_TYPE:-$(uname -s 2>/dev/null || true)}")" \
        "$(rainbond_json_escape "${ARCH_TYPE:-$(uname -m 2>/dev/null || true)}")" \
        "$(rainbond_json_escape "$(uname -r 2>/dev/null || true)")" \
        "$(rainbond_host_cpu_count)" \
        "$(rainbond_host_mem_mb)"
}

function rainbond_log_collect_cluster_status() {
    local node_status cluster_status

    node_status=$(rainbond_diag_kubectl get nodes --no-headers 2>/dev/null || true)
    cluster_status="ClusterFailed"
    if printf '%s' "$node_status" | grep -Eq '(^|[[:space:]])Ready([[:space:]]|$)'; then
        cluster_status="ClusterReady"
    fi
    printf '%s' "$cluster_status"
}

function rainbond_extract_diagnosis_reason() {
    local diagnosis="${1:-}" reason

    reason=$(printf '%s' "$diagnosis" | sed -n 's/.*"root_cause_code":"\([^"]*\)".*/\1/p' | head -n 1)
    if [ -n "$reason" ]; then
        printf '%s' "$reason"
    else
        printf 'operator_not_ready'
    fi
}

function rainbond_operator_is_ready() {
    local pod_status

    pod_status=$(rainbond_diag_kubectl get pod -n rbd-system --no-headers 2>/dev/null | grep '^rainbond-operator' || true)
    while read -r pod_name ready status rest; do
        [ -n "$pod_name" ] || continue
        local current_ready="${ready%/*}"
        local expected_ready="${ready#*/}"
        if [ "$status" = "Running" ] && [ "$current_ready" = "$expected_ready" ] && [ "$expected_ready" != "0" ]; then
            return 0
        fi
    done <<EOF
$pod_status
EOF
    return 1
}

function rainbond_operator_pods_json() {
    local reason="${1:-operator_not_ready}" diagnosis="${2:-}" pod_status pods_json=""

    pod_status=$(rainbond_diag_kubectl get pod -n rbd-system --no-headers 2>/dev/null | grep '^rainbond-operator' || true)
    if [ -z "$pod_status" ]; then
        printf '{"name":"rainbond-operator","status":"NotCreated","ready":"0/1","log":"","events":[{"type":"Warning","reason":"operator_not_created","message":"%s","from":"installer","age":""}]}' \
            "$(rainbond_json_escape "$(rainbond_diag_compact "${diagnosis:-rainbond-operator pod was not created}")")"
        return
    fi

    while read -r pod_name ready status rest; do
        [ -n "$pod_name" ] || continue
        local describe_output event_message waiting_reason pod_log pod_json event_reason

        describe_output=$(rainbond_diag_kubectl describe pod "$pod_name" -n rbd-system 2>&1 || true)
        event_message=$(printf '%s\n' "$describe_output" | grep -E 'Warning|Failed|BackOff|Unhealthy|FailedScheduling|FailedMount|ImagePull|ErrImagePull|NodeNotReady' | head -n 8)
        waiting_reason=$(rainbond_diag_kubectl get pod "$pod_name" -n rbd-system -o jsonpath='{range .status.containerStatuses[*]}{.state.waiting.reason}{" "}{.lastState.terminated.reason}{" "}{end}' 2>/dev/null || true)
        pod_log=$(rainbond_diag_kubectl logs "$pod_name" -n rbd-system --all-containers --tail=80 2>&1 || true)
        event_reason=$(rainbond_diag_compact "${waiting_reason:-$reason}")
        if [ -z "$event_message" ]; then
            event_message="$diagnosis"
        fi

        pod_json=$(printf '{"name":"%s","status":"%s","ready":"%s","log":"%s","events":[{"type":"Warning","reason":"%s","message":"%s","from":"installer","age":""}]}' \
            "$(rainbond_json_escape "$pod_name")" \
            "$(rainbond_json_escape "${status:-Unknown}")" \
            "$(rainbond_json_escape "${ready:-0/1}")" \
            "$(rainbond_json_escape "$(rainbond_diag_compact "$pod_log")")" \
            "$(rainbond_json_escape "${event_reason:-$reason}")" \
            "$(rainbond_json_escape "$(rainbond_diag_compact "$event_message")")")

        if [ -n "$pods_json" ]; then
            pods_json="${pods_json},${pod_json}"
        else
            pods_json="$pod_json"
        fi
    done <<EOF
$pod_status
EOF

    printf '%s' "$pods_json"
}

function rainbond_send_operator_log_collect() {
    local diagnosis="${1:-}" wait_seconds="${2:-0}" reason summary eid enable_cluster err_message pods_json payload

    if [ "${DISABLE_LOG:-}" = "true" ]; then
        return 0
    fi
    if rainbond_operator_is_ready; then
        return 0
    fi

    eid=$(rainbond_log_collect_eid)
    if [ -z "$eid" ]; then
        return 0
    fi

    reason=$(rainbond_extract_diagnosis_reason "$diagnosis")
    summary=$(rainbond_timeout_reason_summary "$reason")
    enable_cluster=$(rainbond_log_collect_enable_cluster)
    err_message="rainbond-operator did not become ready before timeout (${wait_seconds}s): ${summary}"
    pods_json=$(rainbond_operator_pods_json "$reason" "$diagnosis")

    payload=$(printf '{"eid":"%s","version":"%s","enable_cluster":"%s","os":"%s","os_arch":"%s","external_ip":"%s","kernel_version":"%s","err_message":"%s","docker_info":%s,"cluster_info":{"status":"%s"},"region_info":{"status":"RegionFailed-operator_not_ready","pods":[%s]}}' \
        "$(rainbond_json_escape "$eid")" \
        "$(rainbond_json_escape "${RAINBOND_VERSION:-}")" \
        "$(rainbond_json_escape "$enable_cluster")" \
        "$(rainbond_json_escape "${OS_TYPE:-$(uname -s 2>/dev/null || true)}")" \
        "$(rainbond_json_escape "${ARCH_TYPE:-$(uname -m 2>/dev/null || true)}")" \
        "$(rainbond_json_escape "${EIP:-}")" \
        "$(rainbond_json_escape "$(uname -r 2>/dev/null || true)")" \
        "$(rainbond_json_escape "$err_message")" \
        "$(rainbond_log_collect_docker_info_json)" \
        "$(rainbond_json_escape "$(rainbond_log_collect_cluster_status)")" \
        "$pods_json")

    curl --silent -H "Content-Type: application/json" -X POST "${RAINBOND_LOG_COLLECT_URL:-https://log.rainbond.com/logCollect}" \
        -d "$payload" >/dev/null 2>&1 || :
}

function docker_network_repair_message() {
    local failed_check="${1:-unknown}"
    local backend="${2:-unknown}"
    local error_detail="${3:-}"

    if rainbond_use_chinese_prompt; then
        if [ "$failed_check" = "bridge" ]; then
            cat <<EOF
Docker 网络前置检查失败：默认 bridge 网络不存在或不可用
检测命令: docker network inspect bridge
错误信息: $(rainbond_diag_compact "$error_detail")
修复命令:
  sudo systemctl restart docker
  docker network inspect bridge
如果仍失败，请继续查看 Docker 服务日志:
  sudo systemctl status docker --no-pager -l
修复后请重新执行安装脚本。
EOF
        else
            cat <<EOF
Docker 网络前置检查失败：iptables nat 表 DOCKER 链不可用
检测命令: iptables -t nat -S DOCKER
当前 iptables backend: ${backend}
错误信息: $(rainbond_diag_compact "$error_detail")
修复命令:
  sudo modprobe br_netfilter
  sudo modprobe iptable_nat
  sudo systemctl restart docker
  sudo iptables -t nat -S DOCKER
如果当前 backend 是 nf_tables 且仍失败，可切换 legacy 后重启 Docker:
  sudo update-alternatives --set iptables /usr/sbin/iptables-legacy
  sudo update-alternatives --set ip6tables /usr/sbin/ip6tables-legacy
  sudo systemctl restart docker
修复后请重新执行安装脚本。
EOF
        fi
    else
        if [ "$failed_check" = "bridge" ]; then
            cat <<EOF
Docker network preflight failed: default bridge network is missing or unavailable
Check command: docker network inspect bridge
Error: $(rainbond_diag_compact "$error_detail")
Repair commands:
  sudo systemctl restart docker
  docker network inspect bridge
If it still fails, inspect Docker service logs:
  sudo systemctl status docker --no-pager -l
Re-run this installer after repairing Docker.
EOF
        else
            cat <<EOF
Docker network preflight failed: iptables nat DOCKER chain is unavailable
Check command: iptables -t nat -S DOCKER
Current iptables backend: ${backend}
Error: $(rainbond_diag_compact "$error_detail")
Repair commands:
  sudo modprobe br_netfilter
  sudo modprobe iptable_nat
  sudo systemctl restart docker
  sudo iptables -t nat -S DOCKER
If the current backend is nf_tables and it still fails, switch to legacy and restart Docker:
  sudo update-alternatives --set iptables /usr/sbin/iptables-legacy
  sudo update-alternatives --set ip6tables /usr/sbin/ip6tables-legacy
  sudo systemctl restart docker
Re-run this installer after repairing Docker.
EOF
        fi
    fi
}

function check_docker_network_preflight() {
    local backend bridge_error docker_chain_output docker_chain_status

    if [ "${OS_TYPE:-}" != "Linux" ]; then
        return 0
    fi

    if rainbond_use_chinese_prompt; then
        send_info "开始 Docker 网络前置检查..."
    else
        send_info "Starting Docker network preflight..."
    fi

    if ! command -v docker >/dev/null 2>&1; then
        if rainbond_use_chinese_prompt; then
            send_error "Docker 命令不存在，请先安装 Docker 后重试"
        else
            send_error "Docker command not found. Please install Docker and try again."
        fi
        return 1
    fi

    if ! command -v iptables >/dev/null 2>&1; then
        if rainbond_use_chinese_prompt; then
            send_error "iptables 命令不存在，请先安装 iptables 后重试"
        else
            send_error "iptables command not found. Please install iptables and try again."
        fi
        return 1
    fi

    backend=$(iptables --version 2>/dev/null | sed -n 's/.*(\(.*\)).*/\1/p')
    backend=${backend:-unknown}

    if ! bridge_error=$(docker network inspect bridge >/dev/null 2>&1); then
        bridge_error=$(docker network inspect bridge 2>&1 >/dev/null || true)
        send_error "$(docker_network_repair_message bridge "$backend" "$bridge_error")"
        return 1
    fi

    docker_chain_status=0
    docker_chain_output=$(iptables -t nat -S DOCKER 2>&1) || docker_chain_status=$?
    if [ "$docker_chain_status" -ne 0 ]; then
        send_error "$(docker_network_repair_message docker_chain "$backend" "$docker_chain_output")"
        return 1
    fi

    if rainbond_use_chinese_prompt; then
        send_info "Docker 网络前置检查通过，iptables backend: ${backend}"
    else
        send_info "Docker network preflight passed, iptables backend: ${backend}"
    fi
    return 0
}

function send_msg() {
    dest_url="https://log.rainbond.com"
    #msg=${1:-"Terminating by userself."}
    if [ -z "$1" ]; then
        msg="Terminating by userself."
    else
        msg=$1
    fi
    msg_json=$(rainbond_json_escape "$msg")
    os_info_json=$(rainbond_json_escape "${OS_INFO:-}")
    eip_json=$(rainbond_json_escape "${EIP:-}")
    uuid_json=$(rainbond_json_escape "${UUID:-}")
    attempt_json=$(rainbond_json_escape "${INSTALL_ATTEMPT_ID:-}")
    method_json=$(rainbond_json_escape "${RAINBOND_INSTALL_METHOD:-single_node}")
    # send a message to remote url
    curl --silent -H "Content-Type: application/json" -X POST "$dest_url/dindlog" \
        -d "{\"message\":\"$msg_json\", \"os_info\":\"$os_info_json\", \"eip\":\"$eip_json\", \"uuid\":\"$uuid_json\", \"install_attempt_id\":\"$attempt_json\", \"install_method\":\"$method_json\"}" 2>&1 >/dev/null || :

    if [ "$msg" == "Terminating by userself." ]; then
        exit 1
    fi
}

function rainbond_final_event_enabled() {
    [ "${RAINBOND_FINAL_EVENT_ENABLED:-false}" = "true" ] && [ -n "${UUID:-}" ]
}

function rainbond_signal_exit_code() {
    case "${1:-}" in
        INT)
            printf '130'
            ;;
        TERM)
            printf '143'
            ;;
        *)
            printf '1'
            ;;
    esac
}

function rainbond_send_final_event() {
    local final_status="${1:-failed}"
    local reason="${2:-unknown}"
    local exit_code="${3:-1}"
    local details="${4:-}"
    local details_field=""
    local final_message

    if [ "${RAINBOND_FINAL_STATUS_SENT:-false}" = "true" ]; then
        return 0
    fi
    if ! rainbond_final_event_enabled; then
        return 0
    fi

    RAINBOND_FINAL_STATUS_SENT=true
    if [ -n "$details" ]; then
        details_field=",\"details\":\"$(rainbond_json_escape "$(rainbond_diag_compact "$details")")\""
    fi
    final_message="{\"event_type\":\"install_final\",\"install_method\":\"$(rainbond_json_escape "${RAINBOND_INSTALL_METHOD:-single_node}")\",\"install_attempt_id\":\"$(rainbond_json_escape "${INSTALL_ATTEMPT_ID:-}")\",\"final_status\":\"$(rainbond_json_escape "$final_status")\",\"reason\":\"$(rainbond_json_escape "$reason")\",\"exit_code\":$exit_code${details_field}}"
    send_msg "Rainbond install final event: ${final_message}"
}

function rainbond_handle_exit() {
    local exit_code="${1:-0}"

    if [ "$exit_code" -eq 0 ]; then
        rainbond_send_final_event success exit_zero 0
    else
        rainbond_send_final_event failed exit_nonzero "$exit_code"
    fi
    return "$exit_code"
}

function rainbond_handle_signal() {
    local signal_name="${1:-TERM}"
    local exit_code

    exit_code=$(rainbond_signal_exit_code "$signal_name")
    rainbond_send_final_event aborted "signal_${signal_name}" "$exit_code"
    return "$exit_code"
}

function send_info() {
    info=$1
    echo -e "${GREEN}$(date "$TIME") INFO: $info${NC}"
}

function send_warn() {
    warn=$1
    echo -e "${YELLOW}$(date "$TIME") WARN: $warn${NC}"
    send_msg "$warn"
}

function send_error() {
    error=$1
    echo -e "${RED}$(date "$TIME") ERROR: $error${NC}"
    send_msg "$error"
}

# Trap script exits and user/system interrupts so every started EID gets a final state.
trap 'rainbond_exit_code=$?; rainbond_handle_exit "$rainbond_exit_code"; exit "$rainbond_exit_code"' EXIT
trap 'rainbond_handle_signal INT; exit $?' INT
trap 'rainbond_handle_signal TERM; exit $?' TERM

function is_truthy() {
    case "$(echo "${1:-}" | tr '[:upper:]' '[:lower:]')" in
        1|true|yes|on)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

CLI_COMMAND=""
CLI_COMMAND_ARG1=""
CLI_COMMAND_ARG2=""

function parse_cli_args() {
    while [ $# -gt 0 ]; do
        case "$1" in
            show-command)
                CLI_COMMAND="show-command"
                shift 1
                ;;
            port-forward)
                CLI_COMMAND="port-forward"
                CLI_COMMAND_ARG1="${2:-}"
                CLI_COMMAND_ARG2="${3:-}"
                shift 3
                ;;
            "")
                shift 1
                ;;
            *)
                if rainbond_use_chinese_prompt; then
                    send_error "未知参数: $1"
                else
                    send_error "Unknown argument: $1"
                fi
                exit 1
                ;;
        esac
    done
}

parse_cli_args "$@"

########################################
# Required Commands Check
# Check if all required commands are available
########################################

function check_required_commands() {
    local missing_commands=()
    local required_commands=("curl" "awk" "sed" "grep" "tar")

    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            missing_commands+=("$cmd")
        fi
    done

    if [ ${#missing_commands[@]} -gt 0 ]; then
        if rainbond_use_chinese_prompt; then
            send_error "缺少必需命令: ${missing_commands[*]}\n\t请安装这些命令后重试"
        else
            send_error "Missing required commands: ${missing_commands[*]}\n\tPlease install these commands and try again"
        fi
        exit 1
    fi
}

check_required_commands

########################################
# OS Detect
# Automatically check the operating system type.
# Return Linux or Darwin.
########################################

OS_TYPE=$(uname -s)
if [ "${OS_TYPE}" == "Linux" ]; then
    MD5_CMD="md5sum"
elif [ "${OS_TYPE}" == "Darwin" ]; then
    MD5_CMD="md5"
else
    if rainbond_use_chinese_prompt; then
        send_error "${OS_TYPE} 操作系统暂不支持"
        exit 1
    else
        send_error "Rainbond do not support ${OS_TYPE} OS"
        exit 1
    fi
fi

# Use root user or sudo to run this script, Ignore MacOS
if [ "${OS_TYPE}" != "Darwin" ] && [ "$EUID" -ne 0 ]; then
    if rainbond_use_chinese_prompt; then
        send_error "请使用 root 用户或 sudo 运行此脚本\n\t示例: sudo bash $0"
        exit 1
    else
        send_error "Please run this script as root user or with sudo\n\tExample: sudo bash $0"
        exit 1
    fi
fi

# Check Linux kernel version (must be >= 4.x)
if [ "${OS_TYPE}" == "Linux" ]; then
    KERNEL_VERSION=$(uname -r | cut -d'.' -f1)
    if [ "$KERNEL_VERSION" -lt 4 ] 2>/dev/null; then
        if rainbond_use_chinese_prompt; then
            send_error "Linux 内核版本过低，当前版本: $(uname -r)，要求最低版本: 4.x\n\t请升级内核后重试"
        else
            send_error "Linux kernel version is too low, current version: $(uname -r), minimum required: 4.x\n\tPlease upgrade the kernel and try again"
        fi
        exit 1
    fi
fi

# Load iptable_raw module on Linux (requires root)
if [ "${OS_TYPE}" == "Linux" ]; then
    if find /lib/modules/$(uname -r) -type f -name '*.ko*' | grep iptable_raw >/dev/null 2>&1; then
        if ! lsmod | grep iptable_raw >/dev/null 2>&1; then
            echo iptable_raw >/etc/modules-load.d/iptable_raw.conf
            if ! modprobe iptable_raw 2>/dev/null; then
                if rainbond_use_chinese_prompt; then
                    send_warn "无法加载 iptable_raw 模块，可能影响网络功能"
                else
                    send_warn "Failed to load iptable_raw module, may affect network functionality"
                fi
            fi
        fi
    fi
fi


########################################
# Enhanced Environment Check Functions
# Added critical checks to improve success rate
########################################

# Function to check only ports for macOS
function check_ports_only_macos() {
  if rainbond_use_chinese_prompt; then
    send_info "######## 开始检测端口... ########"
  else
    send_info "######## Starting port check... ########"
  fi

  # Check ports
  local ports=("7070" "80" "443")
  local occupied_ports=()
  
  for port in "${ports[@]}"; do
    port_occupied=false
    
    # macOS port detection using netstat
    if netstat -anp tcp 2>/dev/null | grep -E -q "\.${port}[[:space:]]+.*LISTEN"; then
      port_occupied=true
    fi
    
    if [ "$port_occupied" = true ]; then
      occupied_ports+=($port)
    fi
  done
  
  if [ ${#occupied_ports[@]} -gt 0 ]; then
    if rainbond_use_chinese_prompt; then
      send_error "以下端口被占用: \n\t- ${occupied_ports[*]}\n\t请释放这些端口后重试."
    else
      send_error "The following ports are occupied: \n\t- ${occupied_ports[*]}\n\tPlease free these ports and try again."
    fi
    exit 1
  else
    if rainbond_use_chinese_prompt; then
      send_info "端口检测通过，所有必需端口可用"
    else
      send_info "Port check passed, all required ports are available"
    fi
  fi

  if rainbond_use_chinese_prompt; then
    send_info "######## 端口检测通过 ########"
  else
    send_info "######## Port check passed ########"
  fi
}

function check_iptables_command_linux() {
  if ! command -v iptables >/dev/null 2>&1; then
    if rainbond_use_chinese_prompt; then
      send_error "未找到 iptables 命令，请执行 yum -y install iptables 或 apt-get update && apt-get -y install iptables 后重试"
    else
      send_error "iptables command not found. Please run yum -y install iptables or apt-get update && apt-get -y install iptables, then try again."
    fi
    return 1
  fi

  return 0
}

MIN_MEMORY_KB=$((4 * 1024 * 1024))

function check_memory_requirement_linux() {
  local memory_kb
  local memory_gb

  memory_kb=$(awk '/MemTotal/ {print $2; exit}' /proc/meminfo 2>/dev/null)
  if ! echo "${memory_kb}" | grep -Eq '^[0-9]+$'; then
    if rainbond_use_chinese_prompt; then
      send_error "无法检测系统内存，请检查系统环境后重试"
    else
      send_error "Failed to detect system memory, please check the system environment and try again"
    fi
    return 1
  fi

  memory_gb=$((memory_kb / 1024 / 1024))
  if [ "${memory_kb}" -lt "${MIN_MEMORY_KB}" ]; then
    if rainbond_use_chinese_prompt; then
      send_error "内存不足，当前: ${memory_gb}GB，最低要求: 4GB"
    else
      send_error "Memory is insufficient, current: ${memory_gb}GB, minimum required: 4GB"
    fi
    return 1
  fi

  if rainbond_use_chinese_prompt; then
    send_info "内存检测通过，当前: ${memory_gb}GB"
  else
    send_info "Memory check passed, current: ${memory_gb}GB"
  fi

  return 0
}

function check_base_env() {
  if rainbond_use_chinese_prompt; then
    send_info "######## 开始检测基础环境... ########"
  else
    send_info "######## Starting base environment check... ########"
  fi

  # Check and disable firewall
  if rainbond_use_chinese_prompt; then
    send_info "检查并关闭防火墙..."
  else
    send_info "Checking and disabling firewall..."
  fi
  
  # Check and disable firewalld
  if systemctl list-unit-files 2>/dev/null | grep -q firewalld; then
    if systemctl is-active --quiet firewalld 2>/dev/null; then
      if rainbond_use_chinese_prompt; then
        send_info "检测到 firewalld 正在运行，正在停止并禁用..."
      else
        send_info "firewalld is running, stopping and disabling..."
      fi
      if ! systemctl stop firewalld >/dev/null 2>&1; then
        send_warn "无法停止 firewalld，请手动停止"
      fi
      if ! systemctl disable firewalld >/dev/null 2>&1; then
        send_warn "无法禁用 firewalld，请手动禁用"
      fi
    fi
  fi
  
  # Check and disable ufw
  if command -v ufw >/dev/null 2>&1; then
    if ufw status | grep -q "Status: active"; then
      if rainbond_use_chinese_prompt; then
        send_info "检测到 ufw 正在运行，正在停止并禁用..."
      else
        send_info "ufw is active, stopping and disabling..."
      fi
      ufw --force disable >/dev/null 2>&1
    fi
  fi
  
  if ! check_iptables_command_linux; then
    exit 1
  fi

  if ! check_memory_requirement_linux; then
    exit 1
  fi

  # Check and disable swap
  if rainbond_use_chinese_prompt; then
    send_info "检查并关闭交换分区..."
  else
    send_info "Checking and disabling swap..."
  fi
  
  # Check if swap is enabled
  if [ "$(cat /proc/swaps | wc -l)" -gt 1 ]; then
    if rainbond_use_chinese_prompt; then
      send_info "检测到交换分区正在使用，正在关闭..."
    else
      send_info "Swap is enabled, disabling..."
    fi
    
    # Disable swap
    swapoff -a >/dev/null 2>&1
    
    # Comment out swap entries in /etc/fstab to prevent re-enabling on reboot
    if [ -f /etc/fstab ]; then
      if sed -i.bak '/^[^#].*swap/s/^/#/' /etc/fstab 2>/dev/null; then
        if rainbond_use_chinese_prompt; then
          send_info "已修改 /etc/fstab 防止重启后重新启用交换分区"
        else
          send_info "Modified /etc/fstab to prevent swap re-enabling on reboot"
        fi
      else
        if rainbond_use_chinese_prompt; then
          send_warn "修改 /etc/fstab 失败，重启后可能重新启用 swap"
        else
          send_warn "Failed to modify /etc/fstab, swap may re-enable after reboot"
        fi
      fi
    fi
    
    if rainbond_use_chinese_prompt; then
      send_info "交换分区已关闭"
    else
      send_info "Swap disabled successfully"
    fi
  fi

  # Check ports
  local ports=("7070" "80" "443")
  local occupied_ports=()
  
  for port in "${ports[@]}"; do
    port_occupied=false
    
    # Linux specific check
    if command -v ss >/dev/null 2>&1; then
      if ss -tuln 2>/dev/null | grep ":${port} " >/dev/null; then
        port_occupied=true
      fi
    elif command -v netstat >/dev/null 2>&1; then
      if netstat -tuln 2>/dev/null | grep ":${port} " >/dev/null; then
        port_occupied=true
      fi
    elif command -v lsof >/dev/null 2>&1; then
      if lsof -i :${port} >/dev/null 2>&1; then
        port_occupied=true
      fi
    fi
    
    if [ "$port_occupied" = true ]; then
      occupied_ports+=($port)
    fi
  done
  
  if [ ${#occupied_ports[@]} -gt 0 ]; then
    if rainbond_use_chinese_prompt; then
      send_error "以下端口被占用: ${occupied_ports[*]}. 请释放这些端口后重试."
    else
      send_error "The following ports are occupied: ${occupied_ports[*]}. Please free these ports and try again."
    fi
    exit 1
  else
    if rainbond_use_chinese_prompt; then
      send_info "端口检测通过，所有必需端口可用"
    else
      send_info "Port check passed, all required ports are available"
    fi
  fi

  # Test connection to docker registry
  if curl -s --connect-timeout 10 --max-time 30 "https://registry.cn-hangzhou.aliyuncs.com" >/dev/null 2>&1; then
    if rainbond_use_chinese_prompt; then
      send_info "Docker 镜像仓库连接正常"
    else
      send_info "Docker registry connectivity is working"
    fi
  else
    if rainbond_use_chinese_prompt; then
      send_error "Docker 镜像仓库连接测试失败，可能影响镜像下载"
    else
      send_error "Docker registry connectivity test failed, may affect image download"
    fi
    exit 1
  fi
  
  local available_space
  local check_path
  
  if [ "${OS_TYPE}" == "Linux" ]; then
    # Check /opt if it exists, otherwise check root partition
    if [ -d "/opt" ]; then
      check_path="/opt"
    else
      check_path="/"
    fi
    available_space=$(df "$check_path" 2>/dev/null | tail -1 | awk '{print $4}' || echo "0")
  elif [ "${OS_TYPE}" == "Darwin" ]; then
    check_path="/"
    # macOS df output format is different, need to handle it properly
    available_space=$(df -k "$check_path" 2>/dev/null | tail -1 | awk '{print $4}' || echo "0")
  fi
  
  # Convert to numeric value safely
  available_space=$(echo "$available_space" | tr -d 'K' | tr -d 'M' | tr -d 'G' | sed 's/[^0-9]//g')
  available_space=${available_space:-0}
  
  # Check if at least 10GB available (10485760 KB)
  if [ "$available_space" -lt 10485760 ] 2>/dev/null; then
    local available_gb=$((available_space / 1024 / 1024))
    if rainbond_use_chinese_prompt; then
      send_error "磁盘空间不足，当前可用: ${available_gb}GB, 请至少保留10GB空间后重试"
    else
      send_error "Disk space is insufficient, available: ${available_gb}GB, please reserve at least 10GB space and try again"
    fi
    exit 1
  else
    local available_gb=$((available_space / 1024 / 1024))
    if rainbond_use_chinese_prompt; then
      send_info "磁盘空间检测通过，可用空间: ${available_gb}GB"
    else
      send_info "Disk space check passed, available space: ${available_gb}GB"
    fi
  fi

  if rainbond_use_chinese_prompt; then
    send_info "######## 基础环境检测通过 ########"
  else
    send_info "######## Base environment check passed ########"
  fi
}

########################################
# Container Helper Functions
# Reusable functions for container operations
########################################

# Check if rainbond container exists
# Returns: 0 if exists, 1 if not exists
function container_exists() {
  docker ps -a --filter "name=^rainbond$" --format '{{.Names}}' 2>/dev/null | grep -q "^rainbond$"
}

# Check if rainbond container is running
# Returns: 0 if running, 1 if not running
function container_is_running() {
  docker ps --filter "name=^rainbond$" --filter "status=running" --format '{{.Names}}' 2>/dev/null | grep -q "^rainbond$"
}

# Get container IP address
# Outputs: Container IP address or empty string
function get_container_ip() {
  docker inspect rainbond --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' 2>/dev/null
}

# Get EIP from container environment
# Outputs: EIP value or empty string
function get_container_eip() {
  docker inspect rainbond --format '{{range .Config.Env}}{{println .}}{{end}}' 2>/dev/null | grep '^EIP=' | cut -d'=' -f2
}

# Ensure container exists (exit with error if not)
function require_container_exists() {
  if ! container_exists; then
    if rainbond_use_chinese_prompt; then
      send_error "rainbond 容器不存在，请先运行安装脚本"
    else
      send_error "rainbond container does not exist, please run the installation script first"
    fi
    exit 1
  fi
}

# Ensure container is running (exit with error if not)
function require_container_running() {
  require_container_exists

  if ! container_is_running; then
    if rainbond_use_chinese_prompt; then
      send_error "rainbond 容器未运行，请先启动容器"
    else
      send_error "rainbond container is not running, please start the container first"
    fi
    exit 1
  fi
}

function check_rainbond_container() {
  if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    if container_exists; then
      if container_is_running; then
        # Rainbond container is running, get EIP and exit
        local get_eip
        get_eip=$(get_container_eip)
        rainbond_warn_ip_drift "$get_eip"
        if rainbond_use_chinese_prompt; then
          send_info "Rainbond 容器已在运行中.\n\t- 请在浏览器中输入 http://$get_eip:7070 访问 Rainbond."
        else
          send_info "Rainbond container is already running.\n\t- Please enter http://$get_eip:7070 in the browser to access Rainbond."
        fi
        exit 0
      else
        # Container exists but is not running, try to start it
        if rainbond_use_chinese_prompt; then
          send_info "Rainbond 容器已存在但未运行，正在尝试启动..."
        else
          send_info "Rainbond container exists but not running, trying to start..."
        fi

        if docker start rainbond; then
          sleep 3
          local get_eip
          get_eip=$(get_container_eip)
          rainbond_warn_ip_drift "$get_eip"
          if rainbond_use_chinese_prompt; then
            send_info "Rainbond 容器启动成功.\n\t- 请在浏览器中输入 http://$get_eip:7070 访问 Rainbond."
          else
            send_info "Rainbond container started successfully.\n\t- Please enter http://$get_eip:7070 in the browser to access Rainbond."
          fi
          exit 0
        else
          if rainbond_use_chinese_prompt; then
            send_error "Rainbond 容器启动失败，请手动执行 docker start rainbond"
          else
            send_error "Failed to start Rainbond container, please manually run docker start rainbond"
          fi
          exit 1
        fi
      fi
    fi
  fi
}

########################################
# Show Docker Command Function
# Display the docker run command from existing container
########################################

function show_docker_command() {
  # Check if rainbond container exists
  require_container_exists

  # Get container information
  local IMAGE
  local EIP
  local UUID
  local EXISTING_ENABLE_GPU
  local EXISTING_GPU_PROVIDER
  local EXISTING_GPU_RUNTIME_CLASS
  IMAGE=$(docker inspect rainbond --format '{{.Config.Image}}' 2>/dev/null)
  EIP=$(get_container_eip)
  UUID=$(docker inspect rainbond --format '{{range .Config.Env}}{{println .}}{{end}}' 2>/dev/null | grep '^UUID=' | cut -d'=' -f2)
  EXISTING_ENABLE_GPU=$(docker inspect rainbond --format '{{range .Config.Env}}{{println .}}{{end}}' 2>/dev/null | grep '^ENABLE_GPU=' | cut -d'=' -f2)
  EXISTING_GPU_PROVIDER=$(docker inspect rainbond --format '{{range .Config.Env}}{{println .}}{{end}}' 2>/dev/null | grep '^GPU_PROVIDER=' | cut -d'=' -f2)
  EXISTING_GPU_RUNTIME_CLASS=$(docker inspect rainbond --format '{{range .Config.Env}}{{println .}}{{end}}' 2>/dev/null | grep '^GPU_RUNTIME_CLASS_NAME=' | cut -d'=' -f2)

  # Get volume mounts
  local VOLUME_OPTS=$(docker inspect rainbond --format '{{range .Mounts}}{{if eq .Type "bind"}}-v {{.Source}}:{{.Destination}} {{else if eq .Type "volume"}}-v {{.Name}}:{{.Destination}} {{end}}{{end}}' 2>/dev/null)
  local GPU_DOCKER_ARGS=""
  local GPU_ENV_BLOCK=""
  if is_truthy "${EXISTING_ENABLE_GPU}"; then
    GPU_DOCKER_ARGS="  --gpus all \\"
    GPU_ENV_BLOCK="  -e ENABLE_GPU=true \\
  -e GPU_PROVIDER=${EXISTING_GPU_PROVIDER:-nvidia} \\
  -e GPU_RUNTIME_CLASS_NAME=${EXISTING_GPU_RUNTIME_CLASS:-nvidia} \\
  -e NVIDIA_VISIBLE_DEVICES=all \\
  -e NVIDIA_DRIVER_CAPABILITIES=compute,utility \\"
  else
    GPU_ENV_BLOCK="  -e ENABLE_GPU=false \\"
  fi

  # Display the command
  echo -e "${GREEN}"
  if rainbond_use_chinese_prompt; then
    cat << EOF
###############################################
# 您可以复制并修改以下命令来重新部署:

docker run --privileged -d \\
${GPU_DOCKER_ARGS}\
  -p 7070:7070 \\
  -p 80:80 \\
  -p 443:443 \\
  -p 30000-30010:30000-30010 \\
  --name=rainbond \\
  --restart=always \\
  ${VOLUME_OPTS}\\
${GPU_ENV_BLOCK}\
  -e EIP=${EIP} \\
  -e REGION_WS_PROXY_TARGET=ws://127.0.0.1:6060 \\
  -e UUID=${UUID} \\
  ${IMAGE}
EOF
  else
    cat << EOF
# You can copy and modify the following command to redeploy:

docker run --privileged -d \\
${GPU_DOCKER_ARGS}\
  -p 7070:7070 \\
  -p 80:80 \\
  -p 443:443 \\
  -p 30000-30010:30000-30010 \\
  --name=rainbond \\
  --restart=always \\
  ${VOLUME_OPTS}\\
${GPU_ENV_BLOCK}\
  -e EIP=${EIP} \\
  -e REGION_WS_PROXY_TARGET=ws://127.0.0.1:6060 \\
  -e UUID=${UUID} \\
  ${IMAGE}
EOF
  fi
  echo -e "${NC}"
  exit 0
}

########################################
# Port Forward Function
# Setup iptables port forwarding for Rainbond container
########################################

function setup_port_forward() {
  # Only support Linux
  if [ "${OS_TYPE}" != "Linux" ]; then
    if rainbond_use_chinese_prompt; then
      send -e "${RED}错误: 端口转发功能仅在 Linux 系统上支持${NC}"
    else
      echo -e "${RED}Error: Port forwarding is only supported on Linux${NC}"
    fi
    exit 1
  fi

  # Check if rainbond container exists and is running
  require_container_running

  # Get container IP
  local CONTAINER_IP
  CONTAINER_IP=$(get_container_ip)
  if [ -z "$CONTAINER_IP" ]; then
    if rainbond_use_chinese_prompt; then
      echo -e "${RED}错误: 无法获取容器 IP 地址${NC}"
    else
      echo -e "${RED}Error: Failed to get container IP address${NC}"
    fi
    exit 1
  fi

  # Validate port parameters
  local CONTAINER_PORT=$1
  local HOST_PORT=$2

  if [ -z "$CONTAINER_PORT" ] || [ -z "$HOST_PORT" ]; then
    if rainbond_use_chinese_prompt; then
      echo -e "${RED}错误: 缺少端口参数${NC}"
      echo -e "${YELLOW}用法: $0 port-forward <容器端口> <宿主机端口>${NC}"
      echo -e "${YELLOW}示例: $0 port-forward 30011 30011${NC}"
    else
      echo -e "${RED}Error: Missing port parameters${NC}"
      echo -e "${YELLOW}Usage: $0 port-forward <container-port> <host-port>${NC}"
      echo -e "${YELLOW}Example: $0 port-forward 30011 30011${NC}"
    fi
    exit 1
  fi

  # Validate port numbers
  if ! [[ "$CONTAINER_PORT" =~ ^[0-9]+$ ]] || [ "$CONTAINER_PORT" -lt 1 ] || [ "$CONTAINER_PORT" -gt 65535 ]; then
    if rainbond_use_chinese_prompt; then
      echo -e "${RED}错误: 无效的容器端口号: $CONTAINER_PORT (必须是 1-65535 之间的数字)${NC}"
    else
      echo -e "${RED}Error: Invalid container port: $CONTAINER_PORT (must be a number between 1-65535)${NC}"
    fi
    exit 1
  fi

  if ! [[ "$HOST_PORT" =~ ^[0-9]+$ ]] || [ "$HOST_PORT" -lt 1 ] || [ "$HOST_PORT" -gt 65535 ]; then
    if rainbond_use_chinese_prompt; then
      echo -e "${RED}错误: 无效的宿主机端口号: $HOST_PORT (必须是 1-65535 之间的数字)${NC}"
    else
      echo -e "${RED}Error: Invalid host port: $HOST_PORT (must be a number between 1-65535)${NC}"
    fi
    exit 1
  fi

  # Check if iptables command exists
  if ! command -v iptables >/dev/null 2>&1; then
    if rainbond_use_chinese_prompt; then
      echo -e "${RED}错误: 未找到 iptables 命令，请先安装 iptables${NC}"
    else
      echo -e "${RED}Error: iptables command not found, please install iptables first${NC}"
    fi
    exit 1
  fi

  if ! iptables -t nat -I DOCKER -p tcp --dport "${HOST_PORT}" -j DNAT --to-destination "${CONTAINER_IP}:${CONTAINER_PORT}" 2>/dev/null; then
    if rainbond_use_chinese_prompt; then
      echo -e "${RED}错误: 添加 NAT 规则失败${NC}"
    else
      echo -e "${RED}Error: Failed to add NAT rule${NC}"
    fi
    exit 1
  fi

  if ! iptables -I DOCKER -d "${CONTAINER_IP}" -p tcp --dport "${CONTAINER_PORT}" -j ACCEPT 2>/dev/null; then
    if rainbond_use_chinese_prompt; then
      echo -e "${YELLOW}警告: 添加 FILTER 规则失败，但 NAT 规则已添加${NC}"
    else
      echo -e "${YELLOW}Warning: Failed to add FILTER rule, but NAT rule has been added${NC}"
    fi
  fi

  if rainbond_use_chinese_prompt; then
    echo -e "${GREEN}✓ 端口转发配置成功！${NC}"
    echo -e "${GREEN}您现在可以通过宿主机的 ${HOST_PORT} 端口访问容器的 ${CONTAINER_PORT} 端口${NC}"
    echo ""
    echo -e "${YELLOW}注意: 这些 iptables 规则在系统重启后会失效${NC}"
    echo -e "${YELLOW}如需持久化，请使用 iptables-save 保存规则或在容器启动时使用 -p 参数${NC}"
  else
    echo -e "${GREEN}✓ Port forwarding configured successfully!${NC}"
    echo -e "${GREEN}You can now access container port ${CONTAINER_PORT} via host port ${HOST_PORT}${NC}"
    echo ""
    echo -e "${YELLOW}Note: These iptables rules will be lost after system reboot${NC}"
    echo -e "${YELLOW}To persist, use iptables-save or add -p parameter when starting the container${NC}"
  fi

  exit 0
}

########################################
# EIP Helpers
# Detect both the LAN IP of this host and the public IP a browser needs to
# reach it, so the console can advertise an address that actually works.
########################################

RAINBOND_EIP_CONFIRM_TIMEOUT=${RAINBOND_EIP_CONFIRM_TIMEOUT:-30}
RAINBOND_LAN_IP=""
RAINBOND_PUBLIC_IP=""
RAINBOND_ACCESS_LINES_ZH=""
RAINBOND_ACCESS_LINES_EN=""

function rainbond_is_usable_ipv4() {
    local result=$1 old_ifs octet octet_value
    if [ -z "$result" ]; then
        return 1
    fi

    case "$result" in
        *[!0-9.]* | .* | *. | *..*)
            return 1
            ;;
    esac

    old_ifs=$IFS
    IFS=.
    set -- $result
    IFS=$old_ifs

    [ "$#" -eq 4 ] || return 1
    for octet in "$@"; do
        case "$octet" in
            '' | *[!0-9]*)
                return 1
                ;;
        esac
        octet_value=$((10#$octet))
        [ "$octet_value" -le 255 ] || return 1
    done

    [ "$result" != "127.0.0.1" ] && [ "$result" != "0.0.0.0" ]
}

# Func for verify the result entered.
function verify_eip() {
    local result=$1
    if rainbond_is_usable_ipv4 "$result"; then
        export EIP="$result"
        return 0
    fi

    if [ -z "$result" ]; then
        echo -e "${YELLOW}Do not enter null values${NC}"
    elif [ "$result" == "127.0.0.1" ]; then
        if rainbond_use_chinese_prompt; then
            echo -e "${YELLOW}不能使用回环地址 127.0.0.1${NC}"
        else
            echo -e "${YELLOW}Cannot use loopback address 127.0.0.1${NC}"
        fi
    elif [ "$result" == "0.0.0.0" ]; then
        if rainbond_use_chinese_prompt; then
            echo -e "${YELLOW}不能使用 0.0.0.0${NC}"
        else
            echo -e "${YELLOW}Cannot use 0.0.0.0${NC}"
        fi
    fi
    return 1
}

function rainbond_is_private_ipv4() {
    local ip_addr=$1
    case "$ip_addr" in
        10.* | 192.168.*)
            return 0
            ;;
        172.*)
            local second_octet
            second_octet=$(printf '%s' "$ip_addr" | cut -d. -f2)
            [ "$second_octet" -ge 16 ] 2>/dev/null && [ "$second_octet" -le 31 ] 2>/dev/null
            return $?
            ;;
        *)
            return 1
            ;;
    esac
}

function rainbond_skip_ip_interface() {
    case "${1:-}" in
        lo | lo:* | docker* | br-* | veth* | flannel* | cni* | cali* | calico* | kube* | tunl*)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

function rainbond_candidate_host_ips() {
    local line iface cidr ip_addr

    if command -v ip >/dev/null 2>&1; then
        ip -4 -o addr show scope global 2>/dev/null | while IFS= read -r line; do
            set -- $line
            iface=${2:-}
            cidr=${4:-}
            ip_addr=${cidr%%/*}
            rainbond_skip_ip_interface "$iface" && continue
            rainbond_is_usable_ipv4 "$ip_addr" && printf '%s\n' "$ip_addr"
        done
    elif command -v ifconfig >/dev/null 2>&1; then
        ifconfig 2>/dev/null | grep -w inet | awk '{print $2}' | while IFS= read -r ip_addr; do
            rainbond_is_usable_ipv4 "$ip_addr" && printf '%s\n' "$ip_addr"
        done
    else
        return 0
    fi
}

function rainbond_detect_host_eip() {
    local first_ip="" private_ip="" ip_addr

    while IFS= read -r ip_addr; do
        [ -n "$ip_addr" ] || continue
        if [ -z "$first_ip" ]; then
            first_ip=$ip_addr
        fi
        if rainbond_is_private_ipv4 "$ip_addr"; then
            private_ip=$ip_addr
            break
        fi
    done <<EOF
$(rainbond_candidate_host_ips)
EOF

    if [ -n "$private_ip" ]; then
        export EIP="$private_ip"
        return 0
    fi
    if [ -n "$first_ip" ]; then
        export EIP="$first_ip"
        return 0
    fi
    return 1
}

function rainbond_detect_host_eip_value() {
    (rainbond_detect_host_eip >/dev/null 2>&1 && printf '%s' "${EIP:-}")
}

# Public IP detection is on by default; EIP_PROBE=false turns it off.
function rainbond_public_ip_probe_enabled() {
    case "$(echo "${EIP_PROBE:-true}" | tr '[:upper:]' '[:lower:]')" in
        0 | false | no | off)
            return 1
            ;;
        *)
            return 0
            ;;
    esac
}

# Sources for the public IP, tried in order: cloud metadata first (link-local,
# authoritative, no Internet access needed), then public echo services.
# Every source runs with a short timeout, so a blocked network costs the
# installer a few seconds instead of minutes.
function rainbond_public_ip_sources() {
    cat <<'EOF'
metadata|http://100.100.100.200/latest/meta-data/eipv4
metadata|http://metadata.tencentyun.com/latest/meta-data/public-ipv4
metadata|http://169.254.169.254/latest/meta-data/public-ipv4
echo|https://api.ip.sb/ip
echo|http://ip.3322.net
echo|https://ifconfig.me/ip
EOF
}

# Outputs the public IPv4 of this host, or nothing when it cannot be determined.
function rainbond_probe_public_ip() {
    local kind url value

    command -v curl >/dev/null 2>&1 || return 1

    while IFS='|' read -r kind url; do
        [ -n "$url" ] || continue
        if [ "$kind" = "metadata" ]; then
            value=$(curl -sf --noproxy '*' --connect-timeout 1 --max-time 2 "$url" 2>/dev/null | tr -d '[:space:]')
        else
            value=$(curl -sf --connect-timeout 2 --max-time 3 "$url" 2>/dev/null | tr -d '[:space:]')
        fi
        if rainbond_is_usable_ipv4 "$value" && ! rainbond_is_private_ipv4 "$value"; then
            printf '%s\n' "$value"
            return 0
        fi
    done <<EOF
$(rainbond_public_ip_sources)
EOF

    return 1
}

# The installer is normally run through a pipe (curl ... | bash), so stdin is
# not a terminal even when the user is watching; /dev/tty still reaches them.
function rainbond_tty_available() {
    if is_truthy "${RAINBOND_NON_INTERACTIVE:-}"; then
        return 1
    fi
    [ -e /dev/tty ] || return 1
    (exec 3</dev/tty) 2>/dev/null
}

function rainbond_confirm_public_eip() {
    local public_ip=$1 lan_ip=$2 answer=""

    if rainbond_use_chinese_prompt; then
        echo -e "${YELLOW}检测到本机公网 IP: ${public_ip}，内网 IP: ${lan_ip}${NC}"
        echo -e "${YELLOW}从外部浏览器访问 Rainbond 需要使用公网 IP${NC}"
        printf '%b' "${YELLOW}是否使用公网 IP ${public_ip} 作为访问地址? [Y/n] (${RAINBOND_EIP_CONFIRM_TIMEOUT} 秒无输入默认使用公网 IP): ${NC}"
    else
        echo -e "${YELLOW}Detected public IP: ${public_ip}, LAN IP: ${lan_ip}${NC}"
        echo -e "${YELLOW}Reaching Rainbond from an external browser requires the public IP${NC}"
        printf '%b' "${YELLOW}Use public IP ${public_ip} as the access address? [Y/n] (defaults to the public IP after ${RAINBOND_EIP_CONFIRM_TIMEOUT}s): ${NC}"
    fi

    if ! read -r -t "${RAINBOND_EIP_CONFIRM_TIMEOUT}" answer </dev/tty; then
        answer=""
    fi
    echo ""

    case "$answer" in
        n | N | no | No | NO)
            return 1
            ;;
        *)
            return 0
            ;;
    esac
}

# Warn when the address recorded in the running container matches none of this
# host's current addresses: the console builds its default *.nip.io domains from
# it, and they stop resolving once the server IP changes.
function rainbond_warn_ip_drift() {
    local recorded_eip=$1 lan_ip="" public_ip=""

    rainbond_is_usable_ipv4 "$recorded_eip" || return 0

    lan_ip=$(rainbond_detect_host_eip_value)
    if [ "$recorded_eip" = "$lan_ip" ]; then
        return 0
    fi

    if rainbond_public_ip_probe_enabled; then
        public_ip=$(rainbond_probe_public_ip)
    fi
    if [ -n "$public_ip" ] && [ "$recorded_eip" = "$public_ip" ]; then
        return 0
    fi

    if rainbond_use_chinese_prompt; then
        send_warn "服务器访问 IP 可能已变更: 容器记录的是 ${recorded_eip}，当前本机内网 IP 是 ${lan_ip:-未知}${public_ip:+，公网 IP 是 ${public_ip}}"
        send_warn "控制台默认域名(*.${recorded_eip}.nip.io)和网关地址仍指向旧 IP，更换访问 IP 请参考 https://www.rainbond.com/docs/support"
    else
        send_warn "The access IP may have changed: the container records ${recorded_eip}, this host currently has LAN IP ${lan_ip:-unknown}${public_ip:+ and public IP ${public_ip}}"
        send_warn "Default console domains (*.${recorded_eip}.nip.io) and the gateway address still point to the old IP, see https://www.rainbond.com/docs/support"
    fi
}

# Builds the access address block shown on the completion screen. The console
# address always comes with its counterpart, so a user who ends up on the wrong
# side of a NAT still sees the address that works for them.
function rainbond_build_access_lines() {
    local zh_lines en_lines

    zh_lines="#     控制台地址: http://${EIP}:7070"
    en_lines="#     Console URL: http://${EIP}:7070"

    if [ -n "${RAINBOND_PUBLIC_IP}" ] && [ "${RAINBOND_PUBLIC_IP}" != "${EIP}" ]; then
        zh_lines="${zh_lines}
#     公网地址: http://${RAINBOND_PUBLIC_IP}:7070"
        en_lines="${en_lines}
#     Public URL: http://${RAINBOND_PUBLIC_IP}:7070"
    fi

    if [ -n "${RAINBOND_LAN_IP}" ] && [ "${RAINBOND_LAN_IP}" != "${EIP}" ]; then
        zh_lines="${zh_lines}
#     内网地址: http://${RAINBOND_LAN_IP}:7070"
        en_lines="${en_lines}
#     LAN URL: http://${RAINBOND_LAN_IP}:7070"
    fi

    if [ -z "${RAINBOND_PUBLIC_IP}" ] && rainbond_is_private_ipv4 "${EIP}"; then
        zh_lines="${zh_lines}
#     云服务器请用公网 IP: http://<公网IP>:7070"
        en_lines="${en_lines}
#     Cloud server, use public IP: http://<public-ip>:7070"
    fi

    RAINBOND_ACCESS_LINES_ZH=$zh_lines
    RAINBOND_ACCESS_LINES_EN=$en_lines
}

# Shown before the install starts: a closed security group is the most common
# reason the console is unreachable after a successful installation.
function rainbond_print_access_ports_notice() {
    if rainbond_use_chinese_prompt; then
        send_warn "安装前请确认云服务器安全组/防火墙已放行以下端口，否则浏览器无法访问 http://${EIP}:7070"
        echo -e "${YELLOW}    - 7070: 控制台访问端口${NC}"
        echo -e "${YELLOW}    - 80/443: 应用 HTTP/HTTPS 访问端口${NC}"
        echo -e "${YELLOW}    - 30000-30010: 应用对外端口${NC}"
    else
        send_warn "Before installing, make sure the following ports are open in your security group/firewall, otherwise http://${EIP}:7070 stays unreachable"
        echo -e "${YELLOW}    - 7070: console port${NC}"
        echo -e "${YELLOW}    - 80/443: application HTTP/HTTPS ports${NC}"
        echo -e "${YELLOW}    - 30000-30010: application external ports${NC}"
    fi
}

################################################################################
# SECTION 4: Main Installation Flow
################################################################################

# Check for --show parameter
if [ "$CLI_COMMAND" = "show-command" ]; then
  show_docker_command
fi

# Check for port-forward parameter
if [ "$CLI_COMMAND" = "port-forward" ]; then
  setup_port_forward "$CLI_COMMAND_ARG1" "$CLI_COMMAND_ARG2"
fi

# Display Rainbond ASCII banner at the very beginning
echo -e "${GREEN}"
cat << "EOF"
██████   █████  ██ ███    ██ ██████   ██████  ███    ██ ██████
██   ██ ██   ██ ██ ████   ██ ██   ██ ██    ██ ████   ██ ██   ██
██████  ███████ ██ ██ ██  ██ ██████  ██    ██ ██ ██  ██ ██   ██
██   ██ ██   ██ ██ ██  ██ ██ ██   ██ ██    ██ ██  ██ ██ ██   ██
██   ██ ██   ██ ██ ██   ████ ██████   ██████  ██   ████ ██████
EOF
echo -e "${NC}"

if rainbond_use_chinese_prompt; then
  echo -e "${GREEN}欢迎安装 Rainbond${NC}"
  echo -e "${GREEN}版本: ${RAINBOND_VERSION}${NC}"
  echo ""
else
  echo -e "${GREEN}Welcome to install Rainbond ${NC}"
  echo -e "${GREEN}Version: ${RAINBOND_VERSION}${NC}"
  echo ""
fi

# First check if Rainbond container is already running
check_rainbond_container

if [ "${OS_TYPE}" == "Linux" ]; then
  check_base_env
elif [ "${OS_TYPE}" == "Darwin" ]; then
  check_ports_only_macos
fi

########################################
# Arch Detect
# Automatically check the CPU architecture type.
# Return amd64 or arm64.
########################################

if [ "$(arch)" = "x86_64" ] || [ "$(arch)" = "amd64" ]; then
    ARCH_TYPE=amd64
elif [ "$(arch)" = "aarch64" ] || [ "$(arch)" = "arm64" ]; then
    ARCH_TYPE=arm64
elif [ "$(arch)" = "i386" ]; then
    ARCH_TYPE=amd64
    if rainbond_use_chinese_prompt; then
        send_warn "检测到 i386, 我们把它当做 x86_64(amd64). 如果您使用的是 M1 芯片的 MacOS, 确保您禁用了 Rosetta. \n\t 请参阅: https://github.com/goodrain/rainbond/issues/1439 "
    else
        send_warn "i386 has been detected, we'll treat it like x86_64(amd64). If you are using the M1 chip MacOS, make sure your terminal has Rosetta disabled.\n\t Have a look : https://github.com/goodrain/rainbond/issues/1439 "
    fi
else
    if rainbond_use_chinese_prompt; then
        send_error "Rainbond 目前还不支持 $(arch) 架构"
        exit 1
    else
        send_error "Rainbond does not support $(arch) architecture"
        exit 1
    fi
fi

OS_INFO=$(uname -a)
UUID=$(echo "$OS_INFO" | ${MD5_CMD} | cut -b 1-32)

RAINBOND_FINAL_EVENT_ENABLED=true
send_msg "Starting Rainbond installation"

########################################
# Environment Check
# Check docker is running or not.
# Check ports can be use or not.
# If not, quit.
########################################

# Function to check if Docker is installed
check_docker_installed() {
    if command -v docker &>/dev/null; then
        return 0
    else
        return 1
    fi
}

# Function to check if Docker is running
check_docker_running() {
    if docker info &>/dev/null; then
        return 0
    else
        return 1
    fi
}

# Function to start Docker service on Linux
start_docker_service_linux() {
    if rainbond_use_chinese_prompt; then
        send_info "检测到 Docker 已安装但未运行，正在自动启动 Docker 服务..."
    else
        send_info "Docker is installed but not running, starting Docker service automatically..."
    fi
    
    if systemctl start docker >/dev/null 2>&1; then
        sleep 3
        if docker info >/dev/null 2>&1; then
            if rainbond_use_chinese_prompt; then
                send_info "Docker 服务启动成功"
            else
                send_info "Docker service started successfully"
            fi
            return 0
        else
            if rainbond_use_chinese_prompt; then
                send_error "Docker 服务启动失败，请手动启动: systemctl start docker"
            else
                send_error "Docker service failed to start, please start manually: systemctl start docker"
            fi
            return 1
        fi
    else
        if rainbond_use_chinese_prompt; then
            send_error "Docker 服务启动失败，请手动启动: systemctl start docker"
        else
            send_error "Docker service failed to start, please start manually: systemctl start docker"
        fi
        return 1
    fi
}

# Function to check if OrbStack is installed
check_orbstack_installed() {
    command -v orb >/dev/null 2>&1 || [ -d "/Applications/OrbStack.app" ] || [ -d "${HOME}/Applications/OrbStack.app" ]
}

# Function to check if OrbStack is running
check_orbstack_running() {
    if command -v orb >/dev/null 2>&1; then
        orb status >/dev/null 2>&1
    else
        # Check if OrbStack process is running
        pgrep -f "OrbStack" >/dev/null 2>&1
    fi
}

orbstack_wait_seconds() {
    local wait_seconds="${RAINBOND_ORBSTACK_WAIT_SECONDS:-120}"
    case "$wait_seconds" in
        ''|*[!0-9]*)
            wait_seconds=120
            ;;
    esac
    if [ "$wait_seconds" -lt 1 ]; then
        wait_seconds=120
    fi
    echo "$wait_seconds"
}

install_orbstack_macos() {
    if ! is_truthy "${RAINBOND_AUTO_INSTALL_ORBSTACK:-}"; then
        return 1
    fi

    if install_orbstack_from_dmg_macos; then
        return 0
    fi

    if rainbond_use_chinese_prompt; then
        send_warn "OrbStack 官方安装包自动安装失败，正在尝试 Homebrew..."
    else
        send_warn "Official OrbStack installer failed, trying Homebrew..."
    fi

    install_orbstack_with_brew_macos
}

install_orbstack_with_brew_macos() {
    if ! command -v brew >/dev/null 2>&1; then
        if rainbond_use_chinese_prompt; then
            send_warn "未检测到 Homebrew，无法继续通过 Homebrew 安装 OrbStack"
        else
            send_warn "Homebrew is not installed, cannot continue installing OrbStack with Homebrew"
        fi
        return 1
    fi

    local brew_log
    brew_log=$(mktemp "${TMPDIR:-/tmp}/rainbond-brew-orbstack.XXXXXX")

    if rainbond_use_chinese_prompt; then
        send_info "正在通过 Homebrew 自动安装 OrbStack..."
    else
        send_info "Installing OrbStack with Homebrew..."
    fi

    if brew install --cask orbstack >"$brew_log" 2>&1; then
        rm -f "$brew_log"
        hash -r 2>/dev/null || true
        return 0
    fi

    if grep -Eqi 'unknown or unsupported macOS version|MacOSVersion::Error' "$brew_log"; then
        if rainbond_use_chinese_prompt; then
            send_warn "当前 Homebrew 无法识别此 macOS 版本"
        else
            send_warn "Homebrew cannot run on this macOS version"
        fi
    else
        if rainbond_use_chinese_prompt; then
            send_warn "Homebrew 安装 OrbStack 失败"
        else
            send_warn "Homebrew failed to install OrbStack"
        fi
    fi
    rm -f "$brew_log"
    return 1
}

orbstack_download_arch() {
    case "$(uname -m 2>/dev/null)" in
        arm64|aarch64)
            echo "arm64"
            ;;
        x86_64|amd64|i386)
            echo "amd64"
            ;;
        *)
            return 1
            ;;
    esac
}

orbstack_install_dir() {
    if [ -n "${RAINBOND_ORBSTACK_INSTALL_DIR:-}" ]; then
        mkdir -p "$RAINBOND_ORBSTACK_INSTALL_DIR"
        echo "$RAINBOND_ORBSTACK_INSTALL_DIR"
        return
    fi

    if [ -w "/Applications" ]; then
        echo "/Applications"
        return
    fi

    mkdir -p "${HOME}/Applications"
    echo "${HOME}/Applications"
}

install_orbstack_from_dmg_macos() {
    local required_cmd
    for required_cmd in curl hdiutil find; do
        if ! command -v "$required_cmd" >/dev/null 2>&1; then
            if rainbond_use_chinese_prompt; then
                send_warn "无法通过官方安装包自动安装 OrbStack，缺少命令: ${required_cmd}"
            else
                send_warn "Cannot install OrbStack from the official installer, missing command: ${required_cmd}"
            fi
            return 1
        fi
    done

    local download_arch
    if ! download_arch=$(orbstack_download_arch); then
        if rainbond_use_chinese_prompt; then
            send_warn "无法通过官方安装包自动安装 OrbStack，不支持的 macOS 架构: $(uname -m 2>/dev/null)"
        else
            send_warn "Cannot install OrbStack from the official installer, unsupported macOS architecture: $(uname -m 2>/dev/null)"
        fi
        return 1
    fi

    local tmp_dir dmg_file mount_dir install_dir source_app target_app
    tmp_dir=$(mktemp -d "${TMPDIR:-/tmp}/rainbond-orbstack.XXXXXX")
    dmg_file="${tmp_dir}/OrbStack.dmg"
    mount_dir="${tmp_dir}/mount"
    install_dir=$(orbstack_install_dir)
    target_app="${install_dir}/OrbStack.app"

    local max_download_attempts="${RAINBOND_ORBSTACK_DOWNLOAD_RETRIES:-3}"
    case "$max_download_attempts" in
        ''|*[!0-9]*)
            max_download_attempts=3
            ;;
    esac
    if [ "$max_download_attempts" -lt 1 ]; then
        max_download_attempts=3
    fi

    local download_max_time="${RAINBOND_ORBSTACK_DOWNLOAD_MAX_TIME:-1800}"
    case "$download_max_time" in
        ''|*[!0-9]*)
            download_max_time=1800
            ;;
    esac
    if [ "$download_max_time" -lt 60 ]; then
        download_max_time=1800
    fi

    local download_attempt=1
    local download_completed=false
    while [ "$download_attempt" -le "$max_download_attempts" ]; do
        if rainbond_use_chinese_prompt; then
            send_info "正在下载 OrbStack 官方安装包..."
        else
            send_info "Downloading the official OrbStack installer..."
        fi

        if curl --fail --location --connect-timeout 30 --max-time "$download_max_time" -C - --progress-bar "https://orbstack.dev/download/stable/latest/${download_arch}" -o "$dmg_file"; then
            download_completed=true
            break
        fi

        if [ "$download_attempt" -lt "$max_download_attempts" ]; then
            if rainbond_use_chinese_prompt; then
                send_warn "OrbStack 安装包下载失败，正在续传重试 (${download_attempt}/${max_download_attempts})..."
            else
                send_warn "OrbStack installer download failed, retrying (${download_attempt}/${max_download_attempts})..."
            fi
            sleep 2
        fi
        download_attempt=$((download_attempt + 1))
    done

    if [ "$download_completed" != true ]; then
        rm -rf "$tmp_dir"
        if rainbond_use_chinese_prompt; then
            send_warn "OrbStack 安装包下载失败"
        else
            send_warn "Failed to download OrbStack installer"
        fi
        return 1
    fi

    mkdir -p "$mount_dir"
    if ! hdiutil attach "$dmg_file" -nobrowse -quiet -mountpoint "$mount_dir"; then
        rm -rf "$tmp_dir"
        if rainbond_use_chinese_prompt; then
            send_warn "OrbStack 安装包挂载失败"
        else
            send_warn "Failed to mount OrbStack installer"
        fi
        return 1
    fi

    source_app=$(find "$mount_dir" -maxdepth 2 -name "OrbStack.app" -type d | head -n 1)
    if [ -z "$source_app" ]; then
        hdiutil detach "$mount_dir" -quiet >/dev/null 2>&1 || true
        rm -rf "$tmp_dir"
        if rainbond_use_chinese_prompt; then
            send_warn "OrbStack 安装包中未找到 OrbStack.app"
        else
            send_warn "OrbStack.app was not found in the installer"
        fi
        return 1
    fi

    rm -rf "$target_app"
    if command -v ditto >/dev/null 2>&1; then
        if ! ditto "$source_app" "$target_app"; then
            hdiutil detach "$mount_dir" -quiet >/dev/null 2>&1 || true
            rm -rf "$tmp_dir"
            if rainbond_use_chinese_prompt; then
                send_warn "复制 OrbStack.app 失败"
            else
                send_warn "Failed to copy OrbStack.app"
            fi
            return 1
        fi
    else
        if ! cp -R "$source_app" "$install_dir/"; then
            hdiutil detach "$mount_dir" -quiet >/dev/null 2>&1 || true
            rm -rf "$tmp_dir"
            if rainbond_use_chinese_prompt; then
                send_warn "复制 OrbStack.app 失败"
            else
                send_warn "Failed to copy OrbStack.app"
            fi
            return 1
        fi
    fi

    hdiutil detach "$mount_dir" -quiet >/dev/null 2>&1 || true
    rm -rf "$tmp_dir"

    if rainbond_use_chinese_prompt; then
        send_info "OrbStack 已安装到 ${target_app}"
    else
        send_info "OrbStack installed to ${target_app}"
    fi
    return 0
}

start_orbstack_macos() {
    if rainbond_use_chinese_prompt; then
        send_info "正在启动 OrbStack..."
    else
        send_info "Starting OrbStack..."
    fi

    if command -v orb >/dev/null 2>&1 && orb >/dev/null 2>&1; then
        return 0
    fi

    if [ -d "/Applications/OrbStack.app" ] && command -v open >/dev/null 2>&1 && open -g "/Applications/OrbStack.app" >/dev/null 2>&1; then
        return 0
    fi

    if [ -d "${HOME}/Applications/OrbStack.app" ] && command -v open >/dev/null 2>&1 && open -g "${HOME}/Applications/OrbStack.app" >/dev/null 2>&1; then
        return 0
    fi

    if [ -n "${RAINBOND_ORBSTACK_INSTALL_DIR:-}" ] && [ -d "${RAINBOND_ORBSTACK_INSTALL_DIR}/OrbStack.app" ] && command -v open >/dev/null 2>&1 && open -g "${RAINBOND_ORBSTACK_INSTALL_DIR}/OrbStack.app" >/dev/null 2>&1; then
        return 0
    fi

    if command -v open >/dev/null 2>&1 && open -ga OrbStack >/dev/null 2>&1; then
        return 0
    fi

    return 1
}

wait_orbstack_docker_ready() {
    local wait_seconds
    wait_seconds=$(orbstack_wait_seconds)
    local elapsed=0

    while [ "$elapsed" -lt "$wait_seconds" ]; do
        if docker info >/dev/null 2>&1; then
            return 0
        fi
        sleep 2
        elapsed=$((elapsed + 2))
    done

    return 1
}

# Function to handle OrbStack requirement on macOS
handle_orbstack_macos() {
    if rainbond_use_chinese_prompt; then
        send_info "检查 OrbStack 安装状态..."
    else
        send_info "Checking OrbStack installation..."
    fi

    if ! check_orbstack_installed; then
        if ! install_orbstack_macos; then
            if rainbond_use_chinese_prompt; then
                send_error "macOS 上必须使用 OrbStack，请先安装 OrbStack 后重新执行脚本.\n\t下载地址: https://orbstack.dev/\n\t如需脚本自动安装，请执行: RAINBOND_AUTO_INSTALL_ORBSTACK=true bash ./install.sh"
            else
                send_error "OrbStack is required on macOS. Please install OrbStack and re-run this script.\n\tDownload: https://orbstack.dev/\n\tTo let this script install it automatically, run: RAINBOND_AUTO_INSTALL_ORBSTACK=true bash ./install.sh"
            fi
            exit 1
        fi
    fi

    if ! check_orbstack_running || ! docker info >/dev/null 2>&1; then
        if ! start_orbstack_macos || ! wait_orbstack_docker_ready; then
            if rainbond_use_chinese_prompt; then
                send_error "OrbStack 启动后 Docker 仍不可用，请检查 OrbStack 授权和 Docker 兼容模式后重新执行脚本."
            else
                send_error "Docker is still unavailable after starting OrbStack. Please check OrbStack permissions and Docker compatibility, then re-run this script."
            fi
            exit 1
        fi
    fi

    # Check if Docker is available through OrbStack
    if ! docker info >/dev/null 2>&1; then
        if rainbond_use_chinese_prompt; then
            send_error "OrbStack 已运行，但 Docker 不可用。请检查 OrbStack 配置."
        else
            send_error "OrbStack is running, but Docker is not available. Please check OrbStack configuration."
        fi
        exit 1
    fi

    if rainbond_use_chinese_prompt; then
        send_info "✓ OrbStack 检查通过"
    else
        send_info "✓ OrbStack check passed"
    fi
}

# Function to handle Docker Desktop on macOS (deprecated, use OrbStack instead)
handle_docker_desktop_macos() {
    handle_orbstack_macos
}

# Function to create containerd systemd service file
create_containerd_service() {
    if rainbond_use_chinese_prompt; then
        send_info "创建 containerd systemd 服务文件..."
    else
        send_info "Creating containerd systemd service file..."
    fi
    
    # Create containerd.service file
    cat > /etc/systemd/system/containerd.service << 'EOF'
# Copyright The containerd Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

[Unit]
Description=containerd container runtime
Documentation=https://containerd.io
After=network.target local-fs.target dbus.service

[Service]
#uncomment to enable the experimental sbservice (sandboxed) version of containerd/cri integration
#Environment="ENABLE_CRI_SANDBOXES=sandboxed"
ExecStartPre=-/sbin/modprobe overlay
ExecStart=/usr/bin/containerd

Type=notify
Delegate=yes
KillMode=process
Restart=always
RestartSec=5
# Having non-zero Limit*s causes performance problems due to accounting overhead
# in the kernel. We recommend using cgroups to do container-local accounting.
LimitNPROC=infinity
LimitCORE=infinity
LimitNOFILE=infinity
# Comment TasksMax if your systemd version does not supports it.
# Only systemd 226 and above support this version.
TasksMax=infinity
OOMScoreAdjust=-999

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd
    systemctl daemon-reload
}

# Function to create Docker systemd service file
create_docker_service() {
    if rainbond_use_chinese_prompt; then
        send_info "创建 Docker systemd 服务文件..."
    else
        send_info "Creating Docker systemd service file..."
    fi
    
    # Create docker.service file
    cat > /etc/systemd/system/docker.service << 'EOF'
[Unit]
Description=Docker Application Container Engine
Documentation=https://docs.docker.com
After=network-online.target nss-lookup.target docker.socket firewalld.service containerd.service time-set.target
Wants=network-online.target containerd.service
Requires=docker.socket
StartLimitBurst=3
StartLimitIntervalSec=60

[Service]
Type=notify
# the default is not to use systemd for cgroups because the delegate issues still
# exists and systemd currently does not support the cgroup feature set required
# for containers run by docker
ExecStart=/usr/bin/dockerd -H fd:// --containerd=/run/containerd/containerd.sock
ExecReload=/bin/kill -s HUP $MAINPID
TimeoutStartSec=0
RestartSec=2
Restart=always

# Having non-zero Limit*s causes performance problems due to accounting overhead
# in the kernel. We recommend using cgroups to do container-local accounting.
LimitNPROC=infinity
LimitCORE=infinity

# Comment TasksMax if your systemd version does not support it.
# Only systemd 226 and above support this option.
TasksMax=infinity

# set delegate yes so that systemd does not reset the cgroups of docker containers
Delegate=yes

# kill only the docker process, not all processes in the cgroup
KillMode=process
OOMScoreAdjust=-500

[Install]
WantedBy=multi-user.target
EOF
    
    # Create docker.socket file
    cat > /etc/systemd/system/docker.socket << 'EOF'
[Unit]
Description=Docker Socket for the API

[Socket]
ListenStream=/var/run/docker.sock
SocketMode=0660
SocketUser=root
SocketGroup=docker

[Install]
WantedBy=sockets.target
EOF
    
    # Reload systemd
    systemctl daemon-reload
}

restore_docker_binaries() {
    local backup_dir=$1
    local docker_bin_dir=$2
    local binary

    if [ -d "${backup_dir}/binaries" ]; then
        for binary in "${backup_dir}/binaries"/*; do
            [ -f "$binary" ] || continue
            cp -p "$binary" "${docker_bin_dir}/$(basename "$binary")" || return 1
        done
    fi

    if [ -f "${backup_dir}/introduced-binaries" ]; then
        while IFS= read -r binary; do
            [ -n "$binary" ] || continue
            rm -f "${docker_bin_dir}/${binary}" || return 1
        done <"${backup_dir}/introduced-binaries"
    fi
}

docker_upgrade_restore_before_start() {
    local backup_dir=$1
    local docker_bin_dir=$2
    local running_containers=$3
    local reason=$4

    restore_docker_binaries "$backup_dir" "$docker_bin_dir" || true
    start_docker_after_upgrade || true
    restore_previously_running_containers "$running_containers" || true
    if rainbond_use_chinese_prompt; then
        send_error "${reason}；已尝试恢复升级前 Docker，备份目录: ${backup_dir}"
    else
        send_error "${reason}; the previous Docker installation was restored where possible. Backup: ${backup_dir}"
    fi
}

start_docker_after_upgrade() {
    systemctl start containerd >/dev/null 2>&1 && \
        systemctl start docker.socket >/dev/null 2>&1 && \
        systemctl start docker >/dev/null 2>&1
}

stop_docker_for_upgrade() {
    systemctl stop docker.socket >/dev/null 2>&1 || return 1
    systemctl stop docker >/dev/null 2>&1 || return 1
    systemctl stop containerd >/dev/null 2>&1 || return 1

    ! systemctl is-active --quiet docker.socket >/dev/null 2>&1 && \
        ! systemctl is-active --quiet docker >/dev/null 2>&1 && \
        ! systemctl is-active --quiet containerd >/dev/null 2>&1
}

restore_previously_running_containers() {
    local container_id failed=false
    while IFS= read -r container_id; do
        [ -n "$container_id" ] || continue
        if [ "$(docker inspect --format '{{.State.Running}}' "$container_id" 2>/dev/null || true)" = "true" ]; then
            continue
        fi
        if ! docker start "$container_id" >/dev/null 2>&1 || \
           [ "$(docker inspect --format '{{.State.Running}}' "$container_id" 2>/dev/null || true)" != "true" ]; then
            failed=true
        fi
    done <<EOF
${1:-}
EOF
    [ "$failed" = false ]
}

rollback_docker_upgrade() {
    local backup_dir=$1
    local docker_bin_dir=$2
    local running_containers=$3
    local original_version=$4
    local reason_zh=$5
    local reason_en=$6

    if ! stop_docker_for_upgrade; then
        if rainbond_use_chinese_prompt; then
            send_error "${reason_zh}；新版 Docker 无法完全停止，为避免产生混合二进制版本，脚本未覆盖任何文件。请根据备份目录人工恢复: ${backup_dir}"
        else
            send_error "${reason_en}; the new Docker runtime could not be stopped completely. No files were overwritten during rollback to avoid mixed binary versions. Recover manually from: ${backup_dir}"
        fi
        return 1
    fi
    if ! restore_docker_binaries "$backup_dir" "$docker_bin_dir"; then
        if rainbond_use_chinese_prompt; then
            send_error "${reason_zh}；恢复旧 Docker 二进制失败，请根据备份目录人工恢复: ${backup_dir}"
        else
            send_error "${reason_en}; restoring the previous Docker binaries failed. Recover manually from: ${backup_dir}"
        fi
        return 1
    fi

    if start_docker_after_upgrade && [ "$(get_docker_version)" = "$original_version" ] && \
        restore_previously_running_containers "$running_containers"; then
        if rainbond_use_chinese_prompt; then
            send_error "${reason_zh}；已恢复升级前 Docker ${original_version}。跨版本启动可能已写入运行时元数据，请继续检查原有服务；备份目录: ${backup_dir}"
        else
            send_error "${reason_en}; Docker ${original_version} was restored. The attempted cross-version start may have written runtime metadata, so verify existing services. Backup: ${backup_dir}"
        fi
    else
        if rainbond_use_chinese_prompt; then
            send_error "${reason_zh}；自动恢复升级前 Docker 失败，请立即根据备份目录人工恢复: ${backup_dir}"
        else
            send_error "${reason_en}; automatic restoration of the previous Docker failed. Recover it manually from: ${backup_dir}"
        fi
    fi
}

upgrade_docker_from_bundle() {
    local bundle_dir=$1
    local backup_root docker_bin_dir backup_dir binary source target temp_target
    local running_containers docker_root storage_driver installed_version original_version
    backup_root="${RAINBOND_DOCKER_UPGRADE_BACKUP_ROOT:-/var/lib/rainbond}"
    if [ -n "${RAINBOND_DOCKER_BIN_DIR:-}" ]; then
        docker_bin_dir="$RAINBOND_DOCKER_BIN_DIR"
    else
        docker_bin_dir=$(dirname "$(command -v dockerd 2>/dev/null || printf '/usr/bin/dockerd')")
    fi
    backup_dir="${backup_root}/docker-upgrade-backup-$(date +%Y%m%d%H%M%S)-$$"
    if ! running_containers=$(docker ps -q 2>/dev/null) || \
       ! docker_root=$(docker info --format '{{.DockerRootDir}}' 2>/dev/null) || \
       ! storage_driver=$(docker info --format '{{.Driver}}' 2>/dev/null); then
        if rainbond_use_chinese_prompt; then
            send_error "停止 Docker 前无法读取完整运行状态，未执行升级"
        else
            send_error "The complete Docker runtime state could not be read before stopping the daemon; no upgrade was performed"
        fi
        return 1
    fi
    original_version=$(get_docker_version)
    if [ -z "$docker_root" ] || [ -z "$storage_driver" ] || [ -z "$original_version" ]; then
        if rainbond_use_chinese_prompt; then
            send_error "Docker 数据目录、存储驱动或版本为空，未执行升级"
        else
            send_error "Docker root directory, storage driver, or version is empty; no upgrade was performed"
        fi
        return 1
    fi

    if [ ! -d "$bundle_dir" ] || [ ! -d "$docker_bin_dir" ]; then
        return 1
    fi

    mkdir -p "$backup_dir/binaries" "$backup_dir/config" || return 1
    chmod 700 "$backup_dir" || return 1

    for binary in $DOCKER_UPGRADE_BINARIES; do
        source="${bundle_dir}/${binary}"
        [ -f "$source" ] && [ ! -L "$source" ] || return 1
        target="${docker_bin_dir}/${binary}"
        if [ -f "$target" ]; then
            cp -p "$target" "${backup_dir}/binaries/${binary}" || return 1
        else
            printf '%s\n' "$binary" >>"${backup_dir}/introduced-binaries"
        fi
    done

    if [ -d /etc/docker ]; then
        cp -a /etc/docker "${backup_dir}/config/docker" || return 1
    fi
    systemctl cat docker >"${backup_dir}/config/docker.service.effective" 2>/dev/null || true
    systemctl cat docker.socket >"${backup_dir}/config/docker.socket.effective" 2>/dev/null || true
    systemctl cat containerd >"${backup_dir}/config/containerd.service.effective" 2>/dev/null || true
    printf 'docker_version=%s\ndocker_root=%s\nstorage_driver=%s\nrunning_containers=%s\n' \
        "$original_version" "$docker_root" "$storage_driver" "$running_containers" >"${backup_dir}/upgrade-state"

    if rainbond_use_chinese_prompt; then
        send_info "Docker 升级备份已保存到 ${backup_dir}"
    else
        send_info "Docker upgrade backup saved to ${backup_dir}"
    fi

    if [ -f /etc/docker/daemon.json ] && ! "$bundle_dir/dockerd" --validate --config-file /etc/docker/daemon.json >/dev/null 2>&1; then
        if rainbond_use_chinese_prompt; then
            send_error "现有 /etc/docker/daemon.json 无法通过 Docker ${DOCKER_RECOMMENDED_VERSION} 配置校验，未执行升级"
        else
            send_error "The existing /etc/docker/daemon.json is not valid for Docker ${DOCKER_RECOMMENDED_VERSION}; no upgrade was performed"
        fi
        return 1
    fi

    if ! stop_docker_for_upgrade; then
        start_docker_after_upgrade || true
        restore_previously_running_containers "$running_containers" || true
        if rainbond_use_chinese_prompt; then
            send_error "无法完全停止 Docker、docker.socket 或 containerd，未执行升级"
        else
            send_error "Docker, docker.socket, or containerd could not be stopped completely; no upgrade was performed"
        fi
        return 1
    fi

    for binary in $DOCKER_UPGRADE_BINARIES; do
        source="${bundle_dir}/${binary}"
        target="${docker_bin_dir}/${binary}"
        temp_target="${target}.rainbond-upgrade.$$"
        if ! cp "$source" "$temp_target" || ! chmod 0755 "$temp_target" || ! mv -f "$temp_target" "$target"; then
            rm -f "$temp_target"
            if rainbond_use_chinese_prompt; then
                docker_upgrade_restore_before_start "$backup_dir" "$docker_bin_dir" "$running_containers" "Docker 二进制替换失败"
            else
                docker_upgrade_restore_before_start "$backup_dir" "$docker_bin_dir" "$running_containers" "Failed to replace Docker binaries"
            fi
            return 1
        fi
    done

    if ! start_docker_after_upgrade || ! docker info >/dev/null 2>&1; then
        rollback_docker_upgrade "$backup_dir" "$docker_bin_dir" "$running_containers" "$original_version" \
            "Docker ${DOCKER_RECOMMENDED_VERSION} 启动失败" \
            "Docker ${DOCKER_RECOMMENDED_VERSION} failed to start"
        return 1
    fi

    installed_version=$(get_docker_version)
    if [ "$installed_version" != "$DOCKER_RECOMMENDED_VERSION" ]; then
        rollback_docker_upgrade "$backup_dir" "$docker_bin_dir" "$running_containers" "$original_version" \
            "Docker 升级后版本校验失败，当前版本: ${installed_version:-unknown}" \
            "Docker version verification failed after upgrade; current version: ${installed_version:-unknown}"
        return 1
    fi

    if [ "$(docker info --format '{{.DockerRootDir}}' 2>/dev/null || true)" != "$docker_root" ] || \
       [ "$(docker info --format '{{.Driver}}' 2>/dev/null || true)" != "$storage_driver" ]; then
        rollback_docker_upgrade "$backup_dir" "$docker_bin_dir" "$running_containers" "$original_version" \
            "Docker 升级后数据目录或存储驱动发生变化" \
            "Docker root directory or storage driver changed after upgrade"
        return 1
    fi

    if [ -n "$running_containers" ]; then
        restore_previously_running_containers "$running_containers" || {
            rollback_docker_upgrade "$backup_dir" "$docker_bin_dir" "$running_containers" "$original_version" \
                "部分原有容器无法恢复运行" \
                "Some previously running containers could not be restarted"
            return 1
        }
    fi

    if rainbond_use_chinese_prompt; then
        send_info "Docker 已成功升级到 $(get_docker_version)"
    else
        send_info "Docker was successfully upgraded to $(get_docker_version)"
    fi
    return 0
}

docker_archive_checksum() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{print $1}'
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$1" | awk '{print $1}'
    else
        return 1
    fi
}

verify_docker_upgrade_archive() {
    local docker_file=$1
    local expected_sha=$2
    local actual_sha entries expected_entries

    actual_sha=$(docker_archive_checksum "$docker_file" 2>/dev/null || true)
    [ -n "$actual_sha" ] && [ "$actual_sha" = "$expected_sha" ] || return 1

    if ! tar -tvzf "$docker_file" 2>/dev/null | awk '$1 !~ /^[-d]/ { exit 1 }'; then
        return 1
    fi
    entries=$(tar -tzf "$docker_file" 2>/dev/null | LC_ALL=C sort) || return 1
    expected_entries=$(printf '%s\n' \
        docker/ \
        docker/containerd \
        docker/containerd-shim-runc-v2 \
        docker/ctr \
        docker/docker \
        docker/docker-init \
        docker/docker-proxy \
        docker/dockerd \
        docker/runc | LC_ALL=C sort)
    [ "$entries" = "$expected_entries" ]
}

# Function to install Docker on Linux using binary installation
install_docker_linux() {
    local install_mode="${1:-fresh}"

    if [ "$install_mode" = "upgrade" ]; then
        if rainbond_use_chinese_prompt; then
            send_info "开始将静态二进制 Docker 原地升级到 ${DOCKER_RECOMMENDED_VERSION}..."
        else
            send_info "Starting in-place static Docker upgrade to ${DOCKER_RECOMMENDED_VERSION}..."
        fi
    elif rainbond_use_chinese_prompt; then
        send_info "未检测到 Docker 环境，开始二进制安装..."
    else
        send_info "Docker not detected, starting binary installation..."
    fi
    
    # Determine Docker binary URL based on architecture
    local docker_url docker_expected_sha
    if [ "$ARCH_TYPE" = "amd64" ]; then
        docker_url="https://mirrors.tuna.tsinghua.edu.cn/docker-ce/linux/static/stable/x86_64/docker-${DOCKER_RECOMMENDED_VERSION}.tgz"
        docker_expected_sha="$DOCKER_INSTALL_SHA256_AMD64"
    elif [ "$ARCH_TYPE" = "arm64" ]; then
        docker_url="https://mirrors.tuna.tsinghua.edu.cn/docker-ce/linux/static/stable/aarch64/docker-${DOCKER_RECOMMENDED_VERSION}.tgz"
        docker_expected_sha="$DOCKER_INSTALL_SHA256_ARM64"
    fi
    
    # Check if Docker binary already exists and is complete
    local docker_file="/tmp/docker.tgz"
    local docker_work_dir=""
    if [ "$install_mode" = "upgrade" ]; then
        docker_work_dir=$(mktemp -d /tmp/rainbond-docker-upgrade.XXXXXX) || return 1
        chmod 700 "$docker_work_dir" || return 1
        docker_file="${docker_work_dir}/docker.tgz"
    fi
    local download_needed=true
    
    if [ -f "$docker_file" ]; then
        if rainbond_use_chinese_prompt; then
            send_info "检测到已存在的Docker二进制文件，正在验证完整性..."
        else
            send_info "Found existing Docker binary file, verifying integrity..."
        fi
        
         # Check if tar command is available
        if ! command -v tar >/dev/null 2>&1; then
          if rainbond_use_chinese_prompt; then
            send_error "tar 命令未找到，请安装 tar 软件包"
          else
            send_error "tar command not found - please install tar package"
          fi
          exit 1
        fi
    
        # Try to test if the file is a valid tar.gz
        if tar -tzf "$docker_file" >/dev/null 2>&1; then
            if rainbond_use_chinese_prompt; then
                send_info "文件完整，跳过下载"
            else
                send_info "File is complete, skipping download"
            fi
            download_needed=false
        else
            if rainbond_use_chinese_prompt; then
                send_warn "文件损坏或不完整，重新下载"
            else
                send_warn "File is corrupted or incomplete, re-downloading"
            fi
            rm -f "$docker_file"
        fi
    fi
    
    # Download Docker binary with progress and resume capability
    if [ "$download_needed" = true ]; then
        local max_download_attempts="${RAINBOND_DOCKER_DOWNLOAD_RETRIES:-3}"
        case "$max_download_attempts" in
            ''|*[!0-9]*)
                max_download_attempts=3
                ;;
        esac
        if [ "$max_download_attempts" -lt 1 ]; then
            max_download_attempts=3
        fi

        local docker_tmp_file="${docker_file}.download"
        local download_verified=false
        local download_attempt=1

        while [ "$download_attempt" -le "$max_download_attempts" ]; do
            rm -f "$docker_tmp_file"

            if rainbond_use_chinese_prompt; then
                send_info "正在下载Docker二进制文件... $docker_url"
            else
                send_info "Downloading Docker binary... $docker_url"
            fi

            if curl --fail --connect-timeout 30 --max-time 600 --progress-bar -L "$docker_url" -o "$docker_tmp_file"; then
                if { [ "$install_mode" = "upgrade" ] && verify_docker_upgrade_archive "$docker_tmp_file" "$docker_expected_sha"; } || \
                   { [ "$install_mode" != "upgrade" ] && tar -tzf "$docker_tmp_file" >/dev/null 2>&1; }; then
                    mv "$docker_tmp_file" "$docker_file"
                    download_verified=true
                    break
                fi

                rm -f "$docker_tmp_file"
                if [ "$download_attempt" -lt "$max_download_attempts" ]; then
                    if rainbond_use_chinese_prompt; then
                        send_warn "下载的Docker二进制文件损坏，正在重试 (${download_attempt}/${max_download_attempts})..."
                    else
                        send_warn "Downloaded Docker binary is corrupted, retrying (${download_attempt}/${max_download_attempts})..."
                    fi
                fi
            else
                rm -f "$docker_tmp_file"
                if [ "$download_attempt" -lt "$max_download_attempts" ]; then
                    if rainbond_use_chinese_prompt; then
                        send_warn "Docker二进制文件下载失败，正在重试 (${download_attempt}/${max_download_attempts})..."
                    else
                        send_warn "Docker binary download failed, retrying (${download_attempt}/${max_download_attempts})..."
                    fi
                fi
            fi

            download_attempt=$((download_attempt + 1))
            sleep 2
        done

        if [ "$download_verified" != true ]; then
            if rainbond_use_chinese_prompt; then
                send_error "Docker二进制文件多次下载或校验失败，请检查网络、代理或磁盘空间后重试"
            else
                send_error "Docker binary download or verification failed after retries. Please check network, proxy, or disk space and try again"
            fi
            rm -f "$docker_tmp_file" "$docker_file"
            if [ "$install_mode" = "upgrade" ]; then
                rm -rf "$docker_work_dir"
                return 1
            fi
            exit 1
        fi
    fi

    if [ "$install_mode" = "upgrade" ]; then
        local docker_extract_dir="${docker_work_dir}/extract"
        mkdir -p "$docker_extract_dir" || return 1
        if ! tar -xzf "$docker_file" -C "$docker_extract_dir"; then
            rm -rf "$docker_work_dir"
            return 1
        fi
        if ! upgrade_docker_from_bundle "$docker_extract_dir/docker"; then
            rm -rf "$docker_work_dir"
            return 1
        fi
        rm -rf "$docker_work_dir"
        return 0
    fi

    # Extract Docker binary for a fresh installation.
    if ! tar -xzf "$docker_file" -C /tmp; then
        if rainbond_use_chinese_prompt; then
            send_error "Docker二进制文件解压失败"
        else
            send_error "Failed to extract Docker binary"
        fi
        rm -f "$docker_file"
        exit 1
    fi
    
    # Copy Docker binaries to /usr/bin
    if ! cp -r /tmp/docker/* /usr/bin/; then
        if rainbond_use_chinese_prompt; then
            send_error "Docker二进制文件复制失败"
        else
            send_error "Failed to copy Docker binaries"
        fi
        rm -rf /tmp/docker
        exit 1
    fi
    
    # Set executable permissions for all binaries
    chmod +x /usr/bin/docker* /usr/bin/containerd* /usr/bin/ctr /usr/bin/runc
    
    # Create docker group
    groupadd docker >/dev/null 2>&1 || true
    
    # Create containerd systemd service first (Docker depends on it)
    create_containerd_service
    
    # Create Docker systemd service
    create_docker_service
    
    # Clean up downloaded and extracted files
    rm -rf /tmp/docker
    rm -f "$docker_file"
    
    if rainbond_use_chinese_prompt; then
        send_info "Docker二进制安装完成"
    else
        send_info "Docker binary installation completed"
    fi

    # Start containerd first, then Docker service
    if systemctl enable containerd && systemctl start containerd >/dev/null 2>&1; then
        if rainbond_use_chinese_prompt; then
            send_info "containerd 服务启动成功"
        else
            send_info "containerd service started successfully"
        fi
        sleep 2

        # Now start Docker service
        if systemctl enable docker.socket && systemctl enable docker && systemctl start docker >/dev/null 2>&1; then
            if rainbond_use_chinese_prompt; then
                send_info "Docker 服务启动成功"
            else
                send_info "Docker service started successfully"
            fi
            sleep 3
        else
            if rainbond_use_chinese_prompt; then
                send_error "Docker 服务启动失败，请手动启动: systemctl start docker"
            else
                send_error "Docker service failed to start, please start manually: systemctl start docker"
            fi
            exit 1
        fi
    else
        if rainbond_use_chinese_prompt; then
            send_error "containerd 服务启动失败，请手动启动: systemctl start containerd"
        else
            send_error "containerd service failed to start, please start manually: systemctl start containerd"
        fi
        exit 1
    fi
}

# Function to handle Docker installation requirement on macOS
handle_docker_install_macos() {
    if rainbond_use_chinese_prompt; then
        send_error "未检测到 Docker 环境, macOS 上必须使用 OrbStack, 请先安装 OrbStack 然后重新执行本脚本.\n\t下载地址: https://orbstack.dev/"
    else
        send_error "Ops! Docker has not been installed. OrbStack is required on macOS.\nPlease visit the following website to get OrbStack.\n\tDownload: https://orbstack.dev/"
    fi
    exit 1
}


# Function to get the Docker daemon version. The CLI and daemon can differ, so
# checking `docker --version` is not sufficient for installation compatibility.
get_docker_version() {
    docker version --format '{{.Server.Version}}' 2>/dev/null | head -n 1
}

docker_version_number() {
    local version="${1%%-*}"
    local major=0 minor=0 patch=0
    IFS=. read -r major minor patch <<EOF
$version
EOF
    major=${major:-0}
    minor=${minor:-0}
    patch=${patch:-0}
    major=${major%%[^0-9]*}
    minor=${minor%%[^0-9]*}
    patch=${patch%%[^0-9]*}
    major=$((10#${major:-0}))
    minor=$((10#${minor:-0}))
    patch=$((10#${patch:-0}))
    printf '%d%03d%03d\n' "$major" "$minor" "$patch"
}

docker_version_is_supported() {
    local current_version=$1
    local release_version
    release_version=$(printf '%s' "$current_version" | sed -n 's/^\([0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*\).*$/\1/p')
    [ -n "$release_version" ] || return 1
    case "$current_version" in
        *-rc* | *-beta* | *-alpha*)
            return 1
            ;;
    esac
    [ "$(docker_version_number "$release_version")" -ge "$(docker_version_number "$DOCKER_MIN_VERSION")" ]
}

docker_upgrade_reject() {
    if rainbond_use_chinese_prompt; then
        send_error "$1"
    else
        send_error "$2"
    fi
    return 1
}

docker_package_owner_dpkg() {
    local binary=$1 owner ownership
    command -v dpkg-query >/dev/null 2>&1 || return 1
    ownership=$(dpkg-query -S "$binary" 2>/dev/null) || return 1
    owner=$(printf '%s\n' "$ownership" | awk -F ': ' -v binary="$binary" '$2 == binary { print $1; exit }')
    owner=${owner%%:*}
    case "$owner" in
        '' | [!A-Za-z0-9]* | *[!A-Za-z0-9.+-]*)
            return 2
            ;;
    esac
    printf '%s\n' "$owner"
}

docker_package_owner_rpm() {
    local binary=$1 owner
    command -v rpm >/dev/null 2>&1 || return 1
    owner=$(rpm -qf --queryformat '%{NAME}\n' "$binary" 2>/dev/null) || return 1
    owner=$(printf '%s\n' "$owner" | head -n 1)
    case "$owner" in
        '' | [!A-Za-z0-9]* | *[!A-Za-z0-9.+-]*)
            return 2
            ;;
    esac
    printf '%s\n' "$owner"
}

docker_binary_is_package_managed() {
    local binary=$1
    if command -v dpkg-query >/dev/null 2>&1 && dpkg-query -S "$binary" >/dev/null 2>&1; then
        return 0
    fi
    if command -v rpm >/dev/null 2>&1 && rpm -qf "$binary" >/dev/null 2>&1; then
        return 0
    fi
    return 1
}

detect_docker_install_source() {
    local dockerd_path package package_status
    DOCKER_UPGRADE_SOURCE="unknown"
    DOCKER_UPGRADE_PACKAGE=""
    DOCKER_UPGRADE_DOCKERD_PATH=""

    dockerd_path=$(command -v dockerd 2>/dev/null || true)
    [ -n "$dockerd_path" ] || return 1
    dockerd_path=$(readlink -f "$dockerd_path" 2>/dev/null || true)
    [ -n "$dockerd_path" ] || return 1
    DOCKER_UPGRADE_DOCKERD_PATH=$dockerd_path

    package=$(docker_package_owner_dpkg "$dockerd_path")
    package_status=$?
    if [ "$package_status" -eq 0 ]; then
        DOCKER_UPGRADE_SOURCE="apt"
        DOCKER_UPGRADE_PACKAGE=$package
        return 0
    elif [ "$package_status" -eq 2 ]; then
        return 1
    fi
    package=$(docker_package_owner_rpm "$dockerd_path")
    package_status=$?
    if [ "$package_status" -eq 0 ]; then
        if command -v dnf >/dev/null 2>&1; then
            DOCKER_UPGRADE_SOURCE="dnf"
        elif command -v yum >/dev/null 2>&1; then
            DOCKER_UPGRADE_SOURCE="yum"
        else
            return 1
        fi
        DOCKER_UPGRADE_PACKAGE=$package
        return 0
    elif [ "$package_status" -eq 2 ]; then
        return 1
    fi

    if [ -f "$dockerd_path" ] && [ ! -L "$dockerd_path" ]; then
        DOCKER_UPGRADE_SOURCE="static"
        return 0
    fi
    return 1
}

systemd_exec_start_path() {
    local unit=$1
    local exec_start path
    exec_start=$(systemctl show "$unit" --property=ExecStart --value 2>/dev/null || true)
    path=$(printf '%s\n' "$exec_start" | sed -n 's/.*[[:space:]{]path=\([^ ;}]*\).*/\1/p')
    if [ -z "$path" ]; then
        path=$(printf '%s\n' "$exec_start" | awk '{print $1}')
    fi
    readlink -f "$path" 2>/dev/null || true
}

docker_upgrade_common_preflight_linux() {
    local storage_driver swarm_state security_options endpoint shared_service namespaces

    if [ -n "${DOCKER_CONTEXT:-}" ] && [ "$DOCKER_CONTEXT" != "default" ]; then
        docker_upgrade_reject \
            "检测到非默认 DOCKER_CONTEXT=${DOCKER_CONTEXT}，安装脚本不会自动升级本机 Docker" \
            "A non-default DOCKER_CONTEXT=${DOCKER_CONTEXT} is active; the installer will not upgrade the local Docker daemon"
        return 1
    fi
    if [ -n "${DOCKER_HOST:-}" ]; then
        endpoint=$DOCKER_HOST
    else
        endpoint=$(docker context inspect --format '{{.Endpoints.docker.Host}}' 2>/dev/null | head -n 1 || true)
    fi
    case "$endpoint" in
        unix:///var/run/docker.sock | unix:///run/docker.sock)
            ;;
        *)
            docker_upgrade_reject \
                "当前 Docker endpoint 为 ${endpoint:-unknown}，安装脚本只允许升级本机 Docker" \
                "The current Docker endpoint is ${endpoint:-unknown}; the installer only upgrades the local Docker daemon"
            return 1
            ;;
    esac

    storage_driver=$(docker info --format '{{.Driver}}' 2>/dev/null || true)
    if [ "$storage_driver" != "overlay2" ]; then
        docker_upgrade_reject \
            "当前 Docker 存储驱动为 ${storage_driver:-unknown}，安装脚本仅支持自动升级 overlay2 环境" \
            "The current Docker storage driver is ${storage_driver:-unknown}; automatic upgrade is only supported for overlay2"
        return 1
    fi

    swarm_state=$(docker info --format '{{.Swarm.LocalNodeState}}' 2>/dev/null || true)
    case "$swarm_state" in
        '' | inactive)
            ;;
        *)
            docker_upgrade_reject \
                "检测到 Docker Swarm 状态为 ${swarm_state}，为避免影响现有集群，安装脚本不会自动升级 Docker" \
                "Docker Swarm is ${swarm_state}; the installer will not upgrade Docker because it may disrupt the existing cluster"
            return 1
            ;;
    esac

    security_options=$(docker info --format '{{json .SecurityOptions}}' 2>/dev/null || true)
    if printf '%s' "$security_options" | grep -qi rootless; then
        docker_upgrade_reject \
            "检测到 rootless Docker，安装脚本不支持自动升级该运行模式" \
            "Rootless Docker was detected; automatic upgrade is not supported for this runtime mode"
        return 1
    fi

    if command -v ctr >/dev/null 2>&1 && namespaces=$(ctr namespaces list -q 2>/dev/null); then
        namespaces=$(printf '%s\n' "$namespaces" | sed '/^moby$/d; /^$/d' | head -n 1 || true)
        if [ -n "$namespaces" ]; then
            docker_upgrade_reject \
                "检测到 containerd 命名空间 ${namespaces}，可能被其他服务共享，安装脚本不会自动升级 Docker" \
                "containerd namespace ${namespaces} may be shared by another service; the installer will not upgrade Docker"
            return 1
        fi
    elif [ "${DOCKER_UPGRADE_SOURCE:-}" != "static" ]; then
        if rainbond_use_chinese_prompt; then
            send_warn "无法通过 ctr 枚举 containerd 命名空间；将由原包管理器处理依赖，但仍会检查已知容器编排服务"
        else
            send_warn "containerd namespaces could not be enumerated with ctr; dependency handling is delegated to the original package manager while known orchestrator services are still checked"
        fi
    fi

    if [ -z "$(command -v docker 2>/dev/null || true)" ] || [ -z "${DOCKER_UPGRADE_DOCKERD_PATH:-}" ]; then
        docker_upgrade_reject \
            "无法定位 Docker CLI 或 dockerd，安装脚本不会自动覆盖该环境" \
            "Docker CLI or dockerd could not be located; the installer will not overwrite this environment"
        return 1
    fi

    for shared_service in kubelet k3s rke2-server rke2-agent nomad; do
        if systemctl is-active --quiet "$shared_service" >/dev/null 2>&1; then
            docker_upgrade_reject \
                "检测到 ${shared_service} 服务正在运行，可能依赖现有容器运行时，安装脚本不会自动升级 Docker" \
                "The ${shared_service} service is running and may depend on the current container runtime; the installer will not upgrade Docker"
            return 1
        fi
    done

    return 0
}

docker_package_upgrade_preflight_linux() {
    local docker_exec
    if ! command -v systemctl >/dev/null 2>&1 || ! systemctl is-active --quiet docker >/dev/null 2>&1; then
        docker_upgrade_reject \
            "无法确认当前 Docker 由本机 docker.service 管理，安装脚本不会自动调用包管理器升级" \
            "The installer could not confirm that the current Docker daemon is managed by the local docker.service and will not invoke the package manager"
        return 1
    fi
    docker_exec=$(systemd_exec_start_path docker)
    if [ "$docker_exec" != "${DOCKER_UPGRADE_DOCKERD_PATH:-}" ]; then
        docker_upgrade_reject \
            "docker.service 的 ExecStart 与当前软件包中的 dockerd 不一致，安装脚本不会自动升级该环境" \
            "docker.service ExecStart does not match the package-owned dockerd; the installer will not upgrade this environment"
        return 1
    fi
    return 0
}

docker_package_upgrade_candidates() {
    local package_manager=$1 daemon_package=$2
    case "$package_manager" in
        apt | dnf | yum)
            ;;
        *)
            return 1
            ;;
    esac
    case "$daemon_package" in
        '' | [!A-Za-z0-9]* | *[!A-Za-z0-9.+-]*)
            return 1
            ;;
    esac
    printf '%s\n' "$daemon_package"
}

wait_for_docker_after_package_upgrade() {
    local attempt=1
    while [ "$attempt" -le 30 ]; do
        if docker info >/dev/null 2>&1; then
            return 0
        fi
        sleep 1
        attempt=$((attempt + 1))
    done
    return 1
}

restart_docker_after_package_upgrade() {
    systemctl restart docker >/dev/null 2>&1 || return 1
    wait_for_docker_after_package_upgrade
}

upgrade_docker_with_package_manager() {
    local package_manager=$1 daemon_package=$2 packages
    local running_containers docker_root storage_driver original_version installed_version
    local -a package_list

    if ! running_containers=$(docker ps -q 2>/dev/null) || \
       ! docker_root=$(docker info --format '{{.DockerRootDir}}' 2>/dev/null) || \
       ! storage_driver=$(docker info --format '{{.Driver}}' 2>/dev/null); then
        docker_upgrade_reject \
            "升级前无法读取完整 Docker 运行状态，未调用包管理器" \
            "The complete Docker runtime state could not be read before upgrade; the package manager was not invoked"
        return 1
    fi
    original_version=$(get_docker_version)
    if [ -z "$docker_root" ] || [ -z "$storage_driver" ] || [ -z "$original_version" ]; then
        docker_upgrade_reject \
            "Docker 数据目录、存储驱动或版本为空，未调用包管理器" \
            "Docker root directory, storage driver, or version is empty; the package manager was not invoked"
        return 1
    fi
    if ! packages=$(docker_package_upgrade_candidates "$package_manager" "$daemon_package"); then
        docker_upgrade_reject \
            "无法确定需要升级的已安装 Docker 软件包，未执行升级" \
            "The installed Docker package set could not be determined; no upgrade was performed"
        return 1
    fi
    read -r -a package_list <<<"$packages"

    if rainbond_use_chinese_prompt; then
        send_info "将使用原 ${package_manager} 软件源升级已安装软件包: ${packages}"
    else
        send_info "Upgrading installed packages from the original ${package_manager} repository: ${packages}"
    fi

    case "$package_manager" in
        apt)
            if ! apt-get update || ! DEBIAN_FRONTEND=noninteractive apt-get install -y --only-upgrade "${package_list[@]}"; then
                systemctl start docker >/dev/null 2>&1 || true
                restore_previously_running_containers "$running_containers" || true
                docker_upgrade_reject \
                    "Docker 包管理器升级失败；软件包可能已部分变更，脚本不会自动降级，请检查 apt 输出和现有服务" \
                    "The Docker package-manager upgrade failed; packages may have changed partially and will not be downgraded automatically. Check the apt output and existing services"
                return 1
            fi
            ;;
        dnf)
            if ! dnf upgrade -y "${package_list[@]}"; then
                systemctl start docker >/dev/null 2>&1 || true
                restore_previously_running_containers "$running_containers" || true
                docker_upgrade_reject \
                    "Docker 包管理器升级失败；软件包可能已部分变更，脚本不会自动降级，请检查 dnf 输出和现有服务" \
                    "The Docker package-manager upgrade failed; packages may have changed partially and will not be downgraded automatically. Check the dnf output and existing services"
                return 1
            fi
            ;;
        yum)
            if ! yum upgrade -y "${package_list[@]}"; then
                systemctl start docker >/dev/null 2>&1 || true
                restore_previously_running_containers "$running_containers" || true
                docker_upgrade_reject \
                    "Docker 包管理器升级失败；软件包可能已部分变更，脚本不会自动降级，请检查 yum 输出和现有服务" \
                    "The Docker package-manager upgrade failed; packages may have changed partially and will not be downgraded automatically. Check the yum output and existing services"
                return 1
            fi
            ;;
        *)
            return 1
            ;;
    esac

    if ! restart_docker_after_package_upgrade; then
        systemctl start docker >/dev/null 2>&1 || true
        restore_previously_running_containers "$running_containers" || true
        docker_upgrade_reject \
            "包升级后 Docker 服务未恢复，请检查服务状态；脚本不会自动降级软件包" \
            "Docker did not recover after the package upgrade. Check the service status; packages will not be downgraded automatically"
        return 1
    fi

    installed_version=$(get_docker_version)
    if [ -z "$installed_version" ] || ! docker_version_is_supported "$installed_version"; then
        restore_previously_running_containers "$running_containers" || true
        docker_upgrade_reject \
            "Docker 包升级后版本校验失败，当前版本: ${installed_version:-unknown}，要求最低版本: ${DOCKER_MIN_VERSION}" \
            "Docker version verification failed after the package upgrade; current version: ${installed_version:-unknown}, minimum: ${DOCKER_MIN_VERSION}"
        return 1
    fi
    if [ "$(docker info --format '{{.DockerRootDir}}' 2>/dev/null || true)" != "$docker_root" ] || \
       [ "$(docker info --format '{{.Driver}}' 2>/dev/null || true)" != "$storage_driver" ]; then
        restore_previously_running_containers "$running_containers" || true
        docker_upgrade_reject \
            "Docker 包升级后数据目录或存储驱动发生变化，请立即检查原有服务" \
            "Docker root directory or storage driver changed after the package upgrade; inspect existing services immediately"
        return 1
    fi
    if ! restore_previously_running_containers "$running_containers"; then
        docker_upgrade_reject \
            "Docker 已升级，但部分升级前运行的容器无法恢复，请立即检查原有服务" \
            "Docker was upgraded, but some previously running containers could not be restored; inspect existing services immediately"
        return 1
    fi

    if rainbond_use_chinese_prompt; then
        send_info "Docker 已通过 ${package_manager} 从 ${original_version} 升级到 ${installed_version}"
    else
        send_info "Docker was upgraded through ${package_manager} from ${original_version} to ${installed_version}"
    fi
    return 0
}

docker_static_upgrade_preflight_linux() {
    local docker_path dockerd_path binary binary_path binary_dir namespaces docker_exec containerd_exec

    docker_path=$(command -v docker 2>/dev/null || true)
    dockerd_path=${DOCKER_UPGRADE_DOCKERD_PATH:-}
    docker_path=$(readlink -f "$docker_path" 2>/dev/null || true)
    binary_dir=$(dirname "$dockerd_path")
    for binary in $DOCKER_UPGRADE_BINARIES; do
        binary_path=$(command -v "$binary" 2>/dev/null || true)
        if [ -z "$binary_path" ]; then
            case " $DOCKER_UPGRADE_REQUIRED_EXISTING_BINARIES " in
                *" $binary "*)
                    docker_upgrade_reject \
                        "Docker 二进制 ${binary} 缺失，仅支持标准静态二进制安装" \
                        "Docker binary ${binary} is missing; only standard static binary installations are supported"
                    return 1
                    ;;
            esac
            continue
        fi
        if [ -L "$binary_path" ]; then
            docker_upgrade_reject \
                "Docker 二进制 ${binary} 为符号链接，仅支持标准静态二进制安装" \
                "Docker binary ${binary} is a symbolic link; only standard static binary installations are supported"
            return 1
        fi
        binary_path=$(readlink -f "$binary_path" 2>/dev/null || true)
        if [ -z "$binary_path" ] || [ "$(dirname "$binary_path")" != "$binary_dir" ] || \
           docker_binary_is_package_managed "$binary_path"; then
            docker_upgrade_reject \
                "Docker 二进制布局不是脚本可安全覆盖的纯静态安装，可能混用了包管理器文件，请人工升级 Docker" \
                "The Docker binary layout is not a safely replaceable pure static installation and may contain package-managed files; upgrade Docker manually"
            return 1
        fi
    done

    if ! namespaces=$(ctr namespaces list -q 2>/dev/null); then
        docker_upgrade_reject \
            "无法确认 containerd 是否被其他服务共享，安装脚本不会自动升级 Docker" \
            "The installer could not determine whether containerd is shared by another service and will not upgrade Docker"
        return 1
    fi
    namespaces=$(printf '%s\n' "$namespaces" | sed '/^moby$/d; /^$/d' | head -n 1 || true)
    if [ -n "$namespaces" ]; then
        docker_upgrade_reject \
            "检测到 containerd 命名空间 ${namespaces}，可能被其他服务共享，安装脚本不会自动升级 Docker" \
            "containerd namespace ${namespaces} may be shared by another service; the installer will not upgrade Docker"
        return 1
    fi

    if ! systemctl cat docker >/dev/null 2>&1 || ! systemctl cat docker.socket >/dev/null 2>&1 || \
       ! systemctl cat containerd >/dev/null 2>&1; then
        docker_upgrade_reject \
            "未检测到标准的 docker.service、docker.socket 和 containerd.service，无法安全执行自动升级" \
            "Standard docker.service, docker.socket, and containerd.service units were not found; automatic upgrade cannot be performed safely"
        return 1
    fi

    docker_exec=$(systemd_exec_start_path docker)
    containerd_exec=$(systemd_exec_start_path containerd)
    if [ "$docker_exec" != "$dockerd_path" ] || [ "$containerd_exec" != "${binary_dir}/containerd" ]; then
        docker_upgrade_reject \
            "systemd 启动路径与当前 Docker 二进制不一致，安装脚本不会自动覆盖该环境" \
            "The systemd ExecStart paths do not match the current Docker binaries; the installer will not overwrite this environment"
        return 1
    fi

    return 0
}

confirm_docker_upgrade_linux() {
    local current_version=$1
    local upgrade_source=$2 package_name=${3:-}
    local running_count running_names answer upgrade_plan_zh upgrade_plan_en prompt_target_zh prompt_target_en
    running_count=$(docker ps -q 2>/dev/null | sed '/^$/d' | wc -l | tr -d ' ')
    running_names=$(docker ps --format '{{.Names}}' 2>/dev/null | sed '/^$/d' || true)

    case "$upgrade_source" in
        apt | dnf | yum)
            upgrade_plan_zh="沿用现有 ${upgrade_source} 软件包 ${package_name} 和原软件源升级；升级后 Docker Server 必须不低于 ${DOCKER_MIN_VERSION}"
            upgrade_plan_en="Upgrade the existing ${package_name} package from its original ${upgrade_source} repository; the resulting Docker Server must meet minimum ${DOCKER_MIN_VERSION}"
            prompt_target_zh="使用原 ${upgrade_source} 软件源升级 Docker"
            prompt_target_en="upgrade Docker from the original ${upgrade_source} repository"
            ;;
        static)
            upgrade_plan_zh="当前为静态二进制安装，将升级到脚本推荐版本 ${DOCKER_RECOMMENDED_VERSION}"
            upgrade_plan_en="This is a static binary installation and will be upgraded to the installer-recommended version ${DOCKER_RECOMMENDED_VERSION}"
            prompt_target_zh="将 Docker 升级到 ${DOCKER_RECOMMENDED_VERSION}"
            prompt_target_en="upgrade Docker to ${DOCKER_RECOMMENDED_VERSION}"
            ;;
        *)
            return 1
            ;;
    esac

    if rainbond_use_chinese_prompt; then
        send_warn "检测到 Docker Server 版本 ${current_version}，低于 Rainbond 最低要求 ${DOCKER_MIN_VERSION}"
        send_info "$upgrade_plan_zh"
        send_warn "升级需要重启 Docker，当前 ${running_count:-0} 个运行中的容器会短暂中断；脚本会尝试恢复这些容器，但跨版本升级不能保证所有现有服务完全兼容"
        if [ "$upgrade_source" != "static" ]; then
            send_warn "包管理器升级可能同时更新 Docker 依赖；失败后脚本不会自动降级软件包"
        fi
        if [ -n "$running_names" ]; then
            printf '%s\n' "$running_names" | sed 's/^/  - /'
        fi
    else
        send_warn "Docker Server ${current_version} is below Rainbond's minimum requirement ${DOCKER_MIN_VERSION}"
        send_info "$upgrade_plan_en"
        send_warn "Upgrading restarts Docker and briefly interrupts ${running_count:-0} running container(s). The installer will try to restore them, but cross-version compatibility cannot be guaranteed"
        if [ "$upgrade_source" != "static" ]; then
            send_warn "The package manager may also update Docker dependencies; packages will not be downgraded automatically if the upgrade fails"
        fi
        if [ -n "$running_names" ]; then
            printf '%s\n' "$running_names" | sed 's/^/  - /'
        fi
    fi

    case "${RAINBOND_DOCKER_UPGRADE:-ask}" in
        auto)
            return 0
            ;;
        never)
            return 1
            ;;
        ask | '')
            ;;
        *)
            if rainbond_use_chinese_prompt; then
                send_error "RAINBOND_DOCKER_UPGRADE 值无效，支持 ask、auto 或 never"
            else
                send_error "Invalid RAINBOND_DOCKER_UPGRADE value; supported values are ask, auto, or never"
            fi
            return 1
            ;;
    esac

    if ! rainbond_tty_available; then
        if rainbond_use_chinese_prompt; then
            send_error "当前环境无法交互确认。请在终端中重新执行，或确认风险后设置 RAINBOND_DOCKER_UPGRADE=auto"
        else
            send_error "Interactive confirmation is unavailable. Re-run in a terminal, or set RAINBOND_DOCKER_UPGRADE=auto after accepting the risk"
        fi
        return 1
    fi

    if rainbond_use_chinese_prompt; then
        printf '%b' "${YELLOW}是否${prompt_target_zh}并继续安装 Rainbond？[y/N]: ${NC}"
    else
        printf '%b' "${YELLOW}Proceed to ${prompt_target_en} and continue installing Rainbond? [y/N]: ${NC}"
    fi
    read -r answer </dev/tty
    case "$answer" in
        y | Y | yes | YES | Yes)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

ensure_docker_version_linux() {
    local current_version upgrade_source package_name
    current_version=$(get_docker_version)
    if [ -z "$current_version" ]; then
        if rainbond_use_chinese_prompt; then
            send_error "无法读取 Docker Server 版本"
        else
            send_error "Unable to read the Docker Server version"
        fi
        return 1
    fi

    if docker_version_is_supported "$current_version"; then
        return 0
    fi

    if ! detect_docker_install_source; then
        if rainbond_use_chinese_prompt; then
            send_error "无法识别当前 Docker 的安装来源，脚本不会强制替换。请使用原安装方式将 Docker Server 升级到 ${DOCKER_MIN_VERSION} 或更高版本"
        else
            send_error "The Docker installation source could not be identified and will not be force-replaced. Upgrade Docker Server to ${DOCKER_MIN_VERSION} or newer using its original installation method"
        fi
        return 1
    fi
    upgrade_source=$DOCKER_UPGRADE_SOURCE
    package_name=$DOCKER_UPGRADE_PACKAGE

    if ! confirm_docker_upgrade_linux "$current_version" "$upgrade_source" "$package_name"; then
        if rainbond_use_chinese_prompt; then
            send_error "Docker 版本升级已取消，Rainbond 安装停止"
        else
            send_error "Docker upgrade was declined; Rainbond installation has stopped"
        fi
        return 1
    fi
    if ! docker_upgrade_common_preflight_linux; then
        if rainbond_use_chinese_prompt; then
            send_error "当前环境不满足安全自动升级条件，请先按提示人工升级 Docker，Rainbond 安装停止"
        else
            send_error "This host does not meet the safe automatic-upgrade requirements. Upgrade Docker manually as indicated; Rainbond installation has stopped"
        fi
        return 1
    fi
    case "$upgrade_source" in
        apt | dnf | yum)
            if ! docker_package_upgrade_preflight_linux; then
                if rainbond_use_chinese_prompt; then
                    send_error "当前包管理器 Docker 环境不满足安全自动升级条件，请按提示人工升级 Docker，Rainbond 安装停止"
                else
                    send_error "This package-managed Docker installation does not meet the safe automatic-upgrade requirements. Upgrade Docker manually as indicated; Rainbond installation has stopped"
                fi
                return 1
            fi
            if ! upgrade_docker_with_package_manager "$upgrade_source" "$package_name"; then
                return 1
            fi
            ;;
        static)
            if ! docker_static_upgrade_preflight_linux; then
                if rainbond_use_chinese_prompt; then
                    send_error "当前静态二进制环境不满足安全自动升级条件，请按提示人工升级 Docker，Rainbond 安装停止"
                else
                    send_error "This static binary installation does not meet the safe automatic-upgrade requirements. Upgrade Docker manually as indicated; Rainbond installation has stopped"
                fi
                return 1
            fi
            if ! install_docker_linux upgrade; then
                return 1
            fi
            ;;
        *)
            return 1
            ;;
    esac

    current_version=$(get_docker_version)
    if [ -z "$current_version" ] || ! docker_version_is_supported "$current_version"; then
        if rainbond_use_chinese_prompt; then
            send_error "Docker 升级后版本校验失败，当前版本: ${current_version:-unknown}"
        else
            send_error "Docker version verification failed after upgrade; current version: ${current_version:-unknown}"
        fi
        return 1
    fi
    return 0
}

# Preserve the existing macOS behavior: validate the CLI major version only.
validate_docker_version() {
    local docker_version_full docker_version min_version=20
    docker_version_full=$(docker --version 2>/dev/null || echo "Docker version 0.0.0")
    docker_version=$(echo "$docker_version_full" | sed 's/[^0-9]*\([0-9][0-9]*\).*/\1/' || echo "0")
    if [ "$docker_version" -lt "$min_version" ]; then
        if rainbond_use_chinese_prompt; then
            send_error "Docker 版本过低，当前版本: $docker_version.x, 要求最低版本: $min_version.x\n\t- 请更新 Docker 版本: https://docs.docker.com/engine/install/"
        else
            send_error "Docker version is too low, current version: $docker_version.x, minimum required: $min_version.x\n\t- Please update Docker version: https://docs.docker.com/engine/install/"
        fi
        exit 1
    fi
}

set_cpu_mode() {
    ENABLE_GPU=false
    GPU_DOCKER_ARGS=""
    GPU_ENV_ARGS="-e ENABLE_GPU=false"
}

set_gpu_mode() {
    ENABLE_GPU=true
    GPU_DOCKER_ARGS="--gpus all"
    GPU_ENV_ARGS="-e ENABLE_GPU=true -e NVIDIA_VISIBLE_DEVICES=all -e NVIDIA_DRIVER_CAPABILITIES=compute,utility"
}

nvidia_smi_ready() {
    command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >/dev/null 2>&1
}

validate_gpu_support_linux() {
    case "$(echo "${ENABLE_GPU:-auto}" | tr '[:upper:]' '[:lower:]')" in
        false|0|no|off)
            set_cpu_mode
            if rainbond_use_chinese_prompt; then
                send_info "GPU 模式已禁用，将使用 CPU 模式启动 Rainbond"
            else
                send_info "GPU mode is disabled. Rainbond will start in CPU mode."
            fi
            return
            ;;
        true|1|yes|on|auto)
            ;;
        *)
            if rainbond_use_chinese_prompt; then
                send_error "ENABLE_GPU 值无效: ${ENABLE_GPU}，支持 true/false/auto"
            else
                send_error "Invalid ENABLE_GPU value: ${ENABLE_GPU}. Supported values: true/false/auto"
            fi
            exit 1
            ;;
    esac

    if [ "${OS_TYPE}" != "Linux" ]; then
        set_cpu_mode
        if rainbond_use_chinese_prompt; then
            send_warn "GPU 模式当前仅支持 Linux 宿主机，将使用 CPU 模式启动 Rainbond"
        else
            send_warn "GPU mode currently supports Linux hosts only. Rainbond will start in CPU mode."
        fi
        return
    fi

    if ! nvidia_smi_ready; then
        set_cpu_mode
        if rainbond_use_chinese_prompt; then
            send_info "未检测到可用 NVIDIA 驱动，将使用 CPU 模式启动 Rainbond"
        else
            send_info "NVIDIA driver is not ready. Rainbond will start in CPU mode."
        fi
        return
    fi

    set_gpu_mode
    if rainbond_use_chinese_prompt; then
        send_info "检测到可用 NVIDIA 驱动，将使用 GPU 模式启动 Rainbond"
    else
        send_info "NVIDIA driver is ready. Rainbond will start in GPU mode."
    fi
}

build_docker_run_cmd() {
    docker_run_cmd="docker run --privileged -d ${GPU_DOCKER_ARGS} -p 7070:7070 -p 80:80 -p 443:443 -p 30000-30010:30000-30010 --name=rainbond --restart=always \
${VOLUME_OPTS} ${GPU_ENV_ARGS} -e EIP=$EIP -e REGION_WS_PROXY_TARGET=ws://127.0.0.1:6060 -e UUID=${UUID} ${RBD_IMAGE}"
}

# Main Docker management function
manage_docker() {
    # On macOS, check OrbStack first
    if [ "${OS_TYPE}" = "Darwin" ]; then
        handle_orbstack_macos
        validate_docker_version
        return
    fi

    # Linux logic
    if ! check_docker_running; then
        if check_docker_installed; then
            if ! start_docker_service_linux; then
                exit 1
            fi
            if ! ensure_docker_version_linux; then
                exit 1
            fi
        else
            # Docker not installed
            install_docker_linux
        fi
    else
        # Docker is running, validate or upgrade the daemon version
        if ! ensure_docker_version_linux; then
            exit 1
        fi
    fi
}

# Main execution
manage_docker
validate_gpu_support_linux

########################################
# EIP Configure
# Pick the address the console advertises to browsers:
#   1. an explicit EIP always wins;
#   2. otherwise the detected public IP is used - confirmed interactively when a
#      terminal is reachable, adopted automatically when it is not;
#   3. otherwise fall back to the LAN IP of this host.
# Set EIP_PROBE=false to skip the public IP detection entirely.
########################################

if [ -n "$EIP" ]; then
    if verify_eip "$EIP"; then
        RAINBOND_LAN_IP=$(rainbond_detect_host_eip_value)
        if rainbond_use_chinese_prompt; then
            send_info "使用环境变量指定的 IP 地址: $EIP"
        else
            send_info "Using IP address from environment variable: $EIP"
        fi
    else
        if rainbond_use_chinese_prompt; then
            send_error "环境变量 EIP 的值无效: $EIP (必须是有效的 IPv4 地址，且不能是 127.0.0.1 或 0.0.0.0)"
        else
            send_error "Invalid EIP environment variable value: $EIP (must be a valid IPv4 address, and cannot be 127.0.0.1 or 0.0.0.0)"
        fi
        exit 1
    fi
elif rainbond_detect_host_eip; then
    RAINBOND_LAN_IP=$EIP

    if rainbond_public_ip_probe_enabled; then
        RAINBOND_PUBLIC_IP=$(rainbond_probe_public_ip)
    fi

    if [ -n "$RAINBOND_PUBLIC_IP" ] && [ "$RAINBOND_PUBLIC_IP" != "$RAINBOND_LAN_IP" ]; then
        if rainbond_tty_available; then
            if rainbond_confirm_public_eip "$RAINBOND_PUBLIC_IP" "$RAINBOND_LAN_IP"; then
                export EIP="$RAINBOND_PUBLIC_IP"
            else
                export EIP="$RAINBOND_LAN_IP"
            fi
        else
            export EIP="$RAINBOND_PUBLIC_IP"
            if rainbond_use_chinese_prompt; then
                send_info "非交互环境，自动使用检测到的公网 IP，如需改用内网 IP 请以 EIP=${RAINBOND_LAN_IP} 重新执行安装脚本"
            else
                send_info "Non-interactive run, using the detected public IP; rerun with EIP=${RAINBOND_LAN_IP} to use the LAN IP instead"
            fi
        fi
    fi

    if rainbond_use_chinese_prompt; then
        send_info "自动检测到服务器 IP: $EIP"
    else
        send_info "Detected server IP automatically: $EIP"
    fi
else
    if rainbond_use_chinese_prompt; then
        send_error "未能自动检测到可用服务器 IP，请使用 EIP=<服务器IP> 重新执行安装脚本"
    else
        send_error "Failed to detect an available server IP automatically. Please rerun the installer with EIP=<server-ip>"
    fi
    exit 1
fi

rainbond_build_access_lines
rainbond_print_access_ports_notice

################## Main ################
# Start install rainbond standalone
# Automatically generate install cmd with envs
########################################

if rainbond_use_chinese_prompt; then
    echo -e "${GREEN}生成安装命令:${NC}"
    sleep 3
else
    echo -e "${GREEN}Generating the installation command:${NC}"
    sleep 3
fi

# Generate the installation command based on the detect results
if [ "$OS_TYPE" = "Linux" ]; then
  VOLUME_OPTS="-v /opt/rainbond:/opt/rainbond"
elif [ "$OS_TYPE" = "Darwin" ]; then
  VOLUME_OPTS="-v rainbond-opt:/opt/rainbond"
fi

RBD_IMAGE="${IMGHUB_MIRROR}/rainbond:${RAINBOND_VERSION}-k3s"

# Generate cmd
build_docker_run_cmd
send_info "$docker_run_cmd"

# Pull image with retry mechanism
if rainbond_use_chinese_prompt; then
    send_info "获取镜像中 ${RBD_IMAGE}..."
else
    send_info "Pulling image ${RBD_IMAGE}..."
fi

# Try to pull image with retries
pull_success=false
for retry in 1 2 3; do
  if docker pull ${RBD_IMAGE}; then
    pull_success=true
    rbd_image_id=$(docker images | grep k3s | grep "${RAINBOND_VERSION}" | awk '{print $3}')
    if rainbond_use_chinese_prompt; then
      send_info "Rainbond 镜像获取成功，ID: ${rbd_image_id}"
    else
      send_info "Rainbond image pulled successfully, ID: ${rbd_image_id}"
    fi
    break
  else
    if [ "$retry" -lt 3 ]; then
      if rainbond_use_chinese_prompt; then
        send_warn "镜像拉取失败，正在重试 ($retry/3)..."
      else
        send_warn "Image pull failed, retrying ($retry/3)..."
      fi
      sleep 5
    fi
  fi
done

if [ "$pull_success" = false ]; then
  if rainbond_use_chinese_prompt; then
    send_error "镜像拉取失败，请检查网络连接"
  else
    send_error "Image pull failed, please check network connection"
  fi
  exit 1
fi

if ! check_docker_network_preflight; then
  exit 1
fi

sleep 3

# Start container
if rainbond_use_chinese_prompt; then
  send_info "正在启动 Rainbond 容器..."
else
  send_info "Starting Rainbond container..."
fi

if ! docker_run_meg=$(bash -c "$docker_run_cmd" 2>&1); then
    if rainbond_use_chinese_prompt; then
        send_error "Docker 容器启动命令执行失败: $docker_run_meg"
    else
        send_error "Docker container start command failed: $docker_run_meg"
    fi
    exit 1
fi
send_info "$docker_run_meg"

# Verify startup with retry loop
if rainbond_use_chinese_prompt; then
  send_info "正在等待容器启动..."
else
  send_info "Waiting for container to start..."
fi

container_started=false
MAX_WAIT_TIME=60  # Maximum wait time in seconds
for i in $(seq 1 $MAX_WAIT_TIME); do
  if docker ps --filter "name=rainbond" --filter "status=running" | grep -q "rainbond"; then
    container_started=true
    if rainbond_use_chinese_prompt; then
      send_info "Rainbond 容器启动成功（耗时 ${i} 秒）"
    else
      send_info "Rainbond container started successfully (took ${i} seconds)"
    fi
    break
  fi
  # Show progress every 10 seconds
  if [ $((i % 10)) -eq 0 ]; then
    if rainbond_use_chinese_prompt; then
      send_info "仍在等待容器启动... (${i}/${MAX_WAIT_TIME}秒)"
    else
      send_info "Still waiting for container to start... (${i}/${MAX_WAIT_TIME}s)"
    fi
  fi
  sleep 1
done

if [ "$container_started" = false ]; then
  if rainbond_use_chinese_prompt; then
    send_error "Rainbond 容器启动失败或超时（等待了 ${MAX_WAIT_TIME} 秒）"
  else
    send_error "Rainbond container startup failed or timeout (waited ${MAX_WAIT_TIME} seconds)"
  fi
  exit 1
fi

# Wait for Rainbond services to be ready
if rainbond_use_chinese_prompt; then
  send_info "正在等待 Rainbond 服务启动..."
else
  send_info "Waiting for Rainbond services to start..."
fi

# Define expected pods (compatible with Bash 3.2+)
pod_list=(
  "local-path-provisioner"
  "minio"
  "rainbond-operator"
  "rbd-api"
  "rbd-app-ui"
  "rbd-chaos"
  "rbd-gateway"
  "rbd-hub"
  "rbd-monitor"
  "rbd-mq"
  "rbd-worker"
)

pod_ready_reported=""
services_ready=false
MAX_SERVICE_WAIT=600
check_interval=5
elapsed_time=0

# Spinner characters
spinner_chars=("⠋" "⠙" "⠹" "⠸" "⠼" "⠴" "⠦" "⠧" "⠇" "⠏")
spinner_index=0

while [ $elapsed_time -le $MAX_SERVICE_WAIT ]; do
  pod_status=$(docker exec rainbond /bin/k3s kubectl get pod -n rbd-system --no-headers 2>/dev/null)

  if [ -n "$pod_status" ]; then
    all_ready=true

    for prefix in "${pod_list[@]}"; do
      if echo "$pod_status" | grep "^${prefix}" | grep 'Running' >/dev/null 2>&1; then
        if ! echo "$pod_ready_reported" | grep -q "\b${prefix}\b"; then
          printf "\r\033[K"  # Clear spinner line
          echo -e "${GREEN}  ✓ ${prefix}${NC}"
          pod_ready_reported="$pod_ready_reported $prefix"
        fi
      else
        all_ready=false
      fi
    done

    # Check web service if all pods ready
    if [ "$all_ready" = true ]; then
      if curl -s --connect-timeout 5 --max-time 10 "http://127.0.0.1:7070" >/dev/null 2>&1 || \
         curl -s --connect-timeout 5 --max-time 10 "http://${EIP}:7070" >/dev/null 2>&1; then
        printf "\r\033[K"  # Clear spinner line
        if rainbond_use_chinese_prompt; then
          send_info "🎉 所有服务启动完成！"
        else
          send_info "🎉 All services are ready!"
        fi
        send_msg "Rainbond installation successfully"
        rainbond_send_final_event success services_ready 0
        services_ready=true
        break
      fi
    fi
  fi

  if [ $elapsed_time -ge $MAX_SERVICE_WAIT ]; then
    break
  fi

  # Show spinner while waiting (5 seconds with 0.2 second intervals)
  for i in $(seq 1 25); do
    if rainbond_use_chinese_prompt; then
      printf "\r  %s 等待服务启动..." "${spinner_chars[$spinner_index]}"
    else
      printf "\r  %s Waiting for services..." "${spinner_chars[$spinner_index]}"
    fi
    spinner_index=$(( (spinner_index + 1) % 10 ))
    sleep 0.2
  done

  elapsed_time=$((elapsed_time + check_interval))
done

# Clear the spinner line
printf "\r\033[K"

if [ "$services_ready" = false ]; then
  timeout_diagnosis=$(rainbond_collect_timeout_diagnostics "$MAX_SERVICE_WAIT" "$INSTALL_ATTEMPT_ID")
  rainbond_send_operator_log_collect "$timeout_diagnosis" "$MAX_SERVICE_WAIT"
  if rainbond_use_chinese_prompt; then
    send_warn "Rainbond 服务启动超时（等待了 ${MAX_SERVICE_WAIT} 秒）"
    send_msg "Rainbond 服务启动超时诊断: ${timeout_diagnosis}"
    rainbond_send_final_event timeout services_timeout 124 "$timeout_diagnosis"
    send_info "服务可能仍在启动中，请使用以下命令检查状态："
    echo -e "${YELLOW}    docker exec -it rainbond bash${NC}"
    echo -e "${YELLOW}    kubectl get pod -n rbd-system${NC}"
    echo -e "${YELLOW}    kubectl describe pod <pod-name> -n rbd-system${NC}"
  else
    send_warn "Rainbond services startup timeout (waited ${MAX_SERVICE_WAIT} seconds)"
    send_msg "Rainbond services startup timeout diagnosis: ${timeout_diagnosis}"
    rainbond_send_final_event timeout services_timeout 124 "$timeout_diagnosis"
    send_info "Services may still be starting, please check status with:"
    echo -e "${YELLOW}    docker exec -it rainbond bash${NC}"
    echo -e "${YELLOW}    kubectl get pod -n rbd-system${NC}"
    echo -e "${YELLOW}    kubectl describe pod <pod-name> -n rbd-system${NC}"
  fi
fi

if rainbond_use_chinese_prompt; then
  echo -e "${GREEN}"
  if [ "$services_ready" = true ]; then
    cat <<EOF
###############################################
# 🎉 Rainbond 安装成功！
# 版本: $RAINBOND_VERSION
# 架构: $ARCH_TYPE
# 操作系统: $OS_TYPE
# Rainbond 访问地址:
$RAINBOND_ACCESS_LINES_ZH
#
# ⚠️  重要提示:
#     请确保以下端口已在防火墙/安全组中开放:
#     - 7070: 控制台访问端口
#     - 80:   HTTP 服务端口
#     - 443:  HTTPS 服务端口
#
# 文档和支持:
#     📖 文档: https://www.rainbond.com/docs
#     💬 支持: https://www.rainbond.com/docs/support
###############################################

EOF
  else
    cat <<EOF
###############################################
# ⏳ Rainbond 容器已启动，服务仍在初始化中
# 版本: $RAINBOND_VERSION
# 架构: $ARCH_TYPE
# 操作系统: $OS_TYPE
# Rainbond 访问地址:
$RAINBOND_ACCESS_LINES_ZH
#     ⚠️  请等待几分钟后访问
#
# ⚠️  重要提示:
#     请确保以下端口已在防火墙/安全组中开放:
#     - 7070: 控制台访问端口
#     - 80:   HTTP 服务端口
#     - 443:  HTTPS 服务端口
#
# 监控命令:
#     docker exec -it rainbond bash
#     kubectl get pod -n rbd-system
#     kubectl describe pod <pod-name> -n rbd-system
#
# 文档和支持:
#     📖 文档: https://www.rainbond.com/docs
#     🔧 故障排除: https://www.rainbond.com/docs/troubleshooting/install
#     💬 支持: https://www.rainbond.com/docs/support
###############################################

EOF
  fi
  echo -e "${NC}"
else
  echo -e "${GREEN}"
  if [ "$services_ready" = true ]; then
    cat <<EOF
###############################################
# 🎉 Rainbond Installation Successful!
# Version: $RAINBOND_VERSION
# Arch: $ARCH_TYPE
# OS: $OS_TYPE
# Rainbond Access URL:
$RAINBOND_ACCESS_LINES_EN
#
# ⚠️  Important:
#     Please ensure the following ports are open
#     in your firewall/security group:
#     - 7070: Console access port
#     - 80:   HTTP service port
#     - 443:  HTTPS service port
#
# Documentation and Support:
#     📖 Docs: https://www.rainbond.com/docs
#     💬 Support: https://www.rainbond.com/docs/support
###############################################

EOF
  else
    cat <<EOF
###############################################
# ⏳ Rainbond Container Started, Services Still Initializing
# Version: $RAINBOND_VERSION
# Arch: $ARCH_TYPE
# OS: $OS_TYPE
# Rainbond Access URL:
$RAINBOND_ACCESS_LINES_EN
#     ⚠️  Please wait a few minutes before accessing
#
# ⚠️  Important:
#     Please ensure the following ports are open
#     in your firewall/security group:
#     - 7070: Console access port
#     - 80:   HTTP service port
#     - 443:  HTTPS service port
#
# Monitoring Commands:
#     docker exec -it rainbond bash
#     kubectl get pod -n rbd-system
#     kubectl describe pod <pod-name> -n rbd-system
#
# Documentation and Support:
#     📖 Docs: https://www.rainbond.com/docs
#     🔧 Troubleshooting: https://www.rainbond.com/docs/troubleshooting/install
#     💬 Support: https://www.rainbond.com/docs/support
###############################################

EOF
  fi
  echo -e "${NC}"
fi
