#!/bin/bash
IMAGE_DOMAIN=${IMAGE_DOMAIN:-docker.io}
IMAGE_NAMESPACE=${IMAGE_NAMESPACE:-rainbond}
DOMESTIC_BASE_NAME=${DOMESTIC_BASE_NAME:-'registry.cn-hangzhou.aliyuncs.com'}
DOMESTIC_NAMESPACE=${DOMESTIC_NAMESPACE:-'goodrain'}
ARCH=${BUILD_ARCH:-'amd64'}
OFFLINE=${OFFLINE:-'false'}
BUILDER=${BUILDER:-"v5.8.1-release"}
RUNNER=${RUNNER:-"v5.8.1-release"}
TRAVIS_PULL_REQUEST=${TRAVIS_PULL_REQUEST:-false}
# rainbond operator org and branch
OPERATOR_BRANCH=${OPERATOR_BRANCH:-${VERSION}}
OPERATOR_ORG=${OPERATOR_ORG:-'goodrain'}
# adaptor branch
ADAPTOR_BRANCH=${ADAPTOR_BRANCH:-${VERSION}}
# Domestic packing acceleration
if [ "$PROXY" == "domestic" ]; then
  GOPROXY="https://goproxy.cn"
  GITPROXY="https://ghproxy.com/"
  PYTHONPROXY="-i https://pypi.tuna.tsinghua.edu.cn/simple"
fi

if [ -z "$VERSION" ]; then
  if [ -z "$TRAVIS_TAG" ]; then
    VERSION=$TRAVIS_BRANCH-dev
  else
    VERSION=$TRAVIS_TAG
  fi
fi

function release() {
  git_commit=$(git log -n 1 --pretty --format=%h)
  buildTime=$(date +%F-%H)
  release_desc=${VERSION}-${git_commit}-${buildTime}
  image_name="rainbond-console"
  docker build --network=host --build-arg RELEASE_DESC="${release_desc}" -t "${IMAGE_DOMAIN}/${IMAGE_NAMESPACE}/${image_name}:${VERSION}" -f Dockerfile .
  if [ $? -ne 0 ]; then
    exit 1
  fi
  if [ "$TRAVIS_PULL_REQUEST" == "false" ]; then
    docker login "${IMAGE_DOMAIN}" -u "$DOCKER_USERNAME" -p "$DOCKER_PASSWORD"
    docker push "${IMAGE_DOMAIN}/${IMAGE_NAMESPACE}/${image_name}:${VERSION}"
    if [ ${DOMESTIC_BASE_NAME} ]; then
      docker tag "${IMAGE_DOMAIN}/${IMAGE_NAMESPACE}/${image_name}:${VERSION}" "${DOMESTIC_BASE_NAME}/${DOMESTIC_NAMESPACE}/${image_name}:${VERSION}"
      docker login -u "$DOMESTIC_DOCKER_USERNAME" -p "$DOMESTIC_DOCKER_PASSWORD" "${DOMESTIC_BASE_NAME}"
      docker push "${DOMESTIC_BASE_NAME}/${DOMESTIC_NAMESPACE}/${image_name}:${VERSION}"
    fi
  fi
}

