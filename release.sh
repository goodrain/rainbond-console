#!/bin/bash
set -xe

image_name="rbd-app-ui"

#gitDescribe=$(git describe --tag|sed 's/^v//')
#describe_items=($(echo $gitDescribe | tr '-' ' '))
#describe_len=${#describe_items[@]}
#git_commit=$(git log -n 1 --pretty --format=%h)
#if [ $describe_len -ge 3 ];then
#    buildRelease=${describe_items[*]: -2:1}.${describe_items[*]: -1}
#else
#    buildRelease=0.$git_commit
#fi
VERSION=$(git branch | grep '^*' | cut -d ' ' -f 2 | awk -F'V' '{print $2}')
buildTime=$(date +%F-%H)

function release(){

  echo "pull newest code..."
  git pull

  # get commit sha
  git_commit=$(git log -n 1 --pretty --format=%h)

  # get git describe info
  branch_info=$(git branch | grep '^*' | cut -d ' ' -f 2 | tr '-' " ")
  release_desc=${branch_info}-${git_commit}-${buildTime}

  sed "s/__RELEASE_DESC__/${release_desc}/" Dockerfile.release > Dockerfile.build
  docker build -t rainbond/${image_name}:${VERSION} -f Dockerfile.build .
  rm -r ./Dockerfile.build
}

case $1 in
    *)
    release
    ;;
esac