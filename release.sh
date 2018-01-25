#!/bin/bash
set -xe

image_name="rbd-app-ui"

gitDescribe=$(git describe --tag|sed 's/^v//')
describe_items=($(echo $gitDescribe | tr '-' ' '))
describe_len=${#describe_items[@]}
VERSION=${describe_items[0]}
git_commit=$(git log -n 1 --pretty --format=%h)
if [ $describe_len -ge 3 ];then
    buildRelease=${describe_items[-2]}.${describe_items[-1]}
else
    buildRelease=0.$git_commit
fi
if [ -z "$VERSION" ];then
    VERSION=3.4.2
fi

function release(){

  echo "pull newest code..."
  git pull

  # get commit sha
  git_commit=$(git log -n 1 --pretty --format=%h)

  # get git describe info
  branch_info=($(git branch | grep '^*' | cut -d ' ' -f 2 | tr '-' " "))
  release_desc=${branch_info}-${VERSION}-${buildRelease}


  sed "s/__RELEASE_DESC__/${release_desc}/" Dockerfile > Dockerfile.release

  docker build -t rainbond/${image_name}:${VERSION} -f Dockerfile.release .
  rm -r ./Dockerfile.release
  docker push rainbond/${image_name}:${VERSION}
}

case $1 in
    *)
    release
    ;;
esac
