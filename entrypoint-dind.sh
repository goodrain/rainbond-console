#!/bin/bash

RED='\033[0;31m'
GREEN='\033[32;1m'
YELLOW='\033[33;1m'
NC='\033[0m' # No Color

########################################
# Basic Configuration
########################################
function basic_check {
    FREE=$(free -m |awk '/Mem/{print $2}')
    CPUS=$(grep -c "processor" < /proc/cpuinfo)
    DISK=$(df -m / |sed -n '2p'|awk '{print $4}')

    if [ ! "$EIP" ];then
        echo -e "${RED} EIP is required, please execute the following command and restart Rainbond ${NC}"
        echo -e "${RED} export EIP= IP address ${NC}"
        exit 1
    fi

    if [ "$FREE" -lt 4096 ]; then
        echo -e "${YELLOW} WARN: Too little memory, recommended memory configuration is 4G ${NC}"
    fi
    if [ "$CPUS" -lt 2 ];then
        echo -e "${YELLOW} WARN: Too few CPUs, recommended CPU configuration is 2 cores ${NC}"
    fi
    if [ "$DISK" -lt 51200 ];then
        echo -e "${YELLOW} WARN: Too little free disk space, recommended disk space greater than 50G ${NC}"
    fi
    echo -e "${GREEN} INFO: Memory: $FREE MB, CPUs: $CPUS, Disk: $DISK MB ${NC}"
    ## Do domain name resolution
    echo "127.0.0.1  rbd-api-api" >> /etc/hosts
}

########################################
# Start Docker
########################################

function start_docker {
    while_num=0
    supervisorctl start docker
    while true; do
        if docker ps > /dev/null 2>&1; then
            echo -e "${GREEN} INFO: Docker started successfully ${NC}"
            break
        fi
        sleep 5
        echo -e "${YELLOW} WARN: Waiting for Docker to start ${NC}"
        (( while_num++ )) || true
        if [ $(( while_num )) -gt 12 ]; then
            echo -e "${RED} ERROR: Docker failed to start. Please use the command to view the docker log 'docker exec rainbond-allinone /bin/cat /app/logs/dind.log'${NC}"
            exit 1
        fi
    done
}

########################################
# Load Docker Images
########################################

function load_images {
    if docker images | grep -q "rbd-api"; then
        echo -e "${GREEN} INFO: Docker images loaded ${NC}"
    else
        echo -e "${GREEN} INFO: Loading images ${NC}"
        while true; do
            if docker load -i /app/ui/rainbond-"${VERSION}".tar; then
                echo -e "${GREEN} INFO: Docker images success ${NC}"
                break
            fi
        done
    fi
}

########################################
# Start K3s
########################################

function start_k3s {
    # Fix the problem that cgroup version is too high to start
    if [ -f /sys/fs/cgroup/cgroup.controllers ]; then
        mkdir -p /sys/fs/cgroup/init
        xargs -rn1 < /sys/fs/cgroup/cgroup.procs > /sys/fs/cgroup/init/cgroup.procs || :
        sed -e 's/ / +/g' -e 's/^/+/' <"/sys/fs/cgroup/cgroup.controllers" >"/sys/fs/cgroup/cgroup.subtree_control"
    fi

    echo -e "${GREEN} INFO: Starting K3s ${NC}"
    supervisorctl start k3s
    while_num=0
    while true; do
        if kubectl get node | grep Ready > /dev/null 2>&1; then
            echo -e "${GREEN} INFO: K3s started successfully ${NC}"
            break
        fi
        sleep 5
        echo -e "${YELLOW} WARN: Waiting for K3s to start ${NC}"
        (( while_num++ )) || true
        if [ $(( while_num )) -gt 12 ]; then
            echo -e "${RED} ERROR: K3s failed to start. Please use the command to view the k3s log 'docker exec rainbond-allinone /bin/cat /app/logs/k3s.log' ${NC}"
            exit 1
        fi
    done
}

