# -*- coding: utf-8 -*-
# creater by: barnett
from rest_framework import serializers
from www.models.main import TenantServiceInfo, ServiceGroup


ACTION_CHOICE = (
    ("stop", ("stop")),
    ("start", ("start")),
    ("upgrade", ("upgrade")),
    ("deploy", ("deploy")),
)


class AppBaseInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceGroup
        fields = "__all__"


class AppPostInfoSerializer(serializers.Serializer):
    team_alias = serializers.CharField(max_length=16, help_text=u"所属团队别名")
    app_name = serializers.CharField(max_length=128, help_text=u"应用名称")
    region_name = serializers.CharField(max_length=64, help_text=u"数据中心唯一名称")
    group_note = serializers.CharField(max_length=2048, allow_blank=True, default="", help_text=u"应用备注")


class ServiceBaseInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantServiceInfo
        exclude = ["ID", "service_port", "is_web_service", "setting", "env", "inner_port", "volume_mount_path",
                   "host_path", "deploy_version", "is_code_upload", "protocol", "namespace", "volume_type",
                   "port_type", "service_name", "secret"]


class AppInfoSerializer(AppBaseInfoSerializer):
    enterprise_id = serializers.CharField(max_length=32, help_text=u"企业ID(联合云ID)")
    service_count = serializers.IntegerField(help_text=u"组件数量")
    running_service_count = serializers.IntegerField(help_text=u"正在运行的组件数量")
    used_momory = serializers.IntegerField(help_text=u"分配的内存")
    used_cpu = serializers.IntegerField(help_text=u"分配的cpu")
    app_id = serializers.IntegerField(help_text=u"应用id")
    team_name = serializers.CharField(max_length=32, help_text=u"团队名")
    status = serializers.CharField(max_length=32, help_text=u"应用状态")


class MarketInstallSerializer(serializers.Serializer):
    order_id = serializers.CharField(max_length=36, help_text=u"订单ID,通过订单ID去市场下载安装的应用元数据")
    app_id = serializers.IntegerField(help_text=u"安装应用ID")


class ServiceGroupOperationsSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=ACTION_CHOICE, help_text=u"操作类型")


class APPHttpDomainSerializer(serializers.Serializer):
    app_id = serializers.IntegerField(help_text=u"应用id")
    service_key = serializers.CharField(help_text=u"应用组件id")
    container_port = serializers.IntegerField(help_text=u"绑定端口")
    certificate_id = serializers.CharField(help_text=u"证书id", allow_null=True,
                                           allow_blank=True, default="")
    domain_name = serializers.CharField(max_length=253, help_text=u"域名")
    domain_cookie = serializers.CharField(help_text=u"域名cookie", required=False)
    domain_header = serializers.CharField(help_text=u"域名header", required=False)
    the_weight = serializers.CharField(required=False)
    domain_path = serializers.CharField(default="/", help_text=u"域名路径")
    rule_extensions = serializers.ListField(help_text=u"规则扩展", default=[])
    whether_open = serializers.BooleanField(help_text=u"是否开放", default=False)


class APPHttpDomainRspSerializer(serializers.Serializer):
    protocol = serializers.CharField(max_length=64, help_text=u"http or https")
    region_id = serializers.CharField(max_length=64, help_text=u"数据中心id")
    http_rule_id = serializers.CharField(max_length=64, help_text=u"http规则id")
    rule_extensions = serializers.ListField(help_text=u"规则参数")
    service_name = serializers.CharField(max_length=64, help_text=u"组件名称")
    domain_heander = serializers.CharField(max_length=64, allow_blank=True, allow_null=True, help_text=u"header")
    domain_name = serializers.CharField(max_length=64, help_text=u"域名")
    the_weight = serializers.IntegerField()
    service_alias = serializers.CharField(max_length=64, help_text=u"组件昵称")
    domain_type = serializers.CharField(max_length=64, help_text=u"类型")
    create_time = serializers.DateTimeField()
    domain_path = serializers.CharField(help_text=u"域名路径")
    tenant_id = serializers.CharField(help_text=u"团队id")
    certificate_id = serializers.CharField(help_text=u"证书id", allow_null=True, allow_blank=True)
    service_id = serializers.CharField(help_text=u"组件id")
    container_port = serializers.IntegerField(help_text=u"绑定端口")
    type = serializers.IntegerField()
    domain_cookie = serializers.CharField(help_text=u"域名cookie")
