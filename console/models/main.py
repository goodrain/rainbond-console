# -*- coding: utf-8 -*-
import json
import logging
from datetime import datetime
from enum import Enum, IntEnum

from django.db import models
from django.db.models.fields import (AutoField, BooleanField, CharField, DateTimeField, DecimalField, IntegerField)
from django.db.models.fields.files import FileField
from goodrain_web import settings
from www.models.main import TenantServiceInfo
from www.utils.crypt import make_uuid

logger = logging.getLogger("default")

app_scope = (("enterprise", "企业"), ("team", "团队"), ("goodrain", "好雨云市"))
plugin_scope = (("enterprise", "企业"), ("team", "团队"), ("goodrain", "好雨云市"))
user_identity = (("管理员", "admin"), )
enterprise_identity = (("admin", "管理员"), ("viewer", "观察者"))


class BaseModel(models.Model):
    class Meta:
        abstract = True

    ID = models.AutoField(primary_key=True, max_length=10)

    def to_dict(self):
        opts = self._meta
        data = {}
        for f in opts.concrete_fields:
            value = f.value_from_object(self)
            if isinstance(value, datetime):
                value = value.strftime('%Y-%m-%d %H:%M:%S')
            elif isinstance(f, FileField):
                value = value.url if value else None
            data[f.attname] = value
        return data

    def to_json(self):
        opts = self._meta
        data = []
        for f in opts.concrete_fields:
            parameter = {}
            parameter["table"] = opts.db_table
            parameter["name"] = f.name
            parameter["kind"] = self.parse_kind(f)
            parameter["default"] = self.parse_default(f.default)
            parameter["desc"] = f.help_text
            data.append(parameter)
        return data

    def parse_default(self, a):
        # if type(a) == NOT_PROVIDED:
        return ""

    def parse_kind(self, a):
        # print(a.name, type(a))
        if type(a) == CharField:
            return "string"
        if type(a) == AutoField:
            return "int"
        if type(a) == BooleanField:
            return "boolean"
        if type(a) == DecimalField:
            return "decimal"
        if type(a) == DateTimeField:
            return "datetime"
        if type(a) == IntegerField:
            return "int"
        return "string"


class ConsoleSysConfig(BaseModel):
    class Meta:
        db_table = 'console_sys_config'

    key = models.CharField(max_length=32, help_text="key")
    type = models.CharField(max_length=32, help_text="类型")
    value = models.CharField(max_length=4096, null=True, blank=True, help_text="value")
    desc = models.CharField(max_length=100, null=True, blank=True, default="", help_text="描述")
    enable = models.BooleanField(default=True, help_text="是否生效")
    create_time = models.DateTimeField(auto_now_add=True, blank=True, help_text="创建时间")
    enterprise_id = models.CharField(max_length=32, help_text="eid", default="")


class RainbondCenterApp(BaseModel):
    """云市应用包(组)"""

    class Meta:
        db_table = "rainbond_center_app"
        unique_together = ('app_id', 'enterprise_id')

    app_id = models.CharField(max_length=32, help_text="应用包")
    app_name = models.CharField(max_length=64, help_text="应用包名")
    create_user = models.IntegerField(null=True, blank=True, help_text="创建人id")
    create_team = models.CharField(max_length=64, null=True, blank=True, help_text="应用所属团队,可以和创建人id不统一")
    pic = models.CharField(max_length=200, null=True, blank=True, help_text="应用头像信息")
    source = models.CharField(max_length=15, default="", null=True, blank=True, help_text="应用来源(本地创建，好雨云市)")
    dev_status = models.CharField(max_length=32, default="", null=True, blank=True, help_text="开发状态")
    scope = models.CharField(max_length=50, choices=app_scope, help_text="可用范围")
    describe = models.CharField(max_length=400, null=True, blank=True, help_text="云市应用描述信息")
    is_ingerit = models.BooleanField(default=True, help_text="是否可被继承")
    create_time = models.DateTimeField(auto_now_add=True, null=True, blank=True, help_text="创建时间")
    update_time = models.DateTimeField(auto_now=True, blank=True, null=True, help_text="更新时间")
    enterprise_id = models.CharField(max_length=32, default="public", help_text="企业ID")
    install_number = models.IntegerField(default=0, help_text='安装次数')
    is_official = models.BooleanField(default=False, help_text='是否官方认证')
    details = models.TextField(null=True, blank=True, help_text="应用详情")


class RainbondCenterAppVersion(BaseModel):
    """云市应用版本"""

    class Meta:
        db_table = "rainbond_center_app_version"

    enterprise_id = models.CharField(max_length=32, default="public", help_text="企业ID")
    app_id = models.CharField(max_length=32, help_text="应用id")
    version = models.CharField(max_length=32, help_text="版本")
    version_alias = models.CharField(max_length=64, default="NA", help_text="别名")
    app_version_info = models.CharField(max_length=255, help_text="版本信息")
    record_id = models.IntegerField(help_text="分享流程id，控制一个分享流程产出一个实体")
    share_user = models.IntegerField(help_text="分享人id")
    share_team = models.CharField(max_length=64, help_text="来源应用所属团队")
    group_id = models.IntegerField(default=0, help_text="应用归属的服务组id")
    dev_status = models.CharField(max_length=32, default="", null=True, blank=True, help_text="开发状态")
    source = models.CharField(max_length=15, default="", null=True, blank=True, help_text="应用来源(本地创建，好雨云市)")
    scope = models.CharField(max_length=15, default="", null=True, blank=True, help_text="应用分享范围")
    app_template = models.TextField(help_text="全量应用与插件配置信息")
    template_version = models.CharField(max_length=10, default="v2", help_text="模板版本")
    create_time = models.DateTimeField(auto_now_add=True, null=True, blank=True, help_text="创建时间")
    update_time = models.DateTimeField(auto_now_add=True, blank=True, null=True, help_text="更新时间")
    upgrade_time = models.CharField(max_length=30, default="", help_text="升级时间")
    install_number = models.IntegerField(default=0, help_text='安装次数')
    is_official = models.BooleanField(default=False, help_text='是否官方认证')
    is_ingerit = models.BooleanField(default=True, help_text="是否可被继承")
    is_complete = models.BooleanField(default=False, help_text="代码或镜像是否同步完成")
    template_type = models.CharField(max_length=32, null=True, default=None, help_text="模板类型（ram、oam）")
    release_user_id = models.IntegerField(null=True, default=None, help_text="版本release操作人id")
    # region_name is not null,This means that the version can only be installed on that cluster.
    region_name = models.CharField(max_length=64, null=True, default=None, help_text="数据中心名称")
    is_plugin = models.BooleanField(default=False, help_text='应用版本是否作为插件')


