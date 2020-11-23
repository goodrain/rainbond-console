#!/bin/bash

[ -d "./www/static/dists" ] && rm -rf ./www/static/dists/* || mkdir -p ./www/static/dists

cp -a dist/* ./www/static/dists/

cp dist/index.html www/templates/index.html

rm -rf ./static

cp -r www/static ./