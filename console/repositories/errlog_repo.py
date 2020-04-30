# -*- coding: utf8 -*-
from console.models.main import Errlog


class ErrlogRepo(object):
    def create(self, **data):
        Errlog.objects.create(**data)


errlog_repo = ErrlogRepo()
