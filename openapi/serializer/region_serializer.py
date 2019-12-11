# -*- coding: utf-8 -*-
# creater by: barnett
from rest_framework import serializers

from console.enum.region_enum import RegionStatusEnum
from console.models.main import RegionConfig
from openapi.serializer.utils import ipregex
from openapi.serializer.utils import urlregex


class RegionReqValidate(object):
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


class RegionInfoSerializer(serializers.ModelSerializer, RegionReqValidate):
    class Meta:
        model = RegionConfig
        fields = ["region_id", "region_name", "region_alias", "url", "token", "wsurl", "httpdomain",
                  "tcpdomain", "scope", "ssl_ca_cert", "cert_file", "key_file", "status", "desc"]


class UpdateRegionReqSerializer(serializers.ModelSerializer, RegionReqValidate):
    class Meta:
        model = RegionConfig
        fields = ["region_alias", "url", "token", "wsurl", "httpdomain",
                  "tcpdomain", "scope", "ssl_ca_cert", "cert_file", "key_file", "status", "desc"]


class RegionInfoRespSerializer(serializers.Serializer):
    region_id = serializers.CharField(max_length=36, help_text=u"region id")
    region_name = serializers.CharField(max_length=32, help_text=u"数据中心名称")
    region_alias = serializers.CharField(max_length=32, help_text=u"数据中心别名")
    url = serializers.CharField(max_length=256, help_text=u"数据中心API url")
    wsurl = serializers.CharField(max_length=256, help_text=u"数据中心Websocket url")
    httpdomain = serializers.CharField(max_length=256, help_text=u"数据中心http应用访问根域名")
    tcpdomain = serializers.CharField(max_length=256, help_text=u"数据中心tcp应用访问根域名")
    token = serializers.CharField(max_length=138, allow_null=True, allow_blank=True, default="", help_text=u"数据中心token")
    status = serializers.CharField(max_length=2, help_text=u"数据中心状态 0：编辑中 1:启用 2：停用 3:维护中")
    desc = serializers.CharField(max_length=128, allow_blank=True, help_text=u"数据中心描述")
    scope = serializers.CharField(max_length=10, default="private", help_text=u"数据中心范围 private|public")
    ssl_ca_cert = serializers.CharField(max_length=65535, allow_blank=True, allow_null=True, help_text=u"数据中心访问ca证书地址")
    cert_file = serializers.CharField(max_length=65535, allow_blank=True, allow_null=True, help_text=u"验证文件")
    key_file = serializers.CharField(max_length=65535, allow_blank=True, allow_null=True, help_text=u"验证的key")


class ListRegionsRespSerializer(serializers.Serializer):
    total = serializers.IntegerField(help_text=u"总数")
    regions = RegionInfoRespSerializer(many=True)


class UpdateRegionStatusReqSerializer(serializers.Serializer):
    status = serializers.CharField(help_text=u"需要设置的数据中心状态, 可选值为: 'ONLINE', 'OFFLINE', 'MAINTAIN'(大小写不敏感)")

    def validate_status(self, status):
        status = status.upper()
        names = RegionStatusEnum.names()
        if status not in names:
            raise serializers.ValidationError("不支持状态: '{}', 仅支持: {}".format(
                status, ",".join(names)))
        return status