class RainbondCenterAppInherit(BaseModel):
    """云市应用组继承关系"""

    class Meta:
        db_table = "rainbond_center_app_inherit"

    group_key = models.CharField(max_length=32, unique=True, help_text="当前应用")
    version = models.CharField(max_length=20, unique=True, help_text="当前应用版本号")
    derived_group_key = models.CharField(max_length=32, unique=True, help_text="继承哪个云市应用")

    def __unicode__(self):
        return self.to_dict()


class RainbondCenterAppTagsRelation(BaseModel):
    """云市应用标签关系"""

    class Meta:
        db_table = "rainbond_center_app_tag_relation"

    enterprise_id = models.CharField(max_length=36, default="public", help_text="企业id")
    app_id = models.CharField(max_length=32, help_text="当前应用")
    tag_id = models.IntegerField(help_text="标签id")


class RainbondCenterAppTag(BaseModel):
    """云市应用标签"""

    class Meta:
        db_table = "rainbond_center_app_tag"

    name = models.CharField(max_length=32, unique=True, help_text="标签名称")
    enterprise_id = models.CharField(max_length=32, help_text="企业id")
    is_deleted = models.BooleanField(default=False, help_text="是否删除")


class RainbondCenterPlugin(BaseModel):
    """云市插件"""

    class Meta:
        db_table = "rainbond_center_plugin"

    plugin_key = models.CharField(max_length=32, help_text="插件分享key")
    plugin_name = models.CharField(max_length=64, help_text="插件名称")
    plugin_id = models.CharField(max_length=32, null=True, help_text="插件id")
    category = models.CharField(max_length=32, help_text="插件类别")
    record_id = models.IntegerField(help_text="分享流程id")
    version = models.CharField(max_length=20, help_text="版本")
    build_version = models.CharField(max_length=32, help_text="构建版本")
    pic = models.CharField(max_length=100, null=True, blank=True, help_text="插件头像信息")
    scope = models.CharField(max_length=10, choices=plugin_scope, help_text="可用范围")
    source = models.CharField(max_length=15, default="", null=True, blank=True, help_text="应用来源(本地创建，好雨云市)")
    share_user = models.IntegerField(help_text="分享人id")
    share_team = models.CharField(max_length=32, help_text="来源应用所属团队")
    desc = models.CharField(max_length=400, null=True, blank=True, help_text="插件描述信息")
    plugin_template = models.TextField(help_text="全量插件信息")
    is_complete = models.BooleanField(default=False, help_text="代码或镜像是否同步完成")
    create_time = models.DateTimeField(auto_now_add=True, null=True, blank=True, help_text="创建时间")
    update_time = models.DateTimeField(auto_now=True, blank=True, null=True, help_text="更新时间")
    enterprise_id = models.CharField(max_length=32, default='public', help_text="企业id")
    details = models.TextField(null=True, blank=True, help_text="插件详细信息")

    def __unicode__(self):
        return self.to_dict()


class ServiceShareRecord(BaseModel):
    """服务分享记录"""

    class Meta:
        db_table = "service_share_record"

    group_share_id = models.CharField(max_length=32, unique=True, help_text="发布应用组或插件的唯一Key")
    group_id = models.CharField(max_length=32, help_text="分享应用组id或者单独插件ID")
    team_name = models.CharField(max_length=64, help_text="应用所在团队唯一名称")
    event_id = models.CharField(max_length=32, null=True, blank=True, help_text="介质同步事件ID,弃用，使用表service_share_record_event")
    share_version = models.CharField(max_length=15, null=True, blank=True, help_text="应用组发布版本")
    share_version_alias = models.CharField(max_length=64, null=True, blank=True, help_text="应用组发布版本别名")
    share_app_version_info = models.CharField(max_length=255, help_text="应用组发布版本描述")
    is_success = models.BooleanField(default=False, help_text="发布是否成功")
    step = models.IntegerField(default=0, help_text="当前发布进度")
    # 1 发布中 2 取消发布 3 发布完成
    status = models.IntegerField(default=0, help_text="当前发布状态 1, 2, 3")
    app_id = models.CharField(max_length=64, null=True, blank=True, help_text="应用id")
    scope = models.CharField(max_length=64, null=True, blank=True, help_text="分享范围")
    share_app_market_name = models.CharField(max_length=64, null=True, blank=True, help_text="分享应用商店标识")
    share_store_name = models.CharField(max_length=64, null=True, blank=True, help_text="分享应用商店名称，用于记录发布范围指定的应用商店名")
    share_app_model_name = models.CharField(max_length=64, null=True, blank=True, help_text="分享应用模板名称")
    create_time = models.DateTimeField(auto_now_add=True, help_text="创建时间")
    update_time = models.DateTimeField(auto_now_add=True, help_text="更新时间")

    def __unicode__(self):
        return self.to_dict()


class ServiceShareRecordEvent(BaseModel):
    """服务分享订单关联发布事件"""

    class Meta:
        db_table = "service_share_record_event"

    record_id = models.IntegerField(help_text="关联的订单ID")
    region_share_id = models.CharField(max_length=36, help_text="应用数据中心分享反馈ID")
    team_name = models.CharField(max_length=64, help_text="应用所在团队唯一名称")
    service_key = models.CharField(max_length=32, help_text="对应应用key")
    service_id = models.CharField(max_length=32, help_text="对应应用ID")
    service_alias = models.CharField(max_length=64, help_text="对应应用别名")
    service_name = models.CharField(max_length=64, help_text="对应应用名称")
    team_id = models.CharField(max_length=32, help_text="对应所在团队ID")
    event_id = models.CharField(max_length=32, default="", help_text="介质同步事件ID")
    event_status = models.CharField(max_length=32, default="not_start", help_text="事件状态")
    create_time = models.DateTimeField(auto_now_add=True, help_text="创建时间")
    update_time = models.DateTimeField(auto_now_add=True, help_text="更新时间")

    def __unicode__(self):
        return self.to_dict()


class PluginShareRecordEvent(BaseModel):
    """插件分享订单关联发布事件"""

    class Meta:
        db_table = "plugin_share_record_event"

    record_id = models.IntegerField(help_text="关联的记录ID")
    region_share_id = models.CharField(max_length=36, help_text="应用数据中心分享反馈ID")
    team_id = models.CharField(max_length=32, help_text="对应所在团队ID")
    team_name = models.CharField(max_length=64, help_text="应用所在团队唯一名称")
    plugin_id = models.CharField(max_length=32, help_text="对应插件ID")
    plugin_name = models.CharField(max_length=64, help_text="对应插件名称")
    event_id = models.CharField(max_length=32, default="", help_text="介质同步事件ID")
    event_status = models.CharField(max_length=32, default="not_start", help_text="事件状态")
    create_time = models.DateTimeField(auto_now_add=True, help_text="创建时间")
    update_time = models.DateTimeField(auto_now=True, help_text="更新时间")

    def __unicode__(self):
        return self.to_dict()


