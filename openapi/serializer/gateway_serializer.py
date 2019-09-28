# -*- coding: utf-8 -*-
# creater by: barnett
from rest_framework import serializers
from www.models.main import ServiceDomain


class HTTPGatewayRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceDomain
        fields = "__all__"


class PostHTTPGatewayRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceDomain
        exclude = []
