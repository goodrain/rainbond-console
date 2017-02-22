#!/bin/bash
set -o errexit

FORCE=$1
RELEASE_TAG=$(git describe)
RELEASE_VERSION=${RELEASE_TAG%%-*}

PROGRAM="console"

WORKDIR=$PWD
RELEASE_IMAGE="hub.goodrain.com/dc-deploy/$PROGRAM:$RELEASE_VERSION"

sed "$ a ENV RELEASE_TAG $RELEASE_TAG" Dockerfile_release > Dockerfile.release
docker build $FORCE -t $RELEASE_IMAGE -f Dockerfile.release .
docker push $RELEASE_IMAGE

rm -fv Dockerfile.release