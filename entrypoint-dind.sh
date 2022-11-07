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

  FREE=$(free -m | awk '/Mem/{print $2}')
  CPUS=$(grep -c "processor" </proc/cpuinfo)
  DISK=$(df -m / | sed -n '2p' | awk '{print $4}')

  if [ ! "$EIP" ]; then
    export EIP="127.0.0.1"
  fi

  if [ "$FREE" -lt 2048 ]; then
    echo -e "${YELLOW}$(date "$TIME") WARN: Too little memory, recommended memory configuration is 2G ${NC}"
  fi
  if [ "$CPUS" -lt 2 ]; then
    echo -e "${YELLOW}$(date "$TIME") WARN: Too few CPUs, recommended CPU configuration is 2 cores ${NC}"
  fi
  if [ "$DISK" -lt 51200 ]; then
    echo -e "${YELLOW}$(date "$TIME") WARN: Too little free disk space, recommended disk space greater than 50G ${NC}"
  fi
  echo -e "${GREEN}$(date "$TIME") INFO: Memory: $FREE MB, CPUs: $CPUS, Disk: $DISK MB ${NC}"
  ## Do domain name resolution
  echo "127.0.0.1  rbd-api-api" >>/etc/hosts

  echo "alias kubectl='k3s kubectl'" >> ~/.bashrc
  source ~/.bashrc

  # explicitly remove Docker's default PID file to ensure that it can start properly if it was stopped uncleanly (and thus didn't clean up the PID file)
  # find /run /var/run -iname 'docker*.pid' -delete || :
}

