# -*- coding: utf-8 -*-
# creater by: barnett
from rest_framework import serializers

from openapi.serializer.role_serializer import RoleInfoSerializer


class UserInfoSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    email = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=35, help_text=u"邮件地址")
    nick_name = serializers.CharField(required=False, max_length=24, help_text=u"用户昵称")
    phone = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=11, help_text=u"手机号码")
    is_active = serializers.BooleanField(required=False, help_text=u"激活状态")
    origion = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=12, help_text=u"用户来源")
    create_time = serializers.DateTimeField(required=False, help_text=u"创建时间")
    client_ip = serializers.CharField(required=False, allow_blank=True,
                                      allow_null=True, max_length=20, help_text=u"注册ip")
    enterprise_id = serializers.CharField(required=False, max_length=32, help_text=u"enterprise_id")


class ListUsersRespView(serializers.Serializer):
    users = UserInfoSerializer(many=True)
    total = serializers.IntegerField()


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
    phone = serializers.CharField(max_length=11, required=False, allow_blank=True, help_text=u"手机号码")
    is_active = serializers.NullBooleanField(required=False, help_text=u"激活状态")


class CreateAdminUserReqSerializer(serializers.Serializer):
    user_id = serializers.CharField(max_length=32, required=True, help_text=u"用户ID")
    eid = serializers.CharField(max_length=32, required=True, help_text=u"企业ID")


class TeamUserSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    email = serializers.CharField(required=False, allow_null=True, allow_blank=True, max_length=35, help_text=u"邮件地址")
    nick_name = serializers.CharField(required=False, max_length=24, help_text=u"用户昵称")
    phone = serializers.CharField(required=False, max_length=11, allow_blank=True, allow_null=True, help_text=u"手机号码")
    is_active = serializers.BooleanField(required=False, help_text=u"激活状态")
    origion = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=12, help_text=u"用户来源")
    enterprise_id = serializers.CharField(required=False, max_length=32, help_text=u"enterprise_id")
    role_infos = RoleInfoSerializer(many=True)


class ListTeamUsersRespSerializer(serializers.Serializer):
    users = TeamUserSerializer(many=True)
    total = serializers.IntegerField()


class ChangePassWdUserSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(required=True, help_text=u"user_id")
    password = serializers.CharField(max_length=16, required=True, min_length=8, help_text=u"新密码")
    password1 = serializers.CharField(max_length=16, required=True, min_length=8, help_text=u"再次确认新密码")
