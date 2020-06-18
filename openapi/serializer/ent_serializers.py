# -*- coding: utf-8 -*-
# creater by: abe
from rest_framework import serializers

from openapi.serializer.utils import DateCharField


class EnterpriseInfoSerializer(serializers.Serializer):
    enterprise_id = serializers.CharField(max_length=32, help_text=u"企业ID(联合云ID)")
    enterprise_name = serializers.CharField(max_length=64, help_text=u"企业名称")
    enterprise_alias = serializers.CharField(max_length=64, help_text=u"企业别名")
    create_time = DateCharField(max_length=64, help_text=u"创建时间")


class ListEntsRespSerializer(serializers.Serializer):
    total = serializers.IntegerField(help_text=u"总数")
    ents = EnterpriseInfoSerializer(many=True)


class EnterpriseSourceSerializer(serializers.Serializer):
    enterprise_id = serializers.CharField(max_length=32, help_text=u"企业ID(联合云ID)")
    used_cpu = serializers.FloatField(help_text=u"使用的cpu")
    used_memory = serializers.FloatField(help_text=u"使用的内存")
    used_disk = serializers.FloatField(help_text=u"使用的存储")


class UpdEntReqSerializer(serializers.Serializer):
    eid = serializers.CharField(max_length=32, required=True)
    name = serializers.CharField(max_length=64)
    alias = serializers.CharField(max_length=64)
