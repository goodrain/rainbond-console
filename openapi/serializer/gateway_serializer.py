# -*- coding: utf-8 -*-
# creater by: barnett
from rest_framework import serializers
from www.models.main import ServiceDomain


class HTTPGatewayRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceDomain
        fields = "__all__"


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
