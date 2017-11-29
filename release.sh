#!/bin/bash
set -xe

image_name="acp_web"
release_type=$1
release_ver=$2
db_container="console-mysql"

if [ "$release_type" == "" ];then
  echo "please input release type (community | enterprise | all ) and version"
  exit 1
fi

trap 'clean_tmp; exit' QUIT TERM EXIT

function clean_tmp() {
  echo "clean temporary file..."
  [ -f Dockerfile.release ] && rm -rf Dockerfile.release
  docker kill $db_container
  docker rm $db_container
}

function release(){
  release_name=$1      # enterprise | community
  release_version=$2   # 3.2 | 2017.05
  branch_name=${release_name}-${release_version}
  git checkout $branch_name
  echo "pull newest code..."
  git pull

  # get commit sha
  git_commit=$(git log -n 1 --pretty --format=%h)

  # get git describe info
  release_desc=${release_name}-${release_version}-${git_commit}

  # make binary
  git archive $branch_name --format tgz -o hack/source.tgz
  cd hack/

  docker run -d --name console-mysql hub.goodrain.com/dc-deploy/mysql
  sleep 15
  docker exec $db_container ps -ef
  docker exec $db_container mysql -e "create database console;"
  docker exec $db_container mysql -e "grant all on console.* to build@'%' identified by 'build';"
  docker exec $db_container mysql -e "flush privileges;"
  db_ip=$(docker inspect --format '{{.NetworkSettings.IPAddress}}' $db_container)

  sed -e "/^WORKDIR/i ENV MYSQL_HOST $db_ip" \
    Dockerfile_build_template > Dockerfile_build
  docker build -t console-build -f Dockerfile_build .

  rm -rf $PWD/app
  docker run -v $PWD/app:/app -w /app-build/dist console-build rsync -a console_app/ /app
  docker run -v $PWD/app:/app -w /app-build/dist console-build cp -v console_manage/console_manage /app/

  sed "s/__RELEASE_DESC__/${release_desc}/" Dockerfile > Dockerfile.release

  docker build -t hub.goodrain.com/dc-deploy/${image_name}:${release_version} -f Dockerfile.release .
  docker push hub.goodrain.com/dc-deploy/${image_name}:${release_version}
}

case $release_type in
"community")
    release $1 $release_ver
    ;;
"enterprise")
    release $1 $release_ver
    ;;
"all")
    release "community" $release_ver
    release "enterprise" $release_ver
    ;;
esac
