#!/bin/bash

set -xe

image_name="rbd-app-ui"

if [ -z "$TRAVIS_TAG" ]; then
	  VERSION=$TRAVIS_BRANCH-dev
else
	  VERSION=$TRAVIS_TAG
fi


buildTime=$(date +%F-%H)

function release(){
  sed -i "s/VERSION/${VERSION}/g" Dockerfile.release
  git_commit=$(git log -n 1 --pretty --format=%h)
  release_desc=${VERSION}-${git_commit}-${buildTime}
  sed "s/__RELEASE_DESC__/${release_desc}/" Dockerfile.release > Dockerfile.build

  docker build --network=host -t rainbond/${image_name}:${VERSION} -f Dockerfile.build .
  rm -r ./Dockerfile.build
  if [ "$TRAVIS_PULL_REQUEST" == "false" ]; then
     docker login -u $DOCKER_USERNAME -p $DOCKER_PASSWORD
     docker push rainbond/rbd-app-ui:${VERSION}
  fi
}

case $1 in
    *)
    release
    ;;
esac