class ComposeGroup(BaseModel):
    """compose组"""

    class Meta:
        db_table = "compose_group"

    group_id = models.IntegerField(help_text="compose组关联的组id")
    team_id = models.CharField(max_length=32, help_text="团队 id")
    region = models.CharField(max_length=64, help_text="服务所属数据中心")
    compose_content = models.TextField(null=True, blank=True, help_text="compose文件内容")
    compose_id = models.CharField(max_length=32, unique=True, help_text="compose id")
    create_status = models.CharField(
        max_length=15, null=True, blank=True, help_text="compose组创建状态 creating|checking|checked|complete")
    check_uuid = models.CharField(max_length=36, blank=True, null=True, default="", help_text="compose检测ID")
    check_event_id = models.CharField(max_length=32, blank=True, null=True, default="", help_text="compose检测事件ID")
    hub_user = models.CharField(max_length=256, blank=True, null=True, default="", help_text="镜像仓库用户名称")
    hub_pass = models.CharField(max_length=256, blank=True, null=True, default="", help_text="镜像仓库用户密码，服务创建后给服务赋值")

    create_time = models.DateTimeField(auto_now_add=True, null=True, blank=True, help_text="创建时间")


class ComposeServiceRelation(BaseModel):
    """compose组和服务的关系"""

    class Meta:
        db_table = "compose_service_relation"

    team_id = models.CharField(max_length=32, help_text="团队 id")
    service_id = models.CharField(max_length=32, help_text="服务 id")
    compose_id = models.CharField(max_length=32, help_text="compose id")
    create_time = models.DateTimeField(auto_now_add=True, null=True, blank=True, help_text="创建时间")


class ServiceSourceInfo(BaseModel):
    """服务源信息"""

    class Meta:
        db_table = "service_source"

    service = models.OneToOneField(
        TenantServiceInfo,
        to_field='service_id',
        on_delete=models.CASCADE,
        db_constraint=False,
        related_name="service_source_info",
        help_text="服务信息",
    )
    team_id = models.CharField(max_length=32, help_text="服务所在团队ID")
    user_name = models.CharField(max_length=255, null=True, blank=True, help_text="用户名")
    password = models.CharField(max_length=255, null=True, blank=True, help_text="密码")
    group_key = models.CharField(max_length=32, null=True, blank=True, help_text="group of service from market")
    version = models.CharField(max_length=32, null=True, blank=True, help_text="version of service from market")
    service_share_uuid = models.CharField(
        max_length=65, null=True, blank=True, help_text="unique identification of service from market")
    extend_info = models.CharField(max_length=1024, null=True, blank=True, default="", help_text="扩展信息")
    create_time = models.DateTimeField(auto_now_add=True, null=True, blank=True, help_text="创建时间")

    def is_install_from_cloud(self):
        if self.extend_info:
            extend_info = json.loads(self.extend_info)
            if extend_info and extend_info.get("install_from_cloud", False):
                return True
        return False

    def get_market_name(self):
        if self.extend_info:
            extend_info = json.loads(self.extend_info)
            return extend_info.get("market_name")

    def get_template_update_time(self):
        if self.extend_info:
            extend_info = json.loads(self.extend_info)
            update_time = extend_info.get("update_time", None)
            if update_time:
                return datetime.strptime(update_time, '%Y-%m-%d %H:%M:%S')


class TeamGitlabInfo(BaseModel):
    class Meta:
        db_table = "team_gitlab_info"

    team_id = models.CharField(max_length=32, help_text="团队ID")
    repo_name = models.CharField(max_length=100, help_text="代码仓库名称")
    respo_url = models.CharField(max_length=200, null=True, blank=True, help_text="code代码仓库")
    git_project_id = models.IntegerField(help_text="gitlab 中项目id", default=0)
    code_version = models.CharField(max_length=100, null=True, blank=True, help_text="代码版本")
    create_time = models.DateTimeField(auto_now_add=True, blank=True, help_text="创建时间")


class ServiceRecycleBin(BaseModel):
    class Meta:
        db_table = 'tenant_service_recycle_bin'
        unique_together = ('tenant_id', 'service_alias')

    service_id = models.CharField(max_length=32, unique=True, help_text="服务id")
    tenant_id = models.CharField(max_length=32, help_text="租户id")
    service_key = models.CharField(max_length=32, help_text="服务key")
    service_alias = models.CharField(max_length=100, help_text="服务别名")
    service_cname = models.CharField(max_length=100, default='', help_text="服务名")
    service_region = models.CharField(max_length=64, help_text="服务所属区")
    desc = models.CharField(max_length=200, null=True, blank=True, help_text="描述")
    category = models.CharField(max_length=15, help_text="服务分类：application,cache,store")
    service_port = models.IntegerField(help_text="服务端口", default=0)
    is_web_service = models.BooleanField(default=False, blank=True, help_text="是否web服务")
    version = models.CharField(max_length=20, help_text="版本")
    update_version = models.IntegerField(default=1, help_text="内部发布次数")
    image = models.CharField(max_length=200, help_text="镜像")
    cmd = models.CharField(max_length=2048, null=True, blank=True, help_text="启动参数")
    setting = models.CharField(max_length=100, null=True, blank=True, help_text="设置项")
    extend_method = models.CharField(max_length=15, default='stateless', help_text="伸缩方式")
    env = models.CharField(max_length=200, null=True, blank=True, help_text="环境变量")
    min_node = models.IntegerField(help_text="启动个数", default=1)
    min_cpu = models.IntegerField(help_text="cpu个数", default=500)
    min_memory = models.IntegerField(help_text="内存大小单位（M）", default=256)
    inner_port = models.IntegerField(help_text="内部端口", default=0)
    volume_mount_path = models.CharField(max_length=200, null=True, blank=True, help_text="mount目录")
    host_path = models.CharField(max_length=300, null=True, blank=True, help_text="mount目录")
    deploy_version = models.CharField(max_length=20, null=True, blank=True, help_text="部署版本")
    code_from = models.CharField(max_length=20, null=True, blank=True, help_text="代码来源:gitlab,github")
    git_url = models.CharField(max_length=200, null=True, blank=True, help_text="code代码仓库")
    create_time = models.DateTimeField(auto_now_add=True, blank=True, help_text="创建时间")
    git_project_id = models.IntegerField(help_text="gitlab 中项目id", default=0)
    is_code_upload = models.BooleanField(default=False, blank=True, help_text="是否上传代码")
    code_version = models.CharField(max_length=100, null=True, blank=True, help_text="代码版本")
    service_type = models.CharField(max_length=50, null=True, blank=True, help_text="服务类型:web,mysql,redis,mongodb,phpadmin")
    creater = models.IntegerField(help_text="服务创建者", default=0)
    language = models.CharField(max_length=40, null=True, blank=True, help_text="代码语言")
    protocol = models.CharField(max_length=15, default='', help_text="服务协议：http,stream")
    total_memory = models.IntegerField(help_text="内存使用M", default=0)
    is_service = models.BooleanField(default=False, blank=True, help_text="是否inner服务")
    namespace = models.CharField(max_length=100, default='', help_text="镜像发布云帮的区间")

    volume_type = models.CharField(max_length=64, default='shared', help_text="共享类型shared、exclusive")
    port_type = models.CharField(max_length=15, default='multi_outer', help_text="端口类型，one_outer;dif_protocol;multi_outer")
    # 服务创建类型,cloud、assistant
    service_origin = models.CharField(max_length=15, default='assistant', help_text="服务创建类型cloud云市服务,assistant云帮服务")
    expired_time = models.DateTimeField(null=True, help_text="过期时间")
    tenant_service_group_id = models.IntegerField(default=0, help_text="应用归属的服务组id")
    service_source = models.CharField(
        max_length=15, default="", null=True, blank=True, help_text="应用来源(source_code, market, docker_run, docker_compose)")
    create_status = models.CharField(max_length=15, null=True, blank=True, help_text="应用创建状态 creating|complete")
    update_time = models.DateTimeField(auto_now_add=True, blank=True, help_text="更新时间")
    check_uuid = models.CharField(max_length=36, blank=True, null=True, default="", help_text="应用检测ID")
    check_event_id = models.CharField(max_length=32, blank=True, null=True, default="", help_text="应用检测事件ID")
    docker_cmd = models.CharField(max_length=1024, null=True, blank=True, help_text="镜像创建命令")


