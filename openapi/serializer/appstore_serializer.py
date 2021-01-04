# -*- coding: utf-8 -*-
# creater by: abe
from rest_framework import serializers

from openapi.serializer.utils import urlregex


class AppStoreInfoSerializer(serializers.Serializer):
    enterprise_id = serializers.CharField(max_length=32, help_text="企业ID(联合云ID)")
    enterprise_name = serializers.CharField(max_length=64, help_text="企业名称")
    enterprise_alias = serializers.CharField(max_length=64, help_text="企业别名")
    appstore_name = serializers.CharField(help_text="应用市场名称", allow_blank=True)
    access_url = serializers.CharField(help_text="应用市场API地址")


class ListAppStoreInfosRespSerializer(serializers.Serializer):
    total = serializers.IntegerField(help_text="总数")
    appstores = AppStoreInfoSerializer(many=True)


class UpdAppStoreInfoReqSerializer(serializers.Serializer):
    access_url = serializers.CharField(help_text="应用市场API地址")

    def validate_access_url(self, access_url):
        if not urlregex.match(access_url):
            raise serializers.ValidationError("应用市场API地址非法")
        return access_url
