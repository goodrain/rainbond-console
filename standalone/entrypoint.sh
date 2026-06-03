#!/bin/sh

set -e

GPU_BOOTSTRAP_MANIFEST="/opt/rainbond/k3s/server/manifests/rainbond-gpu-bootstrap.yaml"

########################################
# Initialize configuration
########################################
init_configuration() {
  
  if ! mkdir -p /opt/rainbond/k3s/server/manifests /opt/rainbond/k3s/server/static /opt/rainbond/k3s/agent/images; then
    echo "ERROR: Failed to create directory"
    exit 1
  fi
  
  if ! cp /tmp/rainbond-cluster.tgz /opt/rainbond/k3s/server/static/rainbond-cluster.tgz; then
    echo "ERROR: Failed to copy rainbond-cluster.tgz"
    exit 1
  fi

  if [ ! -f "/opt/rainbond/k3s/agent/images/k3s-images.tar.zst" ]; then
    cp /tmp/k3s-images.tar.zst /opt/rainbond/k3s/agent/images/k3s-images.tar.zst
  fi

  rainbond_cluster_yaml
  rainbond_gpu_bootstrap_yaml
}

rainbond_cluster_yaml() {

  GET_EIP=$(hostname -i | awk '{for(i=1;i<=NF;i++) if($i ~ /^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$/) print $i}')

cat > /opt/rainbond/k3s/server/manifests/rainbond-cluster.yaml << EOF
apiVersion: v1
kind: Namespace
metadata:
  name: rbd-system
---
apiVersion: helm.cattle.io/v1
kind: HelmChart
metadata:
  name: rainbond-cluster
  namespace: rbd-system
spec:
  chart: https://%{KUBERNETES_API}%/static/rainbond-cluster.tgz
  targetNamespace: rbd-system
  valuesContent: |-
    Cluster:
      gatewayIngressIPs: ${EIP:-$GET_EIP}
      nodesForChaos:
      - name: node
      nodesForGateway:
      - name: node
        internalIP: $GET_EIP
        externalIP: $GET_EIP
      installVersion: ${VERSION:-v6.0.0-release}
      eid: ${UUID}
EOF
}

rainbond_gpu_bootstrap_yaml() {
  if [ "${ENABLE_GPU:-false}" = "true" ]; then
cat > "${GPU_BOOTSTRAP_MANIFEST}" << EOF
apiVersion: v1
kind: Namespace
metadata:
  name: rbd-system
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: rainbond-gpu-bootstrap
  namespace: rbd-system
data:
  enabled: "true"
  provider: "${GPU_PROVIDER:-nvidia}"
  runtimeClassName: "${GPU_RUNTIME_CLASS_NAME:-nvidia}"
EOF
  else
    rm -f "${GPU_BOOTSTRAP_MANIFEST}"
  fi
}

validate_gpu_runtime() {
  if [ "${ENABLE_GPU:-false}" != "true" ]; then
    return
  fi

  if [ ! -e "/dev/nvidia0" ] || [ ! -e "/dev/nvidiactl" ]; then
    echo "ERROR: GPU mode requested but NVIDIA devices are not available inside the container"
    exit 1
  fi

  if ! command -v nvidia-container-runtime >/dev/null 2>&1; then
    echo "ERROR: GPU mode requested but nvidia-container-runtime is not installed in the dind image"
    exit 1
  fi
}

if [ ! -f "/opt/rainbond/k3s/server/static/rainbond-cluster.tgz" ] || \
   [ ! -f "/opt/rainbond/k3s/server/manifests/rainbond-cluster.yaml" ] || \
   [ ! -f "/opt/rainbond/k3s/agent/images/k3s-images.tar.zst" ]; then
    init_configuration
else
  rainbond_cluster_yaml
  rainbond_gpu_bootstrap_yaml
fi

validate_gpu_runtime

if [ ! -f "/root/.bash_aliases" ]; then
  echo "alias kubectl='k3s kubectl'" >> /root/.bash_aliases
  echo "alias crictl='k3s crictl'" >> /root/.bash_aliases
fi

exec "$@"