class ServiceRelationRecycleBin(BaseModel):
    class Meta:
        db_table = 'tenant_service_relation_recycle_bin'
        unique_together = ('service_id', 'dep_service_id')

    tenant_id = models.CharField(max_length=32, help_text="租户id")
    service_id = models.CharField(max_length=32, help_text="服务id")
    dep_service_id = models.CharField(max_length=32, help_text="依赖服务id")
    dep_service_type = models.CharField(max_length=50, null=True, blank=True, help_text="服务类型:web,mysql,redis,mongodb,phpadmin")
    dep_order = models.IntegerField(help_text="依赖顺序")


class EnterpriseUserPerm(BaseModel):
    """用户在企业的权限"""

    class Meta:
        db_table = 'enterprise_user_perm'

    user_id = models.IntegerField(help_text="用户id")
    enterprise_id = models.CharField(max_length=32, help_text="企业id")
    identity = models.CharField(max_length=15, choices=user_identity, help_text="用户在企业的身份")
    token = models.CharField(max_length=64, help_text="API通信密钥", unique=True)


class UserAccessKey(BaseModel):
    """企业通信凭证"""

    class Meta:
        db_table = 'user_access_key'
        unique_together = (('note', 'user_id'), )

    note = models.CharField(max_length=32, help_text="凭证标识")
    user_id = models.IntegerField(help_text="用户id")
    access_key = models.CharField(max_length=64, unique=True, help_text="凭证")
    expire_time = models.IntegerField(null=True, help_text="过期时间")


class TenantUserRole(BaseModel):
    """用户在一个团队中的角色"""

    class Meta:
        db_table = 'tenant_user_role'
        unique_together = (('role_name', 'tenant_id'), )

    role_name = models.CharField(max_length=32, help_text='角色名称')
    tenant_id = models.IntegerField(null=True, blank=True, help_text='团队id')
    is_default = models.BooleanField(default=False)

    def __unicode__(self):
        return self.to_dict()


class TenantUserPermission(BaseModel):
    """权限及对应的操作"""

    class Meta:
        db_table = 'tenant_user_permission'
        unique_together = (('codename', 'per_info'), )

    codename = models.CharField(max_length=32, help_text='权限名称')
    per_info = models.CharField(max_length=32, help_text='权限对应的操作信息')
    is_select = models.BooleanField(default=True, help_text='自定义权限时是否可以做选项')
    group = models.IntegerField(help_text='这个权限属于哪个权限组', null=True, blank=True)
    per_explanation = models.CharField(max_length=132, null=True, blank=True, help_text='这一条权限操作的具体说明')

    def __unicode__(self):
        return self.to_dict()


class TenantUserRolePermission(BaseModel):
    """团队中一个角色与权限的关系对应表"""

    class Meta:
        db_table = 'tenant_user_role_permission'

    role_id = models.IntegerField(help_text='团队中的一个角色的id')
    per_id = models.IntegerField(help_text='一个权限操作的id')

    def __unicode__(self):
        return self.to_dict()


class PermGroup(BaseModel):
    """权限组，用于给权限分组分类"""

    class Meta:
        db_table = 'tenant_permission_group'

    group_name = models.CharField(max_length=64, help_text='组名')

    def __unicode__(self):
        return self.to_dict()


class ServiceRelPerms(BaseModel):
    """一个用户在一个应用下的权限"""

    class Meta:
        db_table = 'service_user_perms'

    user_id = models.IntegerField(help_text="用户id")
    service_id = models.IntegerField(help_text="服务id")
    perm_id = models.IntegerField(help_text='权限id')

    def __unicode__(self):
        return self.to_dict()


class UserRole(BaseModel):
    class Meta:
        db_table = 'user_role'

    user_id = models.CharField(max_length=32, help_text='用户id')
    role_id = models.CharField(max_length=32, help_text='角色id')


class PermsInfo(BaseModel):
    class Meta:
        db_table = 'perms_info'

    name = models.CharField(max_length=32, unique=True, help_text='权限名称')
    desc = models.CharField(max_length=32, help_text='权限描述')
    code = models.IntegerField(unique=True, help_text='权限编码')
    group = models.CharField(max_length=32, help_text='权限类型')
    kind = models.CharField(max_length=32, help_text='权限所属')


class RolePerms(BaseModel):
    class Meta:
        db_table = 'role_perms'

    role_id = models.IntegerField(help_text="角色id")
    perm_code = models.IntegerField(help_text='权限编码')


class RoleInfo(BaseModel):
    class Meta:
        db_table = 'role_info'

    name = models.CharField(max_length=32, help_text='角色名称')
    kind_id = models.CharField(max_length=64, help_text='角色所属范围id')
    kind = models.CharField(max_length=32, help_text='角色所属')