function release_allinone() {
  git_commit=$(git log -n 1 --pretty --format=%h)
  buildTime=$(date +%F-%H)
  release_desc=${VERSION}-${git_commit}-${buildTime}-allinone
  image_name="rainbond"
  imageName=${IMAGE_DOMAIN}/${IMAGE_NAMESPACE}/${image_name}:${VERSION}
  docker build --network=host --build-arg VERSION="${VERSION}" --build-arg IMAGE_NAMESPACE="${IMAGE_NAMESPACE}"  --build-arg ADAPTOR_BRANCH="${ADAPTOR_BRANCH}" --build-arg RELEASE_DESC="${release_desc}" --build-arg ARCH="${ARCH}" -t "${imageName}" -f Dockerfile.allinone .
  if [ $? -ne 0 ]; then
    exit 1
  fi
  if [ "$TRAVIS_PULL_REQUEST" == "false" ]; then
    if [ "$DOCKER_USERNAME" ]; then
      echo "$DOCKER_PASSWORD" | docker login ${IMAGE_DOMAIN} -u "$DOCKER_USERNAME" --password-stdin
      docker tag "${imageName}" "${imageName}-allinone"
      docker push "${imageName}"
      docker push "${imageName}-allinone"
    fi
    if [ "${DOMESTIC_BASE_NAME}" ]; then
      domestcName=$DOMESTIC_BASE_NAME/$DOMESTIC_NAMESPACE/rainbond:${VERSION}
      docker tag "${imageName}" "${domestcName}"
      docker tag "${imageName}" "${domestcName}-allinone"
      echo "$DOMESTIC_DOCKER_PASSWORD"|docker login -u "$DOMESTIC_DOCKER_USERNAME" "${DOMESTIC_BASE_NAME}" --password-stdin
      docker push "${domestcName}"
      docker push "${domestcName}-allinone"
    fi
  fi
}

function release_dind() {
  git_commit=$(git log -n 1 --pretty --format=%h)
  buildTime=$(date +%F-%H)
  release_desc=${VERSION/-release}-${git_commit}-${buildTime}-allinone
  image_name="rainbond"
  imageName=${IMAGE_DOMAIN}/${IMAGE_NAMESPACE}/${image_name}:${VERSION/-release}-dind-allinone
  domestcName=${DOMESTIC_BASE_NAME}/${DOMESTIC_NAMESPACE}/rainbond:${VERSION/-release}-dind-allinone
  docker build --network=host --build-arg VERSION="${VERSION}" --build-arg IMAGE_NAMESPACE="${IMAGE_NAMESPACE}" \
    --build-arg RELEASE_DESC="${release_desc}" \
    --build-arg ARCH="${ARCH}" \
    --build-arg OPERATOR_BRANCH="${OPERATOR_BRANCH}" \
    --build-arg OPERATOR_ORG="${OPERATOR_ORG}" \
    --build-arg ADAPTOR_BRANCH="${ADAPTOR_BRANCH}" \
    --build-arg GOPROXY="${GOPROXY}" \
    --build-arg GITPROXY="${GITPROXY}" \
    --build-arg PYTHONPROXY="${PYTHONPROXY}" \
    -t "${imageName}" -f Dockerfile.dind .
  if [ $? -ne 0 ]; then
    exit 1
  fi
  if [ "$OFFLINE" == "true" ]; then
    imageName="${imageName}-offline"
    domestcName="${domestcName}-offline"
  fi
  if [ "$TRAVIS_PULL_REQUEST" == "false" ]; then
    if [ "$DOCKER_USERNAME" ]; then
      echo "$DOCKER_PASSWORD" | docker login ${IMAGE_DOMAIN} -u "$DOCKER_USERNAME" --password-stdin
      docker push "${imageName}"
    fi
    if [ "${DOMESTIC_DOCKER_USERNAME}" ]; then
      docker tag ${imageName} ${domestcName}
      docker login -u "$DOMESTIC_DOCKER_USERNAME" -p "$DOMESTIC_DOCKER_PASSWORD" "${DOMESTIC_BASE_NAME}"
      docker push "${domestcName}"
    fi
  fi
}

function build_dind_package () {
  BUILDER=${BUILDER} \
  RUNNER=${RUNNER} \
  OFFLINE=${OFFLINE} \
  IMAGE_DOMAIN=${IMAGE_DOMAIN} \
  IMAGE_NAMESPACE=${IMAGE_NAMESPACE} \
  VERSION=${VERSION} \
  ./build_dind_package.sh
  if [ $? -ne 0 ]; then
    exit 1
  fi
}

case $1 in
allinone)
  release_allinone
  ;;
dind)
  build_dind_package
  release_dind
  ;;
*)
  release
  ;;
esac
