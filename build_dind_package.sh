#!/bin/bash

export NFSCLI_URL="https://rainbond-pkg.oss-cn-shanghai.aliyuncs.com/offline/nfs-client/nfs_all.tar.gz"
export DOCKER_VER=19.03.5
RBD_VER=${RBD_VER:-'v5.6.0-release'}
DOMESTIC_NAMESPACE=${DOMESTIC_NAMESPACE:-'goodrain'}

echo "registry.cn-hangzhou.aliyuncs.com/${DOMESTIC_NAMESPACE}/metrics-server:v0.3.6
registry.cn-hangzhou.aliyuncs.com/${DOMESTIC_NAMESPACE}/rbd-mesh-data-panel:${RBD_VER}
registry.cn-hangzhou.aliyuncs.com/${DOMESTIC_NAMESPACE}/rbd-webcli:${RBD_VER}
registry.cn-hangzhou.aliyuncs.com/${DOMESTIC_NAMESPACE}/etcd:v3.3.18
registry.cn-hangzhou.aliyuncs.com/${DOMESTIC_NAMESPACE}/rbd-eventlog:${RBD_VER}
registry.cn-hangzhou.aliyuncs.com/${DOMESTIC_NAMESPACE}/rbd-init-probe:${RBD_VER}
registry.cn-hangzhou.aliyuncs.com/${DOMESTIC_NAMESPACE}/metrics-scraper:v1.0.4
registry.cn-hangzhou.aliyuncs.com/${DOMESTIC_NAMESPACE}/rbd-chaos:${RBD_VER}
registry.cn-hangzhou.aliyuncs.com/${DOMESTIC_NAMESPACE}/rbd-mq:${RBD_VER}
registry.cn-hangzhou.aliyuncs.com/${DOMESTIC_NAMESPACE}/mysqld-exporter:latest
registry.cn-hangzhou.aliyuncs.com/${DOMESTIC_NAMESPACE}/rbd-resource-proxy:${RBD_VER}
registry.cn-hangzhou.aliyuncs.com/${DOMESTIC_NAMESPACE}/rainbond-operator:${RBD_VER}
registry.cn-hangzhou.aliyuncs.com/${DOMESTIC_NAMESPACE}/rbd-worker:${RBD_VER}
registry.cn-hangzhou.aliyuncs.com/${DOMESTIC_NAMESPACE}/rbd-db:8.0.19
registry.cn-hangzhou.aliyuncs.com/${DOMESTIC_NAMESPACE}/rbd-node:${RBD_VER}
registry.cn-hangzhou.aliyuncs.com/${DOMESTIC_NAMESPACE}/rbd-monitor:${RBD_VER}
registry.cn-hangzhou.aliyuncs.com/${DOMESTIC_NAMESPACE}/kubernetes-dashboard:v2.0.1-3
registry.cn-hangzhou.aliyuncs.com/${DOMESTIC_NAMESPACE}/rbd-gateway:${RBD_VER}
registry.cn-hangzhou.aliyuncs.com/${DOMESTIC_NAMESPACE}/registry:2.6.2
registry.cn-hangzhou.aliyuncs.com/${DOMESTIC_NAMESPACE}/rbd-api:${RBD_VER}
registry.cn-hangzhou.aliyuncs.com/${DOMESTIC_NAMESPACE}/smallimage:latest">./build_image.txt

while read rbd_image_name; do
  rbd_image_tar=$(echo ${rbd_image_name} | awk -F"/" '{print $NF}' | tr : -)
  rbd_offline_image=$(echo ${rbd_image_name} | awk -F"/" '{print $NF}')
  if [[ -f "./offline/rbd_image/${rbd_image_tar}.tgz" ]]; then
    echo "[INFO] ${rbd_image_tar} image already existed"
  else
    
    docker pull ${rbd_image_name} || exit 1
  fi
done <./build_image.txt
docker save -o rainbond-${RBD_VER}.tar `cat ./build_image.txt|xargs`
