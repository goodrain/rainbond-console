# -*- coding: utf-8 -*-
from backends.models import Announcement


class AnnouncementRepo(object):
    def get_announcement(self):
        announcements = Announcement.objects.filter(active=True).order_by("-create_time")
        if announcements:
            context = {
                "announcements": [a.to_dict() for a in announcements]
            }
            return context
        else:
            return {}


announcement_repo = AnnouncementRepo()