# -*- coding: utf8 -*-
from console.repositories.errlog_repo import errlog_repo


class ErrlogService(object):
    def create(self, msg):
        errlog = {
            "msg": msg,
        }
        errlog_repo.create(**errlog)


errlog_service = ErrlogService()
