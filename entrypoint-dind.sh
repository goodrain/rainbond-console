#!/bin/bash

RED='\033[0;31m'
GREEN='\033[32;1m'
YELLOW='\033[33;1m'
NC='\033[0m' # No Color
TIME="+%Y-%m-%d %H:%M:%S"

########################################
# Basic Configuration
########################################
function basic_check {
    FREE=$(free -m |awk '/Mem/{print $2}')
    CPUS=$(grep -c "processor" < /proc/cpuinfo)
    DISK=$(df -m / |sed -n '2p'|awk '{print $4}')

    if [ "$FREE" -lt 2048 ]; then
        echo -e "${YELLOW}$(date "$TIME") WARN: Too little memory, recommended memory configuration is 2G ${NC}"
    fi
    if [ "$CPUS" -lt 2 ];then
        echo -e "${YELLOW}$(date "$TIME") WARN: Too few CPUs, recommended CPU configuration is 2 cores ${NC}"
    fi
    if [ "$DISK" -lt 51200 ];then
        echo -e "${YELLOW}$(date "$TIME") WARN: Too little free disk space, recommended disk space greater than 50G ${NC}"
    fi
    echo -e "${GREEN}$(date "$TIME") INFO: Memory: $FREE MB, CPUs: $CPUS, Disk: $DISK MB ${NC}"
    ## Do domain name resolution
    echo "127.0.0.1  rbd-api-api" >> /etc/hosts

    # explicitly remove Docker's default PID file to ensure that it can start properly if it was stopped uncleanly (and thus didn't clean up the PID file)
    find /run /var/run -iname 'docker*.pid' -delete || :
}

########################################
# Start Docker
########################################

function start_docker {
    while_num=0
    supervisorctl start docker > /dev/null 2>&1
    echo -e "${GREEN}$(date "$TIME") INFO: Docker is starting, please wait ············································${NC}"
    while true; do
        if docker ps > /dev/null 2>&1; then
            echo -e "${GREEN}$(date "$TIME") INFO: Docker started successfully ${NC}"
            break
        fi
        sleep 5
        (( while_num++ )) || true
        if [ $(( while_num )) -gt 12 ]; then
            echo -e "${RED}$(date "$TIME") ERROR: Docker failed to start. Please use the command to view the docker log 'docker exec rainbond-allinone /bin/cat /app/logs/dind.log'${NC}"
            exit 1
        fi
    done
}

########################################
# Load Docker Images
########################################

