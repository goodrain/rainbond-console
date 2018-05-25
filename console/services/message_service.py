# -*- coding: utf8 -*-
"""
  Created on 2018/5/21.
"""
from console.repositories.message_repo import msg_repo, announcement_repo
from console.models.main import UserMessage
from goodrain_web.tools import JuncheePaginator
from www.utils.crypt import make_uuid
from console.constants import MessageType
from django.db.models import Q


class MessageService(object):
    def sync_announcements_for_user(self, user):
        msgs = msg_repo.get_user_announcements(user.user_id)
        noticed_msg_ids = [msg.announcement_id for msg in msgs]
        announcements = announcement_repo.get_enabled_announcements().exclude(announcement_id__in=noticed_msg_ids)
        msg_list = []
        for announce in announcements:
            msg_list.append(UserMessage(
                message_id=make_uuid(),
                receiver_id=user.user_id,
                content=announce.content,
                is_read=False,
                msg_type=MessageType.ANNOUNCEMENT,
                announcement_id=announce.announcement_id,
                title=announce.title,
                level=announce.level
            ))
        UserMessage.objects.bulk_create(msg_list)

    def get_user_msgs(self, user, page_num, page_size, msg_type, is_read):
        query = Q()
        if msg_type:
            query &= Q(msg_type=msg_type)
        if is_read is not None:
            query &= Q(is_read=is_read)
        msgs = msg_repo.get_user_all_msgs(user.user_id).filter(query)
        msg_paginator = JuncheePaginator(msgs, int(page_size))
        total = msg_paginator.count
        page_msgs = msg_paginator.page(page_num)
        return page_msgs, total

    def update_user_msgs(self, user, action, msg_id_list):
        if action == "mark_read":
            UserMessage.objects.filter(receiver_id=user.user_id, ID__in=msg_id_list).update(is_read=True)
        else:
            UserMessage.objects.filter(receiver_id=user.user_id, ID__in=msg_id_list).update(is_read=False)

    def delete_user_msgs(self, user, msg_id_list):
        UserMessage.objects.filter(receiver_id=user.user_id, ID__in=msg_id_list).delete()


msg_service = MessageService()