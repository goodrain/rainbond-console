#!/bin/bash

set -xe

image_name="rbd-app-ui"

IMAGE_DOMAIN="image.goodrain.com"

if [ "$BUILD_IMAGE_DOMAIN" ]; 
then 
IMAGE_DOMAIN=${BUILD_IMAGE_DOMAIN}
fi


if [ -z "$VERSION" ];then
  if [ -z "$TRAVIS_TAG" ]; then
	  VERSION=$TRAVIS_BRANCH-dev
  else
	  VERSION=$TRAVIS_TAG
  fi
fi
buildTime=$(date +%F-%H)

function release(){
  sed -i "s/VERSION/${VERSION}/g" Dockerfile.release
  sed -i "s/IMAGE_DOMAIN/${IMAGE_DOMAIN}/g" Dockerfile.release
  git_commit=$(git log -n 1 --pretty --format=%h)
  release_desc=${VERSION}-${git_commit}-${buildTime}
  sed "s/__RELEASE_DESC__/${release_desc}/" Dockerfile.release > Dockerfile.build

  docker build --network=host -t "${IMAGE_DOMAIN}/${image_name}:${VERSION}" -f Dockerfile.build .
  rm -r ./Dockerfile.build
  if [ "$TRAVIS_PULL_REQUEST" == "false" ]; then
     docker login "${IMAGE_DOMAIN}" -u "$DOCKER_USERNAME" -p "$DOCKER_PASSWORD" "$IMAGE_DOMAIN"
     docker push  "${IMAGE_DOMAIN}/rbd-app-ui:${VERSION}"
  fi
}

case $1 in
    *)
    release
    ;;
esac
