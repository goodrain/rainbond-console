#!/bin/sh

VERSION=${VERSION:-'v6.0.0-release'}

image_list="rainbond/registry:2.6.2
rainbond/rbd-init-probe:${VERSION}
rainbond/rbd-chaos:${VERSION}
rainbond/rbd-mq:${VERSION}
rainbond/rainbond-operator:${VERSION}
rainbond/rbd-worker:${VERSION}
rainbond/rbd-api:${VERSION}
rainbond/rainbond:${VERSION}
rainbond/alpine:latest
rainbond/apisix-ingress-controller:v1.8.3
rainbond/apisix:3.9.1-debian
rainbond/minio:RELEASE.2023-10-24T04-42-36Z
rainbond/rbd-monitor:v2.20.0
rainbond/local-path-provisioner:v0.0.30
rancher/klipper-helm:v0.8.4-build20240523
rancher/mirrored-coredns-coredns:1.10.1
rancher/mirrored-metrics-server:v0.7.0
rancher/mirrored-pause:3.6
busybox:latest"


for image in ${image_list}; do
    docker pull --platform="${ARCH}" "${image}"
done


docker save -o rbd-images-${ARCH}.tar ${image_list}

for image in ${image_list}; do
  docker rmi -f "${image}"
done