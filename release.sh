#!/bin/bash
set -o errexit

FORCE=$1
RELEASE_TAG=$(git describe)

PROGRAM="console"

WORKDIR=$PWD

sed "$ a ENV RELEASE_TAG $RELEASE_TAG" Dockerfile_release > Dockerfile.release
docker build $FORCE -t hub.goodrain.com/goodrain/$PROGRAM:$RELEASE_TAG -f Dockerfile.release .
docker tag hub.goodrain.com/goodrain/$PROGRAM:$RELEASE_TAG hub.goodrain.com/goodrain/$PROGRAM
docker push hub.goodrain.com/goodrain/$PROGRAM

rm -fv Dockerfile.release