class AppExportRecord(BaseModel):
    """应用导出"""

    class Meta:
        db_table = 'app_export_record'

    group_key = models.CharField(max_length=32, help_text="导出应用的key")
    version = models.CharField(max_length=20, help_text="导出应用的版本")
    format = models.CharField(max_length=15, help_text="导出应用的格式")
    event_id = models.CharField(max_length=32, null=True, blank=True, help_text="事件id")
    status = models.CharField(max_length=10, null=True, blank=True, help_text="事件请求状态")
    file_path = models.CharField(max_length=256, null=True, blank=True, help_text="文件地址")
    create_time = models.DateTimeField(auto_now_add=True, null=True, blank=True, help_text="创建时间")
    update_time = models.DateTimeField(auto_now_add=True, null=True, blank=True, help_text="更新时间")
    enterprise_id = models.CharField(max_length=32, help_text="企业ID")
    region_name = models.CharField(max_length=32, null=True, help_text="执行导出的集群ID")


class UserMessage(BaseModel):
    """用户站内信"""

    class Meta:
        db_table = 'user_message'

    message_id = models.CharField(max_length=32, help_text="消息ID")
    receiver_id = models.IntegerField(help_text="接受消息用户ID")
    content = models.CharField(max_length=1000, help_text="消息内容")
    is_read = models.BooleanField(default=False, help_text="是否已读")
    create_time = models.DateTimeField(auto_now=True, null=True, blank=True, help_text="创建时间")
    update_time = models.DateTimeField(auto_now=True, null=True, blank=True, help_text="更新时间")
    msg_type = models.CharField(max_length=32, help_text="消息类型")
    announcement_id = models.CharField(max_length=32, null=True, blank=True, help_text="公告ID")
    title = models.CharField(max_length=64, help_text="消息标题", default="title")
    level = models.CharField(max_length=32, default="low", help_text="通知的等级")


class AppImportRecord(BaseModel):
    class Meta:
        db_table = 'app_import_record'

    event_id = models.CharField(max_length=32, null=True, blank=True, help_text="事件id")
    status = models.CharField(max_length=15, null=True, blank=True, help_text="导入状态")
    scope = models.CharField(max_length=10, null=True, blank=True, default="", help_text="导入范围")
    format = models.CharField(max_length=15, null=True, blank=True, default="", help_text="类型")
    source_dir = models.CharField(max_length=256, null=True, blank=True, default="", help_text="目录地址")
    create_time = models.DateTimeField(auto_now_add=True, null=True, blank=True, help_text="创建时间")
    update_time = models.DateTimeField(auto_now_add=True, null=True, blank=True, help_text="更新时间")
    team_name = models.CharField(max_length=64, null=True, blank=True, help_text="正在导入的团队名称")
    region = models.CharField(max_length=64, null=True, blank=True, help_text="数据中心")
    user_name = models.CharField(max_length=64, null=True, blank=True, help_text="操作人")
    enterprise_id = models.CharField(max_length=64, null=True, blank=True, help_text="企业id")


class PackageUploadRecord(BaseModel):
    class Meta:
        db_table = 'package_upload_record'

    event_id = models.CharField(max_length=32, null=True, blank=True, help_text="事件id")
    status = models.CharField(max_length=15, null=True, blank=True, help_text="导入状态")
    format = models.CharField(max_length=15, null=True, blank=True, default="", help_text="类型")
    source_dir = models.CharField(max_length=256, null=True, blank=True, default="", help_text="目录地址")
    team_name = models.CharField(max_length=32, null=True, blank=True, help_text="正在导入的团队名称")
    region = models.CharField(max_length=32, null=True, blank=True, help_text="数据中心")
    component_id = models.CharField(max_length=32, null=True, blank=True, help_text="组件id")
    create_time = models.DateTimeField(auto_now_add=True, null=True, blank=True, help_text="创建时间")
    update_time = models.DateTimeField(auto_now_add=True, null=True, blank=True, help_text="更新时间")


class GroupAppBackupRecord(BaseModel):
    class Meta:
        db_table = 'groupapp_backup'

    group_id = models.IntegerField(help_text="组ID")
    event_id = models.CharField(max_length=32, null=True, blank=True, help_text="事件id")
    group_uuid = models.CharField(max_length=32, null=True, blank=True, help_text="group UUID")
    version = models.CharField(max_length=32, null=True, blank=True, help_text="备份版本")
    backup_id = models.CharField(max_length=36, null=True, blank=True, help_text="备份ID")
    team_id = models.CharField(max_length=32, null=True, blank=True, help_text="团队ID")
    user = models.CharField(max_length=64, null=True, blank=True, help_text="备份人")
    region = models.CharField(max_length=64, null=True, blank=True, help_text="数据中心")
    status = models.CharField(max_length=15, null=True, blank=True, help_text="时间请求状态")
    note = models.CharField(max_length=255, null=True, blank=True, default="", help_text="备份说明")
    mode = models.CharField(max_length=15, null=True, blank=True, default="", help_text="备份类型")
    source_dir = models.CharField(max_length=256, null=True, blank=True, default="", help_text="目录地址")
    backup_size = models.BigIntegerField(help_text="备份文件大小")
    create_time = models.DateTimeField(auto_now_add=True, null=True, blank=True, help_text="创建时间")
    total_memory = models.IntegerField(help_text="备份应用的总内存")
    backup_server_info = models.CharField(max_length=400, null=True, blank=True, default="", help_text="备份服务信息")
    source_type = models.CharField(max_length=32, null=True, blank=True, help_text="源类型")


class GroupAppMigrateRecord(BaseModel):
    class Meta:
        db_table = 'groupapp_migrate'

    group_id = models.IntegerField(help_text="组ID")
    event_id = models.CharField(max_length=32, null=True, blank=True, help_text="事件id")
    group_uuid = models.CharField(max_length=32, null=True, blank=True, help_text="group UUID")
    version = models.CharField(max_length=32, null=True, blank=True, help_text="迁移的版本")
    backup_id = models.CharField(max_length=36, null=True, blank=True, help_text="备份ID")
    migrate_team = models.CharField(max_length=32, null=True, blank=True, help_text="迁移的团队名称")
    user = models.CharField(max_length=64, null=True, blank=True, help_text="恢复人")
    migrate_region = models.CharField(max_length=64, null=True, blank=True, help_text="迁移的数据中心")
    status = models.CharField(max_length=15, null=True, blank=True, help_text="时间请求状态")
    migrate_type = models.CharField(max_length=15, default="migrate", help_text="类型")
    restore_id = models.CharField(max_length=36, null=True, blank=True, help_text="恢复ID")
    create_time = models.DateTimeField(auto_now_add=True, null=True, blank=True, help_text="创建时间")
    original_group_id = models.IntegerField(help_text="原始组ID")
    original_group_uuid = models.CharField(max_length=32, null=True, blank=True, help_text="原始group UUID")


