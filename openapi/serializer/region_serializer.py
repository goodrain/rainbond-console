# -*- coding: utf-8 -*-
# creater by: barnett
from rest_framework import serializers

from openapi.models.main import RegionConfig
from openapi.serializer.utils import ipregex
from openapi.serializer.utils import urlregex


class RegionInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegionConfig
        fields = ["region_id", "region_name", "region_alias", "url", "token", "wsurl", "httpdomain",
                  "tcpdomain", "scope", "ssl_ca_cert", "cert_file", "key_file", "status", "desc"]

    def validate_url(self, url):
        if not urlregex.match(url):
            raise serializers.ValidationError("数据中心API地址非法")
        return url

    def validate_wsurl(self, wsurl):
        if not urlregex.match(wsurl):
            raise serializers.ValidationError("数据中心Websocket地址非法")
        return wsurl

    def validate_tcpdomain(self, tcpdomain):
        if not ipregex.match(tcpdomain):
            raise serializers.ValidationError("TCP访问地址非法")
        return tcpdomain

    def validate_status(self, status):
        if status not in ['0', '1', '2', '3']:
            raise serializers.ValidationError("数据中心状态值不正确")
        return status

    def validate_scope(self, scope):
        if scope not in ["private", "public"]:
            raise serializers.ValidationError("数据中心开放类型不正确")
        return scope
