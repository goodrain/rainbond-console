#!/bin/bash

# Basic environment variables
RAINBOND_VERSION=${VERSION:-'v5.10.1'}
IMGHUB_MIRROR="registry.cn-hangzhou.aliyuncs.com/goodrain"

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
    if find /lib/modules/$(uname -r) -type f -name '*.ko*' | grep iptable_raw; then
        if ! lsmod | grep iptable_raw; then
            echo iptable_raw >/etc/modules-load.d/iptable_raw.conf
            modprobe iptable_raw
        fi
    fi
elif [ "${OS_TYPE}" == "Darwin" ]; then
    MD5_CMD="md5"
else
    send_error "Rainbond do not support ${OS_TYPE} OS"
    exit 1
fi

OS_INFO=$(uname -a)
UUID=$(echo $OS_INFO | ${MD5_CMD} | cut -b 1-32)

################ Start #################
send_info "Welcome! let\`s start Rainbond dind allinone distribution..."

########################################
# Envrionment Check
# Check docker is running or not.
# Check ports can be use or not.
# If not, quit.
########################################

if ! (docker info &>/dev/null); then
    if (which docker &>/dev/null); then
        send_error "Ops! Docker daemon is not running. Start docker first please.\nTry to exec 'systemctl start docker' in Linux or start Docker Desktop APP in MacOS.\nAnd re-exec this script."
        exit 1
    elif [ "${OS_TYPE}" = "Linux" ]; then
        send_warn "Ops! Docker has not been installed.\nDocker is going to be automatically installed...\n"
        sleep 3
        curl -sfL https://get.rainbond.com/install_docker | bash
        if [ "$?" != "0" ]; then
            send_error "Ops! Automatic docker installation failed."
            exit 1
        fi
    elif [ "${OS_TYPE}" = "Darwin" ]; then
        send_warn "Ops! Docker has not been installed.\nPlease visit the following website to get the latest Docker Desktop APP.\n\thttps://www.docker.com/products/docker-desktop/"
        exit 1
    fi
else
    if docker ps -a | grep rainbond-allinone 2>&1 >/dev/null; then
        send_error "Ops! rainbond-allinone container already exists.\n\t- Ensure if rainbond-allinone is running.\n\t- Try to exec 'docker start rainbond-allinone' to start it.\n\t- Or you can remove it by 'docker rm -f rainbond-allinone'"
        exit 1
    fi
fi

ports=(80 443 6060 7070 8443)
for port in ${ports[@]}; do
    if (curl -s 127.0.0.1:$port >/dev/null); then
        send_error "Ops! Port $port has been used."
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
    send_warn "i386 has been detect, we'll treat it like x86_64(amd64). If you are using the M1 chip MacOS,make sure your terminal has Rosetta disabled.\n\t Have a look : https://github.com/goodrain/rainbond/issues/1439 "
else
    send_error "Rainbond do not support $(arch) architecture"
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
        echo -e "${YELLOW}Do not enter null values${NC}"
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
            echo -e "${YELLOW}Wrong index of IP${NC}"
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
 
The following IP has been detected:
EOF
    echo -e ${NC}

    for ((i = 1; i <= $IF_NUM; i++)); do
        echo -e "\t${GREEN}$i${NC} : ${ip_list[$i - 1]}"
    done

    for i in 1 2 3; do
        echo -e "\n${GREEN}For example: enter '1' to choose the first IP, or input '11.22.33.44'(IPv4 address) for specific one ${NC}"
        echo -n -e "Enter your choose or a specific IP address:"
        read res
        verify_eip $IF_NUM $res && break
        echo -e "${RED}Incorrect input, please try again${NC}"
        if [ "$i" = "3" ]; then
            send_error "The input error exceeds 3 times, aborting"
            exit 1
        fi
    done
else
    # Gave some tips
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

    for i in 1 2 3; do
        echo -n -e "Enter your choose or a specific IP address:"
        read RES
        verify_eip $IF_NUM $RES && break
        echo -e "${RED}Incorrect input, please try again${NC}"
        if [ "$i" = "3" ]; then
            send_error "The input error exceeds 3 times, aborting"
            exit 1
        fi
    done
fi

################## Main ################
# Start install rainbond-dind-allinone
# Automatically generate install cmd with envs
########################################

# Gave some info
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
send_info "Pulling image ${RBD_IMAGE}..."
if docker pull ${RBD_IMAGE}; then
    rbd_image_id=$(docker images | grep dind-allinone | grep ${RAINBOND_VERSION} | awk '{print $3}')
    send_info "Use dind image with ID:${rbd_image_id}"
else
    send_error "Pull image failed."
fi
sleep 3

# Run container
send_info "Rainbond dind allinone distribution is installing...\n"
docker_run_meg=$(bash -c "$docker_run_cmd" 2>&1)
send_info "$docker_run_meg"
sleep 3

# Verify startup
container_id=$(docker ps -a | grep rainbond-allinone | awk '{print $1}')
if docker ps | grep rainbond-allinone 2>&1 >/dev/null; then
    send_info "Rainbond dind allinone container startup succeeded with $container_id.\nPay attention to the installation log.\n"
else
    send_warn "Ops! Rainbond dind allinone container startup failed.\nPay attention to the installation log.\n"
    send_msg "$(docker logs rainbond-allinone)" # Msg maybe too lang
fi

sleep 3
# Follow logs stdout
docker logs -f rainbond-allinone
