#!/bin/sh


########################################
# Initialize configuration
########################################
init_configuration() {
  
  if ! mkdir -p /var/lib/rancher/k3s/server/manifests /var/lib/rancher/k3s/server/static /var/lib/rancher/k3s/agent/images; then
    echo "ERROR: Failed to create directory"
    exit 1
  fi
  
  if ! cp /tmp/rainbond-cluster.tgz /var/lib/rancher/k3s/server/static/rainbond-cluster.tgz; then
    echo "ERROR: Failed to copy rainbond-cluster.tgz"
    exit 1
  fi

  if ! cat > /var/lib/rancher/k3s/server/manifests/rainbond-cluster.yaml << EOF ; then
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
    useK3sContainerd: true
    Cluster:
      gatewayIngressIPs: ${EIP:-$(hostname -i)}
      nodesForChaos:
      - name: node
      nodesForGateway:
      - name: node
        internalIP: $(hostname -i)
        externalIP: $(hostname -i)
      rainbondImageRepository: rainbond
    Component:
      sqlite_mode:
        enabled: true
      rbd_db:
        enabled: false
EOF
    echo "ERROR: Failed to create rainbond-cluster.yaml"
    exit 1
  fi

  if [ ! -f "/var/lib/rancher/k3s/agent/images/rbd-images.tar" ]; then
    cp /tmp/rbd-images.tar /var/lib/rancher/k3s/agent/images/rbd-images.tar
  fi
}

if [ ! -f "/var/lib/rancher/k3s/server/static/rainbond-cluster.tgz" ] || \
   [ ! -f "/var/lib/rancher/k3s/server/manifests/rainbond-cluster.yaml" ]; \
   [ ! -f "/var/lib/rancher/k3s/agent/images/rbd-images.tar" ]; then
    init_configuration
fi

exec "$@"