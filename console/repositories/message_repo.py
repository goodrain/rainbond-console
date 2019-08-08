# -*- coding: utf8 -*-
"""
  Created on 2018/5/21.
"""
from console.models.main import Announcement
from console.models.main import UserMessage
from console.constants import MessageType


class AnnouncementRepository(object):
    def get_enabled_announcements(self):
        return Announcement.objects.filter(active=True)

    def get_close_announcements(self):
        return Announcement.objects.filter(active=False)

    def get_all_announcements_id(self):
        all_obj = Announcement.objects.all()
        return [obj.announcement_id for obj in all_obj]


class MessageRepository(object):
    def get_user_announcements(self, use_id):
        return UserMessage.objects.filter(receiver_id=use_id, msg_type=MessageType.ANNOUNCEMENT)

    def get_user_all_msgs(self, user_id):
        return UserMessage.objects.filter(receiver_id=user_id)

    def get_usermessage_queryset(self, announcement_id):
        return UserMessage.objects.filter(announcement_id=announcement_id)

    def get_all_usermessage(self):
        return UserMessage.objects.exclude(announcement_id__isnull=True)


announcement_repo = AnnouncementRepository()
msg_repo = MessageRepository()
