# -*- coding: utf-8 -*-
# creater by: barnett
from rest_framework import serializers


class UserInfoSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    email = serializers.EmailField(required=False, max_length=35, help_text=u"邮件地址")
    nick_name = serializers.CharField(required=False, max_length=24, help_text=u"用户昵称")
    phone = serializers.CharField(required=False, max_length=11, help_text=u"手机号码")
    is_active = serializers.BooleanField(required=False, help_text=u"激活状态")
    origion = serializers.CharField(required=False, allow_blank=True, max_length=12, help_text=u"用户来源")
    create_time = serializers.DateTimeField(required=False, help_text=u"创建时间")
    client_ip = serializers.CharField(required=False, allow_blank=True, max_length=20, help_text=u"注册ip")
    enterprise_id = serializers.CharField(required=False, max_length=32, help_text=u"enterprise_id")


class ListUsersRespView(serializers.Serializer):
    users = UserInfoSerializer(many=True)
    total = serializers.IntegerField()

    def create(self, data):
        self.total = data["total"]
        self.users = UserInfoSerializer(data["users"], many=True)


class CreateUserSerializer(serializers.Serializer):
    nick_name = serializers.CharField(max_length=24, required=True, help_text=u"用户昵称")
    password = serializers.CharField(max_length=16, required=True, min_length=8, help_text=u"用户昵称")
    enterprise_id = serializers.CharField(max_length=32, required=True, help_text=u"enterprise_id")
    email = serializers.EmailField(max_length=35, required=False, help_text=u"邮件地址")
    phone = serializers.CharField(max_length=11, required=False, help_text=u"手机号码")
    is_active = serializers.BooleanField(required=False, default=True, help_text=u"激活状态")
    origion = serializers.CharField(required=False, max_length=12, help_text=u"用户来源")


class UpdateUserSerializer(serializers.Serializer):
    password = serializers.CharField(max_length=16, required=False, min_length=8, help_text=u"用户昵称")
    enterprise_id = serializers.CharField(max_length=32, required=False, help_text=u"enterprise_id")
    email = serializers.EmailField(max_length=35, required=False, help_text=u"邮件地址")
    phone = serializers.CharField(max_length=11, required=False, help_text=u"手机号码")
    is_active = serializers.NullBooleanField(required=False, help_text=u"激活状态")
