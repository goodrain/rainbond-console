# This script is used to install Rainbond standalone on Linux and MacOS

#!/bin/bash

# Basic environment variables
RAINBOND_VERSION=${VERSION:-'v6.3.1-release'}
IMGHUB_MIRROR=${IMGHUB_MIRROR:-'registry.cn-hangzhou.aliyuncs.com/goodrain'}

# Define colorful stdout
RED='\033[0;31m'
GREEN='\033[32;1m'
YELLOW='\033[33;1m'
NC='\033[0m'
TIME="+%Y-%m-%d %H:%M:%S"

########################################
# Information collection
# Automatically collect the install details.
# Help us improve the success rate of installation.
########################################

function send_msg() {
    dest_url="https://log.rainbond.com"
    #msg=${1:-"Terminating by userself."}
    if [ -z "$1" ]; then
        msg="Terminating by userself."
    else
        msg=$(echo $1 | tr '"' " " | tr "'" " ")
    fi
    # send a message to remote url
    curl --silent -H "Content-Type: application/json" -X POST "$dest_url/dindlog" \
        -d "{\"message\":\"$msg\", \"os_info\":\"${OS_INFO}\", \"eip\":\"$EIP\", \"uuid\":\"${UUID}\"}" 2>&1 >/dev/null || :

    if [ "$msg" == "Terminating by userself." ]; then
        exit 1
    fi
}