class GroupAppBackupImportRecord(BaseModel):
    class Meta:
        db_table = 'groupapp_backup_import'

    event_id = models.CharField(max_length=32, null=True, blank=True, help_text="事件id")
    status = models.CharField(max_length=15, null=True, blank=True, help_text="时间请求状态")
    file_temp_dir = models.CharField(max_length=256, null=True, blank=True, default="", help_text="目录地址")
    create_time = models.DateTimeField(auto_now_add=True, null=True, blank=True, help_text="创建时间")
    update_time = models.DateTimeField(auto_now_add=True, null=True, blank=True, help_text="更新时间")
    team_name = models.CharField(max_length=64, null=True, blank=True, help_text="正在导入的团队名称")
    region = models.CharField(max_length=64, null=True, blank=True, help_text="数据中心")


class Applicants(BaseModel):
    class Meta:
        db_table = 'applicants'

    # 用户ID
    user_id = models.IntegerField(help_text='申请用户ID')
    user_name = models.CharField(max_length=64, null=False, help_text="申请用户名")
    # 团队
    team_id = models.CharField(max_length=33, help_text='所属团队id')
    team_name = models.CharField(max_length=64, null=False, help_text="申请组名")
    # 申请时间
    apply_time = models.DateTimeField(auto_now_add=True, null=True, blank=True, help_text="申请时间")
    # is_pass是否通过
    is_pass = models.IntegerField(default=0, help_text='0表示审核中，1表示通过审核，2表示审核未通过')
    # 团队名
    team_alias = models.CharField(max_length=64, null=False, help_text="团队名")


class DeployRelation(BaseModel):
    class Meta:
        db_table = "deploy_relation"

    # 应用服务id
    service_id = models.CharField(max_length=32, unique=True, help_text="服务id")
    key_type = models.CharField(max_length=10, help_text="密钥类型")
    secret_key = models.CharField(max_length=200, help_text="密钥")


class ServiceBuildSource(BaseModel):
    """
    save the build source information of the service
    """

    class Meta:
        db_table = "service_build_source"

    service_id = models.CharField(max_length=32, unique=True, help_text="service id")
    group_key = models.CharField(max_length=32, help_text="key to market app, unique identifier")
    version = models.CharField(max_length=32, help_text="version to market app")


class TenantServiceBackup(BaseModel):
    class Meta:
        db_table = "tenant_service_backup"

    region_name = models.CharField(max_length=64, help_text="数据中心名称")
    tenant_id = models.CharField(max_length=32)
    service_id = models.CharField(max_length=32)
    backup_id = models.CharField(max_length=32, unique=True)
    backup_data = models.TextField()
    create_time = models.DateTimeField(auto_now_add=True, null=True, blank=True, help_text="创建时间")
    update_time = models.DateTimeField(auto_now_add=True, blank=True, null=True, help_text="更新时间")


class UpgradeStatus(IntEnum):
    """升级状态"""
    NOT = 1  # 未升级
    UPGRADING = 2  # 升级中
    UPGRADED = 3  # 已升级
    ROLLING = 4  # 回滚中
    ROLLBACK = 5  # 已回滚
    PARTIAL_UPGRADED = 6  # 部分升级
    PARTIAL_ROLLBACK = 7  # 部分回滚
    UPGRADE_FAILED = 8  # 升级失败
    ROLLBACK_FAILED = 9  # 回滚失败
    DEPLOY_FAILED = 10


class AppUpgradeRecordType(Enum):
    UPGRADE = "upgrade"
    ROLLBACK = "rollback"


class AppUpgradeRecord(BaseModel):
    """云市应用升级记录"""

    class Meta:
        db_table = "app_upgrade_record"

    tenant_id = models.CharField(max_length=33, help_text="租户id")
    group_id = models.IntegerField(help_text="应用组id")
    group_key = models.CharField(max_length=32, help_text="应用包")
    group_name = models.CharField(max_length=64, help_text="应用包名")
    version = models.CharField(max_length=20, default='', help_text="版本号")
    old_version = models.CharField(max_length=20, default='', help_text="旧版本号")
    status = models.IntegerField(default=UpgradeStatus.NOT.value, help_text="升级状态")
    update_time = models.DateTimeField(auto_now=True, help_text="更新时间")
    create_time = models.DateTimeField(auto_now_add=True, help_text="创建时间")
    market_name = models.CharField(max_length=64, null=True, help_text="商店标识")
    is_from_cloud = models.BooleanField(default=False, help_text="应用来源")
    upgrade_group_id = models.IntegerField(default=0, help_text="升级组件组id")
    snapshot_id = models.CharField(max_length=32, null=True)
    record_type = models.CharField(max_length=64, null=True, help_text="记录类型, 升级/回滚")
    parent_id = models.IntegerField(default=0, help_text="回滚记录对应的升级记录 ID")

    def to_dict(self):
        record = super(AppUpgradeRecord, self).to_dict()
        record["can_rollback"] = self.can_rollback()
        record["is_finished"] = self.is_finished()
        return record

    def is_finished(self):
        return self.status not in [UpgradeStatus.NOT.value, UpgradeStatus.UPGRADING.value, UpgradeStatus.ROLLING.value]

    def can_rollback(self):
        if self.record_type != AppUpgradeRecordType.UPGRADE.value:
            return False
        statuses = [
            UpgradeStatus.UPGRADED.value,
            UpgradeStatus.ROLLBACK.value,
            UpgradeStatus.PARTIAL_UPGRADED.value,
            UpgradeStatus.PARTIAL_ROLLBACK.value,
            UpgradeStatus.PARTIAL_ROLLBACK.value,
            UpgradeStatus.DEPLOY_FAILED.value,
        ]
        return self.status in statuses

    def can_upgrade(self):
        return self.status == UpgradeStatus.NOT.value

    def can_deploy(self):
        if not self.is_finished():
            return False
        statuses = [
            UpgradeStatus.UPGRADE_FAILED.value, UpgradeStatus.ROLLBACK_FAILED.value, UpgradeStatus.PARTIAL_UPGRADED.value,
            UpgradeStatus.PARTIAL_ROLLBACK.value, UpgradeStatus.DEPLOY_FAILED.value
        ]
        return True if self.status in statuses else False


