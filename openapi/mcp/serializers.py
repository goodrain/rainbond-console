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
    status = serializers.CharField(help_text="状态")
    container_memory = serializers.IntegerField(help_text="容器内存")
    container_cpu = serializers.IntegerField(help_text="容器CPU")
    cur_status = serializers.CharField(help_text="当前状态")
    status_cn = serializers.CharField(help_text="状态中文")
    start_time = serializers.DateTimeField(help_text="启动时间", required=False)
    pod_list = serializers.ListField(help_text="Pod列表", child=serializers.DictField(), required=False)

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
    is_deploy = serializers.BooleanField(help_text="是否部署", default=True)
    build_version = serializers.CharField(help_text="构建版本", required=False, allow_blank=True)


class AddPortRequestSerializer(serializers.Serializer):
    """添加端口请求参数序列化器"""
    port = serializers.IntegerField(help_text="端口号", required=True)
    protocol = serializers.ChoiceField(help_text="协议类型", choices=["http", "tcp", "udp"], required=True)
    is_outer_service = serializers.BooleanField(help_text="是否开启对外服务", required=False, default=False)


class PortBaseSerializer(serializers.Serializer):
    """端口基本信息序列化器"""
    container_port = serializers.IntegerField(help_text="容器端口")
    protocol = serializers.CharField(help_text="协议类型")
    is_outer_service = serializers.BooleanField(help_text="是否开启对外服务")
    k8s_service_name = serializers.CharField(help_text="k8s服务名称")
    is_inner_service = serializers.BooleanField(help_text="是否开启对内服务")
