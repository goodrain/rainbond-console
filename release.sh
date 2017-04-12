BASE_DIR=$PWD
git archive community --format tgz -o hack/source.tgz

cd hack/

db_container=$(docker run -d hub.goodrain.com/dc-deploy/mysql)
sleep 15
docker exec $db_container ps -ef
docker exec $db_container mysql -e "create database console;"
docker exec $db_container mysql -e "grant all on console.* to build@'%' identified by 'build';"
docker exec $db_container mysql -e "flush privileges;"
db_ip=$(docker inspect --format '{{.NetworkSettings.IPAddress}}' $db_container)
sed -e "/^WORKDIR/i ENV MYSQL_HOST $db_ip" Dockerfile_build_template > Dockerfile_build

docker build -t console-build -f Dockerfile_build .

rm -rf $PWD/app
docker run -v $PWD/app:/app -w /app-build/dist console-build rsync -a console_app /app/
docker run -v $PWD/app:/app -w /app-build/dist console-build cp -v console_manage/console_manage /app/

docker build -t console-release -f Dockerfile_release .