########################################
# Configuration Containerd and CNI plugin
########################################
function configuration {
  if [ -f /etc/cni/net.d/10-containerd-net.conflist ]; then
    echo -e "${GREEN}$(date "$TIME") INFO: 10-containerd-net.conflist file already exists ${NC}"
  fi
  if [ -f /etc/containerd/config.toml ]; then
    echo -e "${GREEN}$(date "$TIME") INFO: config.toml file already exists ${NC}"
  fi
  if [ -f /etc/containerd/certs.d/goodrain.me/hosts.toml ]; then
    echo -e "${GREEN}$(date "$TIME") INFO: hosts.toml file already exists ${NC}"
    return
  fi
  mkdir -p /etc/cni/net.d /etc/containerd /etc/containerd/certs.d/goodrain.me

cat > /etc/cni/net.d/10-containerd-net.conflist << EOF
{
  "cniVersion": "1.0.0",
  "name": "containerd-net",
  "plugins": [
    {
      "type": "bridge",
      "bridge": "cni0",
      "isGateway": true,
      "ipMasq": true,
      "promiscMode": true,
      "ipam": {
        "type": "host-local",
        "ranges": [
          [{
            "subnet": "10.88.0.0/24"
          }]
        ],
        "routes": [
          { "dst": "0.0.0.0/0" }
        ]
      }
    },
    {
      "type": "portmap",
      "capabilities": {"portMappings": true}
    }
  ]
}
EOF

cat > /etc/containerd/config.toml << EOF
disabled_plugins = []
imports = []
oom_score = 0
plugin_dir = ""
required_plugins = []
root = "/app/data/containerd"
state = "/run/containerd"
temp = ""
version = 2

[cgroup]
  path = ""

[debug]
  address = ""
  format = ""
  gid = 0
  level = ""
  uid = 0

[grpc]
  address = "/run/containerd/containerd.sock"
  gid = 0
  max_recv_message_size = 16777216
  max_send_message_size = 16777216
  tcp_address = ""
  tcp_tls_ca = ""
  tcp_tls_cert = ""
  tcp_tls_key = ""
  uid = 0

[metrics]
  address = ""
  grpc_histogram = false

[plugins]

  [plugins."io.containerd.gc.v1.scheduler"]
    deletion_threshold = 0
    mutation_threshold = 100
    pause_threshold = 0.02
    schedule_delay = "0s"
    startup_delay = "100ms"

  [plugins."io.containerd.grpc.v1.cri"]
    device_ownership_from_security_context = false
    disable_apparmor = false
    disable_cgroup = false
    disable_hugetlb_controller = true
    disable_proc_mount = false
    disable_tcp_service = true
    enable_selinux = false
    enable_tls_streaming = false
    enable_unprivileged_icmp = false
    enable_unprivileged_ports = false
    ignore_image_defined_volumes = false
    max_concurrent_downloads = 3
    max_container_log_line_size = 16384
    netns_mounts_under_state_dir = false
    restrict_oom_score_adj = false
    sandbox_image = "docker.io/rainbond/mirrored-pause:3.1"
    selinux_category_range = 1024
    stats_collect_period = 10
    stream_idle_timeout = "4h0m0s"
    stream_server_address = "127.0.0.1"
    stream_server_port = "0"
    systemd_cgroup = false
    tolerate_missing_hugetlb_controller = true
    unset_seccomp_profile = ""

    [plugins."io.containerd.grpc.v1.cri".cni]
      bin_dir = "/opt/cni/bin"
      conf_dir = "/etc/cni/net.d"
      conf_template = ""
      ip_pref = ""
      max_conf_num = 1

    [plugins."io.containerd.grpc.v1.cri".containerd]
      default_runtime_name = "runc"
      disable_snapshot_annotations = true
      discard_unpacked_layers = false
      ignore_rdt_not_enabled_errors = false
      no_pivot = false
      snapshotter = "overlayfs"

      [plugins."io.containerd.grpc.v1.cri".containerd.default_runtime]
        base_runtime_spec = ""
        cni_conf_dir = ""
        cni_max_conf_num = 0
        container_annotations = []
        pod_annotations = []
        privileged_without_host_devices = false
        runtime_engine = ""
        runtime_path = ""
        runtime_root = ""
        runtime_type = ""

        [plugins."io.containerd.grpc.v1.cri".containerd.default_runtime.options]

      [plugins."io.containerd.grpc.v1.cri".containerd.runtimes]

        [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc]
          base_runtime_spec = ""
          cni_conf_dir = ""
          cni_max_conf_num = 0
          container_annotations = []
          pod_annotations = []
          privileged_without_host_devices = false
          runtime_engine = ""
          runtime_path = ""
          runtime_root = ""
          runtime_type = "io.containerd.runc.v2"

          [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc.options]
            BinaryName = ""
            CriuImagePath = ""
            CriuPath = ""
            CriuWorkPath = ""
            IoGid = 0
            IoUid = 0
            NoNewKeyring = false
            NoPivotRoot = false
            Root = ""
            ShimCgroup = ""
            SystemdCgroup = false

      [plugins."io.containerd.grpc.v1.cri".containerd.untrusted_workload_runtime]
        base_runtime_spec = ""
        cni_conf_dir = ""
        cni_max_conf_num = 0
        container_annotations = []
        pod_annotations = []
        privileged_without_host_devices = false
        runtime_engine = ""
        runtime_path = ""
        runtime_root = ""
        runtime_type = ""

        [plugins."io.containerd.grpc.v1.cri".containerd.untrusted_workload_runtime.options]

    [plugins."io.containerd.grpc.v1.cri".image_decryption]
      key_model = "node"

    [plugins."io.containerd.grpc.v1.cri".registry]
      config_path = ""

      [plugins."io.containerd.grpc.v1.cri".registry.auths]

      [plugins."io.containerd.grpc.v1.cri".registry.configs]
        [plugins."io.containerd.grpc.v1.cri".registry.configs."goodrain.me"]
          [plugins."io.containerd.grpc.v1.cri".registry.configs."goodrain.me".tls]
            insecure_skip_verify = true

      [plugins."io.containerd.grpc.v1.cri".registry.mirrors]
        [plugins."io.containerd.grpc.v1.cri".registry.mirrors."docker.io"]
          endpoint = ["https://dockerhub.azk8s.cn","https://docker.mirrors.ustc.edu.cn", "http://hub-mirror.c.163.com"]

    [plugins."io.containerd.grpc.v1.cri".x509_key_pair_streaming]
      tls_cert_file = ""
      tls_key_file = ""

  [plugins."io.containerd.internal.v1.opt"]
    path = "/opt/containerd"

  [plugins."io.containerd.internal.v1.restart"]
    interval = "10s"

  [plugins."io.containerd.internal.v1.tracing"]
    sampling_ratio = 1.0
    service_name = "containerd"

  [plugins."io.containerd.metadata.v1.bolt"]
    content_sharing_policy = "shared"

  [plugins."io.containerd.monitor.v1.cgroups"]
    no_prometheus = false

  [plugins."io.containerd.runtime.v1.linux"]
    no_shim = false
    runtime = "runc"
    runtime_root = ""
    shim = "containerd-shim"
    shim_debug = false

  [plugins."io.containerd.service.v1.diff-service"]
    default = ["walking"]

  [plugins."io.containerd.service.v1.tasks-service"]
    rdt_config_file = ""

  [plugins."io.containerd.snapshotter.v1.aufs"]
    root_path = ""

  [plugins."io.containerd.snapshotter.v1.btrfs"]
    root_path = ""

  [plugins."io.containerd.snapshotter.v1.devmapper"]
    async_remove = false
    base_image_size = ""
    discard_blocks = false
    fs_options = ""
    fs_type = ""
    pool_name = ""
    root_path = ""

  [plugins."io.containerd.snapshotter.v1.native"]
    root_path = ""

  [plugins."io.containerd.snapshotter.v1.overlayfs"]
    root_path = ""
    upperdir_label = false

  [plugins."io.containerd.snapshotter.v1.zfs"]
    root_path = ""

  [plugins."io.containerd.tracing.processor.v1.otlp"]
    endpoint = ""
    insecure = false
    protocol = ""

[proxy_plugins]

[stream_processors]

  [stream_processors."io.containerd.ocicrypt.decoder.v1.tar"]
    accepts = ["application/vnd.oci.image.layer.v1.tar+encrypted"]
    args = ["--decryption-keys-path", "/etc/containerd/ocicrypt/keys"]
    env = ["OCICRYPT_KEYPROVIDER_CONFIG=/etc/containerd/ocicrypt/ocicrypt_keyprovider.conf"]
    path = "ctd-decoder"
    returns = "application/vnd.oci.image.layer.v1.tar"

  [stream_processors."io.containerd.ocicrypt.decoder.v1.tar.gzip"]
    accepts = ["application/vnd.oci.image.layer.v1.tar+gzip+encrypted"]
    args = ["--decryption-keys-path", "/etc/containerd/ocicrypt/keys"]
    env = ["OCICRYPT_KEYPROVIDER_CONFIG=/etc/containerd/ocicrypt/ocicrypt_keyprovider.conf"]
    path = "ctd-decoder"
    returns = "application/vnd.oci.image.layer.v1.tar+gzip"

[timeouts]
  "io.containerd.timeout.bolt.open" = "0s"
  "io.containerd.timeout.shim.cleanup" = "5s"
  "io.containerd.timeout.shim.load" = "5s"
  "io.containerd.timeout.shim.shutdown" = "3s"
  "io.containerd.timeout.task.state" = "2s"

[ttrpc]
  address = ""
  gid = 0
  uid = 0
EOF

cat > /etc/containerd/certs.d/goodrain.me/hosts.toml << EOF
[host."https://goodrain.me"]
  capabilities = ["pull", "resolve","push"]
  skip_verify = true
EOF
}

