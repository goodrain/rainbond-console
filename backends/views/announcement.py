# -*- coding: utf8 -*-
import logging
from rest_framework.response import Response
from django.forms.models import model_to_dict
from backends.models.main import Announcement
from backends.views.base import BaseAPIView
from backends.services.resultservice import *
from backends.serializers import AnnouncementSerilizer

logger = logging.getLogger("default")


class AllAnnouncementView(BaseAPIView):
    def get(self, request, *args, **kwargs):
        """
        获取所有公告信息

        """
        try:
            announcements = Announcement.objects.all()
            announce_list = [model_to_dict(a) for a in announcements]
            result = generate_result(
                "0000", "success", "查询成功", list=announce_list
            )
        except Exception as e:
            logger.exception(e)
            result = generate_error_result()
        return Response(result)

    def post(self, request, *args, **kwargs):
        """
        添加公告
        ---
        serializer: AnnouncementSerilizer
        """
        try:
            data = request.data

            serializer = AnnouncementSerilizer(data=data)
            if not serializer.is_valid():
                logger.error("params error")
                result = generate_result(
                    "1003", "params error", "参数错误")
                return Response(result)
            from www.utils.crypt import make_uuid
            announcement_id = make_uuid()
            params = dict(serializer.data)
            params.update({"announcement_id": announcement_id})

            Announcement.objects.create(**params)
            result = generate_result(
                "0000", "success", "添加成功")
        except Exception as e:
            logger.exception(e)
            result = generate_error_result()
        return Response(result)


class AnnouncementView(BaseAPIView):
    def delete(self, request, announcement_id, *args, **kwargs):
        """
        删除公告
        ---
        parameters:
            - name: announcement_id
              description: 公告ID
              required: true
              type: string
              paramType: path
        """
        try:
            Announcement.objects.get(announcement_id=announcement_id).delete()
            result = generate_result("0000", "success", "公告删除成功")

        except Announcement.DoesNotExist as e:
            result = generate_result("8001", "label not exist", "该公告不存在")
        except Exception as e:
            logger.exception(e)
            result = generate_error_result()
        return Response(result)

    def put(self, request, announcement_id, *args, **kwargs):
        """
        更新公告
        ---
        parameters:
        -   name: body
            description: 修改内容 字段有 content,a_tag,a_tag_url,type,active(启用)
            required: true
            type: string
            paramType: body
        """
        try:
            data = request.data["body"]
            import json
            data = json.loads(data)
            params = {}

            for k, v in data.iteritems():
                params[k] = v
            self.update_announcement(announcement_id, **params)
            code = "0000"
            msg = "success"
            msg_show = "公告修改成功"
            result = generate_result(code, msg, msg_show)

        except Exception as e:
            logger.exception(e)
            result = generate_error_result()
        return Response(result)

    def update_announcement(self, announcement_id, **params):
        announcement = Announcement.objects.get(announcement_id=announcement_id)
        for k, v in params.items():
            setattr(announcement, k, v)
        announcement.save(update_fields=params.keys())