function send_info() {
    info=$1
    echo -e "${GREEN}$(date "$TIME") INFO: $info${NC}"
    send_msg "$info"
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

# Trap SIGINT signal when detect Ctrl + C
trap send_msg SIGINT

########################################
# OS Detect
# Automatically check the operating system type.
# Return Linux or Darwin.
########################################

OS_TYPE=$(uname -s)
if [ "${OS_TYPE}" == "Linux" ]; then
    MD5_CMD="md5sum"
    if find /lib/modules/$(uname -r) -type f -name '*.ko*' | grep iptable_raw >/dev/null 2>&1; then
        if ! lsmod | grep iptable_raw >/dev/null 2>&1; then
            echo iptable_raw >/etc/modules-load.d/iptable_raw.conf
            modprobe iptable_raw
        fi
    fi
elif [ "${OS_TYPE}" == "Darwin" ]; then
    MD5_CMD="md5"
else
    if [ "$LANG" == "zh_CN.UTF-8" ]; then
        send_error "${OS_TYPE} 操作系统暂不支持"
        exit 1
    else
        send_error "Rainbond do not support ${OS_TYPE} OS"
        exit 1
    fi
fi

# Use root user to run this script, Ignore MacOS
if [ "${OS_TYPE}" != "Darwin" ] && [ "$EUID" -ne 0 ]; then
    if [ "$LANG" == "zh_CN.UTF-8" ]; then
        send_error "请使用 root 用户运行此脚本"
        exit 1
    else
        send_error "Please run this script as root user"
        exit 1
    fi
fi


########################################
# Enhanced Environment Check Functions
# Added critical checks to improve success rate
########################################

function check_base_env() {
  if [ "$LANG" == "zh_CN.UTF-8" ]; then
    send_info "######## 开始检测基础环境... ########"
  else
    send_info "######## Starting base environment check... ########"
  fi

  # Check and disable firewall
  if [ "$LANG" == "zh_CN.UTF-8" ]; then
    send_info "检查并关闭防火墙..."
  else
    send_info "Checking and disabling firewall..."
  fi
  
  # Check and disable firewalld
  if command -v firewalld >/dev/null 2>&1 || systemctl list-unit-files | grep -q firewalld; then
    if systemctl is-active --quiet firewalld; then
      if [ "$LANG" == "zh_CN.UTF-8" ]; then
        send_info "检测到 firewalld 正在运行，正在停止并禁用..."
      else
        send_info "firewalld is running, stopping and disabling..."
      fi
      systemctl stop firewalld >/dev/null 2>&1
      systemctl disable firewalld >/dev/null 2>&1
    fi
  fi
  
  # Check and disable ufw
  if command -v ufw >/dev/null 2>&1; then
    if ufw status | grep -q "Status: active"; then
      if [ "$LANG" == "zh_CN.UTF-8" ]; then
        send_info "检测到 ufw 正在运行，正在停止并禁用..."
      else
        send_info "ufw is active, stopping and disabling..."
      fi
      ufw --force disable >/dev/null 2>&1
    fi
  fi
  
  # Check and disable swap
  if [ "$LANG" == "zh_CN.UTF-8" ]; then
    send_info "检查并关闭交换分区..."
  else
    send_info "Checking and disabling swap..."
  fi
  
  # Check if swap is enabled
  if [ "$(cat /proc/swaps | wc -l)" -gt 1 ]; then
    if [ "$LANG" == "zh_CN.UTF-8" ]; then
      send_info "检测到交换分区正在使用，正在关闭..."
    else
      send_info "Swap is enabled, disabling..."
    fi
    
    # Disable swap
    swapoff -a >/dev/null 2>&1
    
    # Comment out swap entries in /etc/fstab to prevent re-enabling on reboot
    if [ -f /etc/fstab ]; then
      sed -i.bak '/^[^#].*swap/s/^/#/' /etc/fstab
      if [ "$LANG" == "zh_CN.UTF-8" ]; then
        send_info "已修改 /etc/fstab 防止重启后重新启用交换分区"
      else
        send_info "Modified /etc/fstab to prevent swap re-enabling on reboot"
      fi
    fi
    
    if [ "$LANG" == "zh_CN.UTF-8" ]; then
      send_info "交换分区已关闭"
    else
      send_info "Swap disabled successfully"
    fi
  fi

  # Check ports
  local ports=("7070" "80" "443" "6060")
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
    if [ "$LANG" == "zh_CN.UTF-8" ]; then
      send_error "以下端口被占用: ${occupied_ports[*]}. 请释放这些端口后重试."
    else
      send_error "The following ports are occupied: ${occupied_ports[*]}. Please free these ports and try again."
    fi
    exit 1
  else
    if [ "$LANG" == "zh_CN.UTF-8" ]; then
      send_info "端口检测通过，所有必需端口可用"
    else
      send_info "Port check passed, all required ports are available"
    fi
  fi

  # Test connection to docker registry
  if curl -s --connect-timeout 10 --max-time 30 "https://registry.cn-hangzhou.aliyuncs.com" >/dev/null 2>&1; then
    if [ "$LANG" == "zh_CN.UTF-8" ]; then
      send_info "Docker 镜像仓库连接正常"
    else
      send_info "Docker registry connectivity is working"
    fi
  else
    if [ "$LANG" == "zh_CN.UTF-8" ]; then
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
  
  # Check if at least 20GB available (20971520 KB)
  if [ "$available_space" -lt 20971520 ] 2>/dev/null; then
    local available_gb=$((available_space / 1024 / 1024))
    if [ "$LANG" == "zh_CN.UTF-8" ]; then
      send_warn "磁盘空间可能不足，当前可用: ${available_gb}GB，建议至少保留20GB空间"
    else
      send_warn "Disk space may be insufficient, available: ${available_gb}GB, recommend at least 20GB free space"
    fi
  else
    local available_gb=$((available_space / 1024 / 1024))
    if [ "$LANG" == "zh_CN.UTF-8" ]; then
      send_info "磁盘空间检测通过，可用空间: ${available_gb}GB"
    else
      send_info "Disk space check passed, available space: ${available_gb}GB"
    fi
  fi

  if [ "$LANG" == "zh_CN.UTF-8" ]; then
    send_info "######## 基础环境检测通过 ########"
  else
    send_info "######## Base environment check passed ########"
  fi
}

function check_rainbond_container() {
  if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    if docker ps -a --filter "name=^rainbond$" | grep -q "rainbond"; then
      if docker ps --filter "name=^rainbond$" --filter "status=running" | grep -q "rainbond"; then
        # Rainbond container is running, get EIP and exit
        local get_eip=$(docker inspect rainbond --format '{{range .Config.Env}}{{println .}}{{end}}' | grep '^EIP=' | cut -d'=' -f2)
        if [ "$LANG" == "zh_CN.UTF-8" ]; then
          send_info "Rainbond 容器已在运行中.\n\t- 请在浏览器中输入 http://$get_eip:7070 访问 Rainbond."
        else
          send_info "Rainbond container is already running.\n\t- Please enter http://$get_eip:7070 in the browser to access Rainbond."
        fi
        exit 0
      else
        # Container exists but is not running, try to start it
        if [ "$LANG" == "zh_CN.UTF-8" ]; then
          send_info "Rainbond 容器已存在但未运行，正在尝试启动..."
        else
          send_info "Rainbond container exists but not running, trying to start..."
        fi
        
        if docker start rainbond; then
          sleep 3
          local get_eip=$(docker inspect rainbond --format '{{range .Config.Env}}{{println .}}{{end}}' | grep '^EIP=' | cut -d'=' -f2)
          if [ "$LANG" == "zh_CN.UTF-8" ]; then
            send_info "Rainbond 容器启动成功.\n\t- 请在浏览器中输入 http://$get_eip:7070 访问 Rainbond."
          else
            send_info "Rainbond container started successfully.\n\t- Please enter http://$get_eip:7070 in the browser to access Rainbond."
          fi
          exit 0
        else
          if [ "$LANG" == "zh_CN.UTF-8" ]; then
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

# First check if Rainbond container is already running
check_rainbond_container

if [ "${OS_TYPE}" == "Linux" ]; then
  check_base_env
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
    if [ "$LANG" == "zh_CN.UTF-8" ]; then
        send_warn "检测到 i386, 我们把它当做 x86_64(amd64). 如果您使用的是 M1 芯片的 MacOS, 确保您禁用了 Rosetta. \n\t 请参阅: https://github.com/goodrain/rainbond/issues/1439 "
    else
        send_warn "i386 has been detected, we'll treat it like x86_64(amd64). If you are using the M1 chip MacOS, make sure your terminal has Rosetta disabled.\n\t Have a look : https://github.com/goodrain/rainbond/issues/1439 "
    fi
else
    if [ "$LANG" == "zh_CN.UTF-8" ]; then
        send_error "Rainbond 目前还不支持 $(arch) 架构"
        exit 1
    else
        send_error "Rainbond does not support $(arch) architecture"
        exit 1
    fi
fi

OS_INFO=$(uname -a)
UUID=$(echo $OS_INFO | ${MD5_CMD} | cut -b 1-32)

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
    if [ "$LANG" == "zh_CN.UTF-8" ]; then
        send_info "检测到 Docker 已安装但未运行，正在自动启动 Docker 服务..."
    else
        send_info "Docker is installed but not running, starting Docker service automatically..."
    fi
    
    if systemctl start docker >/dev/null 2>&1; then
        sleep 3
        if docker info >/dev/null 2>&1; then
            if [ "$LANG" == "zh_CN.UTF-8" ]; then
                send_info "Docker 服务启动成功"
            else
                send_info "Docker service started successfully"
            fi
            return 0
        else
            if [ "$LANG" == "zh_CN.UTF-8" ]; then
                send_error "Docker 服务启动失败，请手动启动: systemctl start docker"
            else
                send_error "Docker service failed to start, please start manually: systemctl start docker"
            fi
            return 1
        fi
    else
        if [ "$LANG" == "zh_CN.UTF-8" ]; then
            send_error "Docker 服务启动失败，请手动启动: systemctl start docker"
        else
            send_error "Docker service failed to start, please start manually: systemctl start docker"
        fi
        return 1
    fi
}

# Function to handle Docker Desktop on macOS
handle_docker_desktop_macos() {
    if [ "$LANG" == "zh_CN.UTF-8" ]; then
        send_error "检测到 Docker Desktop APP 已安装但未运行，请先启动 Docker Desktop APP 后重新执行脚本."
    else
        send_error "Docker Desktop APP is installed but not running. Please start Docker Desktop APP and re-run this script."
    fi
    exit 1
}

# Function to create containerd systemd service file
create_containerd_service() {
    if [ "$LANG" == "zh_CN.UTF-8" ]; then
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
    if [ "$LANG" == "zh_CN.UTF-8" ]; then
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
    if [ "$LANG" == "zh_CN.UTF-8" ]; then
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
        if [ "$LANG" == "zh_CN.UTF-8" ]; then
            send_info "检测到已存在的Docker二进制文件，正在验证完整性..."
        else
            send_info "Found existing Docker binary file, verifying integrity..."
        fi
        
        # Try to test if the file is a valid tar.gz
        if tar -tzf "$docker_file" >/dev/null 2>&1; then
            if [ "$LANG" == "zh_CN.UTF-8" ]; then
                send_info "文件完整，跳过下载"
            else
                send_info "File is complete, skipping download"
            fi
            download_needed=false
        else
            if [ "$LANG" == "zh_CN.UTF-8" ]; then
                send_warn "文件损坏或不完整，重新下载"
            else
                send_warn "File is corrupted or incomplete, re-downloading"
            fi
            rm -f "$docker_file"
        fi
    fi
    
    # Download Docker binary with progress and resume capability
    if [ "$download_needed" = true ]; then
        if [ "$LANG" == "zh_CN.UTF-8" ]; then
            send_info "正在下载Docker二进制文件... $docker_url"
        else
            send_info "Downloading Docker binary... $docker_url"
        fi
        
        # Use curl with resume capability, timeout, and progress bar
        if ! curl --connect-timeout 30 --max-time 600 -C - --progress-bar -L "$docker_url" -o "$docker_file"; then
            if [ "$LANG" == "zh_CN.UTF-8" ]; then
                send_error "Docker二进制文件下载失败，请检查网络连接"
            else
                send_error "Failed to download Docker binary, please check network connection"
            fi
            rm -f "$docker_file"
            exit 1
        fi
        
        # Verify downloaded file
        if ! tar -tzf "$docker_file" >/dev/null 2>&1; then
            if [ "$LANG" == "zh_CN.UTF-8" ]; then
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
        if [ "$LANG" == "zh_CN.UTF-8" ]; then
            send_error "Docker二进制文件解压失败"
        else
            send_error "Failed to extract Docker binary"
        fi
        rm -f "$docker_file"
        exit 1
    fi
    
    # Copy Docker binaries to /usr/bin
    if ! cp -r /tmp/docker/* /usr/bin/; then
        if [ "$LANG" == "zh_CN.UTF-8" ]; then
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
    
    if [ "$LANG" == "zh_CN.UTF-8" ]; then
        send_info "Docker二进制安装完成"
    else
        send_info "Docker binary installation completed"
    fi
    
    # Start containerd first, then Docker service
    if systemctl enable containerd && systemctl start containerd >/dev/null 2>&1; then
        if [ "$LANG" == "zh_CN.UTF-8" ]; then
            send_info "containerd 服务启动成功"
        else
            send_info "containerd service started successfully"
        fi
        sleep 2
        
        # Now start Docker service
        if systemctl enable docker.socket && systemctl enable docker && systemctl start docker >/dev/null 2>&1; then
            if [ "$LANG" == "zh_CN.UTF-8" ]; then
                send_info "Docker 服务启动成功"
            else
                send_info "Docker service started successfully"
            fi
            sleep 3
        else
            if [ "$LANG" == "zh_CN.UTF-8" ]; then
                send_error "Docker 服务启动失败，请手动启动: systemctl start docker"
            else
                send_error "Docker service failed to start, please start manually: systemctl start docker"
            fi
            exit 1
        fi
    else
        if [ "$LANG" == "zh_CN.UTF-8" ]; then
            send_error "containerd 服务启动失败，请手动启动: systemctl start containerd"
        else
            send_error "containerd service failed to start, please start manually: systemctl start containerd"
        fi
        exit 1
    fi
}

# Function to handle Docker installation requirement on macOS
handle_docker_install_macos() {
    if [ "$LANG" == "zh_CN.UTF-8" ]; then
        send_error "未检测到 Docker 环境, 请先安装 Docker Desktop APP, 然后重新执行本脚本.\n\thttps://www.docker.com/products/docker-desktop/"
    else
        send_error "Ops! Docker has not been installed.\nPlease visit the following website to get the latest Docker Desktop APP.\n\thttps://www.docker.com/products/docker-desktop/"
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
        if [ "$LANG" == "zh_CN.UTF-8" ]; then
            send_error "Docker 版本过低，当前版本: $docker_version.x, 要求最低版本: $min_version.x\n\t- 请更新 Docker 版本: https://docs.docker.com/engine/install/"
        else
            send_error "Docker version is too low, current version: $docker_version.x, minimum required: $min_version.x\n\t- Please update Docker version: https://docs.docker.com/engine/install/"
        fi
        exit 1
    fi
}

# Main Docker management function
manage_docker() {
    if ! check_docker_running; then
        if check_docker_installed; then
            case "${OS_TYPE}" in
                "Linux")
                    if ! start_docker_service_linux; then
                        exit 1
                    fi
                    validate_docker_version
                    ;;
                "Darwin")
                    handle_docker_desktop_macos
                    validate_docker_version
                    ;;
            esac
        else
            # Docker not installed
            case "${OS_TYPE}" in
                "Linux")
                    install_docker_linux
                    ;;
                "Darwin")
                    handle_docker_install_macos
                    ;;
            esac
        fi
    else
        # Docker is running, validate version
        validate_docker_version
    fi
}

# Main execution
manage_docker

########################################
# EIP Detect
# Automatically check the IP address.
# User customization is also supported.
########################################

# Choose tool for IP detect.
if which ip >/dev/null; then
    IF_NUM=$(ip -4 a | egrep -v "docker0|flannel|cni|calico|kube|127.0.0.1" | grep inet | wc -l)
    IPS=$(ip -4 a | egrep -v "docker0|flannel|cni|calico|kube|127.0.0.1" | grep inet | awk '{print $2}' | awk -F '/' '{print $1}' | tr '\n' ' ')
elif which ifconfig >/dev/null; then
    IF_NUM=$(ifconfig | grep -w inet | awk '{print $2}' | grep -v 127.0.0.1 | wc -l)
    IPS=$(ifconfig | grep -w inet | awk '{print $2}' | grep -v 127.0.0.1)
elif which ipconfig >/dev/null; then
    # TODO
    IF_NUM=$(ipconfig ifcount)
    IPS=""
else
    IF_NUM=0
    IPS=""
fi

# Func for verify the result entered.
function verify_eip() {
    local result=$2
    local max=$1
    if [ -z $result ]; then
        echo -e "${YELLOW}Do not enter null values${NC}"
        return 1
    # Regular matching IPv4
    elif [[ $result =~ ^([0-9]{1,2}|1[0-9][0-9]|2[0-4][0-9]|25[0-5]).([0-9]{1,2}|1[0-9][0-9]|2[0-4][0-9]|25[0-5]).([0-9]{1,2}|1[0-9][0-9]|2[0-4][0-9]|25[0-5]).([0-9]{1,2}|1[0-9][0-9]|2[0-4][0-9]|25[0-5])$ ]]; then
        # Check if it's 127.0.0.1
        if [ "$result" == "127.0.0.1" ]; then
            if [ "$LANG" == "zh_CN.UTF-8" ]; then
                echo -e "${YELLOW}不能使用回环地址 127.0.0.1${NC}"
            else
                echo -e "${YELLOW}Cannot use loopback address 127.0.0.1${NC}"
            fi
            return 1
        fi
        if [ "$result" == "0.0.0.0" ]; then
          if [ "$LANG" == "zh_CN.UTF-8" ]; then
            echo -e "${YELLOW}不能使用 0.0.0.0${NC}"
          else
            echo -e "${YELLOW}Cannot use 0.0.0.0${NC}"
          fi
          return 1
        fi
        export EIP=$result
        return 0
    # Regular matching positive integer
    elif [[ $result =~ ^[0-9]+$ ]]; then
        if [ $result -gt 0 ] && [ $result -le $max ]; then
            export EIP=${ip_list[$result - 1]}
            return 0
        else
            return 1
        fi
    else
        return 1
    fi
}

# The user chooses the IP address to use
if [ -n "$IPS" ]; then
    # Convert to indexed array
    declare -a ip_list=$(echo \($IPS\))

    # Gave some tips
    if [ "$LANG" == "zh_CN.UTF-8" ]; then
        echo -e ${GREEN}
        cat <<EOF
###############################################
# 脚本将自动检测到系统中存在的 IP 地址
# 您可以通过输入序号来选择一个 IP 地址
# 如果您有公网 IP 地址, 直接输入即可
###############################################
 
检测到以下IP:
EOF
        echo -e ${NC}
    else
        echo -e ${GREEN}
        cat <<EOF
###############################################
# The script automatically detects IP addresses in the system
# You can choose one by enter its index
# If you have an Public IP, Just type it in
###############################################
 
The following IP has been detected:
EOF
        echo -e ${NC}
    fi
    for ((i = 1; i <= $IF_NUM; i++)); do
        echo -e "\t${GREEN}$i${NC} : ${ip_list[$i - 1]}"
    done

    for i in 1 2 3; do
        if [ "$LANG" == "zh_CN.UTF-8" ]; then
            echo -e "\n${GREEN}例如: 输入 '1 or 2' 选择 IP, 或指定IP '11.22.33.44'(IPv4 address), 直接回车则使用默认 IP 地址${NC}"
            verify_eip $IF_NUM 1
            echo -n -e "输入您的选择或指定 IP 地址(默认IP是: $EIP):"
        else
            echo -e "\n${GREEN}For example: enter '1 or 2' to choose the IP, or input '11.22.33.44'(IPv4 address) for specific one, press enter to use the default IP address${NC}"
            verify_eip $IF_NUM 1
            echo -n -e "Enter your choose or a specific IP address( Default IP is $EIP):"
        fi
        read res
        if [ -z $res ]; then
            verify_eip $IF_NUM 1 && break
        else
            verify_eip $IF_NUM $res && break
        fi
        if [ "$LANG" == "zh_CN.UTF-8" ]; then
            echo -e "${RED}输入错误, 请重新输入${NC}"
        else
            echo -e "${RED}Incorrect input, please try again${NC}"
        fi
        if [ "$i" = "3" ]; then
            if [ "$LANG" == "zh_CN.UTF-8" ]; then
                send_error "输入错误超过3次, 中止安装"
                exit 1
            else
                send_error "The input error exceeds 3 times, aborting"
                exit 1
            fi
        fi
    done
else
    # Gave some tips
    if [ "$LANG" == "zh_CN.UTF-8" ]; then
        echo -e ${YELLOW}
        cat <<EOF
###############################################
# 自定检测 IP 失败
# 您必须指定一个 IP
# 例如: 
#   您可以输入 "11.22.33.44" 来指定一个 IP
###############################################
EOF
        echo -e ${NC}
    else
        echo -e ${YELLOW}
        cat <<EOF
###############################################
# Failed to automatically detect IP
# You have to specify your own IP
# For example: 
#   you can enter "11.22.33.44" for specific one
###############################################
EOF
        echo -e ${NC}
    fi
    for i in 1 2 3; do
        if [ "$LANG" == "zh_CN.UTF-8" ]; then
            echo -n -e "请输入您的 IP 地址:"
        else
            echo -n -e "Enter your IP address:"
        fi
        read RES
        verify_eip $IF_NUM $RES && break
        if [ "$LANG" == "zh_CN.UTF-8" ]; then
            echo -e "${RED}输入错误, 请重新输入${NC}"
        else
            echo -e "${RED}Incorrect input, please try again${NC}"
        fi
        if [ "$i" = "3" ]; then
            if [ "$LANG" == "zh_CN.UTF-8" ]; then
                send_error "输入错误超过3次, 中止安装"
                exit 1
            else
                send_error "The input error exceeds 3 times, aborting"
                exit 1
            fi
        fi
    done
fi

################## Main ################
# Start install rainbond standalone
# Automatically generate install cmd with envs
########################################

if [ "$LANG" == "zh_CN.UTF-8" ]; then
    echo -e "${GREEN}生成安装命令:${NC}"
    sleep 3
else
    echo -e "${GREEN}Generating the installation command:${NC}"
    sleep 3
fi

# Generate the installation command based on the detect results
if [ "$OS_TYPE" = "Linux" ]; then
  VOLUME_OPTS="-v /opt/rainbond:/opt/rainbond"
  RBD_IMAGE="${IMGHUB_MIRROR}/rainbond:${RAINBOND_VERSION}-k3s"
elif [ "$OS_TYPE" = "Darwin" ]; then
  VOLUME_OPTS="-v rainbond-opt:/opt/rainbond"
  RBD_IMAGE="${IMGHUB_MIRROR}/rainbond:${RAINBOND_VERSION}-k3s"
fi

# Generate cmd
docker_run_cmd="docker run --privileged -d -p 7070:7070 -p 80:80 -p 443:443 -p 6060:6060 -p 30000-30010:30000-30010 --name=rainbond --restart=always \
${VOLUME_OPTS} -e EIP=$EIP -e UUID=${UUID} ${RBD_IMAGE}"
send_info "$docker_run_cmd"

# Pull image with retry mechanism
if [ "$LANG" == "zh_CN.UTF-8" ]; then
    send_info "获取镜像中 ${RBD_IMAGE}..."
else
    send_info "Pulling image ${RBD_IMAGE}..."
fi

# Try to pull image with retries
pull_success=false
for retry in 1 2 3; do
  if docker pull ${RBD_IMAGE}; then
    pull_success=true
    rbd_image_id=$(docker images | grep k3s | grep ${RAINBOND_VERSION} | awk '{print $3}')
    if [ "$LANG" == "zh_CN.UTF-8" ]; then
      send_info "Rainbond 镜像获取成功，ID: ${rbd_image_id}"
    else
      send_info "Rainbond image pulled successfully, ID: ${rbd_image_id}"
    fi
    break
  else
    if [ "$retry" -lt 3 ]; then
      if [ "$LANG" == "zh_CN.UTF-8" ]; then
        send_warn "镜像拉取失败，正在重试 ($retry/3)..."
      else
        send_warn "Image pull failed, retrying ($retry/3)..."
      fi
      sleep 5
    fi
  fi
done

if [ "$pull_success" = false ]; then
  if [ "$LANG" == "zh_CN.UTF-8" ]; then
    send_error "镜像拉取失败，请检查网络连接"
  else
    send_error "Image pull failed, please check network connection"
  fi
  exit 1
fi

sleep 3

# Start container
if [ "$LANG" == "zh_CN.UTF-8" ]; then
  send_info "正在启动 Rainbond 容器..."
else
  send_info "Starting Rainbond container..."
fi

docker_run_meg=$(bash -c "$docker_run_cmd" 2>&1)
send_info "$docker_run_meg"
sleep 3

# Verify startup
sleep 5  # 等待容器启动
if docker ps --filter "name=rainbond" --filter "status=running" | grep -q "rainbond"; then
  if [ "$LANG" == "zh_CN.UTF-8" ]; then
    send_info "Rainbond 容器启动成功"
  else
    send_info "Rainbond container started successfully"
  fi
else
  if [ "$LANG" == "zh_CN.UTF-8" ]; then
    send_error "Rainbond 容器启动失败"
  else
    send_error "Rainbond container startup failed"
  fi
fi

if [ "$LANG" == "zh_CN.UTF-8" ]; then
  echo -e ${GREEN}
  cat <<EOF
###############################################
# Rainbond 版本: $RAINBOND_VERSION
# 架构: $ARCH_TYPE
# 操作系统: $OS_TYPE
# Rainbond 文档: https://www.rainbond.com/docs
################################################
# 访问 Rainbond:
#     - 请等待 5 分钟左右系统完全启动，随后在浏览器中输入 http://$EIP:7070 访问 Rainbond.
#     - 您可以通过以下命令观察启动进度: 
#         - docker exec -it rainbond bash 
#         - watch kubectl get pod -n rbd-system
#     - 如遇问题，请阅读故障排除文档 https://www.rainbond.com/docs/troubleshooting/install
# 如无法解决，请反馈至: 
#     - https://www.rainbond.com/docs/support
###############################################

EOF
  echo -e "${NC}"
else
  echo -e ${GREEN}
  cat <<EOF
###############################################
# Rainbond Version: $RAINBOND_VERSION
# Arch: $ARCH_TYPE
# OS: $OS_TYPE
# Rainbond Docs: https://www.rainbond.com/docs
################################################
# Access Rainbond:
#     - Please wait 5 minutes for system to fully start, then enter http://$EIP:7070 in the browser to access Rainbond.
#     - You can observe the startup progress with the following commands:
#         - docker exec -it rainbond bash 
#         - kubectl get pod -n rbd-system
#     - If you encounter problems, please read the troubleshooting document https://www.rainbond.com/docs/troubleshooting/install
# If you cannot solve the problem, please feedback to: 
#     - https://www.rainbond.com/docs/support
###############################################

EOF
  echo -e "${NC}"
fi