class ServiceUpgradeRecord(BaseModel):
    """云市服务升级记录"""

    class Meta:
        db_table = "service_upgrade_record"

    class UpgradeType(Enum):
        UPGRADE = 'upgrade'
        ADD = 'add'

    app_upgrade_record = models.ForeignKey(
        AppUpgradeRecord,
        on_delete=models.CASCADE,
        db_constraint=False,
        related_name="service_upgrade_records",
        help_text="这条服务升级记录所关联的云市场应用升级记录",
    )
    service = models.ForeignKey(
        TenantServiceInfo,
        to_field='service_id',
        on_delete=models.CASCADE,
        db_constraint=False,
        related_name="service_upgrade_records",
        help_text="服务所关联的服务升级记录",
    )
    service_cname = models.CharField(max_length=100, help_text="服务名")
    upgrade_type = models.CharField(max_length=20, default=UpgradeType.UPGRADE.value, help_text="升级类型")
    event_id = models.CharField(max_length=32, null=True)
    update = models.TextField(help_text="升级信息")
    status = models.IntegerField(default=UpgradeStatus.NOT.value, help_text="升级状态")
    update_time = models.DateTimeField(auto_now=True, help_text="更新时间")
    create_time = models.DateTimeField(auto_now_add=True, help_text="创建时间")

    def is_finished(self):
        return self.status not in [UpgradeStatus.NOT.value, UpgradeStatus.UPGRADING.value, UpgradeStatus.ROLLING.value]


class RegionConfig(BaseModel):
    class Meta:
        db_table = 'region_info'

    region_id = models.CharField(max_length=36, unique=True, help_text="region id")
    region_name = models.CharField(max_length=64, unique=True, help_text="数据中心名称,不可修改")
    region_alias = models.CharField(max_length=64, help_text="数据中心别名")
    region_type = models.CharField(max_length=64, null=True, default=json.dumps([]), help_text="数据中心类型")
    url = models.CharField(max_length=256, help_text="数据中心API url")
    wsurl = models.CharField(max_length=256, help_text="数据中心Websocket url")
    httpdomain = models.CharField(max_length=256, help_text="数据中心http应用访问根域名")
    tcpdomain = models.CharField(max_length=256, help_text="数据中心tcp应用访问根域名")
    token = models.CharField(max_length=255, null=True, blank=True, default="", help_text="数据中心token")
    status = models.CharField(max_length=2, help_text="数据中心状态 0：编辑中 1:启用 2：停用 3:维护中")
    create_time = models.DateTimeField(auto_now_add=True, blank=True, help_text="创建时间")
    desc = models.CharField(max_length=200, blank=True, help_text="数据中心描述")
    scope = models.CharField(max_length=10, default="private", help_text="数据中心范围 private|public")
    ssl_ca_cert = models.TextField(blank=True, null=True, help_text="数据中心访问ca证书地址")
    cert_file = models.TextField(blank=True, null=True, help_text="验证文件")
    key_file = models.TextField(blank=True, null=True, help_text="验证的key")
    enterprise_id = models.CharField(max_length=36, null=True, blank=True, help_text="enterprise id")
    provider = models.CharField(max_length=24, null=True, default='', help_text="底层集群供应类型")
    provider_cluster_id = models.CharField(max_length=64, null=True, default='', help_text="底层集群ID")


def logo_path(instance, filename):
    suffix = filename.split('.')[-1]
    return '{0}/logo/{1}.{2}'.format(settings.MEDIA_ROOT, make_uuid(), suffix)


class CloundBangImages(BaseModel):
    class Meta:
        db_table = 'clound_bang_images'

    identify = models.CharField(max_length=32, help_text='标识')
    logo = models.FileField(upload_to=logo_path, null=True, blank=True, help_text="logo")
    create_time = models.DateTimeField(auto_now_add=True, help_text="创建时间")


class Announcement(BaseModel):
    class Meta:
        db_table = "announcement"

    announcement_id = models.CharField(max_length=32, null=False, help_text="通知id")
    content = models.CharField(max_length=1000, help_text="通知内容")
    a_tag = models.CharField(max_length=256, null=True, blank=True, default="", help_text="A标签文字")
    a_tag_url = models.CharField(max_length=1024, null=True, blank=True, default="", help_text="a标签跳转地址")
    type = models.CharField(max_length=32, null=True, blank=True, default="all", help_text="通知类型")
    active = models.BooleanField(default=True, help_text="通知是否启用")
    create_time = models.DateTimeField(auto_now_add=True, blank=True, help_text="创建时间")
    title = models.CharField(max_length=64, help_text="通知标题", default="title")
    level = models.CharField(max_length=32, default="low", help_text="通知的等级")


class AutoscalerRules(BaseModel):
    class Meta:
        db_table = "autoscaler_rules"

    rule_id = models.CharField(max_length=32, unique=True, help_text="自动伸缩规则ID")
    service_id = models.CharField(max_length=32, help_text="关联的组件ID")
    enable = models.BooleanField(default=True, help_text="是否启用自动伸缩规则")
    xpa_type = models.CharField(max_length=3, help_text="自动伸缩规则类型: hpa, vpa")
    min_replicas = models.IntegerField(help_text="最小副本数")
    max_replicas = models.IntegerField(help_text="最大副本数")


class AutoscalerRuleMetrics(BaseModel):
    class Meta:
        db_table = "autoscaler_rule_metrics"
        unique_together = ('rule_id', 'metric_type', 'metric_name')

    rule_id = rule_id = models.CharField(max_length=32, help_text="关联的自动伸缩规则ID")
    metric_type = models.CharField(max_length=16, help_text="指标类型")
    metric_name = models.CharField(max_length=255, help_text="指标名称")
    metric_target_type = models.CharField(max_length=13, help_text="指标目标类型")
    metric_target_value = models.IntegerField(help_text="指标目标值")


class OAuthServices(BaseModel):
    class Meta:
        db_table = "oauth_service"

    name = models.CharField(max_length=32, null=False, unique=True, help_text="oauth服务名称")
    client_id = models.CharField(max_length=64, null=False, help_text="client_id")
    client_secret = models.CharField(max_length=64, null=False, help_text="client_secret")
    redirect_uri = models.CharField(max_length=255, null=False, help_text="redirect_uri")
    home_url = models.CharField(max_length=255, null=True, help_text="auth_url")
    auth_url = models.CharField(max_length=255, null=True, help_text="auth_url")
    access_token_url = models.CharField(max_length=255, null=True, help_text="access_token_url")
    api_url = models.CharField(max_length=255, null=True, help_text="api_url")
    oauth_type = models.CharField(max_length=16, null=True, help_text="oauth_type")
    eid = models.CharField(max_length=64, null=True, help_text="user_id")
    enable = models.NullBooleanField(null=True, default=True, help_text="user_id")
    is_deleted = models.NullBooleanField(null=True, default=False, help_text="is_deleted")
    is_console = models.NullBooleanField(null=True, default=False, help_text="is_console")
    is_auto_login = models.NullBooleanField(null=True, default=False, help_text="is_auto_login")
    is_git = models.NullBooleanField(null=True, default=True, help_text="是否为git仓库")