########################################
# Start Rainbond
########################################
IMAGE_DOMAIN=${IMAGE_DOMAIN:-docker.io}
IMAGE_NAMESPACE=${IMAGE_NAMESPACE:-rainbond}

function start_rainbond {
    # create namespace
    if kubectl get ns | grep rbd-system > /dev/null 2>&1; then
        echo -e "${GREEN} INFO: Namespace rbd-system already exists ${NC}"
    else
        kubectl create ns rbd-system
        echo -e "${GREEN} INFO: Create namespace rbd-system ${NC}"
    fi

    # create helm rainbond-operator
    HELM_RAINBOND_OPERATOR=$(helm list -n rbd-system | grep rainbond-operator | awk '{print $1}')
    if [[ "$HELM_RAINBOND_OPERATOR" == "rainbond-operator" ]]; then
        echo -e "${GREEN} INFO: Helm rainbond-operator already exists ${NC}"
    else
        RBD_LIST=(rbd-api rbd-chaos rbd-eventlog rbd-gateway rbd-monitor rbd-mq rbd-node rbd-resource-proxy rbd-webcli rbd-worker rbdcluster)
        for item in "${RBD_LIST[@]}"; do
            sed -i "s/v5.6.0-release/${VERSION}/g" /app/ui/rainbond-operator/config/single_node_cr/"$item".yml
        done

        helm install rainbond-operator /app/chart -n rbd-system --kubeconfig /root/.kube/config \
            --set operator.image.name="${IMAGE_DOMAIN}"/"${IMAGE_NAMESPACE}"/rainbond-operator \
            --set operator.image.tag="${VERSION}"
        echo -e "${GREEN} INFO: Helm rainbond-operator installed ${NC}"

        # setting rainbondcluster
        NODE_NAME=$(kubectl get node | sed -n '2p' | awk '{print $1}')
        NODE_IP=$(kubectl get node -owide | sed -n '2p' | awk '{print $6}')
        EIP=${EIP:-$NODE_IP}
        IIP=${IIP:-$NODE_IP}
        sed -i "s/single_node_name/$NODE_NAME/" /app/ui/rainbond-operator/config/single_node_cr/rbdcluster.yml
        sed -i "s/single_node_external_ip/$EIP/" /app/ui/rainbond-operator/config/single_node_cr/rbdcluster.yml
        sed -i "s/single_node_internal_ip/$IIP/" /app/ui/rainbond-operator/config/single_node_cr/rbdcluster.yml

        if kubectl apply -f /app/ui/rainbond-operator/config/single_node_cr/ -n rbd-system > /dev/null 2>&1; then
            echo -e "${GREEN} INFO: Rainbond Region installed ${NC}"
        else
            echo -e "${RED} ERROR: Rainbond Region failed to install ${NC}"
            exit 1
        fi
    fi
    while true; do
        if curl http://"$(kubectl get svc -n rbd-system | grep rbd-api-api-inner | awk '{print $3}')":8888/v2/health 2>&1 | grep health > /dev/null 2>&1; then
            echo -e "${GREEN} INFO: Rainbond Region started successfully ${NC}"
            break
        fi
        sleep 5
        echo -e "${YELLOW} WARN: Waiting for Rainbond start ${NC}"
    done
    supervisorctl start console
    while true; do
        if curl http://127.0.0.1:7070 > /dev/null 2>&1; then
            echo -e "${GREEN} INFO: Rainbond started successfully, Please pass http://$EIP:7070 Access Rainbond ${NC}"
            break
        fi
        sleep 5
    done
}

function stop_container {
    echo -e "${GREEN} INFO: Stopping K3s ${NC}"
    supervisorctl stop k3s
    echo -e "${GREEN} INFO: Stopping Docker ${NC}"
    systemctl stop docker
    exit 1
}

trap stop_container SIGTERM

# basic environment check
basic_check

# start docker
start_docker

# load docker images
load_images

# start k3s
start_k3s

# start rainbond
start_rainbond
