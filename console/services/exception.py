# -*- coding: utf8 -*-


class ErrDepServiceNotFound(Exception):
    def __init__(self, sid=None):
        msg = "dep service not found"
        if sid:
            msg = "dep service not found(service_id={})".format(sid)
        super(ErrDepServiceNotFound, self).__init__(msg)


class ErrAdminUserDoesNotExist(Exception):
    def __init__(self, msg=""):
        super(ErrAdminUserDoesNotExist, self).__init__(msg)


class ErrCannotDelLastAdminUser(Exception):
    def __init__(self, msg=""):
        super(ErrCannotDelLastAdminUser, self).__init__(msg)