function load_images {
    echo -e "${GREEN}$(date "$TIME") INFO: move images ${NC}"
    mkdir -p /app/data/k3s/agent/images
    mv /app/ui/rainbond-"${VERSION}".tar /app/data/k3s/agent/images/
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
    supervisorctl start k3s > /dev/null 2>&1
    echo -e "${GREEN}$(date "$TIME") INFO: K3s is starting, please wait ············································${NC}"
    while_num=0
    while true; do
        K3S_STATUS=$(netstat -nltp | grep k3s | grep -c -E "6443|6444|10248|10249|10250|10251|10256|10257|10258|10259")
        if [[ "${K3S_STATUS}" == "10" ]]; then
            if kubectl get node | grep Ready > /dev/null 2>&1; then
                echo -e "${GREEN}$(date "$TIME") INFO: K3s started successfully ${NC}"
                break
            fi
        fi
        sleep 5
        (( while_num++ )) || true
        if [ $(( while_num )) -gt 12 ]; then
            echo -e "${RED}$(date "$TIME") ERROR: K3s failed to start. Please use the command to view the k3s log 'docker exec rainbond-allinone /bin/cat /app/logs/k3s.log' ${NC}"
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
        echo -e "${GREEN}$(date "$TIME") INFO: Namespace rbd-system already exists ${NC}"
    else
        kubectl create ns rbd-system
        echo -e "${GREEN}$(date "$TIME") INFO: Create namespace rbd-system ${NC}"
    fi

    # create helm rainbond-operator
    HELM_RAINBOND_OPERATOR=$(helm list -n rbd-system | grep rainbond-operator | awk '{print $1}')
    if [[ "$HELM_RAINBOND_OPERATOR" == "rainbond-operator" ]]; then
        echo -e "${GREEN}$(date "$TIME") INFO: Helm rainbond-operator already exists ${NC}"
    else
        RBD_LIST=(rbd-api rbd-chaos rbd-eventlog rbd-gateway rbd-monitor rbd-mq rbd-node rbd-resource-proxy rbd-webcli rbd-worker rbdcluster)
        for item in "${RBD_LIST[@]}"; do
            sed -i "s/v5.6.0-release/${VERSION}/g" /app/ui/rainbond-operator/config/single_node_cr/"$item".yml
        done
        ping -c 3 buildpack.oss-cn-shanghai.aliyuncs.com  >/dev/null 2>&1
        if [ $? != 0 ]; then
            sed -i "s#rainbond/rbd-resource-proxy:v5.6.0-release#nginx:1.19#g" /app/ui/rainbond-operator/config/single_node_cr/rbd-resource-proxy.yml
        fi
        helm install rainbond-operator /app/chart -n rbd-system --kubeconfig /root/.kube/config \
            --set operator.image.name="${IMAGE_DOMAIN}"/"${IMAGE_NAMESPACE}"/rainbond-operator \
            --set operator.image.tag="${VERSION}" \
            --set operator.image.env[0].name=IS_SQLLITE \
            --set operator.image.env[0].value=TRUE \
            --set operator.isDind=true
        echo -e "${GREEN}$(date "$TIME") INFO: Helm rainbond-operator installed ${NC}"

        # setting rainbondcluster
        NODE_NAME=$(kubectl get node | sed -n '2p' | awk '{print $1}')
        NODE_IP=$(kubectl get node -owide | sed -n '2p' | awk '{print $6}')
        EIP=${EIP:-$NODE_IP}
        IIP=${IIP:-$NODE_IP}
        sed -i "s/single_node_name/$NODE_NAME/" /app/ui/rainbond-operator/config/single_node_cr/rbdcluster.yml
        sed -i "s/single_node_external_ip/$EIP/" /app/ui/rainbond-operator/config/single_node_cr/rbdcluster.yml
        sed -i "s/single_node_internal_ip/$IIP/" /app/ui/rainbond-operator/config/single_node_cr/rbdcluster.yml

        if kubectl apply -f /app/ui/rainbond-operator/config/single_node_cr/ -n rbd-system > /dev/null 2>&1; then
            echo -e "${GREEN}$(date "$TIME") INFO: Rainbond Region installed ${NC}"
        else
            echo -e "${RED}$(date "$TIME") ERROR: Rainbond Region failed to install ${NC}"
            exit 1
        fi
    fi
    echo -e "${GREEN}$(date "$TIME") INFO: Rainbond Region is starting, please wait ············································${NC}"
    while true; do
        if netstat -nltp | grep 8443 > /dev/null 2>&1; then
            if curl http://"$(kubectl get svc -n rbd-system | grep rbd-api-api-inner | awk '{print $3}')":8888/v2/health 2>&1 | grep health > /dev/null 2>&1; then
                echo -e "${GREEN}$(date "$TIME") INFO: Rainbond Region started successfully ${NC}"
                break
            fi
        fi
        sleep 5
    done
    mkdir -p /app/containerd_certificate
    cp `find / -name server.crt|sed -n 1p` /app/containerd_certificate/
    kubectl get secret -oyaml -nrbd-system |grep tls.crt|awk '{print $2}'|base64 -d > /app/containerd_certificate/tls.crt
    kubectl get secret -oyaml -nrbd-system |grep tls.key|awk '{print $2}'|base64 -d > /app/containerd_certificate/tls.key
    mv /app/ui/registries.yaml /etc/rancher/k3s/
    grpasswd=`kubectl get rainbondcluster -oyaml -nrbd-system |grep password|awk '{print $2}'`
    sed -i "s/grpasswd/$grpasswd/g" /etc/rancher/k3s/registries.yaml
    sed -i "s/grpasswd/``/g" /etc/rancher/k3s/registries.yaml
    supervisorctl restart k3s > /dev/null 2>&1
    echo -e "${GREEN}$(date "$TIME") INFO: K3s is restarting, please wait ············································${NC}"
    while_num=0
    while true; do
        K3S_STATUS=$(netstat -nltp | grep k3s | grep -c -E "6443|6444|10248|10249|10250|10251|10256|10257|10258|10259")
        if [[ "${K3S_STATUS}" == "10" ]]; then
            if kubectl get node | grep Ready > /dev/null 2>&1; then
                echo -e "${GREEN}$(date "$TIME") INFO: K3s restarted successfully ${NC}"
                break
            fi
        fi
        sleep 5
        (( while_num++ )) || true
        if [ $(( while_num )) -gt 12 ]; then
            echo -e "${RED}$(date "$TIME") ERROR: K3s failed to restart. Please use the command to view the k3s log 'docker exec rainbond-allinone /bin/cat /app/logs/k3s.log' ${NC}"
            exit 1
        fi
    done
    kubectl delete pod `kubectl get pod -nrbd-system|grep rbd-chaos|awk '{print $1}'` -nrbd-system
    supervisorctl start console > /dev/null 2>&1
    echo -e "${GREEN}$(date "$TIME") INFO: Rainbond console is starting, please wait ············································${NC}"
    while true; do
        if curl http://127.0.0.1:7070 > /dev/null 2>&1; then
            echo -e "${GREEN}$(date "$TIME") INFO: Rainbond started successfully, Please pass http://$EIP:7070 Access Rainbond ${NC}"
            break
        fi
        sleep 5
    done
}

function stop_container {
    echo -e "${GREEN}$(date "$TIME") INFO: Stopping K3s ${NC}"
    supervisorctl stop k3s
#    echo -e "${GREEN}$(date "$TIME") INFO: Stopping Docker ${NC}"
#    systemctl stop docker
    exit 1
}

trap stop_container SIGTERM

# basic environment check
basic_check

# start docker
#start_docker

# load containerd images
load_images

# start k3s
start_k3s

# start rainbond
start_rainbond
