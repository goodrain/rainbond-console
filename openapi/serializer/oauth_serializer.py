# -*- coding: utf-8 -*-
# create by: panda-zxs

from rest_framework import serializers


class OAuthTypeSerializer(serializers.Serializer):
    type = serializers.CharField(max_length=64, allow_null=True, allow_blank=True, help_text=u"oauth服务类型")