########################################
# Start Containerd
########################################
function start_containerd {
  while_num=0
  supervisorctl start containerd >/dev/null 2>&1
  echo -e "${GREEN}$(date "$TIME") INFO: Containerd is starting, please wait ············································${NC}"
  while true; do
    if nerdctl ps >/dev/null 2>&1; then
      echo -e "${GREEN}$(date "$TIME") INFO: Containerd started successfully ${NC}"
      break
    fi
    sleep 5
    ((while_num++)) || true
    if [ $((while_num)) -gt 12 ]; then
      echo -e "${RED}$(date "$TIME") ERROR: Containerd failed to start. Please use the command to view the containerd log 'docker exec rainbond-allinone /bin/cat /app/logs/containerd.log'${NC}"
      exit 1
    fi
  done
}

########################################
# Load Images
########################################
function load_images {
  
  if nerdctl -n k8s.io images | grep rbd-api >/dev/null 2>&1; then
    echo -e "${GREEN}$(date "$TIME") INFO: Container images loaded ${NC}"
    return
  fi

  echo -e "${GREEN}$(date "$TIME") INFO: Start loaded images ···························${NC}"
  while true; do
    if nerdctl -n k8s.io load -i /app/ui/rainbond-"${VERSION}".tar; then
      echo -e "${GREEN}$(date "$TIME") INFO: Load container images successfully ${NC}"
      break
    fi
  done
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
    K3S_STATUS=$(netstat -nltp | grep k3s | grep -c -E "6443|6444|10248|10249|10250|10251|10256|10257|10258|10259")
    if [[ "${K3S_STATUS}" == "10" ]]; then
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
IMAGE_DOMAIN=${IMAGE_DOMAIN:-docker.io}
IMAGE_NAMESPACE=${IMAGE_NAMESPACE:-rainbond}

function start_rainbond {
  # create namespace
  if k3s kubectl get ns | grep rbd-system >/dev/null 2>&1; then
    echo -e "${GREEN}$(date "$TIME") INFO: Namespace rbd-system already exists ${NC}"
  else
    k3s kubectl create ns rbd-system
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
    
    helm install rainbond-operator /app/chart -n rbd-system --kubeconfig /root/.kube/config \
      --set operator.image.name="${IMAGE_DOMAIN}"/"${IMAGE_NAMESPACE}"/rainbond-operator \
      --set operator.image.tag="${VERSION}" \
      --set operator.image.env[0].name=IS_SQLLITE \
      --set operator.image.env[0].value=TRUE
    echo -e "${GREEN}$(date "$TIME") INFO: Helm rainbond-operator installed ${NC}"

    # setting rainbondcluster
    NODE_NAME=$(k3s kubectl get node | sed -n '2p' | awk '{print $1}')
    NODE_IP=$(k3s kubectl get node -owide | sed -n '2p' | awk '{print $6}')
    EIP=${EIP:-$NODE_IP}
    IIP=${IIP:-$NODE_IP}
    sed -i "s/single_node_name/$NODE_NAME/" /app/ui/rainbond-operator/config/single_node_cr/rbdcluster.yml
    sed -i "s/single_node_external_ip/$EIP/" /app/ui/rainbond-operator/config/single_node_cr/rbdcluster.yml
    sed -i "s/single_node_internal_ip/$IIP/" /app/ui/rainbond-operator/config/single_node_cr/rbdcluster.yml

    if k3s kubectl apply -f /app/ui/rainbond-operator/config/single_node_cr/ -n rbd-system >/dev/null 2>&1; then
      echo -e "${GREEN}$(date "$TIME") INFO: Rainbond Region installed ${NC}"
    else
      echo -e "${RED}$(date "$TIME") ERROR: Rainbond Region failed to install ${NC}"
      exit 1
    fi
  fi

  echo -e "${GREEN}$(date "$TIME") INFO: Rainbond Region is starting, please wait ············································${NC}"
  while true; do
    if netstat -nltp | grep 8443 >/dev/null 2>&1; then
      if curl http://"$(k3s kubectl get svc -n rbd-system | grep rbd-api-api-inner | awk '{print $3}')":8888/v2/health 2>&1 | grep health >/dev/null 2>&1; then
        echo -e "${GREEN}$(date "$TIME") INFO: Rainbond Region started successfully ${NC}"
        break
      fi
    fi
    sleep 5
  done

  supervisorctl start console >/dev/null 2>&1
  echo -e "${GREEN}$(date "$TIME") INFO: Rainbond console is starting, please wait ············································${NC}"
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

# configuration containerd and cni plugin
configuration

# start containerd
start_containerd

# load containerd images
load_images

# start k3s
start_k3s

# start rainbond
start_rainbond
