#!/bin/sh

image_list="rancher/klipper-helm:v0.8.4-build20240523
rancher/mirrored-coredns-coredns:1.10.1
rancher/mirrored-metrics-server:v0.7.0
rancher/mirrored-pause:3.6
busybox:latest"


for image in ${image_list}; do
    docker pull --platform="${ARCH}" "${image}"
done

sudo apt-get update && sudo apt-get -y install zstd

docker save ${image_list} | zstd -T0 -19 -o k3s-images-"${ARCH}".tar.zst