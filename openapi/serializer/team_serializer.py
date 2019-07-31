# -*- coding: utf-8 -*-
# creater by: barnett
from rest_framework import serializers


class TeamInfoPostSerializer(serializers.Serializer):
    tenant_name = serializers.CharField(max_length=24, help_text=u"团队名称")
    team_owner = serializers.IntegerField(help_text=u"团队拥有者用户ID")


class TeamInfoSerializer(serializers.Serializer):
    tenant_id = serializers.CharField(max_length=32, help_text=u"团队ID")
    tenant_name = serializers.CharField(max_length=24, help_text=u"团队名称")
    region = serializers.CharField(max_length=24, help_text=u"数据中心名称")
    is_active = serializers.BooleanField(help_text=u"是否激活")
    create_time = serializers.DateTimeField(help_text=u"创建时间")
    creater = serializers.CharField(help_text=u"团队拥有者用户ID")
    tenant_alias = serializers.CharField(max_length=24, help_text=u"团队别名")
    enterprise_id = serializers.CharField(max_length=32, help_text=u"企业ID")
    service_num = serializers.IntegerField(help_text=u"团队的服务数量", required=False)
    region_num = serializers.IntegerField(help_text=u"团队开通的数据中心数量", required=False)


class ListTeamRespSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    tenants = TeamInfoSerializer(many=True)


class CreateTeamReqSerializer(serializers.Serializer):
    tenant_name = serializers.CharField(max_length=24, help_text=u"团队名称")
    enterprise_id = serializers.CharField(max_length=32, help_text=u"团队所属企业ID,未提供时默认使用请求用户企业ID")
    creator = serializers.IntegerField(help_text=u"团队所属人，未提供时默认使用登录用户作为所属人", required=False)
    region = serializers.CharField(max_length=24, help_text=u"默认开通的数据中心，未指定则不开通", required=False)


class UpdateTeamInfoReqSerializer(serializers.Serializer):
    region = serializers.CharField(max_length=24, help_text=u"数据中心名称", required=False)
    is_active = serializers.BooleanField(help_text=u"是否激活", required=False)
    creater = serializers.IntegerField(help_text=u"团队拥有者用户ID", required=False)
    tenant_alias = serializers.CharField(max_length=24, help_text=u"团队别名", required=False)
    enterprise_id = serializers.CharField(max_length=32, help_text=u"企业ID", required=False)


class RoleInfoRespSerializer(serializers.Serializer):
    role_id = serializers.IntegerField(help_text=u"角色ID")
    role_name = serializers.CharField(max_length=32, help_text=u"角色名称")


class CreateTeamUserReqSerializer(serializers.Serializer):
    role_ids = serializers.CharField(max_length=255, help_text=u"角色ID列表")

    def validate_role_ids(self, role_ids):
        role_ids = role_ids.replace(" ", "")
        for role_id in role_ids.split(","):
            try:
                int(role_id)
            except ValueError:
                raise serializers.ValidationError("角色ID格式不正确")
