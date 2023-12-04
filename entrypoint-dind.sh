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

  FREE_TOTAL=$(awk '/MemTotal/ {print $2}' /proc/meminfo)
  FREE_TOTAL_MB=$((FREE_TOTAL / 1024))
  CPUS=$(grep -c "processor" </proc/cpuinfo)
  DISK=$(df -m / | sed -n '2p' | awk '{print $4}')

  if [ ! "$EIP" ]; then
    export EIP="127.0.0.1"
  fi

  if [ "$FREE_TOTAL_MB" -lt 2048 ]; then
    echo -e "${YELLOW}$(date "$TIME") WARN: Too little memory, recommended memory configuration is 2G ${NC}"
  fi
  if [ "$CPUS" -lt 2 ]; then
    echo -e "${YELLOW}$(date "$TIME") WARN: Too few CPUs, recommended CPU configuration is 2 cores ${NC}"
  fi
  if [ "$DISK" -lt 51200 ]; then
    echo -e "${YELLOW}$(date "$TIME") WARN: Too little free disk space, recommended disk space greater than 50G ${NC}"
  fi
  echo -e "${GREEN}$(date "$TIME") INFO: Memory: $FREE_TOTAL_MB MB, CPUs: $CPUS, Disk: $DISK MB ${NC}"
  ## Do domain name resolution
  echo "127.0.0.1  rbd-api-api" >>/etc/hosts

  echo "alias kubectl='k3s kubectl'" >> ~/.bashrc
  echo "alias crictl='k3s crictl'" >> ~/.bashrc
  source ~/.bashrc

  # explicitly remove Docker's default PID file to ensure that it can start properly if it was stopped uncleanly (and thus didn't clean up the PID file)
  # find /run /var/run -iname 'docker*.pid' -delete || :
}

########################################
# Configuration
########################################
function configuration {

  if [ ! -d "/opt/rainbond" ]; then
    mkdir -p /opt/rainbond;
  fi

  if [ ! -d "/app/logs" ]; then
    mkdir -p /app/logs;
  fi

  if [ ! -d "/var/log/supervisor" ]; then
    mkdir -p /var/log/supervisor;
  fi

  if [ ! -d "/app/data" ]; then
    mkdir -p /app/data;
  fi

  if [ ! -d "/root/.ssh" ]; then
    mkdir -p /root/.ssh;
  fi

  if [ ! -f "/usr/local/bin/nerdctl" ]; then
    cp /app/ui/nerdctl /usr/local/bin/nerdctl
  fi

  if [ ! -f "/usr/local/bin/helm" ]; then
    cp /app/ui/helm /usr/local/bin/helm
  fi

  if [ ! -f "/usr/local/bin/k3s" ]; then
    cp /app/ui/k3s /usr/local/bin/k3s
  fi

  if [ ! -f "/usr/bin/log" ]; then
    cp /app/ui/log /usr/bin/log
  fi

  # Create manifests path
  if [ ! -d "/app/data/k3s/server/manifests" ]; then
    mkdir -p /app/data/k3s/server/manifests;
  fi

  sed -i "s/v5.6.0-release/${VERSION}/g" /app/ui/01-rbd-operator.yml
  sed -i "s/v5.6.0-release/${VERSION}/g" /app/ui/02-rbd-region.yml
  cp /app/ui/01-rbd-operator.yml /app/data/k3s/server/manifests
  cp /app/ui/02-rbd-region.yml /app/data/k3s/server/manifests

  # Setting rainbondcluster
  NODE_INTERNAL_IP=$(hostname -i)
  EIP=${EIP:-$NODE_IP}

  sed -i "s/single_node_external_ip/$EIP/" /app/data/k3s/server/manifests/02-rbd-region.yml
  sed -i "s/single_node_internal_ip/$NODE_INTERNAL_IP/" /app/data/k3s/server/manifests/02-rbd-region.yml

  # Create images path
  if [ ! -d "/app/data/k3s/agent/images" ]; then
    mkdir -p /app/data/k3s/agent/images
  fi

  # Move rainbond.tar to k3s images path
  if [ ! -f "/app/data/k3s/agent/images/rainbond-${VERSION}.tar" ]; then
    cp /app/ui/rainbond-${VERSION}.tar /app/data/k3s/agent/images/rainbond-${VERSION}.tar
  fi

  # Create registries file path
  if [ ! -d "/etc/rancher/k3s" ]; then
    mkdir -p /etc/rancher/k3s
  fi

  # Create k3s registries file
  if [ ! -f "/etc/rancher/k3s/registries.yaml" ]; then
cat > /etc/rancher/k3s/registries.yaml << EOF
mirrors:
  "docker.io":
    endpoint:
      - "https://dockerhub.azk8s.cn"
      - "https://docker.mirrors.ustc.edu.cn"
      - "http://hub-mirror.c.163.com"
  "goodrain.me":
    endpoint:
      - "https://goodrain.me"
configs:
  "goodrain.me":
    auth:
      username: admin
      password: admin
    tls:
      insecure_skip_verify: true
EOF
  fi
}

