#!/bin/bash
# This script determines whether the user opens the k3s cluster


FREE=`free -m |awk '/Mem/{print $4}'`
CPUS=`cat /proc/cpuinfo | grep "processor" | wc -l`
DISK=`df -m / |awk '/sda1/{print $4}'`
# Move the dockerd k3s configuration to let the supervisor manage the process
# Unzip the image package and delete the compressed package
function k3s_start() {
    mv /etc/supervisor/conf.d/dind.conf.bak  /etc/supervisor/conf.d/dind.conf
}

# dockerd startup parameters are passed in through environment variables
function Pass_dockerd_parameters() {
    sed -i "/dockerd/ s/$/ "${DOCKER_ARGS}"/" /etc/supervisor/conf.d/dind.conf
}
function Pass_k3s_parameters() {
    sed -i "/traefik/ s/$/ "${K3S_ARGS}"/" /app/ui/k3s.sh
}

## Judge whether to start k3s through environment variables
if [ -n "${DOCKER_ARGS}" ];then
    Pass_dockerd_parameters
fi

if [ -n "${K3S_ARGS}" ];then
    Pass_k3s_parameters
fi

if [ "${ENABLE_CLUSTER}" == 'true' ];then
    # explicitly remove Docker's default PID file to ensure that it can start properly if it was stopped uncleanly (and thus didn't clean up the PID file)
    find /run /var/run -iname 'docker*.pid' -delete || :
    
    # memory detection（4G）
    if [ $FREE -lt 4096 ]; then
        echo -e "\033[31m \!\!\!Problem: free=$FREE,Insufficient memory, at least 4G memory is required. \033[0m"
    fi
    
    # cpu core detection (2)
    if [ $CPUS  -lt 2 ];then
        echo -e "\033[31m \!\!\!Problem: cpus=$CPUS,Insufficient number of cores, at least 2 cores required. \033[0m"
    fi

    # disk detection (50G)
    if [ $DISK -lt 51200 ];then
        echo -e "\033[31m \!\!\!Problem: disk=$DISK,Insufficient disk space, at least 50G required. \033[0m"
    fi
        k3s_start
fi


## Execute subsequent commands
exec $@
