# -*- coding: utf8 -*-

import logging

from django.views.decorators.cache import never_cache
from rest_framework import serializers
from base_view import EnterpriseMarketAPIView
from console.models.main import UserMessage
from console.repositories.user_repo import user_repo
from backends.services.exceptions import UserNotExistError

logger = logging.getLogger('default')


class MessageSerilizer(serializers.Serializer):
    nick_name = serializers.CharField(required=True, max_length=24, help_text=u'接受消息用户的nick_name')
    content = serializers.CharField(max_length=256, required=True, help_text=u"通知内容")
    msg_type = serializers.CharField(max_length=32, required=True, help_text=u"通知类型")
    title = serializers.CharField(max_length=64, required=True, help_text=u"通知标题")
    level = serializers.CharField(max_length=32, required=True, help_text=u"通知的等级")


class UserMessageView(EnterpriseMarketAPIView):
    @never_cache
    def post(self, request, *args, **kwargs):
        """
        给一个用户推送一条站内信
        ---
        parameters:
            - name: nick_name
              description: 接受消息用户的nick_name
              required: true
              type: int
              paramType: form
            - name: title
              description: 标题
              required: true
              type: string
              paramType: form
            - name: content
              description: 消息内容
              required: true
              type: string
              paramType: form
            - name: msg_type
              description: 消息类型  公告 = "announcement"  提醒 = "own_money" 消息 = "service_abnormal"
              required: true
              type: string
              paramType: form
            - name: level
              description: 消息等级 high，mid，low
              required: true
              type: string
              paramType: form

        """
        try:
            data = request.data
            print data
            serializer = MessageSerilizer(data=data)
            if not serializer.is_valid():
                logger.error("params error")
                return self.error_response(
                    code="400", msg="params error", msg_show="参数错误")
            from www.utils.crypt import make_uuid
            message_id = make_uuid()
            params = dict(serializer.data)
            nick_name = params.get("nick_name")
            user_obj = user_repo.get_user_by_username(nick_name)
            params.update({"message_id": message_id})
            params.update({"receiver_id": user_obj.user_id})
            del params["nick_name"]
            UserMessage.objects.create(**params)
            return self.success_response(
                msg="success", msg_show="添加成功")
        except UserNotExistError as e:
            logger.exception(e)
            return self.error_response(code=400, msg_show=e.message)
        except Exception as e:
            logger.exception(e)
            return self.error_response()
