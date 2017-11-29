#coding=utf-8

# Note:
#     md5 crypto func

import hashlib
import sys

reload(sys)
sys.setdefaultencoding('utf8')

def md5Sign(prestr, key):
    prestr = prestr + key
    m = hashlib.md5()
    m.update(prestr)
    return m.hexdigest()

def md5Verify(prestr, sign, key):
    my_sign = md5Sign(prestr, key)
    if my_sign == sign:
        return True
    return False
