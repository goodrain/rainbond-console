# -*- coding: utf-8 -*-
# creater by: barnett
import re

from openapi.serializer.utils import DateCharField
from rest_framework import serializers, validators
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

THIRD_COMPONENT_SOURCE_CHOICE = (
    ("static", ("static")),
    ("api", ("api")),
)

NAME_FORMAT = re.compile("^[a-zA-Z]")
NAME_LETTER = re.compile("^(?!\d+$)[\da-zA-Z_]+$")
FIRST_LETTER = re.compile("^[a-zA-Z]")


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
            "git_full_name", "update_time", "create_time", "expired_time"
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


class MarketInstallSerializer(serializers.Serializer):
    enterprise_id = serializers.CharField(max_length=32, help_text=u"企业ID(联合云ID)")
    team_id = serializers.CharField(max_length=32, help_text=u"团队id")
    note = serializers.CharField(max_length=1024, help_text=u"备注")
    ID = serializers.IntegerField(help_text=u"应用id")
    region_name = serializers.CharField(max_length=64, help_text=u"数据中心名")
    service_list = ServiceBaseInfoSerializer(many=True)

    def to_internal_value(self, data):
        return data


class InstallSerializer(serializers.Serializer):
    market_url = serializers.CharField(max_length=255, help_text=u"应用商店路由")
    market_domain = serializers.CharField(max_length=64, help_text=u"应用商店domain")
    market_type = serializers.CharField(max_length=64, help_text=u"应用商店类型")
    market_access_key = serializers.CharField(max_length=64, allow_null=True, help_text=u"应用商店令牌")
    app_model_id = serializers.CharField(max_length=64, help_text=u"应用id")
    app_model_version = serializers.CharField(max_length=64, help_text=u"应用版本")


class ListUpgradeSerializer(serializers.Serializer):
    market_name = serializers.CharField(max_length=64, help_text=u"应用商店名称")
    app_model_id = serializers.CharField(max_length=32, help_text=u"应用模型id")
    app_model_name = serializers.CharField(max_length=64, help_text=u"应用模型名称")
    current_version = serializers.CharField(max_length=64, help_text=u"当前版本")
    enterprise_id = serializers.CharField(max_length=64, help_text=u"企业id")
    can_upgrade = serializers.BooleanField(help_text=u"可升级")
    upgrade_versions = serializers.ListField(help_text=u"可升级的版本列表")
    source = serializers.CharField(max_length=32, help_text=u"应用模型来源")


class UpgradeBaseSerializer(serializers.Serializer):
    market_name = serializers.CharField(max_length=64, allow_null=True, help_text=u"应用商店名称")
    app_model_id = serializers.CharField(max_length=32, help_text=u"应用模型id")
    app_model_version = serializers.CharField(max_length=64, help_text=u"当前版本")


class UpgradeSerializer(serializers.Serializer):
    update_versions = UpgradeBaseSerializer(many=True)


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
    create_time = DateCharField(max_length=64, help_text=u"创建时间")
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


class MonitorDataSerializers(serializers.Serializer):
    value = serializers.ListField()

    def to_internal_value(self, data):
        return data


class ComponentMonitorBaseSerializers(serializers.Serializer):
    resultType = serializers.CharField(max_length=64, required=False, help_text=u"返回类型")
    result = MonitorDataSerializers(many=True)

    def to_internal_value(self, data):
        return data


class ComponentMonitorItemsSerializers(serializers.Serializer):
    data = ComponentMonitorBaseSerializers(required=False)
    monitor_item = serializers.CharField(max_length=32, help_text=u"监控项")
    status = serializers.CharField(max_length=32, required=False, help_text=u"监控状态")


class ComponentMonitorSerializers(serializers.Serializer):
    monitors = ComponentMonitorItemsSerializers(many=True, required=False, allow_null=True)
    service_id = serializers.CharField(max_length=32, help_text=u"组件id")
    service_cname = serializers.CharField(max_length=64, help_text=u"组件名")
    service_alias = serializers.CharField(max_length=64, help_text=u"组件昵称")


def name_validator(value):
    if not NAME_LETTER.search(value) or not FIRST_LETTER.search(value):
        raise validators.ValidationError(code=400, detail=u"变量名不合法， 请输入以字母开头且为数字、大小写字母、'_'、'-'的组合")


class ComponentEnvsBaseSerializers(serializers.Serializer):
    note = serializers.CharField(max_length=100, required=False, help_text=u"备注")
    name = serializers.CharField(max_length=100, validators=[name_validator], help_text=u"环境变量名")
    value = serializers.CharField(max_length=1024, help_text=u"环境变量值")
    is_change = serializers.BooleanField(default=True, help_text=u"是否可改变")
    scope = serializers.CharField(max_length=32, default=u"inner", help_text=u"范围")


class ComponentEnvsSerializers(serializers.Serializer):
    envs = ComponentEnvsBaseSerializers(many=True)


class CreateThirdComponentSerializer(serializers.Serializer):
    endpoints_type = serializers.ChoiceField(choices=THIRD_COMPONENT_SOURCE_CHOICE, help_text=u"Endpoint 注册方式")
    endpoints = serializers.ListField(help_text=u"Endpoint 列表")
    component_name = serializers.CharField(max_length=64, help_text=u"组件名称")


class CreateThirdComponentResponseSerializer(ServiceBaseInfoSerializer):
    api_service_key = serializers.CharField(help_text=u"API 授权Key, 类型为api时有效")
    url = serializers.CharField(help_text=u"API地址, 类型为api时有效")
