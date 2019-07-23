# -*- coding: utf-8 -*-
# creater by: barnett
from rest_framework import serializers


class BaseCfgSerializer(serializers.Serializer):
    key = serializers.CharField(max_length=32)
    type = serializers.CharField(max_length=32)
    value = serializers.CharField(max_length=4096)
    desc = serializers.CharField(max_length=40)
    enable = serializers.BooleanField()
    create_time = serializers.DateTimeField()
