# -*- coding: utf-8 -*-
# creater by: barnett
from rest_framework import serializers
from www.models.main import TenantServiceInfo, ServiceGroup


class AppBaseInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceGroup
        fields = "__all__"


class AppPostInfoSerializer(serializers.Serializer):
    team_alias = serializers.CharField(max_length=16, help_text=u"所属团队别名")
    app_name = serializers.CharField(max_length=64, help_text=u"应用名称")
    region_name = serializers.CharField(max_length=64, help_text=u"数据中心唯一名称")


class ServiceBaseInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantServiceInfo
        exclude = ["ID", "service_port", "is_web_service", "setting", "env", "inner_port", "volume_mount_path",
                   "host_path", "deploy_version", "is_code_upload", "protocol", "namespace", "volume_type",
                   "port_type", "service_name", "secret"]


class AppInfoSerializer(AppBaseInfoSerializer):
    enterprise_id = serializers.CharField(max_length=32, help_text=u"企业ID(联合云ID)")
    service_list = ServiceBaseInfoSerializer(many=True, required=False)
    status = serializers.CharField(max_length=32, help_text=u"应用状态")


class MarketInstallSerializer(serializers.Serializer):
    order_id = serializers.CharField(max_length=36, help_text=u"订单ID,通过订单ID去市场下载安装的应用元数据")
    app_id = serializers.IntegerField(help_text=u"安装应用ID")
