# -*- coding: utf8 -*-
"""
  Created on 18/1/26.
"""
import re


def is_path_legal(path):
    r = re.compile(r'^\/([\w-]+\/?)+$')
    if not r.match(path):
        return False
    return True
