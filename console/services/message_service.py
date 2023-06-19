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
            msg_list.append(
                UserMessage(
                    message_id=make_uuid(),
                    receiver_id=user.user_id,
                    content=announce.content,
                    is_read=False,
                    msg_type=MessageType.ANNOUNCEMENT,
                    announcement_id=announce.announcement_id,
                    title=announce.title,
                    level=announce.level,
                    create_time=announce.create_time))
        UserMessage.objects.bulk_create(msg_list)
        # 更新已有的公告
        old_announcements = announcement_repo.get_enabled_announcements().filter(announcement_id__in=noticed_msg_ids)
        for announce in old_announcements:
            usermessage_query = msg_repo.get_usermessage_queryset(announce.announcement_id)
            usermessage_query.update(content=announce.content, title=announce.title, level=announce.level)
        # 删除已经删除的公告
        announcements_id_list = announcement_repo.get_all_announcements_id()
        msg_repo.get_all_usermessage().exclude(announcement_id__in=announcements_id_list).delete()

        # 删除关闭启用的公告
        close_announcements = announcement_repo.get_close_announcements().filter(announcement_id__in=noticed_msg_ids)
        close_announcements_list = [obj.announcement_id for obj in close_announcements]
        msg_repo.get_all_usermessage().filter(announcement_id__in=close_announcements_list).delete()

    def get_user_msgs(self, user, page_num, page_size, msg_type, is_read):
        query = Q()
        if msg_type:
            query &= Q(msg_type=msg_type)
        if is_read is not None:
            query &= Q(is_read=is_read)
        if msg_type and is_read:
            msgs = msg_repo.get_user_all_msgs(user.user_id).order_by("-create_time")
        else:
            msgs = msg_repo.get_user_all_msgs(user.user_id).filter(query).order_by("-create_time")
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
