# -*- coding: utf-8 -*-

import logging
from typing import Optional

from django.core.exceptions import ObjectDoesNotExist
from console.models.main import ServiceBuildSource

logger = logging.getLogger("default")


class ServiceBuildSourceRepository(object):
    def save(self, service_id: str, group_key: str, version: str) -> ServiceBuildSource:
        return ServiceBuildSource.objects.create(service_id=service_id, group_key=group_key, version=version)

    def get_by_service_id(self, service_id: str) -> Optional[ServiceBuildSource]:
        try:
            return ServiceBuildSource.objects.get(service_id=service_id)
        except ObjectDoesNotExist:
            logger.warning("Service ID: {}; Service build source not found.".format(service_id))
            return None

    def update_version_by_sid(self, service_id: str, version: str) -> None:
        ServiceBuildSource.objects.filter(service_id=service_id).update(version=version)
