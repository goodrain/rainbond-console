#!/bin/bash

# Basic environment variables 
RAINBOND_VERSION=${VERSION:-'v5.11.0'}
IMGHUB_MIRROR="registry.cn-hangzhou.aliyuncs.com/goodrain"
LANG=$(locale | grep -qi 'UTF-8' && echo 'true' || echo 'false')

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
    if [ -z "$1" ]; then
        if [ "$LANG" == "true" ]; then
            msg="用户自行终止。"
        else
            msg="Terminating by userself."
        fi
    else
        msg=$(echo $1 | tr '"' " " | tr "'" " ")
    fi
    # send a message to remote url
    curl --silent -H "Content-Type: application/json" -X POST "$dest_url/dindlog" \
        -d "{\"message\":\"$msg\", \"os_info\":\"${OS_INFO}\", \"eip\":\"$EIP\", \"uuid\":\"${UUID}\"}" 2>&1 >/dev/null || :

    if [ "$msg" == "用户自行终止。" ] || [ "$msg" == "Terminating by userself." ]; then
        exit 1
    fi
}

function send_info() {
    info=$1
    if [ "$LANG" == "true" ]; then
        echo -e "${GREEN}$(date "$TIME") 信息: $info${NC}"
    else
        echo -e "${GREEN}$(date "$TIME") INFO: $info${NC}"
    fi
    send_msg "$info"
}

function send_warn() {
    warn=$1
    if [ "$LANG" == "true" ]; then
        echo -e "${YELLOW}$(date "$TIME") 警告: $warn${NC}"
    else
        echo -e "${YELLOW}$(date "$TIME") WARN: $warn${NC}"
    fi
    send_msg "$warn"
}

