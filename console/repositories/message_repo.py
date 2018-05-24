# -*- coding: utf8 -*-
"""
  Created on 2018/5/21.
"""
from backends.models.main import Announcement
from console.models.main import UserMessage
from console.constants import MessageType


class AnnouncementRepository(object):
    def get_enabled_announcements(self):
        return Announcement.objects.filter(active=True)


class MessageRepository(object):
    def get_user_announcements(self, use_id):
        return UserMessage.objects.filter(receiver_id=use_id, msg_type=MessageType.ANNOUNCEMENT)

    def get_user_all_msgs(self, user_id):
        return UserMessage.objects.filter(receiver_id=user_id)

announcement_repo = AnnouncementRepository()
msg_repo = MessageRepository()
