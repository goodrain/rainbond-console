# -*- coding: utf8 -*-
"""
  Created on 18/1/12.
"""
import logging

from backends.models.main import Announcement

logger = logging.getLogger("default")


class AnnouncementRepository(object):
    def create(self, **data):
        Announcement.objects.create(**data)

    def update(self, aid, **data):
        Announcement.objects.filter(announcement_id=aid).update(**data)

    def delete(self, aid):
        Announcement.objects.filter(announcement_id=aid).delete()
