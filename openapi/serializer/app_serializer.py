# -*- coding: utf-8 -*-
# creater by: barnett
import re

from openapi.serializer.utils import DateCharField
from rest_framework import serializers, validators
from www.models.main import ServiceGroup, TenantServiceInfo, TenantServicesPort

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

COMPONENT_BUILD_TYPE = (
    ("source_code", ("source_code")),
    ("docker_image", ("docker_image")),
    ("market", ("market")),
)

COMPONENT_PORT_PROTOCOL = (
    ("http", ("http")),
    ("tcp", ("tcp")),
    ("udp", ("udp")),
    ("mysql", ("msyql")),
    ("grpc", ("grpc")),
)

COMPONENT_PORT_ACTION = (("open_outer", ("open_outer")), ("only_open_outer", ("only_open_outer")),
                         ("close_outer", ("close_outer")), ("open_inner", ("open_inner")), ("close_inner", ("close_inner")),
                         ("change_protocol", ("change_protocol")), ("change_port_alias", ("change_port_alias")))

COMPONENT_SOURCE_TYPE = (
    ("svn", ("svn")),
    ("git", ("git")),
    ("oss", ("oss")),
)

NAME_FORMAT = re.compile("^[a-zA-Z]")
NAME_LETTER = re.compile("^(?!\d+$)[\da-zA-Z_]+$")
FIRST_LETTER = re.compile("^[a-zA-Z]")


class AppBaseInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceGroup
        fields = "__all__"


class AppPostInfoSerializer(serializers.Serializer):
    app_name = serializers.CharField(max_length=128, help_text="应用名称")
    app_note = serializers.CharField(max_length=2048, allow_blank=True, default="", help_text="应用备注")


class ServiceBaseInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantServiceInfo
        exclude = [
            "ID", "service_port", "is_web_service", "setting", "env", "inner_port", "volume_mount_path", "host_path",
            "deploy_version", "is_code_upload", "protocol", "namespace", "volume_type", "port_type", "service_name", "secret",
            "git_full_name", "update_time", "create_time", "expired_time"
        ]

    # component status
    status = serializers.CharField(max_length=32, allow_blank=True, default="", help_text="组件状态")
    access_infos = serializers.ListField(required=False, allow_empty=True, default=[], help_text="组件访问地址")


class ServicePortSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantServicesPort
        exclude = ["ID", "tenant_id", "service_id", "name"]


class AppInfoSerializer(AppBaseInfoSerializer):
    enterprise_id = serializers.CharField(max_length=32, help_text="企业ID(联合云ID)")
    service_count = serializers.IntegerField(help_text="组件数量")
    running_service_count = serializers.IntegerField(help_text="正在运行的组件数量")
    used_momory = serializers.IntegerField(help_text="分配的内存")
    used_cpu = serializers.IntegerField(help_text="分配的cpu")
    app_id = serializers.IntegerField(help_text="应用id")
    team_name = serializers.CharField(max_length=32, help_text="团队名")
    status = serializers.ChoiceField(choices=APP_STATUS_CHOICE, help_text="应用状态")


class MarketInstallSerializer(serializers.Serializer):
    enterprise_id = serializers.CharField(max_length=32, help_text="企业ID(联合云ID)")
    team_id = serializers.CharField(max_length=32, help_text="团队id")
    note = serializers.CharField(max_length=1024, help_text="备注")
    ID = serializers.IntegerField(help_text="应用id")
    region_name = serializers.CharField(max_length=64, help_text="数据中心名")
    service_list = ServiceBaseInfoSerializer(many=True)

    def to_internal_value(self, data):
        return data


class InstallSerializer(serializers.Serializer):
    market_url = serializers.CharField(max_length=255, help_text="应用商店路由")
    market_domain = serializers.CharField(max_length=64, help_text="应用商店domain")
    market_type = serializers.CharField(max_length=64, help_text="应用商店类型")
    market_access_key = serializers.CharField(max_length=64, allow_null=True, help_text="应用商店令牌")
    app_model_id = serializers.CharField(max_length=64, help_text="应用id")
    app_model_version = serializers.CharField(max_length=64, help_text="应用版本")


class ListUpgradeSerializer(serializers.Serializer):
    market_name = serializers.CharField(max_length=64, help_text="应用商店名称")
    app_model_id = serializers.CharField(max_length=32, help_text="应用模型id")
    app_model_name = serializers.CharField(max_length=64, help_text="应用模型名称")
    current_version = serializers.CharField(max_length=64, help_text="当前版本")
    enterprise_id = serializers.CharField(max_length=64, help_text="企业id")
    can_upgrade = serializers.BooleanField(help_text="可升级")
    upgrade_versions = serializers.ListField(help_text="可升级的版本列表")
    source = serializers.CharField(max_length=32, help_text="应用模型来源")


