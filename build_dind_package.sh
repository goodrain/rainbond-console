#!/bin/bash

IMAGE_DOMAIN=${IMAGE_DOMAIN:-docker.io}
IMAGE_NAMESPACE=${IMAGE_NAMESPACE:-rainbond}
VERSION=${VERSION:-'v5.6.0-release'}

image_list="rainbond/registry:2.6.2
rainbond/etcd:v3.3.18
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
rainbond/mirrored-pause:3.1
rancher/local-path-provisioner:v0.0.20
rancher/mirrored-library-busybox:1.32.1"

docker pull rainbond/mirrored-metrics-server:v0.5.0
docker pull rainbond/mirrored-coredns-coredns:1.8.4
docker tag rainbond/mirrored-metrics-server:v0.5.0 rancher/mirrored-metrics-server:v0.5.0
docker tag rainbond/mirrored-coredns-coredns:1.8.4 rancher/mirrored-coredns-coredns:1.8.4

for image in ${image_list}; do
    docker pull "${image}"
done


docker save -o rainbond-"${VERSION}".tar ${image_list} rancher/mirrored-metrics-server:v0.5.0 rancher/mirrored-coredns-coredns:1.8.4
