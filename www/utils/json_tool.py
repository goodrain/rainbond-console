# -*- coding: utf8 -*-
import json as jsmod


def json_dump(obj, indent=None):
    """ Dump an object to json string, only basic types are supported.
    @return json string or `None` if failed

    >>> json_dump({'int': 1, 'none': None, 'str': 'string'})
    '{"int":1,"none":null,"str":"string"}'
    """
    try:
        jstr = jsmod.dumps(obj, separators=(',', ':'), indent=indent)
    except:
        jstr = None
    return jstr


def json_load(json):
    """ Load from json string and create a new python object
    @return object or `None` if failed

    >>> json_load('{"int":1,"none":null,"str":"string"}')
    {u'int': 1, u'none': None, u'str': u'string'}
    """
    try:
        obj = jsmod.loads(json)
    except:
        obj = None
    return obj
