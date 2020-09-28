# -*- coding: utf8 -*-
import logging

from www.models.main import RegionApp

logger = logging.getLogger("default")


class RegionAppRepository(object):
    @staticmethod
    def create(**data):
        return RegionApp.objects.create(**data)


region_app_repo = RegionAppRepository()
