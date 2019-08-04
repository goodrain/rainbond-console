# -*- coding: utf-8 -*-
from rest_framework import serializers


class RoleInfoSerializer(serializers.Serializer):
    role_name = serializers.CharField(max_length=32, required=True, help_text=u"角色名称")
    role_id = serializers.CharField(max_length=32, required=True, help_text=u"角色ID")
