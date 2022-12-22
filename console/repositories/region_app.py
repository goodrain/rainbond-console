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

    @staticmethod
    def list_by_app_ids(region_name, app_ids):
        return RegionApp.objects.filter(region_name=region_name, app_id__in=app_ids)

    @staticmethod
    def list_by_region_app_ids(region_name, region_app_ids):
        return RegionApp.objects.filter(region_name=region_name, region_app_id__in=region_app_ids)


region_app_repo = RegionAppRepository()
