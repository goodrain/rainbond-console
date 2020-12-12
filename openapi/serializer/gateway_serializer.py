# -*- coding: utf-8 -*-
# creater by: barnett
import json

from drf_yasg.utils import swagger_serializer_method
from rest_framework import serializers
from www.models.main import ServiceDomain, ServiceTcpDomain


class HTTPGatewayRuleSerializer(serializers.ModelSerializer):
    rule_extensions = serializers.SerializerMethodField()

    class Meta:
        model = ServiceDomain
        exclude = ["create_time"]

    @swagger_serializer_method(serializer_or_field=serializers.ListField)
    def get_rule_extensions(self, instance):
        try:
            return json.loads(instance.rule_extensions)
        except Exception:
            try:
                return eval(instance.rule_extensions)
            except Exception:
                return []


class TCPGatewayRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceTcpDomain
        exclude = ["create_time"]


class GatewayRuleSerializer(serializers.Serializer):
    http = HTTPGatewayRuleSerializer(many=True, required=False)
    tcp = TCPGatewayRuleSerializer(many=True, required=False)


class EnterpriseHTTPGatewayRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceDomain
        exclude = ["create_time"]

    region_name = serializers.CharField(help_text=u"所属集群ID")
    team_name = serializers.CharField(help_text=u"所属团队唯一名称")
    app_id = serializers.IntegerField(help_text=u"所属应用ID")
    auto_ssl_config = serializers.CharField(max_length=32, help_text=u"自动签发方式")


class HTTPHeaderSerializer(serializers.Serializer):
    key = serializers.CharField(help_text=u"请求头Key")
    value = serializers.CharField(help_text=u"请求头Value")


class HTTPConfiguration(serializers.Serializer):
    proxy_body_size = serializers.IntegerField(help_text=u"请求主体大小", default=0)
    proxy_buffer_numbers = serializers.IntegerField(help_text=u"缓冲区数量", default=4)
    proxy_buffer_size = serializers.IntegerField(help_text=u"缓冲区大小", default=4)
    proxy_buffering = serializers.CharField(help_text=u"是否开启ProxyBuffer", default="off")
    proxy_connect_timeout = serializers.IntegerField(help_text=u"连接超时时间", default=75)
    proxy_read_timeout = serializers.IntegerField(help_text=u"读超时时间", default=60)
    proxy_send_timeout = serializers.IntegerField(help_text=u"发送超时时间", default=60)
    set_headers = HTTPHeaderSerializer(many=True)


class PostHTTPGatewayRuleSerializer(serializers.Serializer):
    service_id = serializers.CharField(help_text=u"应用组件id")
    container_port = serializers.IntegerField(help_text=u"绑定端口")
    certificate_id = serializers.IntegerField(help_text=u"证书id", default=0, required=False)
    domain_name = serializers.CharField(max_length=253, help_text=u"域名")
    domain_cookie = serializers.CharField(help_text=u"域名cookie", required=False)
    domain_header = serializers.CharField(help_text=u"域名header", required=False)
    the_weight = serializers.IntegerField(required=False)
    domain_path = serializers.CharField(default="/", help_text=u"域名路径")
    rule_extensions = serializers.ListField(help_text=u"规则扩展", default=[])
    whether_open = serializers.BooleanField(help_text=u"是否开放", default=False)
    auto_ssl = serializers.BooleanField(help_text=u"是否自动匹配证书，升级为https，如果开启，由外部服务完成升级", default=False)
    auto_ssl_config = serializers.CharField(help_text=u"自动分发证书配置", required=False, default=None)
    configuration = HTTPConfiguration(help_text=u"高级参数配置", required=False, default=None)


class PostTCPGatewayRuleExtensionsSerializer(serializers.Serializer):
    key = serializers.CharField(max_length=32)
    value = serializers.CharField(max_length=32)


class PostTCPGatewayRuleSerializer(serializers.Serializer):
    container_port = serializers.IntegerField(help_text=u"组件端口")
    service_id = serializers.CharField(max_length=32, help_text=u"组件id")
    end_point = serializers.CharField(max_length=32, help_text=u"ip地址:端口")
    rule_extensions = PostTCPGatewayRuleExtensionsSerializer(many=True, required=False, help_text=u"规则扩展")
    default_port = serializers.IntegerField(help_text=u"映射端口")
    default_ip = serializers.CharField(max_length=32, help_text=u"映射id地址")


class PostGatewayRuleSerializer(serializers.Serializer):
    protocol = serializers.CharField(max_length=32, help_text=u"协议")
    tcp = PostTCPGatewayRuleSerializer(required=False)
    http = PostHTTPGatewayRuleSerializer(required=False)


class UpdatePostHTTPGatewayRuleSerializer(serializers.Serializer):
    service_id = serializers.CharField(help_text=u"应用组件id")
    container_port = serializers.IntegerField(help_text=u"绑定端口", required=False)
    certificate_id = serializers.IntegerField(help_text=u"证书id", default=0, required=False)
    domain_name = serializers.CharField(max_length=253, help_text=u"域名", required=False)
    domain_cookie = serializers.CharField(help_text=u"域名cookie", required=False)
    domain_header = serializers.CharField(help_text=u"域名header", required=False)
    the_weight = serializers.IntegerField(required=False)
    domain_path = serializers.CharField(help_text=u"域名路径", required=False)
    rule_extensions = serializers.ListField(help_text=u"规则扩展", required=False)
    whether_open = serializers.BooleanField(help_text=u"是否开放", required=False)
    auto_ssl = serializers.BooleanField(help_text=u"是否自动匹配证书，升级为https，如果开启，由外部服务完成升级", required=False)
    auto_ssl_config = serializers.CharField(help_text=u"自动分发证书配置", required=False, default=None)
