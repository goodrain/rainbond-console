# -*- coding: utf-8 -*-
# creater by: barnett
from rest_framework import serializers

from www.models.main import ServiceDomain


class HTTPGatewayRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceDomain
        fields = "__all__"


class EnterpriseHTTPGatewayRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceDomain
        fields = "__all__"

    region_name = serializers.CharField(help_text=u"所属集群ID")
    team_name = serializers.CharField(help_text=u"所属团队唯一名称")
    app_id = serializers.IntegerField(help_text=u"所属应用ID")
    auto_ssl_config = serializers.CharField(max_length=32, help_text=u"自动签发方式")


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
    auto_ssl_config = serializers.BooleanField(help_text=u"自动分发证书配置", required=False)


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
    auto_ssl_config = serializers.BooleanField(help_text=u"自动分发证书配置", required=False)
