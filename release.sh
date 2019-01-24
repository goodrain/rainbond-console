#!/bin/bash

set -xe

image_name="rbd-app-ui"

VERSION=5.0
buildTime=$(date +%F-%H)

function release(){

  git_commit=$(git log -n 1 --pretty --format=%h)

  release_desc=${VERSION}-${git_commit}-${buildTime}

  sed "s/__RELEASE_DESC__/${release_desc}/" Dockerfile.release > Dockerfile.build
  docker build -t 27-1/${image_name}:${VERSION} -f Dockerfile.build .
  rm -r ./Dockerfile.build
}

case $1 in
    *)
    release
    ;;
esac
