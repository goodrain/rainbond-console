# -*- coding: utf-8 -*-
from rest_framework import serializers


class RoleInfoSerializer(serializers.Serializer):
    role_name = serializers.CharField(max_length=255, help_text="角色名称")
    role_id = serializers.CharField(max_length=64, help_text="角色ID")
