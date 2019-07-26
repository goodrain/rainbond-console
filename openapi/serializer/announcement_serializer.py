# -*- coding: utf-8 -*-
# creater by: barnett
from rest_framework import serializers


class AnnouncementRespSerilizer(serializers.Serializer):
    announcement_id = serializers.CharField(max_length=32, help_text=u"通知唯一标识")
    content = serializers.CharField(max_length=1000, help_text=u"通知内容")
    a_tag = serializers.CharField(max_length=256, help_text=u"A标签文字")
    a_tag_url = serializers.CharField(max_length=1024, help_text=u"a标签跳转地址")
    type = serializers.CharField(max_length=15, help_text=u"通知类型")
    active = serializers.BooleanField(required=False, help_text=u"通知是否启用")
    title = serializers.CharField(max_length=64, help_text=u"通知标题")
    level = serializers.CharField(max_length=32, help_text=u"通知的等级")


class ListAnnouncementRespSerializer(serializers.Serializer):
    toatl = serializers.IntegerField()
    announcements = AnnouncementRespSerilizer(many=True)