class UpgradeBaseSerializer(serializers.Serializer):
    market_name = serializers.CharField(max_length=64, allow_null=True, help_text="应用商店名称")
    app_model_id = serializers.CharField(max_length=32, help_text="应用模型id")
    app_model_version = serializers.CharField(max_length=64, help_text="当前版本")


class UpgradeSerializer(serializers.Serializer):
    update_versions = UpgradeBaseSerializer(many=True)


class ServiceGroupOperationsSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=ACTION_CHOICE, help_text="操作类型")
    service_ids = serializers.ListField(help_text="组件ID列表，不传值则操作应用下所有组件", required=False, default=None)


class AppServiceEventsSerializer(serializers.Serializer):
    EventID = serializers.CharField(max_length=64, help_text="事件id")
    UserName = serializers.CharField(max_length=64, help_text="操作人")
    EndTime = serializers.CharField(max_length=64, help_text="结束事件")
    Target = serializers.CharField(max_length=64, help_text="操作目标类型")
    OptType = serializers.CharField(max_length=64, help_text="事件类型")
    TargetID = serializers.CharField(max_length=64, help_text="操作目标id")
    ServiceID = serializers.CharField(max_length=64, help_text="服务id")
    Status = serializers.CharField(max_length=64, help_text="状态")
    RequestBody = serializers.CharField(max_length=64, help_text="请求参数")
    create_time = DateCharField(max_length=64, help_text="创建时间")
    FinalStatus = serializers.CharField(max_length=64, help_text="最终状态")
    StartTime = serializers.CharField(max_length=64, help_text="开始时间")
    SynType = serializers.CharField(max_length=64, help_text="同步状态")
    Message = serializers.CharField(max_length=64, help_text="日志")
    TenantID = serializers.CharField(max_length=64, help_text="团队id")
    ID = serializers.CharField(max_length=64, help_text="记录id")


class ListServiceEventsResponse(serializers.Serializer):
    page = serializers.IntegerField(help_text="当前页数")
    page_size = serializers.IntegerField(help_text="每页数量")
    total = serializers.IntegerField(help_text="数据总数")
    events = AppServiceEventsSerializer(many=True)


def new_memory_validator(value):
    if not isinstance(value, int):
        raise serializers.ValidationError('请输入int类型数据')
    if value % 64 == 1:
        raise serializers.ValidationError('参数不正确，请输入64的倍数')
    if value > 65536 or value < 64:
        raise serializers.ValidationError('参数超出范围，请选择64~65536之间的整数值', value)


def new_cpu_validator(value):
    if not isinstance(value, int):
        raise serializers.ValidationError('请输入int类型数据')
    if value < 0:
        raise serializers.ValidationError('请输入正整数数据')


def new_node_validator(value):
    if not isinstance(value, int):
        raise serializers.ValidationError('请输入int类型数据')
    if value > 100 or value < 1:
        raise serializers.ValidationError('参数超出范围，请选择1~100之间的整数值', value)


class AppServiceTelescopicVerticalSerializer(serializers.Serializer):
    new_memory = serializers.IntegerField(help_text="组件内存", allow_null=False, validators=[new_memory_validator])
    new_gpu = serializers.IntegerField(help_text="组件gpu显存申请", allow_null=True, validators=[new_cpu_validator])
    new_cpu = serializers.IntegerField(help_text="组件cpu额度申请", allow_null=True, validators=[new_cpu_validator])


class AppServiceTelescopicHorizontalSerializer(serializers.Serializer):
    new_node = serializers.IntegerField(help_text="组件节点", allow_null=False, validators=[new_node_validator])


class TeamAppsCloseSerializers(serializers.Serializer):
    service_ids = serializers.ListField(required=False)


class MonitorDataSerializers(serializers.Serializer):
    value = serializers.ListField()

    def to_internal_value(self, data):
        return data


class ComponentMonitorBaseSerializers(serializers.Serializer):
    resultType = serializers.CharField(max_length=64, required=False, help_text="返回类型")
    result = MonitorDataSerializers(many=True)

    def to_internal_value(self, data):
        return data


class ComponentMonitorItemsSerializers(serializers.Serializer):
    data = ComponentMonitorBaseSerializers(required=False)
    monitor_item = serializers.CharField(max_length=32, help_text="监控项")
    status = serializers.CharField(max_length=32, required=False, help_text="监控状态")


class ComponentMonitorSerializers(serializers.Serializer):
    monitors = ComponentMonitorItemsSerializers(many=True, required=False, allow_null=True)
    service_id = serializers.CharField(max_length=32, help_text="组件id")
    service_cname = serializers.CharField(max_length=64, help_text="组件名")
    service_alias = serializers.CharField(max_length=64, help_text="组件昵称")


