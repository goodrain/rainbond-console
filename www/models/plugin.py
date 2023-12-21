# -*- coding: utf8 -*-
from django.db import models

from .main import BaseModel

data_type = (
    ("组件端口", 'upstream_port'),
    ("组件下游依赖端口", "downstream_port"),
    ("无", "un_define"),
)
injection_method = (("自主发现", 'auto'), ("环境变量", "env"))
plugin_status = (
    ("启用", "active"),
    ("停用", "deactivate"),
)


class TenantPlugin(BaseModel):
    """插件基础信息"""
    class Meta:
        db_table = "tenant_plugin"

    plugin_id = models.CharField(max_length=32, help_text="插件ID")
    tenant_id = models.CharField(max_length=32, help_text="租户ID")
    region = models.CharField(max_length=64, help_text="数据中心")
    create_user = models.IntegerField(help_text="创建插件的用户id")
    desc = models.CharField(max_length=256, default="", help_text="描述")
    plugin_name = models.CharField(max_length=32, help_text="插件名称")
    plugin_alias = models.CharField(max_length=32, help_text="插件别名")
    category = models.CharField(max_length=32, help_text="插件类别")
    build_source = models.CharField(max_length=12, null=False, blank=False, help_text="安装来源 dockerfile|image")
    image = models.CharField(max_length=256, null=True, blank=True, help_text="镜像地址")
    code_repo = models.CharField(max_length=256, null=True, blank=True, help_text="docker构建代码仓库地址")
    create_time = models.DateTimeField(auto_now_add=True, help_text="创建时间")
    origin = models.CharField(max_length=12,
                              default="source_code",
                              null=False,
                              blank=False,
                              help_text="插件来源 source_code|market|local_market")
    origin_share_id = models.CharField(max_length=32, default="new_create", help_text="分享的插件的id,自己创建为new_create")
    username = models.CharField(max_length=32, null=True, blank=True, help_text="镜像仓库或代码仓库用户名")
    password = models.CharField(max_length=32, null=True, blank=True, help_text="镜像仓库或代码仓库秘密")


class PluginBuildVersion(BaseModel):
    """插件构建版本"""
    class Meta:
        db_table = "plugin_build_version"

    plugin_id = models.CharField(max_length=32, help_text="插件ID")
    tenant_id = models.CharField(max_length=32, help_text="租户ID")
    region = models.CharField(max_length=64, help_text="数据中心")
    user_id = models.IntegerField(help_text="构建此版本的用户id")
    update_info = models.CharField(max_length=256, help_text="插件更新说明")
    build_version = models.CharField(max_length=32, help_text="构建版本")
    build_status = models.CharField(max_length=32, help_text="构建状态 unbuild，build_fail，building，build_success")
    plugin_version_status = models.CharField(max_length=32, default="unfixed", help_text="版本状态 unfixed | fixed")
    min_memory = models.IntegerField(help_text="构建内存大小")
    min_cpu = models.IntegerField(help_text="构建cpu大小")
    event_id = models.CharField(max_length=32, default="", blank=True, null=True, help_text="事件ID")
    build_cmd = models.CharField(max_length=128, null=True, blank=True, help_text="构建命令")
    image_tag = models.CharField(max_length=100, null=True, blank=True, default="latest", help_text="镜像版本")
    code_version = models.CharField(max_length=32, null=True, blank=True, default="master", help_text="代码版本")
    build_time = models.DateTimeField(auto_now_add=True, help_text="创建时间")


class PluginConfigGroup(BaseModel):
    """插件配置组"""
    class Meta:
        db_table = "plugin_config_group"

    plugin_id = models.CharField(max_length=32, help_text="插件ID")
    build_version = models.CharField(max_length=32, help_text="构建版本")
    config_name = models.CharField(max_length=32, help_text="配置名称")
    service_meta_type = models.CharField(max_length=32, choices=data_type, help_text="依赖数据类型")
    injection = models.CharField(max_length=32, help_text="注入方式 auto, env")
    create_time = models.DateTimeField(auto_now_add=True, help_text="创建时间")


class PluginConfigItems(BaseModel):
    """插件配置组下的配置项"""
    class Meta:
        db_table = "plugin_config_items"

    plugin_id = models.CharField(max_length=32, help_text="插件ID")
    build_version = models.CharField(max_length=32, help_text="构建版本")
    service_meta_type = models.CharField(max_length=32, choices=data_type, help_text="依赖数据类型")
    attr_name = models.CharField(max_length=64, help_text="属性名")
    attr_type = models.CharField(max_length=16, help_text="属性类型")
    attr_alt_value = models.TextField(help_text="属性值")
    attr_default_value = models.TextField(null=True, blank=True, help_text="默认值")
    is_change = models.BooleanField(default=False, blank=True, help_text="是否可改变")
    create_time = models.DateTimeField(auto_now_add=True, help_text="创建时间")
    attr_info = models.CharField(max_length=32, null=True, blank=True, help_text="配置项说明")
    protocol = models.CharField(max_length=32, null=True, blank=True, default="", help_text="协议")


