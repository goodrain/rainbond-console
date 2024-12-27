#!/bin/sh


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

  if ! cat > /opt/rainbond/k3s/server/manifests/rainbond-cluster.yaml << EOF ; then
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
      gatewayIngressIPs: ${EIP:-$(hostname -i)}
      nodesForChaos:
      - name: node
      nodesForGateway:
      - name: node
        internalIP: $(hostname -i)
        externalIP: $(hostname -i)
      installVersion: ${VERSION:-v6.0.0-release}
      eid: ${UUID}
EOF
    echo "ERROR: Failed to create rainbond-cluster.yaml"
    exit 1
  fi

  if [ ! -f "/opt/rainbond/k3s/agent/images/rbd-images.tar" ]; then
    cp /tmp/rbd-images.tar /opt/rainbond/k3s/agent/images/rbd-images.tar
  fi
}

if [ ! -f "/opt/rainbond/k3s/server/static/rainbond-cluster.tgz" ] || \
   [ ! -f "/opt/rainbond/k3s/server/manifests/rainbond-cluster.yaml" ]; \
   [ ! -f "/opt/rainbond/k3s/agent/images/rbd-images.tar" ]; then
    init_configuration
fi

if [ ! -f "/root/.bash_aliases" ]; then
  echo "alias kubectl='k3s kubectl'" >> /root/.bash_aliases
  echo "alias crictl='k3s crictl'" >> /root/.bash_aliases
fi

exec "$@"