# -*- coding: utf8 -*-
"""
  Created on 18/1/12.
"""
import logging
from typing import Any

from console.models.main import Announcement

logger = logging.getLogger("default")


class AnnouncementRepository(object):
    def create(self, **data: Any) -> None:
        Announcement.objects.create(**data)

    def update(self, aid: str, **data: Any) -> None:
        Announcement.objects.filter(announcement_id=aid).update(**data)

    def delete(self, aid: str) -> None:
        Announcement.objects.filter(announcement_id=aid).delete()
