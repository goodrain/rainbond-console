# -*- coding: utf-8 -*-
# creater by: abe
from rest_framework import serializers


class EnterpriseListInfoSerializer(serializers.Serializer):
    enterprise_id = serializers.CharField(max_length=32, help_text=u"企业ID(联合云ID)")
    enterprise_name = serializers.CharField(max_length=64, help_text=u"企业名称")
    enterprise_alias = serializers.CharField(max_length=64, help_text=u"企业别名")
    create_time = serializers.DateTimeField(help_text=u"创建时间")
    region_num = serializers.IntegerField(help_text=u"集群数量")
    user_num = serializers.IntegerField(help_text=u"用户数量")
    team_num = serializers.IntegerField(help_text=u"团队数量")
    is_active = serializers.BooleanField(help_text=u"是否启用")


class ListEntsRespSerializer(serializers.Serializer):
    total = serializers.IntegerField(help_text=u"总数")
    data = EnterpriseListInfoSerializer(many=True)


class UpdEntReqSerializer(serializers.Serializer):
    eid = serializers.CharField(max_length=32, required=True)
    name = serializers.CharField(max_length=64)
    alias = serializers.CharField(max_length=64)


class EnterpriseSourceSerializer(serializers.Serializer):
    enterprise_id = serializers.CharField(max_length=32, help_text=u"企业ID(联合云ID)")
    used_cpu = serializers.FloatField(help_text=u"使用的cpu")
    used_memory = serializers.FloatField(help_text=u"使用的内存")
    used_disk = serializers.FloatField(help_text=u"使用的存储")
