# -*- coding: utf-8 -*-
import random
import string


def make_default_version():
    default_version = ''.join(random.sample(string.ascii_letters + string.digits, 8))
    return default_version
