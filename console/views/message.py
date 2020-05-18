# -*- coding: utf8 -*-
"""
  Created on 18/5/5.
"""
import logging

from django.views.decorators.cache import never_cache
from rest_framework.response import Response

from console.services.message_service import msg_service
from console.views.base import RegionTenantHeaderView
from www.decorator import perm_required
from www.utils.return_message import general_message, error_message

logger = logging.getLogger('default')


class UserMessageView(RegionTenantHeaderView):
    @never_cache
    # @perm_required("tenant_access")
    def get(self, request, *args, **kwargs):
        """
        查询用户的站内信息
        ---
        parameters:
            - name: tenantName
              description: 团队名称
              required: true
              type: string
              paramType: path
            - name: msg_type
              description: 消息类别(warn|news|announcement)
              required: false
              type: string
              paramType: query
            - name: is_read
              description: 是否已读（1表示已读，0表示未读）
              required: false
              type: boolean
              paramType: query
            - name: page_num
              description: 页码
              required: false
              type: string
              paramType: query
            - name: page_size
              description: 每页数量
              required: false
              type: string
              paramType: query

        """
        # try:
        msg_type = request.GET.get("msg_type", None)
        page_num = int(request.GET.get("page_num", 1))
        page_size = int(request.GET.get("page_size", 5))
        is_read = request.GET.get("is_read", None)
        if is_read:
            is_read = bool(int(is_read))
        # 先同步数据
        msg_service.sync_announcements_for_user(self.user)
        # 再获取数据
        msgs, total = msg_service.get_user_msgs(self.user, page_num, page_size, msg_type, is_read)
        result = general_message(200, 'success', "查询成功", list=[msg.to_dict() for msg in msgs], total=total)
        # except Exception as e:
        #     logger.exception(e)
        #     result = error_message(e.message)
        return Response(result, status=result["code"])

    @never_cache
    def put(self, request, *args, **kwargs):
        """
        将站内信息标记为已读或未读
        ---
        parameters:
            - name: tenantName
              description: 团队名称
              required: true
              type: string
              paramType: path
            - name: msg_ids
              description: 信息ID,多个信息以英文逗号隔开
              required: true
              type: string
              paramType: form
            - name: action
              description: (mark_read 标记为已读|mark_unread 标记为未读)
              required: true
              type: string
              paramType: form

        """
        # try:
        msg_ids = request.data.get("msg_ids", None)
        action = request.data.get("action", None)
        if not msg_ids:
            return Response(general_message(200, "msg ids is null", "参数为空，未做修改"), status=200)
        if not action:
            return Response(general_message(400, "action is null", "请指明操作类型"), status=400)
        try:
            if action != "mark_read" and action != "mark_unread":
                raise TypeError("参数格式错误")
            msg_id_list = [int(msg_id) for msg_id in msg_ids.split(",")]
        except Exception as e:
            logger.exception(e)
            return Response(general_message(400, "Incorrect parameter format", "参数格式错误"), status=400)
        msg_service.update_user_msgs(self.user, action, msg_id_list)

        result = general_message(200, 'success', "更新成功")
        # except Exception as e:
        #     logger.exception(e)
        #     result = error_message(e.message)
        return Response(result, status=result["code"])

    @never_cache
    def delete(self, request, *args, **kwargs):
        """
        删除站内信
        ---
        parameters:
            - name: tenantName
              description: 团队名称
              required: true
              type: string
              paramType: path
            - name: msg_ids
              description: 信息ID,多个信息以英文逗号隔开
              required: true
              type: string
              paramType: form

        """
        # try:
        msg_ids = request.data.get("msg_ids", None)
        if not msg_ids:
            return Response(general_message(400, "msg ids is null", "请指明需删除的消息"), status=400)
        msg_id_list = [int(msg_id) for msg_id in msg_ids.split(",")]
        msg_service.delete_user_msgs(self.user, msg_id_list)

        result = general_message(200, 'success', "删除成功")
        # except Exception as e:
        #     logger.exception(e)
        #     result = error_message(e.message)
        return Response(result, status=result["code"])
