# -*- coding: utf8 -*-
import logging
from typing import Any, Optional

from django.db.models import QuerySet

from www.models.main import RegionApp

logger = logging.getLogger("default")


class RegionAppRepository(object):
    @staticmethod
    def create(**data: Any) -> RegionApp:
        return RegionApp.objects.create(**data)

    @staticmethod
    def get_region_app_id(region_name: str, app_id: str) -> str:
        region_app = RegionApp.objects.get(region_name=region_name, app_id=app_id)
        return region_app.region_app_id

    @staticmethod
    def get_app_id(region_name: str, region_app_id: str) -> int:
        region_app = RegionApp.objects.get(region_name=region_name, region_app_id=region_app_id)
        return region_app.app_id

    @staticmethod
    def list_by_app_ids(region_name: str, app_ids: Any) -> QuerySet:
        return RegionApp.objects.filter(region_name=region_name, app_id__in=app_ids)

    @staticmethod
    def list_by_region_app_ids(region_name: str, region_app_ids: Any) -> QuerySet:
        return RegionApp.objects.filter(region_name=region_name, region_app_id__in=region_app_ids)

    @staticmethod
    def list_by_region_and_app_ids(region_name: str, app_ids: Any) -> QuerySet:
        return RegionApp.objects.filter(region_name=region_name, app_id__in=app_ids)

    @staticmethod
    def get_region_app(region_name: str, app_id: str) -> Optional[RegionApp]:
        region_app = RegionApp.objects.filter(region_name=region_name, app_id=app_id).first()
        return region_app


region_app_repo = RegionAppRepository()
