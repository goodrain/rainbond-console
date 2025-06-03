from rest_framework import serializers

class RegionSerializer(serializers.Serializer):
    """集群序列化器"""
    region_name = serializers.CharField(help_text="集群名称")
    region_alias = serializers.CharField(help_text="集群别名")
    status = serializers.CharField(help_text="集群状态")
    desc = serializers.CharField(help_text="集群描述", required=False, allow_null=True)

class TeamSerializer(serializers.Serializer):
    """团队序列化器"""
    team_alias = serializers.CharField(help_text="团队别名")
    create_time = serializers.DateTimeField(help_text="创建时间")
    owner_name = serializers.CharField(help_text="创建者名称", required=False)
    region_list = serializers.ListField(help_text="区域列表", child=serializers.DictField(), required=False)


class AppSerializer(serializers.Serializer):
    """应用序列化器"""
    group_id = serializers.IntegerField(help_text="应用ID", source="ID")
    group_name = serializers.CharField(help_text="应用名称")
    group_alias = serializers.CharField(help_text="应用别名", required=False)
    description = serializers.CharField(help_text="应用描述", required=False, allow_null=True)
    update_time = serializers.DateTimeField(help_text="更新时间")
    create_time = serializers.DateTimeField(help_text="创建时间")

class CreateAppRequestSerializer(serializers.Serializer):
    """创建应用请求参数序列化器"""
    app_name = serializers.CharField(help_text="应用名", required=False, allow_blank=True)

class CreateAppResponseSerializer(serializers.Serializer):
    """创建应用响应参数序列化器"""
    bean = AppSerializer(help_text="应用信息")
    code = serializers.IntegerField(help_text="状态码", default=200)
    msg = serializers.CharField(help_text="状态信息", default="success")
    msg_show = serializers.CharField(help_text="显示信息", default="创建成功")


class ComponentBaseSerializer(serializers.Serializer):
    """组件基础序列化器"""
    service_id = serializers.CharField(help_text="组件ID")
    service_cname = serializers.CharField(help_text="组件名称")
    update_time = serializers.DateTimeField(help_text="更新时间")
    status = serializers.CharField(help_text="组件状态")


class ComponentStatusSerializer(serializers.Serializer):
    """组件状态序列化器"""
    service_id = serializers.CharField(help_text="组件ID")
    service_cname = serializers.CharField(help_text="组件名称")
    update_time = serializers.DateTimeField(help_text="更新时间")
    min_memory = serializers.IntegerField(help_text="最小内存")
    status_cn = serializers.CharField(help_text="状态中文")


class ComponentLogSerializer(serializers.Serializer):
    """组件日志序列化器"""
    message = serializers.CharField(help_text="日志内容")

    class Meta:
        fields = "__all__"

    def to_representation(self, instance):
        """自定义日志输出格式"""
        if isinstance(instance, str):
            return {"message": instance}
        return super().to_representation(instance)


class CreateComponentRequestSerializer(serializers.Serializer):
    """创建组件请求参数序列化器"""
    service_cname = serializers.CharField(help_text="组件名称", max_length=100)
    repo_url = serializers.CharField(help_text="代码仓库地址")
    branch = serializers.CharField(help_text="代码分支", default="master")
    username = serializers.CharField(help_text="仓库用户名", required=False, allow_blank=True)
    password = serializers.CharField(help_text="仓库密码", required=False, allow_blank=True)


class AddPortRequestSerializer(serializers.Serializer):
    """添加端口请求参数序列化器"""
    port = serializers.IntegerField(help_text="端口号", required=True)
    protocol = serializers.ChoiceField(help_text="协议类型", choices=["http", "tcp", "udp"], required=True)
    is_outer_service = serializers.BooleanField(help_text="是否开启对外服务", required=False, default=False)


class PortBaseSerializer(serializers.Serializer):
    """端口基本信息序列化器"""
    port = serializers.IntegerField(help_text="容器端口", source="container_port")
    protocol = serializers.CharField(help_text="协议类型")
    is_outer_service = serializers.BooleanField(help_text="是否开启对外服务")
    is_inner_service = serializers.BooleanField(help_text="是否开启对内服务")


class ComponentPortSerializer(serializers.Serializer):
    """组件端口信息序列化器"""
    container_port = serializers.IntegerField(help_text="容器端口")
    protocol = serializers.CharField(help_text="协议类型")
    is_outer_service = serializers.BooleanField(help_text="是否开启对外服务")
    is_inner_service = serializers.BooleanField(help_text="是否开启对内服务")
    access_urls = serializers.ListField(help_text="访问地址列表", child=serializers.CharField(), required=False, allow_null=True)


class ComponentEnvSerializer(serializers.Serializer):
    """组件环境变量序列化器"""
    attr_name = serializers.CharField(help_text="变量名")
    attr_value = serializers.CharField(help_text="变量值")
    name = serializers.CharField(help_text="名称")
    scope = serializers.CharField(help_text="范围")
    is_change = serializers.BooleanField(help_text="是否可改变")


class ComponentVolumeSerializer(serializers.Serializer):
    """组件存储信息序列化器"""
    volume_name = serializers.CharField(help_text="存储名称")
    volume_path = serializers.CharField(help_text="挂载路径")
    volume_capacity = serializers.IntegerField(help_text="存储容量")


class ComponentDetailSerializer(serializers.Serializer):
    """组件详情序列化器"""
    service_id = serializers.CharField(help_text="组件ID")
    service_cname = serializers.CharField(help_text="组件名称")
    service_alias = serializers.CharField(help_text="组件别名")
    update_time = serializers.DateTimeField(help_text="更新时间")
    min_memory = serializers.IntegerField(help_text="内存大小")
    min_cpu = serializers.IntegerField(help_text="CPU大小")
    status_cn = serializers.CharField(help_text="运行状态")
    
    # 扩展信息
    ports = ComponentPortSerializer(many=True, help_text="端口列表")
    envs = ComponentEnvSerializer(many=True, help_text="环境变量列表")
    volumes = ComponentVolumeSerializer(many=True, help_text="存储列表")


class ComponentHistoryLogSerializer(serializers.Serializer):
    """组件历史日志序列化器"""
    logs = serializers.ListField(help_text="日志列表", child=serializers.CharField())
    lines = serializers.IntegerField(help_text="日志行数", default=100)
