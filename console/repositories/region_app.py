# -*- coding: utf8 -*-
import logging

from www.models.main import RegionApp

logger = logging.getLogger("default")


class RegionAppRepository(object):
    @staticmethod
    def create(**data):
        return RegionApp.objects.create(**data)

    @staticmethod
    def get_region_app_id(region_name, app_id):
        region_app = RegionApp.objects.get(region_name=region_name, app_id=app_id)
        return region_app.region_app_id


region_app_repo = RegionAppRepository()
