#! /bin/bash

# check code
flake8 --exclude env,static,www/alipay_direct,www/utils/mnssdk,backends --extend-ignore=W605 --max-line-length 129 ./
if [ $? -ne 0 ]; then
    exit 1
fi

# check code format
yapf --exclude env --exclude static --exclude www/alipay_direct --exclude www/utils/mnssdk --exclude backends --style style.cfg  -r ./ -i