function send_error() {
    error=$1
    if [ "$LANG" == "true" ]; then
        echo -e "${RED}$(date "$TIME") 错误: $error${NC}"
    else
        echo -e "${RED}$(date "$TIME") ERROR: $error${NC}"
    fi
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
    if find /lib/modules/$(uname -r) -type f -name '*.ko*' | grep iptable_raw; then
        if ! lsmod | grep iptable_raw; then
            echo iptable_raw >/etc/modules-load.d/iptable_raw.conf
            modprobe iptable_raw
        fi
    fi
elif [ "${OS_TYPE}" == "Darwin" ]; then
    MD5_CMD="md5"
else
    if [ "$LANG" == "true" ]; then
        send_error "Rainbond 不支持 ${OS_TYPE} 操作系统"
    else
        send_error "Rainbond do not support ${OS_TYPE} OS"
    fi
    exit 1
fi

OS_INFO=$(uname -a)
UUID=$(echo $OS_INFO | ${MD5_CMD} | cut -b 1-32)

################ Start #################
if [ "$LANG" == "true" ]; then
    send_info "欢迎！让我们开始 Rainbond 发行版的安装吧！"
else
    send_info "Welcome! let\`s start Rainbond dind allinone distribution..."
fi

########################################
# Envrionment Check
# Check docker is running or not.
# Check ports can be use or not.
# If not, quit.
########################################

if ! (docker info &>/dev/null); then
    if (which docker &>/dev/null); then
        if [ "$LANG" == "true" ]; then
            send_error "Ops! Docker daemon is not running. Start docker first please.\nTry to exec 'systemctl start docker' in Linux or start Docker Desktop APP in MacOS.\nAnd re-exec this script."
        else
            send_error "错误：Docker 守护进程未运行。请先启动 Docker。\n在 Linux 系统下执行 'systemctl start docker' 命令，或在 MacOS 系统下启动 Docker Desktop APP。\n然后再次执行本脚本。"
        fi
        exit 1
    elif [ "${OS_TYPE}" = "Linux" ]; then
        if [ "$LANG" == "true" ]; then
            send_warn "Ops! Docker has not been installed.\nDocker is going to be automatically installed...\n"
        else
            send_warn "警告：未安装 Docker。\n正在自动安装 Docker...\n"
        fi
        sleep 3
        curl -sfL https://get.rainbond.com/install_docker | bash
        if [ "$?" != "0" ]; then
            if [ "$LANG" == "true" ]; then
                send_error "Ops! Automatic docker installation failed."
            else
                send_error "错误：自动安装 Docker 失败。"
            fi
            exit 1
        fi
    elif [ "${OS_TYPE}" = "Darwin" ]; then
        if [ "$LANG" == "true" ]; then
            send_warn "Ops! Docker has not been installed.\nPlease visit the following website to get the latest Docker Desktop APP.\n\thttps://www.docker.com/products/docker-desktop/"
        else
            send_warn "警告：未安装 Docker。\n请访问以下网站获取最新的 Docker Desktop APP。\n\thttps://www.docker.com/products/docker-desktop/"
        fi
        exit 1
    fi
else
    if docker ps -a | grep rainbond-allinone 2>&1 >/dev/null; then
        if [ "$LANG" == "true" ]; then
            send_error "Ops! rainbond-allinone container already exists.\n\t- Ensure if rainbond-allinone is running.\n\t- Try to exec 'docker start rainbond-allinone' to start it.\n\t- Or you can remove it by 'docker rm -f rainbond-allinone'"
        else
            send_error "错误：rainbond-allinone 容器已经存在。\n\t- 请确保 rainbond-allinone 正在运行。\n\t- 尝试执行 'docker start rainbond-allinone' 命令启动它。\n\t- 或者您可以通过 'docker rm -f rainbond-allinone' 命令删除它。"
        fi
        exit 1
    fi
fi

ports=(80 443 6060 7070 8443)
for port in ${ports[@]}; do
    if (curl -s 127.0.0.1:$port >/dev/null); then
        if [ "$LANG" == "true" ]; then
            send_error "Ops! Port $port has been used."
        else
            send_error "错误：端口 $port 已经被占用。"
        fi
        exit 1
    fi
done

########################################
# Arch Detect
# Automatically check the CPU architecture type.
# Return amd64 or arm64.
########################################

if [ $(arch) = "x86_64" ] || [ $(arch) = "amd64" ]; then
    ARCH_TYPE=amd64
elif [ $(arch) = "aarch64" ] || [ $(arch) = "arm64" ]; then
    ARCH_TYPE=arm64
elif [ $(arch) = "i386" ]; then
    ARCH_TYPE=amd64
    if [ "$LANG" == "true" ]; then
        send_warn "检测到 i386，我们将把它视为 x86_64 (amd64) 处理。如果你正在使用 M1 芯片的 MacOS，请确保终端已禁用 Rosetta。\n\t 请参考: https://github.com/goodrain/rainbond/issues/1439"
    else
        send_warn "i386 has been detected, we'll treat it like x86_64 (amd64). If you are using the M1 chip MacOS, make sure your terminal has Rosetta disabled.\n\t Have a look: https://github.com/goodrain/rainbond/issues/1439"
    fi
else
    if [ "$LANG" == "true" ]; then
        send_error "Rainbond 不支持 $(arch) 架构"
    else
        send_error "Rainbond does not support $(arch) architecture"
    fi
    exit 1
fi

########################################
# EIP Detect
# Automatically check the IP address.
# User customization is also supported.
########################################

# Choose tool for IP detect.
if which ip >/dev/null; then
    IF_NUM=$(ip -4 a | egrep -v "docker0|flannel|cni|calico|kube" | grep inet | wc -l)
    IPS=$(ip -4 a | egrep -v "docker0|flannel|cni|calico|kube" | grep inet | awk '{print $2}' | awk -F '/' '{print $1}' | tr '\n' ' ')
elif which ifconfig >/dev/null; then
    IF_NUM=$(ifconfig | grep -w inet | awk '{print $2}' | wc -l)
    IPS=$(ifconfig | grep -w inet | awk '{print $2}')
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
        if [ "$LANG" == "true" ]; then
            echo -e "${YELLOW}不要输入空值${NC}"
        else
            echo -e "${YELLOW}Do not enter null values${NC}"
        fi
        return 1
    # Regular matching IPv4
    elif [[ $result =~ ^([0-9]{1,2}|1[0-9][0-9]|2[0-4][0-9]|25[0-5]).([0-9]{1,2}|1[0-9][0-9]|2[0-4][0-9]|25[0-5]).([0-9]{1,2}|1[0-9][0-9]|2[0-4][0-9]|25[0-5]).([0-9]{1,2}|1[0-9][0-9]|2[0-4][0-9]|25[0-5])$ ]]; then
        export EIP=$result
        return 0
    # Regular matching positive integer
    elif [[ $result =~ \d? ]]; then
        if [ $result -gt 0 ] && [ $result -le $max ]; then
            export EIP=${ip_list[$result - 1]}
            return 0
        else
            if [ "$LANG" == "true" ]; then
                echo -e "${YELLOW}错误的IP索引${NC}"
            else
                echo -e "${YELLOW}Wrong index of IP${NC}"
            fi
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

    # Print colored output based on system locale
    if [ "$LANG" == "true" ]; then
        echo -e ${GREEN}
        cat <<EOF
###############################################
# 自动检测到以下IP地址
# 您可以通过输入索引来选择其中一个IP地址
# 如果您有一个公网IP，请直接输入
# 例如：
#   输入"1"以选择第一个IP
#   或输入"11.22.33.44"以选择特定的IP
###############################################

自动检测到以下IP地址：
EOF
    else
        echo -e ${GREEN}
        cat <<EOF
###############################################
# The following IP are automatically detected
# You can choose one by enter its index
# If you have an Public IP, Just type it in
# For example: 
#   you can enter "1" to choose the first IP
#   or enter "11.22.33.44" for specific one
###############################################

The following IP addresses have been detected:
EOF
    fi
    echo -e ${NC}

    for ((i = 1; i <= $IF_NUM; i++)); do
        echo -e "\t${GREEN}$i${NC} : ${ip_list[$i - 1]}"
    done
		
		for i in 1 2 3; do
    		if [ "$LANG" == "true" ]; then
        		echo -e "\n${GREEN}例如：输入'1'选择第一个IP，或输入'11.22.33.44'(IPv4地址)选择特定的IP ${NC}"
        		echo -n -e "输入您的选择或指定的IP地址："
   			else
        		echo -e "\n${GREEN}For example: enter '1' to choose the first IP, or input '11.22.33.44'(IPv4 address) for specific one ${NC}"
       		  echo -n -e "Enter your choose or a specific IP address:"
    		fi
    
    read res
    verify_eip $IF_NUM $res && break

    		if [ "$LANG" == "true" ]; then
       		 echo -e "${RED}输入有误，请重试${NC}"
   		  else
       		 echo -e "${RED}Incorrect input, please try again${NC}"
   		  fi
    
    		if [ "$i" = "3" ]; then
        		if [ "$LANG" == "true" ]; then
           		  send_error "输入错误超过3次，正在终止程序"
       		  else
            		send_error "The input error exceeds 3 times, aborting"
        		fi
       		  exit 1
    		fi
		done
else
    # Print colored output based on system locale
    if [ "$LANG" == "true" ]; then
        echo -e ${YELLOW}
        cat <<EOF
###############################################
# 未能自动检测到IP地址
# 您需要指定自己的IP地址
# 例如：
#   输入"11.22.33.44"选择特定的IP地址
###############################################
EOF
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
    fi
    echo -e ${NC}

    for i in 1 2 3; do
        if [ "$LANG" == "true" ]; then
        		echo -n -e "输入您的选择或指定的IP地址："
    		else
        		echo -n -e "Enter your choose or a specific IP address:"
    		fi

    read RES
    verify_eip $IF_NUM $RES && break

    		if [ "$LANG" == "true" ]; then
        		echo -e "${RED}输入有误，请重试${NC}"
    		else
        		echo -e "${RED}Incorrect input, please try again${NC}"
    		fi
    		
        if [ "$i" = "3" ]; then
        		if [ "$LANG" == "true" ]; then
           		  send_error "输入错误超过3次，正在终止程序"
       		  else
            		send_error "The input error exceeds 3 times, aborting"
        		fi
       		  exit 1
    		fi
    done
fi

################## Main ################
# Start install rainbond-dind-allinone
# Automatically generate install cmd with envs
########################################

if [ "$LANG" == "true" ]; then
    echo -e ${GREEN}
    cat <<EOF
###############################################
# 将安装以下配置的 Rainbond 发行版：
# Rainbond 版本：$RAINBOND_VERSION
# 架构：$ARCH_TYPE
# 操作系统：$OS_TYPE
# 网站：http://$EIP:7070
# Rainbond 文档：https://www.rainbond.com/docs
# 如遇到任何问题，可以反馈给我们：
#     https://github.com/goodrain/rainbond
###############################################
EOF
    echo -e "${NC}"
    echo -e "${GREEN}正在生成安装命令：${NC}"
else
    echo -e ${GREEN}
    cat <<EOF
###############################################
# Rainbond dind allinone will be installed with:
# Rainbond Version: $RAINBOND_VERSION
# Arch: $ARCH_TYPE
# OS: $OS_TYPE
# Web Site: http://$EIP:7070
# Rainbond Docs: https://www.rainbond.com/docs
# You can submit an issue if you encounter any problems:
#     https://github.com/goodrain/rainbond
###############################################
EOF
    echo -e "${NC}"
    echo -e "${GREEN}Generating the installation command:${NC}"
fi
sleep 3

# Generate the installation command based on the detect results
if [ "$OS_TYPE" = "Linux" ]; then
    if [ "$ARCH_TYPE" = "amd64" ]; then
        VOLUME_OPTS="-v ~/.ssh:/root/.ssh -v ~/rainbonddata:/app/data -v /opt/rainbond:/opt/rainbond"
        RBD_IMAGE="${IMGHUB_MIRROR}/rainbond:${RAINBOND_VERSION}-dind-allinone"
    elif [ "$ARCH_TYPE" = "arm64" ]; then
        VOLUME_OPTS="-v ~/.ssh:/root/.ssh -v ~/rainbonddata:/app/data -v /opt/rainbond:/opt/rainbond"
        RBD_IMAGE="${IMGHUB_MIRROR}/rainbond:${RAINBOND_VERSION}-arm64-dind-allinone"
    fi
elif [ "$OS_TYPE" = "Darwin" ]; then
    if [ "$ARCH_TYPE" = "amd64" ]; then
        VOLUME_OPTS="-v ~/.ssh:/root/.ssh -v rainbond-data:/app/data -v rainbond-opt:/opt/rainbond"
        RBD_IMAGE="${IMGHUB_MIRROR}/rainbond:${RAINBOND_VERSION}-dind-allinone"
    elif [ "$ARCH_TYPE" = "arm64" ]; then
        VOLUME_OPTS="-v ~/.ssh:/root/.ssh -v rainbond-data:/app/data -v rainbond-opt:/opt/rainbond"
        RBD_IMAGE="${IMGHUB_MIRROR}/rainbond:${RAINBOND_VERSION}-arm64-dind-allinone"
    fi
fi

# Generate cmd
docker_run_cmd="docker run --privileged -d -p 7070:7070 -p 80:80 -p 443:443 -p 6060:6060 -p 8443:8443 -p 10000-10010:10000-10010 --name=rainbond-allinone --restart=on-failure \
${VOLUME_OPTS} -e EIP=$EIP -e UUID=${UUID} ${RBD_IMAGE}"
send_info "$docker_run_cmd"

# Pull image
if [ "$LANG" == "true" ]; then
    send_info "Pulling image ${RBD_IMAGE}..."
else
    send_info "正在拉取镜像 ${RBD_IMAGE}..."
fi

if docker pull ${RBD_IMAGE}; then
    rbd_image_id=$(docker images | grep dind-allinone | grep ${RAINBOND_VERSION} | awk '{print $3}')    
    if [ "$LANG" == "true" ]; then
        send_info "Use dind image with ID:${rbd_image_id}"
    else
        send_info "使用的发行版镜像 ID 为:${rbd_image_id}"
    fi
else
    if [ "$LANG" == "true" ]; then
        send_error "Pull image failed."
    else
        send_error "拉取镜像失败."
    fi
fi
sleep 3

# Run container
if [ "$LANG" == "true" ]; then
    send_info "Rainbond 发行版正在安装中...\n"
else
    send_info "Rainbond dind allinone distribution is installing...\n"
fi
docker_run_meg=$(bash -c "$docker_run_cmd" 2>&1)
send_info "$docker_run_meg"
sleep 3

# Verify startup
if [ "$LANG" == "true" ]; then
    container_id=$(docker ps -a | grep rainbond-allinone | awk '{print $1}')
    if docker ps | grep rainbond-allinone 2>&1 >/dev/null; then
        send_info "Rainbond 发行版容器启动成功，容器ID为 $container_id。\n请注意安装日志。\n"
    else
        send_warn " 警告：Rainbond 发行版容器启动失败。\n请注意安装日志。\n"
        send_msg "$(docker logs rainbond-allinone)" # 消息可能太长
    fi
else
    container_id=$(docker ps -a | grep rainbond-allinone | awk '{print $1}')
    if docker ps | grep rainbond-allinone 2>&1 >/dev/null; then
        send_info "Rainbond dind allinone container startup succeeded with $container_id.\nPay attention to the installation log.\n"
    else
        send_warn "Ops! Rainbond dind allinone container startup failed.\nPay attention to the installation log.\n"
        send_msg "$(docker logs rainbond-allinone)" # Msg maybe too lang
    fi
fi
sleep 3

# Follow logs stdout
docker logs -f rainbond-allinone
