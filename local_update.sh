#!/bin/bash

[ -d "./www/static/dists" ] && rm -rf ./www/static/dists/* || mkdir -p ./www/static/dists

cp -a dist/* ./www/static/dists/

mv dist/index.html www/templates/index.html
