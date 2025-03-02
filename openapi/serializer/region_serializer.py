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
            "ssl_ca_cert", "cert_file", "key_file", "status", "desc", "enterprise_id"
        ]


class RegionInfoRSerializer(serializers.Serializer):
    region_name = serializers.CharField(help_text="数据中心名")
    region_alias = serializers.CharField(help_text="数据中心昵称")
    url = serializers.CharField(allow_null=True, help_text="数据中心API url")
    wsurl = serializers.CharField(allow_null=True, help_text="数据中心Websocket url")
    httpdomain = serializers.CharField(allow_null=True, help_text="数据中心http应用访问根域名")
    tcpdomain = serializers.CharField(allow_null=True, help_text="数据中心tcp应用访问根域名")
    scope = serializers.CharField(allow_null=True, help_text="数据中心范围private|public")
    ssl_ca_cert = serializers.CharField(allow_null=True, help_text="数据中心访问ca证书地址")
    cert_file = serializers.CharField(allow_null=True, help_text="验证文件")
    key_file = serializers.CharField(allow_null=True, help_text="验证的key")
    desc = serializers.CharField(allow_null=True, allow_blank=True, help_text="数据中心描述")
    used_disk = serializers.FloatField(required=False, help_text="使用的存储")
    total_disk = serializers.FloatField(required=False, help_text="全部存储")
    used_memory = serializers.FloatField(required=False, help_text="使用内存")
    total_memory = serializers.FloatField(required=False, help_text="全部内存")
    used_cpu = serializers.FloatField(required=False, help_text="使用cpu")
    total_cpu = serializers.FloatField(required=False, help_text="全部cpu")
    health_status = serializers.CharField(required=False, help_text="集群状态")
    status = serializers.CharField(required=False, help_text="状态")
    manage_node = serializers.IntegerField(required=False, help_text="管理节点总数")
    notready_manage_node = serializers.IntegerField(required=False, help_text="不健康管理节点数")
    compute_node = serializers.IntegerField(required=False, help_text="计算节点总数")
    notready_compute_node = serializers.IntegerField(required=False, help_text="不健康计算节点数")
    etcd_node = serializers.IntegerField(required=False, help_text="etcd节点总数")
    notready_etcd_node = serializers.IntegerField(required=False, help_text="不健康etcd节点数")


class UpdateRegionReqSerializer(serializers.ModelSerializer, RegionReqValidate):
    class Meta:
        model = RegionConfig
        fields = [
            "region_alias", "url", "token", "wsurl", "httpdomain", "tcpdomain", "scope", "ssl_ca_cert", "cert_file", "key_file",
            "status", "desc"
        ]


class RegionInfoRespSerializer(serializers.Serializer):
    region_id = serializers.CharField(max_length=36, required=False, help_text="region id")
    region_name = serializers.CharField(max_length=32, help_text="集群名称")
    region_alias = serializers.CharField(max_length=32, help_text="集群别名")
    url = serializers.CharField(max_length=256, help_text="集群API url")
    wsurl = serializers.CharField(max_length=256, required=False, help_text="集群Websocket url")
    httpdomain = serializers.CharField(max_length=256, required=False, help_text="集群http应用访问根域名")
    tcpdomain = serializers.CharField(max_length=256, required=False, help_text="集群tcp应用访问根域名")
    status = serializers.CharField(max_length=2, help_text="集群状态 0：编辑中 1:启用 2：停用 3:维护中")
    desc = serializers.CharField(max_length=128, allow_blank=True, help_text="集群描述")
    scope = serializers.CharField(max_length=10, default="private", help_text="数据中心范围 private|public")
    ssl_ca_cert = serializers.CharField(max_length=65535, required=False, allow_null=True, help_text="api ca file")
    cert_file = serializers.CharField(max_length=65535, required=False, allow_null=True, help_text="api cert file")
    key_file = serializers.CharField(max_length=65535, required=False, allow_null=True, help_text="api cert key file")


class ListRegionsRespSerializer(serializers.Serializer):
    total = serializers.IntegerField(help_text="总数")
    regions = RegionInfoRespSerializer(many=True)


class UpdateRegionStatusReqSerializer(serializers.Serializer):
    status = serializers.CharField(help_text="需要设置的集群状态, 可选值为: 'ONLINE', 'OFFLINE', 'MAINTAIN'(大小写不敏感)")

    def validate_status(self, status):
        status = status.upper()
        names = RegionStatusEnum.names()
        if status not in names:
            raise serializers.ValidationError("不支持状态: '{}', 仅支持: {}".format(status, ",".join(names)))
        return status
