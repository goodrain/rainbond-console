#!/bin/bash

IMAGE_DOMAIN=${IMAGE_DOMAIN:-docker.io}
IMAGE_NAMESPACE=${IMAGE_NAMESPACE:-rainbond}
VERSION=${VERSION:-'v5.6.0-release'}
OFFLINE=${OFFLINE:-"false"}
BUILDER=${BUILDER:-"v5.8.1-release"}
RUNNER=${RUNNER:-"v5.8.1-release"}
ARCH=$(uname -m)

image_list="rainbond/kubernetes-dashboard:v2.6.1
rainbond/registry:2.6.2
rainbond/metrics-server:v0.4.1
rainbond/etcd:v3.3.18
rainbond/metrics-scraper:v1.0.4
${IMAGE_DOMAIN}/${IMAGE_NAMESPACE}/rbd-mesh-data-panel:${VERSION}
${IMAGE_DOMAIN}/${IMAGE_NAMESPACE}/rbd-webcli:${VERSION}
${IMAGE_DOMAIN}/${IMAGE_NAMESPACE}/rbd-eventlog:${VERSION}
${IMAGE_DOMAIN}/${IMAGE_NAMESPACE}/rbd-init-probe:${VERSION}
${IMAGE_DOMAIN}/${IMAGE_NAMESPACE}/rbd-chaos:${VERSION}
${IMAGE_DOMAIN}/${IMAGE_NAMESPACE}/rbd-mq:${VERSION}
${IMAGE_DOMAIN}/${IMAGE_NAMESPACE}/rbd-resource-proxy:${VERSION}
${IMAGE_DOMAIN}/${IMAGE_NAMESPACE}/rainbond-operator:${VERSION}
${IMAGE_DOMAIN}/${IMAGE_NAMESPACE}/rbd-worker:${VERSION}
${IMAGE_DOMAIN}/${IMAGE_NAMESPACE}/rbd-node:${VERSION}
${IMAGE_DOMAIN}/${IMAGE_NAMESPACE}/rbd-monitor:${VERSION}
${IMAGE_DOMAIN}/${IMAGE_NAMESPACE}/rbd-gateway:${VERSION}
${IMAGE_DOMAIN}/${IMAGE_NAMESPACE}/rbd-api:${VERSION}
registry.cn-hangzhou.aliyuncs.com/goodrain/smallimage:latest
rancher/local-path-provisioner:v0.0.20
rancher/mirrored-coredns-coredns:1.8.4
rancher/mirrored-metrics-server:v0.5.0
rancher/mirrored-library-busybox:1.32.1"


for image in ${image_list}; do
    docker pull "${image}"
done

# mirrored-pause 3.1 not arm64 image
if [[ "${ARCH}" == "x86_64" ]]; then
  docker pull rancher/mirrored-pause:3.1
else
  docker pull rancher/mirrored-pause:3.2
  docker tag rancher/mirrored-pause:3.2 rancher/mirrored-pause:3.1
fi

docker save -o rainbond-"${VERSION}".tar ${image_list} rancher/mirrored-pause:3.1
