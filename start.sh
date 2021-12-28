#!/bin/bash
# This script determines whether the user opens the k3s cluster

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
    k3s_start
fi


## Execute subsequent commands
exec $@
