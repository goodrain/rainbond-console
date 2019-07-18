# -*- coding: utf-8 -*-
# creater by: barnett
from openapi.serializer.utils import urlregex, ipregex
from openapi.models.main import RegionConfig
from rest_framework import serializers


class RegionInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegionConfig
        fields = "__all__"

    def validate_url(self, url):
        if not urlregex.match(url):
            raise serializers.ValidationError("数据中心API")

    def validate_wsurl(self, wsurl):
        if not urlregex.match(wsurl):
            raise serializers.ValidationError("数据中心Websocket地址非法")

    def validate_tcpdomain(self, tcpdomain):
        if not ipregex.match(tcpdomain):
            raise serializers.ValidationError("TCP访问地址非法")
