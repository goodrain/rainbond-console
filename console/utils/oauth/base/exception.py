# -*- coding: utf8 -*-


class NoAccessKeyErr(Exception):
    def __init__(self, value):
        self.message = value

    def __str__(self):
        return self.message


class NoOAuthServiceErr(Exception):
    def __init__(self, value):
        self.message = value

    def __str__(self):
        return self.message


class GetOAuthUserErr(Exception):
    def __init__(self, msg):
        super(GetOAuthUserErr, self).__init__(msg)
