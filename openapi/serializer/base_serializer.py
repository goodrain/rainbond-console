# -*- coding: utf-8 -*-
# creater by: barnett
from rest_framework import serializers


class TokenSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=64)


class FailSerializer(serializers.Serializer):
    msg = serializers.CharField(max_length=300)


class SuccessSerializer(serializers.Serializer):
    msg = serializers.CharField(max_length=300)
