#!/bin/bash

# npm install             
# npm start
# npm run build
docker run -p 4042:4042 --rm -w /app -it -v `pwd`:/app node:6.9.0 npm start