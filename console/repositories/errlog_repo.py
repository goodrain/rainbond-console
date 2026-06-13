# -*- coding: utf8 -*-
from typing import Any

from console.models.main import Errlog


class ErrlogRepo(object):
    def create(self, **data: Any) -> None:
        Errlog.objects.create(**data)


errlog_repo = ErrlogRepo()
