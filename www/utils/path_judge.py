# -*- coding: utf8 -*-
import re


def is_path_legal(path):
    r = re.compile(r'^\/([\w-]+\/?)+$')
    if not r.match(path):
        return False
    return True
