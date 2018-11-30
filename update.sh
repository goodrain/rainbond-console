#!/bin/bash

UI_REPO="https://github.com/goodrain/rainbond-ui.git"

[ -d "/tmp/ui" ] && rm -rf /tmp/ui

git clone --depth 1 $UI_REPO /tmp/ui

[ -d "./www/static/dists" ] && rm -rf ./www/static/dists/* || mkdir -p ./www/static/dists

cp -a /tmp/ui/dist/* ./www/static/dists/

mv ./www/static/dists/index.html www/templates/index.html

rm -rf /tmp/ui

