#!/bin/bash

set -xe

VERSION=5.1.0
buildTime=$(date +%F-%H)

function release(){

  sed -i "s/VERSION/${VERSION}/g" Dockerfile.release
  git_commit=$(git log -n 1 --pretty --format=%h)
  release_desc=${VERSION}-${git_commit}-${buildTime}
  sed "s/__RELEASE_DESC__/${release_desc}/" Dockerfile.release > Dockerfile.build
  docker build -t rainbond/rbd-app-ui:${VERSION} -f Dockerfile.build .
  rm -r ./Dockerfile.build
}

case $1 in
    *)
    release
    ;;
esac
