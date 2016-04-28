#!/bin/bash
if [ -z $1 ]; then
    echo "Usage: $0 tag"
    exit 2
fi

TAG=$1
FORCE=$2

PROGRAM="console"

WORKDIR=$PWD
BUILDDIR="$PWD/build"

TAG_EXIST=$(git tag | grep $TAG)

if [ -z "$TAG_EXIST" ]; then
    echo "unknow tag: $TAG"
    exit 2
else
    mkdir -pv $BUILDDIR
    git archive --format=tar $TAG | gzip | tar zxf - -C $BUILDDIR
    cd $BUILDDIR
    mv Dockerfile_release Dockerfile
    docker build $FORCE -t hub.goodrain.com/goodrain/$PROGRAM:$TAG .
    cd $WORKDIR
    rm -rf $BUILDDIR
    docker tag hub.goodrain.com/goodrain/$PROGRAM:$TAG hub.goodrain.com/goodrain/$PROGRAM
    docker push hub.goodrain.com/goodrain/$PROGRAM
fi
