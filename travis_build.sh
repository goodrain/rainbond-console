#!/bin/bash
image_name="rbd-app-ui"

IMAGE_DOMAIN=${BUILD_IMAGE_DOMAIN:-docker.io}
IMAGE_NAMESPACE=${BUILD_IMAGE_NAMESPACE:-rainbond}

if [ -z "$VERSION" ];then
  if [ -z "$TRAVIS_TAG" ]; then
	  VERSION=$TRAVIS_BRANCH-dev
  else
	  VERSION=$TRAVIS_TAG
  fi
fi

function release(){
  git_commit=$(git log -n 1 --pretty --format=%h)
  buildTime=$(date +%F-%H)
  release_desc=${VERSION}-${git_commit}-${buildTime}
  docker build --network=host --build-arg VERSION="${VERSION}" --build-arg RELEASE_DESC="${release_desc}"  -t "${IMAGE_DOMAIN}/${IMAGE_NAMESPACE}/${image_name}:${VERSION}" -f Dockerfile.release .
  if [ "$TRAVIS_PULL_REQUEST" == "false" ]; then
     docker login "${IMAGE_DOMAIN}" -u "$DOCKER_USERNAME" -p "$DOCKER_PASSWORD"
     docker push  "${IMAGE_DOMAIN}/${IMAGE_NAMESPACE}/rbd-app-ui:${VERSION}"
     if [ ${DOMESTIC_BASE_NAME} ];
			then
				docker tag "${IMAGE_DOMAIN}/${IMAGE_NAMESPACE}/rbd-app-ui:${VERSION}" "${DOMESTIC_BASE_NAME}/${DOMESTIC_NAMESPACE}/rbd-app-ui:${VERSION}"
				docker login -u "$DOMESTIC_DOCKER_USERNAME" -p "$DOMESTIC_DOCKER_PASSWORD" "${DOMESTIC_BASE_NAME}"
				docker push "${DOMESTIC_BASE_NAME}/${DOMESTIC_NAMESPACE}/rbd-app-ui:${VERSION}"
			fi
  fi
}

case $1 in
    *)
    release
    ;;
esac
