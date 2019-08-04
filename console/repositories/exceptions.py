# -*- coding: utf-8 -*-


class UserRoleNotFoundException(Exception):
    def __init__(self, msg=""):
        msg = msg if msg else "user role not found"
        super(UserRoleNotFoundException, self).__init__(msg)