class TenantServicePluginRelation(BaseModel):
    """组件和插件关系"""
    class Meta:
        db_table = "tenant_service_plugin_relation"

    service_id = models.CharField(max_length=32, help_text="组件ID")
    plugin_id = models.CharField(max_length=32, help_text="插件ID")
    build_version = models.CharField(max_length=32, help_text="构建版本")
    service_meta_type = models.CharField(max_length=32, choices=data_type, help_text="依赖数据类型")
    plugin_status = models.BooleanField(default=True, blank=True, help_text="插件状态")
    create_time = models.DateTimeField(auto_now_add=True, help_text="创建时间")
    min_memory = models.IntegerField(help_text="构建内存大小")
    min_cpu = models.IntegerField(null=True, blank=True, help_text="构建cpu大小")


class TenantServicePluginAttr(BaseModel):
    """旧版组件插件属性"""
    class Meta:
        db_table = "tenant_service_plugin_attr"

    service_id = models.CharField(max_length=32, help_text="组件ID")
    service_alias = models.CharField(max_length=32, help_text="主组件别名")
    dest_service_id = models.CharField(max_length=32, help_text="组件ID")
    dest_service_alias = models.CharField(max_length=32, help_text="组件别名")
    plugin_id = models.CharField(max_length=32, help_text="插件ID")
    service_meta_type = models.CharField(max_length=32, choices=data_type, help_text="依赖数据类型")
    injection = models.CharField(max_length=32, help_text="注入方式 auto, env")
    container_port = models.IntegerField(help_text="依赖端口")
    protocol = models.CharField(max_length=16, help_text="端口协议", default="uneed")
    attr_name = models.CharField(max_length=64, help_text="变量名")
    attr_value = models.CharField(max_length=128, help_text="变量值")
    attr_alt_value = models.CharField(max_length=128, help_text="可选值")
    attr_type = models.CharField(max_length=16, help_text="属性类型")
    attr_default_value = models.CharField(max_length=128, null=True, blank=True, help_text="默认值")
    is_change = models.BooleanField(default=False, blank=True, help_text="是否可改变")
    attr_info = models.CharField(max_length=32, null=True, blank=True, help_text="配置项说明")


class ServicePluginConfigVar(BaseModel):
    """新版组件插件属性"""
    class Meta:
        db_table = "service_plugin_config_var"

    service_id = models.CharField(max_length=32, help_text="组件ID")
    plugin_id = models.CharField(max_length=32, help_text="插件ID")
    build_version = models.CharField(max_length=32, help_text="构建版本")
    service_meta_type = models.CharField(max_length=32, choices=data_type, help_text="依赖数据类型")
    injection = models.CharField(max_length=32, help_text="注入方式 auto, env")
    dest_service_id = models.CharField(max_length=32, default='', help_text="组件ID")
    dest_service_alias = models.CharField(max_length=32, default="", help_text="组件别名")
    container_port = models.IntegerField(help_text="依赖端口")
    attrs = models.TextField(help_text="键值对", default="")
    protocol = models.CharField(max_length=16, help_text="端口协议", default="")
    create_time = models.DateTimeField(auto_now_add=True, help_text="创建时间")


class ConstKey():
    UPSTREAM_PORT = "upstream_port"
    DOWNSTREAM_PORT = "downstream_port"
    UNDEFINE = "un_define"
    AUTO_JNJECTION = "auto_jnjection"
    AUTO_ENV = "auto_env"


class HasNoDownStreamService(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class TenantPluginShareInfo(BaseModel):
    class Meta:
        db_table = "tenant_plugin_share"

    share_id = models.CharField(max_length=32, help_text="分享的插件ID")
    share_version = models.CharField(max_length=32, help_text="分享的构建版本")
    origin_plugin_id = models.CharField(max_length=32, help_text="插件原始的ID")
    tenant_id = models.CharField(max_length=32, help_text="租户ID")
    user_id = models.IntegerField(help_text="分享插件的用户id")
    desc = models.CharField(max_length=256, default="", help_text="描述")
    plugin_name = models.CharField(max_length=32, help_text="插件名称")
    plugin_alias = models.CharField(max_length=32, help_text="插件别名")
    category = models.CharField(max_length=32, help_text="插件类别")
    image = models.CharField(max_length=256, null=True, blank=True, help_text="镜像地址")

    update_info = models.CharField(max_length=256, help_text="分享更新说明")

    min_memory = models.IntegerField(help_text="构建内存大小")
    min_cpu = models.IntegerField(help_text="构建cpu大小")
    build_cmd = models.CharField(max_length=128, null=True, blank=True, help_text="构建命令")
    config = models.CharField(max_length=4096, help_text="插件配置项")
    create_time = models.DateTimeField(auto_now_add=True, help_text="创建时间")
