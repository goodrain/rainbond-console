# -*- coding: utf8 -*-
from datetime import datetime

from console.repositories.announcement_repo import AnnouncementRepository
from www.utils.crypt import make_uuid


class AnnouncementService(object):

    def create(self, ancm):
        ancm.update({"announcement_id": make_uuid()})
        ancm.update({"create_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
        repo = AnnouncementRepository()
        repo.create(**ancm)

    def update(self, ancm):
        data = {}
        if ancm.get("content", None) is not None:
            data["content"] = ancm.get("content", "")
        if ancm.get("a_tag", None) is not None:
            data["a_tag"] = ancm.get("a_tag", "")
        if ancm.get("a_tag_url", None) is not None:
            data["a_tag_url"] = ancm.get("a_tag_url", "")
        if ancm.get("type", None) is not None:
            data["type"] = ancm.get("type", "")
        if ancm.get("active", None) is not None:
            data["active"] = ancm.get("active", "")
        if ancm.get("create_time", None) is not None:
            data["create_time"] = ancm.get("create_time", "")
        if ancm.get("title", None) is not None:
            data["title"] = ancm.get("title", "")
        if ancm.get("level", None) is not None:
            data["level"] = ancm.get("level", "")

        repo = AnnouncementRepository()
        repo.update(ancm["aid"], **data)

    def delete(self, aid):
        repo = AnnouncementRepository()
        repo.delete(aid)
