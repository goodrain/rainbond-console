# -*- coding: utf-8 -*-
# creater by: barnett
from rest_framework import serializers

from www.models.main import ServiceGroup

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


class ServiceBaseInfoSerializer(serializers.Serializer):
    service_id = serializers.CharField(max_length=32, help_text=u"组件id")
    tenant_id = serializers.CharField(max_length=32, help_text=u"租户id")
    service_key = serializers.CharField(max_length=32, help_text=u"组件key")
    service_alias = serializers.CharField(max_length=100, help_text=u"组件别名")
    service_cname = serializers.CharField(max_length=100, default='', help_text=u"组件名")
    service_region = serializers.CharField(max_length=64, help_text=u"组件所属区")
    desc = serializers.CharField(max_length=200, help_text=u"描述")
    category = serializers.CharField(max_length=15, help_text=u"组件分类：application,cache,store")
    version = serializers.CharField(max_length=255, help_text=u"版本")
    update_version = serializers.IntegerField(help_text=u"内部发布次数")
    image = serializers.CharField(max_length=200, help_text=u"镜像")
    cmd = serializers.CharField(max_length=2048, help_text=u"启动参数")
    extend_method = serializers.CharField(max_length=32, help_text=u"组件部署类型,stateless or state")
    min_node = serializers.IntegerField(help_text=u"启动个数")
    min_cpu = serializers.IntegerField(help_text=u"cpu个数")
    min_memory = serializers.IntegerField(help_text=u"内存大小单位（M）")
    code_from = serializers.CharField(max_length=20, help_text=u"代码来源:gitlab,github")
    git_url = serializers.CharField(max_length=2047, help_text=u"code代码仓库")
    create_time = serializers.DateTimeField(help_text=u"创建时间")
    git_project_id = serializers.IntegerField(help_text=u"gitlab 中项目id")
    code_version = serializers.CharField(max_length=100, help_text=u"代码版本")
    service_type = serializers.CharField(max_length=50, help_text=u"组件类型:web,mysql,redis,mongodb,phpadmin")
    creater = serializers.IntegerField(help_text=u"组件创建者")
    language = serializers.CharField(max_length=40, help_text=u"代码语言")
    total_memory = serializers.IntegerField(help_text=u"内存使用M")
    is_service = serializers.BooleanField(help_text=u"是否inner组件")
    # 组件创建类型,cloud、assistant
    service_origin = serializers.CharField(max_length=15, help_text=u"组件创建类型cloud云市组件,assistant云帮组件")
    expired_time = serializers.DateTimeField(help_text=u"过期时间")
    tenant_service_group_id = serializers.IntegerField(help_text=u"组件归属的组件组id")
    open_webhooks = serializers.BooleanField(help_text=u'是否开启自动触发部署功能（兼容老版本组件）')

    service_source = serializers.CharField(max_length=15, help_text=u"组件来源(source_code, market, docker_run, docker_compose)")
    create_status = serializers.CharField(max_length=15, help_text=u"组件创建状态 creating|complete")
    update_time = serializers.DateTimeField(help_text=u"更新时间")
    check_uuid = serializers.CharField(max_length=36, help_text=u"组件检测ID")
    check_event_id = serializers.CharField(max_length=32, help_text=u"组件检测事件ID")
    docker_cmd = serializers.CharField(max_length=1024, help_text=u"镜像创建命令")
    server_type = serializers.CharField(max_length=5, help_text=u"源码仓库类型")
    is_upgrate = serializers.BooleanField(help_text=u'是否可以更新')
    build_upgrade = serializers.BooleanField(help_text=u'组件构建后是否升级')
    oauth_service_id = serializers.IntegerField(help_text=u"拉取源码所用的OAuth服务id")
    # component status
    status = serializers.CharField(max_length=32, help_text=u"组件状态")


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
    order_id = serializers.CharField(max_length=36, help_text=u"订单ID,通过订单ID去市场下载安装的应用元数据")


class ServiceGroupOperationsSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=ACTION_CHOICE, help_text=u"操作类型")
    service_ids = serializers.ListField(help_text=u"组件ID列表，不传值则操作应用下所有组件", required=False, default=None)
