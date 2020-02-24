#!/bin/bash

set -xe

image_name="rbd-app-ui"

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
  git_commit=$(git log -n 1 --pretty --format=%h)
  release_desc=${VERSION}-${git_commit}-${buildTime}
  sed "s/__RELEASE_DESC__/${release_desc}/" Dockerfile.release > Dockerfile.build

  docker build --network=host -t rainbond/${image_name}:${VERSION} -f Dockerfile.build .
  rm -r ./Dockerfile.build
  if [ "$TRAVIS_PULL_REQUEST" == "false" ]; then
     docker login -u $DOCKER_USERNAME -p $DOCKER_PASSWORD
     docker push rainbond/rbd-app-ui:${VERSION}
     if [ ${DOMESTIC_BASE_NAME} ];
			then
				docker tag "rainbond/rbd-app-ui:${VERSION}" "${DOMESTIC_BASE_NAME}/${DOMESTIC_NAMESPACE}/rbd-app-ui:${VERSION}"
				docker login -u "$DOMESTIC_DOCKER_USERNAME" -p "$DOMESTIC_DOCKER_PASSWORD" ${DOMESTIC_BASE_NAME}
				docker push "${DOMESTIC_BASE_NAME}/${DOMESTIC_NAMESPACE}/rbd-app-ui:${VERSION}"
			fi
  fi
}

case $1 in
    *)
    release
    ;;
esac
