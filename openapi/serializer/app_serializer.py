# -*- coding: utf-8 -*-
# creater by: barnett
from rest_framework import serializers

from www.models.main import ServiceGroup, TenantServiceInfo

ACTION_CHOICE = (
    ("stop", ("stop")),
    ("start", ("start")),
    ("upgrade", ("upgrade")),
    ("deploy", ("deploy")),
)

APP_STATUS_CHOICE = (
    ("running", ("running")),
    ("part_running", ("part_running")),
    ("closed", ("closed")),
)


class AppBaseInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceGroup
        fields = "__all__"


class AppPostInfoSerializer(serializers.Serializer):
    app_name = serializers.CharField(max_length=128, help_text=u"应用名称")
    app_note = serializers.CharField(max_length=2048, allow_blank=True, default="", help_text=u"应用备注")


class ServiceBaseInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantServiceInfo
        exclude = [
            "ID", "service_port", "is_web_service", "setting", "env", "inner_port", "volume_mount_path", "host_path",
            "deploy_version", "is_code_upload", "protocol", "namespace", "volume_type", "port_type", "service_name", "secret",
            "git_full_name"
        ]

    # component status
    status = serializers.CharField(max_length=32, allow_blank=True, default="", help_text=u"组件状态")


class AppInfoSerializer(AppBaseInfoSerializer):
    enterprise_id = serializers.CharField(max_length=32, help_text=u"企业ID(联合云ID)")
    service_count = serializers.IntegerField(help_text=u"组件数量")
    running_service_count = serializers.IntegerField(help_text=u"正在运行的组件数量")
    used_momory = serializers.IntegerField(help_text=u"分配的内存")
    used_cpu = serializers.IntegerField(help_text=u"分配的cpu")
    app_id = serializers.IntegerField(help_text=u"应用id")
    team_name = serializers.CharField(max_length=32, help_text=u"团队名")
    status = serializers.ChoiceField(choices=APP_STATUS_CHOICE, help_text=u"应用状态")


class InstallSerializer(serializers.Serializer):
    market_url = serializers.CharField(max_length=255, help_text=u"应用商店路由")
    market_domain = serializers.CharField(max_length=64, help_text=u"应用商店domain")
    market_type = serializers.CharField(max_length=64, help_text=u"应用商店类型")
    market_access_key = serializers.CharField(max_length=64, help_text=u"应用商店令牌")
    app_model_id = serializers.CharField(max_length=64, help_text=u"应用id")
    app_model_version = serializers.CharField(max_length=64, help_text=u"应用版本")
    app_id = serializers.CharField(max_length=64, help_text=u"应用组id")


class ServiceGroupOperationsSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=ACTION_CHOICE, help_text=u"操作类型")
    service_ids = serializers.ListField(help_text=u"组件ID列表，不传值则操作应用下所有组件", required=False, default=None)


class AppServiceEventsSerializer(serializers.Serializer):
    EventID = serializers.CharField(max_length=64, help_text=u"事件id")
    UserName = serializers.CharField(max_length=64, help_text=u"操作人")
    EndTime = serializers.CharField(max_length=64, help_text=u"结束事件")
    Target = serializers.CharField(max_length=64, help_text=u"操作目标类型")
    OptType = serializers.CharField(max_length=64, help_text=u"事件类型")
    TargetID = serializers.CharField(max_length=64, help_text=u"操作目标id")
    ServiceID = serializers.CharField(max_length=64, help_text=u"服务id")
    Status = serializers.CharField(max_length=64, help_text=u"状态")
    RequestBody = serializers.CharField(max_length=64, help_text=u"请求参数")
    create_time = serializers.CharField(max_length=64, help_text=u"创建时间")
    FinalStatus = serializers.CharField(max_length=64, help_text=u"最终状态")
    StartTime = serializers.CharField(max_length=64, help_text=u"开始时间")
    SynType = serializers.CharField(max_length=64, help_text=u"同步状态")
    Message = serializers.CharField(max_length=64, help_text=u"日志")
    TenantID = serializers.CharField(max_length=64, help_text=u"团队id")
    ID = serializers.CharField(max_length=64, help_text=u"记录id")


class ListServiceEventsResponse(serializers.Serializer):
    page = serializers.IntegerField(help_text=u"当前页数")
    page_size = serializers.IntegerField(help_text=u"每页数量")
    total = serializers.IntegerField(help_text=u"数据总数")
    events = AppServiceEventsSerializer(many=True)


def new_memory_validator(value):
    if not isinstance(value, int):
        raise serializers.ValidationError('请输入int类型数据')
    if value % 64 == 1:
        raise serializers.ValidationError('参数不正确，请输入64的倍数')
    if value > 65536 or value < 64:
        raise serializers.ValidationError('参数超出范围，请选择64~65536之间的整数值', value)


def new_node_validator(value):
    if not isinstance(value, int):
        raise serializers.ValidationError('请输入int类型数据')
    if value > 100 or value < 1:
        raise serializers.ValidationError('参数超出范围，请选择1~100之间的整数值', value)


class AppServiceTelescopicVerticalSerializer(serializers.Serializer):
    new_memory = serializers.IntegerField(help_text=u"组件内存", allow_null=False, validators=[new_memory_validator])


class AppServiceTelescopicHorizontalSerializer(serializers.Serializer):
    new_node = serializers.IntegerField(help_text=u"组件节点", allow_null=False, validators=[new_node_validator])


class TeamAppsCloseSerializers(serializers.Serializer):
    service_ids = serializers.ListField(required=False)
