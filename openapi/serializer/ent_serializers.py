# -*- coding: utf-8 -*-
# creater by: abe
from rest_framework import serializers


class EnterpriseInfoSerializer(serializers.Serializer):
    enterprise_id = serializers.CharField(max_length=32)
    enterprise_name = serializers.CharField(max_length=64)
    enterprise_alias = serializers.CharField(max_length=64)
    create_time = serializers.DateTimeField()
    enterprise_token = serializers.CharField(max_length=256)
