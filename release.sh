#!/bin/bash
set -o errexit

FORCE=$1
RELEASE_TAG=$(git describe)

PROGRAM="console"

WORKDIR=$PWD

sed "$ a ENV RELEASE_TAG $RELEASE_TAG" Dockerfile_release > Dockerfile.release
docker build $FORCE -t hub.goodrain.com/dc-deploy/$PROGRAM:$RELEASE_TAG -f Dockerfile.release .
docker tag hub.goodrain.com/dc-deploy/$PROGRAM:$RELEASE_TAG hub.goodrain.com/dc-deploy/$PROGRAM
docker push hub.goodrain.com/dc-deploy/$PROGRAM

# rename tag
#docker tag `docker images  | grep console | grep latest | awk '{print $3}'` hub.goodrain.com/dc-deploy/console:community
docker tag `docker images  | grep console | grep latest | awk '{print $3}'` hub.goodrain.com/dc-deploy/console:pre-release
docker images | grep console | grep community

# remove old images
#docker images  | grep console | grep -v `docker images| grep console|grep community |awk '{print $3}'` | awk '{print $3}' | xargs docker rmi

# push community
docker push hub.goodrain.com/dc-deploy/console:pre-release

rm -fv Dockerfile.release