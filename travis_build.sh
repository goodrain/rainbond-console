#!/bin/bash

set -xe

image_name="rbd-app-ui"

IMAGE_DOMAIN=${BUILD_IMAGE_DOMAIN:-docker.io}
IMAGE_NAMESPACE=${BUILD_IMAGE_NAMESPACE:-rainbond}

PROMQL_PARSER_URL=${PROMQL_PARSER_URL:-https://github.com/GLYASAI/promql-parser/releases/download/v0.1-alpha/promql-parser}

if [ -z "$VERSION" ];then
  if [ -z "$TRAVIS_TAG" ]; then
	  VERSION=$TRAVIS_BRANCH-dev
  else
	  VERSION=$TRAVIS_TAG
  fi
fi

function release(){
  sed -i "s/VERSION/${VERSION}/g" Dockerfile.release
  git_commit=$(git log -n 1 --pretty --format=%h)
  buildTime=$(date +%F-%H)
  release_desc=${VERSION}-${git_commit}-${buildTime}
  sed "s/__RELEASE_DESC__/${release_desc}/" Dockerfile.release > Dockerfile.build

  if [[ ! -f promql-parser ]] ; then
    echo "Downloading ${PROMQL_PARSER_URL} to bin/linux/promql-parser"
    time wget ${PROMQL_PARSER_URL}
  fi

  docker build --network=host -t ${IMAGE_DOMAIN}/${IMAGE_NAMESPACE}/${image_name}:${VERSION} -f Dockerfile.build .
  rm -r ./Dockerfile.build
  if [ "$TRAVIS_PULL_REQUEST" == "false" ]; then
     docker login ${IMAGE_DOMAIN} -u $DOCKER_USERNAME -p $DOCKER_PASSWORD
     docker push  ${IMAGE_DOMAIN}/${IMAGE_NAMESPACE}/rbd-app-ui:${VERSION}
     if [ ${DOMESTIC_BASE_NAME} ];
			then
				docker tag "${IMAGE_DOMAIN}/${IMAGE_NAMESPACE}/rbd-app-ui:${VERSION}" "${DOMESTIC_BASE_NAME}/${DOMESTIC_NAMESPACE}/rbd-app-ui:${VERSION}"
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