def name_validator(value):
    if not NAME_LETTER.search(value) or not FIRST_LETTER.search(value):
        raise validators.ValidationError(code=400, detail="变量名不合法， 请输入以字母开头且为数字、大小写字母、'_'、'-'的组合")


class ComponentEnvsBaseSerializers(serializers.Serializer):
    note = serializers.CharField(max_length=100, required=False, help_text="备注")
    name = serializers.CharField(max_length=100, validators=[name_validator], help_text="环境变量名")
    value = serializers.CharField(max_length=1024, help_text="环境变量值")
    is_change = serializers.BooleanField(default=True, help_text="是否可改变")
    scope = serializers.CharField(max_length=32, default="inner", help_text="范围")


class ComponentEnvsSerializers(serializers.Serializer):
    envs = ComponentEnvsBaseSerializers(many=True)


class CreateThirdComponentSerializer(serializers.Serializer):
    endpoints_type = serializers.ChoiceField(choices=THIRD_COMPONENT_SOURCE_CHOICE, help_text="Endpoint 注册方式")
    endpoints = serializers.ListField(help_text="Endpoint 列表")
    component_name = serializers.CharField(max_length=64, help_text="组件名称")


class CreateThirdComponentResponseSerializer(ServiceBaseInfoSerializer):
    api_service_key = serializers.CharField(help_text="API 授权Key, 类型为api时有效")
    url = serializers.CharField(help_text="API地址, 类型为api时有效")


class ComponentEventSerializers(serializers.Serializer):
    event_id = serializers.CharField(max_length=64, help_text="事件ID")


class ComponentUpdatePortReqSerializers(serializers.Serializer):
    action = serializers.ChoiceField(choices=COMPONENT_PORT_ACTION, required=True, allow_null=False, help_text="端口操作类型")
    port_alias = serializers.CharField(max_length=255, required=False, allow_null=True, help_text="端口别名")
    protocol = serializers.ChoiceField(
        choices=COMPONENT_PORT_PROTOCOL, default='http', required=False, allow_null=True, help_text="端口协议")
    k8s_service_name = serializers.CharField(max_length=255, required=False, allow_null=True, help_text="内部域名")


class ComponentPortReqSerializers(serializers.Serializer):
    port = serializers.IntegerField(help_text="组件端口", required=True, allow_null=False)
    protocol = serializers.ChoiceField(
        choices=COMPONENT_PORT_PROTOCOL, default='http', required=False, allow_null=True, help_text="端口协议")
    port_alias = serializers.CharField(max_length=255, required=False, allow_null=True, help_text="端口别名")
    is_inner_service = serializers.BooleanField(help_text="开启对内端口")


class ComponentBuildReqSerializers(serializers.Serializer):
    build_type = serializers.ChoiceField(choices=COMPONENT_BUILD_TYPE, required=False, allow_null=True, help_text="组件构建源类型")
    server_type = serializers.ChoiceField(choices=COMPONENT_SOURCE_TYPE, required=False, allow_null=True, help_text="源码来源类型")
    branch = serializers.CharField(max_length=255, required=False, allow_null=True, default="master", help_text="代码分支，tag信息")
    repo_url = serializers.CharField(max_length=1024, required=False, allow_null=True, help_text="来源仓库服务地址，包括代码仓库、镜像仓库、OSS地址")
    username = serializers.CharField(max_length=255, required=False, allow_null=True, help_text="来源仓库服务账号")
    password = serializers.CharField(max_length=255, required=False, allow_null=True, help_text="来源仓库服务密码")


class DeployAppSerializer(serializers.Serializer):
    app_id = serializers.IntegerField(help_text="应用id", required=False)
    deploy_type = serializers.CharField(max_length=255, required=True, help_text="部署类型，支持2种:docker-compose, ram")
    action = serializers.CharField(max_length=255, required=True, help_text="操作类型，如:deploy, update")
    group_key = serializers.CharField(max_length=128, required=False, help_text="生成模型的key")
    group_version = serializers.CharField(max_length=128, required=False, help_text="生成模型的version")


class ChangeDeploySourceSerializer(serializers.Serializer):
    image = serializers.CharField(max_length=512, required=True, help_text="镜像地址")


class ServiceVolumeSerializer(serializers.Serializer):
    volume_name = serializers.CharField(max_length=512, required=True, help_text="名称")
    volume_path = serializers.CharField(max_length=512, required=True, help_text="挂载路径")
    volume_capacity = serializers.IntegerField(required=True, help_text="存储配额(GB)")
    volume_type = serializers.CharField(max_length=512, required=True, help_text="储存类型")
