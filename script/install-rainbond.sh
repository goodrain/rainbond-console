#!/bin/bash

# This script is used to install Rainbond standalone on Linux and MacOS

# Basic environment variables
RAINBOND_VERSION=${VERSION:-'v6.9.2-release'}
IMGHUB_MIRROR=${IMGHUB_MIRROR:-'registry.cn-hangzhou.aliyuncs.com/goodrain'}
ENABLE_GPU=${ENABLE_GPU:-auto}

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
    command -v orb >/dev/null 2>&1 || [ -d "/Applications/OrbStack.app" ]
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

# Function to handle OrbStack requirement on macOS
handle_orbstack_macos() {
    if rainbond_use_chinese_prompt; then
        send_info "检查 OrbStack 安装状态..."
    else
        send_info "Checking OrbStack installation..."
    fi

    if ! check_orbstack_installed; then
        if rainbond_use_chinese_prompt; then
            send_error "macOS 上必须使用 OrbStack，请先安装 OrbStack 后重新执行脚本.\n\t下载地址: https://orbstack.dev/"
        else
            send_error "OrbStack is required on macOS. Please install OrbStack and re-run this script.\n\tDownload: https://orbstack.dev/"
        fi
        exit 1
    fi

    if ! check_orbstack_running; then
        if rainbond_use_chinese_prompt; then
            send_error "检测到 OrbStack 已安装但未运行，请先启动 OrbStack 后重新执行脚本."
        else
            send_error "OrbStack is installed but not running. Please start OrbStack and re-run this script."
        fi
        exit 1
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

# Function to install Docker on Linux using binary installation
install_docker_linux() {
    if rainbond_use_chinese_prompt; then
        send_info "未检测到 Docker 环境，开始二进制安装..."
    else
        send_info "Docker not detected, starting binary installation..."
    fi
    
    # Determine Docker binary URL based on architecture
    local docker_url
    local docker_version="28.3.1"
    if [ "$ARCH_TYPE" = "amd64" ]; then
        docker_url="https://mirrors.tuna.tsinghua.edu.cn/docker-ce/linux/static/stable/x86_64/docker-${docker_version}.tgz"
    elif [ "$ARCH_TYPE" = "arm64" ]; then
        docker_url="https://mirrors.tuna.tsinghua.edu.cn/docker-ce/linux/static/stable/aarch64/docker-${docker_version}.tgz"
    fi
    
    # Check if Docker binary already exists and is complete
    local docker_file="/tmp/docker.tgz"
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
        if rainbond_use_chinese_prompt; then
            send_info "正在下载Docker二进制文件... $docker_url"
        else
            send_info "Downloading Docker binary... $docker_url"
        fi
        
        # Use curl with resume capability, timeout, and progress bar
        if ! curl --connect-timeout 30 --max-time 600 -C - --progress-bar -L "$docker_url" -o "$docker_file"; then
            if rainbond_use_chinese_prompt; then
                send_error "Docker二进制文件下载失败，请检查网络连接"
            else
                send_error "Failed to download Docker binary, please check network connection"
            fi
            rm -f "$docker_file"
            exit 1
        fi
        
        # Verify downloaded file
        if ! tar -tzf "$docker_file" >/dev/null 2>&1; then
            if rainbond_use_chinese_prompt; then
                send_error "下载的文件损坏，请重新执行脚本"
            else
                send_error "Downloaded file is corrupted, please re-run the script"
            fi
            rm -f "$docker_file"
            exit 1
        fi
    fi

    # Extract Docker binary
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


# Function to get Docker version
get_docker_version() {
    local docker_version_full=$(docker --version 2>/dev/null || echo "Docker version 0.0.0")
    echo "$docker_version_full" | sed 's/[^0-9]*\([0-9][0-9]*\).*/\1/' || echo "0"
}

# Function to validate Docker version (must be >= 20.x)
validate_docker_version() {
    local docker_version=$(get_docker_version)
    local min_version=20
    
    if [ "$docker_version" -lt $min_version ]; then
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
            validate_docker_version
        else
            # Docker not installed
            install_docker_linux
        fi
    else
        # Docker is running, validate version
        validate_docker_version
    fi
}

# Main execution
manage_docker
validate_gpu_support_linux

########################################
# EIP Configure
# Automatically detect the host IP used by Rainbond.
# User customization via EIP is also supported.
########################################

function rainbond_is_usable_ipv4() {
    local result=$1
    if [ -z "$result" ]; then
        return 1
    elif [[ $result =~ ^([0-9]{1,2}|1[0-9][0-9]|2[0-4][0-9]|25[0-5])\.([0-9]{1,2}|1[0-9][0-9]|2[0-4][0-9]|25[0-5])\.([0-9]{1,2}|1[0-9][0-9]|2[0-4][0-9]|25[0-5])\.([0-9]{1,2}|1[0-9][0-9]|2[0-4][0-9]|25[0-5])$ ]]; then
        [ "$result" != "127.0.0.1" ] && [ "$result" != "0.0.0.0" ]
        return $?
    fi
    return 1
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

# Check if EIP is already set via environment variable
if [ -n "$EIP" ]; then
    if verify_eip "$EIP"; then
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
else
    if rainbond_detect_host_eip; then
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
fi

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
#     当前检测地址: http://$EIP:7070
#     云服务器请用公网 IP: http://<公网IP>:7070
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
#     当前检测地址: http://$EIP:7070
#     云服务器请用公网 IP: http://<公网IP>:7070
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
#     Detected URL: http://$EIP:7070
#     Cloud server, use public IP: http://<public-ip>:7070
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
#     Detected URL: http://$EIP:7070
#     Cloud server, use public IP: http://<public-ip>:7070
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
