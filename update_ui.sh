#!/bin/bash

UI_REPO="https://github.com/goodrain/rainbond-ui.git"

ui_dir="./test/ui"

[ -d $ui_dir ] && rm -rf $ui_dir

branch=$(git symbolic-ref --short -q HEAD)

git clone -b "$branch" --depth 1 $UI_REPO $ui_dir

if [ -d "./www/static/dists" ]; then
    rm -rf ./www/static/dists/*
else
    mkdir -p ./www/static/dists
fi

pushd $ui_dir && yarn install && yarn build

mkdir ./www/static/dists/
cp -a $ui_dir/dist/* ./www/static/dists/

mv ./www/static/dists/index.html www/templates/index.html

rm -rf $ui_dir
