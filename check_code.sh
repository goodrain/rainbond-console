#! /bin/bash

# check code
echo "start check code specification by flake8"
flake8 --exclude env,static,www/alipay_direct,www/utils/mnssdk,backends --extend-ignore=W605 --max-line-length 129 ./
if [ $? -ne 0 ]; then
    exit 1
fi
echo "check code specification success"
# check code format
echo "start check code style by yapf"
yapf --exclude env --exclude static --exclude www/alipay_direct --exclude www/utils/mnssdk --exclude backends --style style.cfg  -r ./ -i
[[ -z $(git status -s) ]] || { echo "some code do not format before commit, please run 'make format' before git commit"; exit 1;}
echo "check code style success"

