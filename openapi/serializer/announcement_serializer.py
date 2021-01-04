# -*- coding: utf-8 -*-
# creater by: barnett
from rest_framework import serializers


class CreateAncmReqSerilizer(serializers.Serializer):
    content = serializers.CharField(max_length=1000, required=True, allow_blank=True, help_text="通知内容")
    type = serializers.CharField(max_length=15, required=True, allow_blank=True, help_text="通知类型")
    active = serializers.BooleanField(required=True, help_text="通知是否启用")
    title = serializers.CharField(max_length=64, required=True, allow_blank=True, help_text="通知标题")
    level = serializers.CharField(max_length=32, required=True, allow_blank=True, help_text="通知的等级")
    a_tag = serializers.CharField(max_length=256, required=False, allow_blank=True, help_text="A标签文字")
    a_tag_url = serializers.CharField(max_length=1024, required=False, allow_blank=True, help_text="a标签跳转地址")


class UpdateAncmReqSerilizer(serializers.Serializer):
    content = serializers.CharField(min_length=0, max_length=1000, required=False, allow_blank=True, help_text="通知内容")
    type = serializers.CharField(min_length=0, max_length=15, required=False, allow_blank=True, help_text="通知类型")
    active = serializers.NullBooleanField(required=False, help_text="通知是否启用")
    title = serializers.CharField(min_length=0, max_length=64, required=False, allow_blank=True, help_text="通知标题")
    level = serializers.CharField(min_length=0, max_length=32, required=False, allow_blank=True, help_text="通知的等级")
    a_tag = serializers.CharField(min_length=0, max_length=256, required=False, allow_blank=True, help_text="A标签文字")
    a_tag_url = serializers.CharField(min_length=0, max_length=1024, required=False, allow_blank=True, help_text="a标签跳转地址")


class AnnouncementRespSerilizer(serializers.Serializer):
    announcement_id = serializers.CharField(min_length=0, max_length=32, required=False, allow_blank=True, help_text="通知唯一标识")
    content = serializers.CharField(min_length=0, max_length=1000, required=False, allow_blank=True, help_text="通知内容")
    a_tag = serializers.CharField(min_length=0, max_length=256, required=False, allow_blank=True, help_text="A标签文字")
    a_tag_url = serializers.CharField(min_length=0, max_length=1024, required=False, allow_blank=True, help_text="a标签跳转地址")
    type = serializers.CharField(min_length=0, max_length=15, required=False, allow_blank=True, help_text="通知类型")
    active = serializers.BooleanField(required=False, help_text="通知是否启用")
    title = serializers.CharField(min_length=0, max_length=64, required=False, allow_blank=True, help_text="通知标题")
    level = serializers.CharField(min_length=0, max_length=32, required=False, allow_blank=True, help_text="通知的等级")


class ListAnnouncementRespSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    announcements = AnnouncementRespSerilizer(many=True)