class UserOAuthServices(BaseModel):
    class Meta:
        db_table = "user_oauth_service"

    oauth_user_id = models.CharField(max_length=64, null=True, help_text="oauth_user_id")
    oauth_user_name = models.CharField(max_length=64, null=True, help_text="oauth_user_name")
    oauth_user_email = models.CharField(max_length=64, null=True, help_text="oauth_user_email")
    service_id = models.IntegerField(null=True, help_text="service_id")
    is_auto_login = models.NullBooleanField(null=True, default=False, help_text="is_auto_login")
    is_authenticated = models.NullBooleanField(null=True, default=False, help_text="is_authenticated")
    is_expired = models.NullBooleanField(null=True, default=False, help_text="is_expired")
    access_token = models.CharField(max_length=2047, null=True, help_text="access_token_url")
    refresh_token = models.CharField(max_length=64, null=True, help_text="refresh_token")
    user_id = models.IntegerField(null=True, default=None, help_text="user_id")
    code = models.CharField(max_length=256, null=True, help_text="user_id")


class UserFavorite(BaseModel):
    class Meta:
        db_table = "user_favorite"

    name = models.CharField(max_length=64, help_text="收藏视图名称")
    url = models.CharField(max_length=255, help_text="收藏视图链接")
    user_id = models.IntegerField(help_text="用户id")
    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)
    custom_sort = models.IntegerField(help_text="用户自定义排序")
    is_default = models.BooleanField(default=False, help_text="用户自定义排序")


class Errlog(BaseModel):
    class Meta:
        db_table = "errlog"

    msg = models.CharField(max_length=2047, null=True, blank=True, default="", help_text="error log of front end")
    username = models.CharField(max_length=255, null=True, blank=True, default="")
    enterprise_id = models.CharField(max_length=255, null=True, blank=True, default="")
    address = models.CharField(max_length=2047, null=True, blank=True, default="")


class AppMarket(BaseModel):
    class Meta:
        db_table = "app_market"
        unique_together = ('name', 'enterprise_id')

    name = models.CharField(max_length=64, help_text="应用商店标识")
    url = models.CharField(max_length=255, help_text="应用商店链接")
    domain = models.CharField(max_length=64, help_text="应用商店域名")
    access_key = models.CharField(max_length=255, null=True, blank=True, help_text="应用商店访问令牌")
    enterprise_id = models.CharField(max_length=32, help_text="企业id")
    type = models.CharField(max_length=32, help_text="类型")


class ServiceMonitor(BaseModel):
    class Meta:
        db_table = "tenant_service_monitor"
        unique_together = ('name', 'tenant_id')

    name = models.CharField(max_length=64, help_text="名称")
    tenant_id = models.CharField(max_length=32, help_text="团队ID")
    service_id = models.CharField(max_length=32, help_text="组件ID")
    path = models.CharField(max_length=255, help_text="监控路径")
    port = models.IntegerField(help_text="端口号")
    service_show_name = models.CharField(max_length=64, help_text="展示名称")
    interval = models.CharField(max_length=10, help_text="收集指标时间间隔")


class ApplicationConfigGroup(BaseModel):
    class Meta:
        db_table = "app_config_group"
        unique_together = ('region_name', 'app_id', 'config_group_name')

    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)
    app_id = models.IntegerField(help_text="application ID")
    config_group_name = models.CharField(max_length=64, help_text="application config group name")
    deploy_type = models.CharField(max_length=32, help_text="effective type")
    enable = models.BooleanField(help_text="effective status")
    region_name = models.CharField(max_length=64, help_text="region name")
    config_group_id = models.CharField(max_length=32, help_text="config group id")


class ConfigGroupItem(BaseModel):
    class Meta:
        db_table = "app_config_group_item"

    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)
    app_id = models.IntegerField(help_text="application ID")
    config_group_name = models.CharField(max_length=64, help_text="application config group name")
    item_key = models.CharField(max_length=1024, help_text="config item key")
    item_value = models.TextField(max_length=65535, help_text="config item value")
    config_group_id = models.CharField(max_length=32, help_text="config group id")


class ConfigGroupService(BaseModel):
    class Meta:
        db_table = "app_config_group_service"

    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)
    app_id = models.IntegerField(help_text="application ID")
    config_group_name = models.CharField(max_length=64, help_text="application config group name")
    service_id = models.CharField(max_length=32, help_text="service ID")
    config_group_id = models.CharField(max_length=32, help_text="config group id")


class ComponentGraph(BaseModel):
    class Meta:
        db_table = "component_graphs"

    component_id = models.CharField(max_length=32, help_text="the identity of the component")
    graph_id = models.CharField(max_length=32, help_text="the identity of the graph")
    title = models.CharField(max_length=255, help_text="the title of the graph")
    promql = models.CharField(max_length=2047, help_text="the title of the graph")
    sequence = models.IntegerField(help_text="the sequence number of the graph")


class AppUpgradeSnapshot(BaseModel):
    class Meta:
        db_table = "app_upgrade_snapshots"

    create_time = models.DateTimeField(auto_now_add=True, null=True, blank=True, help_text="创建时间")
    update_time = models.DateTimeField(auto_now_add=True, blank=True, null=True, help_text="更新时间")
    tenant_id = models.CharField(max_length=32)
    upgrade_group_id = models.IntegerField(default=0, help_text="升级组件组id")
    snapshot_id = models.CharField(max_length=32, help_text="the identity of the snapshot")
    snapshot = models.TextField()


class ComponentK8sAttributes(BaseModel):
    class Meta:
        db_table = "component_k8s_attributes"

    create_time = models.DateTimeField(auto_now_add=True, null=True, blank=True, help_text="创建时间")
    update_time = models.DateTimeField(auto_now_add=True, blank=True, null=True, help_text="更新时间")
    tenant_id = models.CharField(max_length=32)
    component_id = models.CharField(max_length=32, help_text="the identity of the component")
    # Name Define the attribute name, which is currently supported
    # [nodeSelector/labels/tolerations/volumes/serviceAccountName/privileged/affinity]
    name = models.CharField(max_length=255, help_text="the name of the attribute")
    # The field type defines how the attribute is stored. Currently, `json/yaml/string` are supported
    save_type = models.CharField(max_length=32)
    # Define the attribute value, which is stored in the database.
    # The value is stored in the database in the form of `json/yaml/string`.
    attribute_value = models.TextField(help_text="the attribute value")