########################################
# Start K3s
########################################
function start_k3s {
  # Fix the problem that cgroup version is too high to start
  if [ -f /sys/fs/cgroup/cgroup.controllers ]; then
    mkdir -p /sys/fs/cgroup/init
    xargs -rn1 </sys/fs/cgroup/cgroup.procs >/sys/fs/cgroup/init/cgroup.procs || :
    sed -e 's/ / +/g' -e 's/^/+/' <"/sys/fs/cgroup/cgroup.controllers" >"/sys/fs/cgroup/cgroup.subtree_control"
  fi
  supervisorctl start k3s >/dev/null 2>&1
  echo -e "${GREEN}$(date "$TIME") INFO: K3s is starting, please wait ············································${NC}"
  while_num=0
  while true; do
    K3S_STATUS=$(netstat -nltp | grep k3s | grep -c -E "6443|6444|10248|10249|10250|10256|10257|10258|10259")
    if [[ "${K3S_STATUS}" == "9" ]]; then
      if k3s kubectl get node | grep Ready >/dev/null 2>&1; then
        echo -e "${GREEN}$(date "$TIME") INFO: K3s Started successfully ${NC}"
        break
      fi
    fi
    sleep 20
    ((while_num++)) || true
    if [ $((while_num)) -gt 12 ]; then
      echo -e "${RED}$(date "$TIME") ERROR: K3s failed to start. Please use the command to view the k3s log 'docker exec rainbond-allinone /bin/cat /app/logs/k3s.log' ${NC}"
      exit 1
    fi
  done
}

########################################
# Start Rainbond
########################################
function start_rainbond {

  # Check whether the k3s starts successfully
  echo -e "${GREEN}$(date "$TIME") INFO: Rainbond Region is starting, please wait ············································${NC}"
  supervisorctl start console >/dev/null 2>&1
  echo -e "${GREEN}$(date "$TIME") INFO: Rainbond console is starting, please wait ············································${NC}"

  while true; do
    if netstat -nltp | grep 8443 >/dev/null 2>&1; then
      if curl http://"$(k3s kubectl get svc -n rbd-system | grep rbd-api-api-inner | awk '{print $3}')":8888/v2/health 2>&1 | grep health >/dev/null 2>&1; then
        echo -e "${GREEN}$(date "$TIME") INFO: Rainbond Region started successfully ${NC}"
        break
      fi
    fi
    sleep 5
  done

  # Check whether the Rainbond region starts successfully
  while true; do
    if curl http://127.0.0.1:7070 >/dev/null 2>&1; then
      echo -e "${GREEN}$(date "$TIME") INFO: Rainbond started successfully, Please pass http://$EIP:7070 Access Rainbond ${NC}"
      break
    fi
    sleep 5
  done
}

function stop_container {
  echo -e "${GREEN}$(date "$TIME") INFO: Stopping K3s ${NC}"
  supervisorctl stop k3s
  exit 1
}

trap stop_container SIGTERM

# basic environment check
basic_check

# Configuration
configuration

# start k3s
start_k3s

# start rainbond
start_rainbond
