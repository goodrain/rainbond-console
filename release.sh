set -e
BASE_DIR=$PWD
CURR_BRANCH=$(git branch | grep ^* | awk '{print $2}')
git archive $CURR_BRANCH --format tgz -o hack/source.tgz

cd hack/

db_container=console-mysql
docker run -d --name console-mysql hub.goodrain.com/dc-deploy/mysql
sleep 15
docker exec $db_container ps -ef
docker exec $db_container mysql -e "create database console;"
docker exec $db_container mysql -e "grant all on console.* to build@'%' identified by 'build';"
docker exec $db_container mysql -e "flush privileges;"
db_ip=$(docker inspect --format '{{.NetworkSettings.IPAddress}}' $db_container)

RELEASE_TAG=$(git describe --tag)
RELEASE_VERSION=${RELEASE_TAG%%-*}

sed -e "/^WORKDIR/i ENV MYSQL_HOST $db_ip" \
  Dockerfile_build_template > Dockerfile_build

echo $RELEASE_VERSION > VERSION
docker build -t console-build -f Dockerfile_build .

rm -rf $PWD/app
docker run -v $PWD/app:/app -w /app-build/dist console-build rsync -a console_app/ /app
docker run -v $PWD/app:/app -w /app-build/dist console-build cp -v console_manage/console_manage /app/

RELEASE_IMAGE="hub.goodrain.com/dc-deploy/console:$CURR_BRANCH"
PRE_IMAGE="${RELEASE_IMAGE}.pre"

docker build -t $PRE_IMAGE -f Dockerfile_release .
docker push $PRE_IMAGE
docker kill $db_container
docker rm $db_container

echo "Only pushed pre-release image $PRE_IMAGE"
echo "If need to push the release image, run these commands"
echo -e "\n  docker tag $PRE_IMAGE $RELEASE_IMAGE && docker push $RELEASE_IMAGE"