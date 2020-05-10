# -*- coding: utf8 -*-
from console.repositories.errlog_repo import errlog_repo


class ErrlogService(object):
    def create(self, msg, username, enterprise_id, address):
        errlog = {
            "msg": msg,
            "username": username,
            "enterprise_id": enterprise_id,
            "address": address,
        }
        errlog_repo.create(**errlog)


errlog_service = ErrlogService()
