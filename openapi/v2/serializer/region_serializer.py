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
            raise serializers.ValidationError("集群API地址非法")
        return url

    def validate_wsurl(self, wsurl):
        if not urlregex.match(wsurl):
            raise serializers.ValidationError("集群Websocket地址非法")
        return wsurl

    def validate_tcpdomain(self, tcpdomain):
        if not ipregex.match(tcpdomain):
            raise serializers.ValidationError("TCP访问地址非法")
        return tcpdomain

    def validate_status(self, status):
        if status not in ['0', '1', '2', '3']:
            raise serializers.ValidationError("集群状态值不正确")
        return status

    def validate_scope(self, scope):
        if scope not in ["private", "public"]:
            raise serializers.ValidationError("集群开放类型不正确")
        return scope


class RegionInfoSerializer(serializers.ModelSerializer, RegionReqValidate):
    class Meta:
        model = RegionConfig
        fields = [
            "region_id", "region_name", "region_alias", "url", "token", "wsurl", "httpdomain", "tcpdomain", "scope",
            "ssl_ca_cert", "cert_file", "key_file", "status", "desc"
        ]


class UpdateRegionReqSerializer(serializers.ModelSerializer, RegionReqValidate):
    class Meta:
        model = RegionConfig
        fields = [
            "region_alias", "url", "token", "wsurl", "httpdomain", "tcpdomain", "scope", "ssl_ca_cert", "cert_file", "key_file",
            "status", "desc"
        ]


class RegionTypesField(serializers.ListField):
    child = serializers.CharField(max_length=32)


class RegionInfoRespSerializer(serializers.Serializer):
    region_id = serializers.CharField(max_length=36, help_text=u"region id")
    enterprise_id = serializers.CharField(max_length=36, help_text=u"企业ID")
    enterprise_alias = serializers.CharField(max_length=256, help_text=u"企业别名")
    region_name = serializers.CharField(max_length=32, help_text=u"集群名称")
    region_alias = serializers.CharField(max_length=32, help_text=u"集群别名")
    region_type = RegionTypesField(help_text=u"集群类型")
    url = serializers.CharField(max_length=256, help_text=u"集群API url")
    wsurl = serializers.CharField(max_length=256, help_text=u"集群Websocket url")
    httpdomain = serializers.CharField(max_length=256, help_text=u"集群http应用访问根域名")
    tcpdomain = serializers.CharField(max_length=256, help_text=u"集群tcp应用访问根域名")
    status = serializers.CharField(max_length=2, help_text=u"集群状态 0：编辑中 1:启用 2：停用 3:维护中")
    desc = serializers.CharField(max_length=128, allow_blank=True, help_text=u"集群描述")
    ssl_ca_cert = serializers.CharField(max_length=65535, allow_blank=True, allow_null=True, help_text=u"api ca file")
    cert_file = serializers.CharField(max_length=65535, allow_blank=True, allow_null=True, help_text=u"api cert file")
    key_file = serializers.CharField(max_length=65535, allow_blank=True, allow_null=True, help_text=u"api cert key file")
    total_memory = serializers.IntegerField(help_text=u"调度内存总和MB")
    used_memory = serializers.IntegerField(help_text=u"调度内存使用量MB")
    total_cpu = serializers.IntegerField(help_text=u"调度CPU总和")
    used_cpu = serializers.FloatField(help_text=u"调度CPU使用量")
    total_disk = serializers.IntegerField(help_text=u"全局共享存储总量GB")
    used_disk = serializers.IntegerField(help_text=u"全局共享存储使用量GB")
    rbd_version = serializers.CharField(help_text=u"集群版本", allow_blank=True, allow_null=True)


class ListRegionsRespSerializer(serializers.Serializer):
    total = serializers.IntegerField(help_text=u"总数")
    data = RegionInfoRespSerializer(many=True)


class UpdateRegionStatusReqSerializer(serializers.Serializer):
    status = serializers.CharField(help_text=u"需要设置的集群状态, 可选值为: 'ONLINE', 'OFFLINE', 'MAINTAIN'(大小写不敏感)")

    def validate_status(self, status):
        status = status.upper()
        names = RegionStatusEnum.names()
        if status not in names:
            raise serializers.ValidationError("不支持状态: '{}', 仅支持: {}".format(status, ",".join(names)))
        return status
