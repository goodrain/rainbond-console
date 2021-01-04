# -*- coding: utf8 -*-
"""
  Created on 18/1/26.
"""
import re


def is_path_legal(path):
    r = re.compile(r'^\/([\w-]+\/?)+([\w-]?.+\/?)?([\w-]?.[\w-]+\/?)$')
    if not r.match(path):
        return False
    return True


def set_get_url(url, params):
    return "?".join([url, "&".join(["=".join(x) for x in list(params.items())])])
