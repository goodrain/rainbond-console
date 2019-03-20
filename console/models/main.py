# -*- coding: utf-8 -*-
import logging
from datetime import datetime

from django.db import models
from django.db.models.fields.files import FileField

logger = logging.getLogger("default")

app_scope = (("enterprise", u"企业"), ("team", u"团队"), ("goodrain", u"好雨云市"))
plugin_scope = (("enterprise", u"企业"), ("team", u"团队"), ("goodrain", u"好雨云市"))
user_identity = ((u"管理员", "admin"),)


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
            data[f.name] = value
        return data


class RainbondCenterApp(BaseModel):
    """云市应用包(组)"""

    class Meta:
        db_table = "rainbond_center_app"
        unique_together = ('group_key', 'version', 'enterprise_id')

    group_key = models.CharField(max_length=32, help_text=u"应用包")
    group_name = models.CharField(max_length=64, help_text=u"应用包名")
    share_user = models.IntegerField(help_text=u"分享人id")
    record_id = models.IntegerField(help_text=u"分享流程id，控制一个分享流程产出一个实体")
    share_team = models.CharField(max_length=32, help_text=u"来源应用所属团队")
    tenant_service_group_id = models.IntegerField(default=0, help_text=u"应用归属的服务组id")
    pic = models.CharField(max_length=100, null=True, blank=True, help_text=u"应用头像信息")
    source = models.CharField(max_length=15, default="", null=True, blank=True, help_text=u"应用来源(本地创建，好雨云市)")
    version = models.CharField(max_length=20, help_text=u"版本")
    scope = models.CharField(max_length=10, choices=app_scope, help_text=u"可用范围")
    describe = models.CharField(max_length=400, null=True, blank=True, help_text=u"云市应用描述信息")
    app_template = models.TextField(help_text=u"全量应用与插件配置信息")
    is_complete = models.BooleanField(default=False, help_text=u"代码或镜像是否同步完成")
    is_ingerit = models.BooleanField(default=True, help_text=u"是否可被继承")
    template_version = models.CharField(max_length=10, default="v2", help_text=u"模板版本")
    create_time = models.DateTimeField(auto_now_add=True, null=True, blank=True, help_text=u"创建时间")
    update_time = models.DateTimeField(auto_now_add=True, blank=True, null=True, help_text=u"更新时间")
    enterprise_id = models.CharField(max_length=32, default="public", help_text=u"企业ID")
    install_number = models.IntegerField(default=0, help_text=u'安装次数')
    is_official = models.BooleanField(default=False, help_text=u'是否官方认证')
    details = models.TextField(null=True, blank=True, help_text=u"应用详情")
    upgrade_time = models.CharField(max_length=30, default="", help_text=u"升级时间")

    def __unicode__(self):
        return self.to_dict()


class RainbondCenterAppInherit(BaseModel):
    """云市应用组继承关系"""

    class Meta:
        db_table = "rainbond_center_app_inherit"

    group_key = models.CharField(max_length=32, unique=True, help_text=u"当前应用")
    version = models.CharField(max_length=20, unique=True, help_text=u"当前应用版本号")
    derived_group_key = models.CharField(max_length=32, unique=True, help_text=u"继承哪个云市应用")

    def __unicode__(self):
        return self.to_dict()


class RainbondCenterPlugin(BaseModel):
    """云市插件"""

    class Meta:
        db_table = "rainbond_center_plugin"

    plugin_key = models.CharField(max_length=32,  help_text=u"插件分享key")
    plugin_name = models.CharField(max_length=32, help_text=u"插件名称")
    plugin_id = models.CharField(max_length=32, null=True, help_text=u"插件id")
    category = models.CharField(max_length=32, help_text=u"插件类别")
    record_id = models.IntegerField(help_text=u"分享流程id")
    version = models.CharField(max_length=20, help_text=u"版本")
    build_version = models.CharField(max_length=32, help_text=u"构建版本")
    pic = models.CharField(max_length=100,null=True, blank=True, help_text=u"插件头像信息")
    scope = models.CharField(max_length=10, choices=plugin_scope, help_text=u"可用范围")
    source = models.CharField(max_length=15, default="", null=True, blank=True, help_text=u"应用来源(本地创建，好雨云市)")
    share_user = models.IntegerField(help_text=u"分享人id")
    share_team = models.CharField(max_length=32, help_text=u"来源应用所属团队")
    desc = models.CharField(max_length=400, null=True, blank=True, help_text=u"插件描述信息")
    plugin_template = models.TextField(help_text=u"全量插件信息")
    is_complete = models.BooleanField(default=False, help_text=u"代码或镜像是否同步完成")
    create_time = models.DateTimeField(auto_now_add=True, null=True, blank=True, help_text=u"创建时间")
    update_time = models.DateTimeField(auto_now=True, blank=True, null=True, help_text=u"更新时间")
    enterprise_id = models.CharField(max_length=32, default='public', help_text=u"企业id")
    details = models.TextField(null=True, blank=True, help_text=u"插件详细信息")

    def __unicode__(self):
        return self.to_dict()


class ServiceShareRecord(BaseModel):
    """服务分享记录"""

    class Meta:
        db_table = "service_share_record"

    group_share_id = models.CharField(max_length=32, unique=True, help_text=u"发布应用组或插件的唯一Key")
    group_id = models.CharField(max_length=32, help_text=u"分享应用组id或者单独插件ID")
    team_name = models.CharField(max_length=32, help_text=u"应用所在团队唯一名称")
    event_id = models.CharField(max_length=32, help_text=u"介质同步事件ID,弃用，使用表service_share_record_event")
    share_version = models.CharField(max_length=15, help_text=u"应用组发布版本")
    is_success = models.BooleanField(default=False, help_text=u"发布是否成功")
    step = models.IntegerField(default=0, help_text=u"当前发布进度")
    create_time = models.DateTimeField(auto_now_add=True, help_text=u"创建时间")
    update_time = models.DateTimeField(auto_now_add=True, help_text=u"更新时间")

    def __unicode__(self):
        return self.to_dict()


class ServiceShareRecordEvent(BaseModel):
    """服务分享订单关联发布事件"""

    class Meta:
        db_table = "service_share_record_event"

    record_id = models.IntegerField(help_text=u"关联的订单ID")
    region_share_id = models.CharField(max_length=36, help_text=u"应用数据中心分享反馈ID")
    team_name = models.CharField(max_length=32, help_text=u"应用所在团队唯一名称")
    service_key = models.CharField(max_length=32, help_text=u"对应应用key")
    service_id = models.CharField(max_length=32, help_text=u"对应应用ID")
    service_alias = models.CharField(max_length=10, help_text=u"对应应用别名")
    service_name = models.CharField(max_length=32, help_text=u"对应应用名称")
    team_id = models.CharField(max_length=32, help_text=u"对应所在团队ID")
    event_id = models.CharField(max_length=32, default="", help_text=u"介质同步事件ID")
    event_status = models.CharField(max_length=32, default="not_start", help_text=u"事件状态")
    create_time = models.DateTimeField(auto_now_add=True, help_text=u"创建时间")
    update_time = models.DateTimeField(auto_now_add=True, help_text=u"更新时间")

    def __unicode__(self):
        return self.to_dict()


class PluginShareRecordEvent(BaseModel):
    """插件分享订单关联发布事件"""

    class Meta:
        db_table = "plugin_share_record_event"

    record_id = models.IntegerField(help_text=u"关联的记录ID")
    region_share_id = models.CharField(max_length=36, help_text=u"应用数据中心分享反馈ID")
    team_id = models.CharField(max_length=32, help_text=u"对应所在团队ID")
    team_name = models.CharField(max_length=32, help_text=u"应用所在团队唯一名称")
    plugin_id = models.CharField(max_length=32, help_text=u"对应插件ID")
    plugin_name = models.CharField(max_length=32, help_text=u"对应插件名称")
    event_id = models.CharField(max_length=32, default="", help_text=u"介质同步事件ID")
    event_status = models.CharField(max_length=32, default="not_start", help_text=u"事件状态")
    create_time = models.DateTimeField(auto_now_add=True, help_text=u"创建时间")
    update_time = models.DateTimeField(auto_now=True, help_text=u"更新时间")

    def __unicode__(self):
        return self.to_dict()


class ComposeGroup(BaseModel):
    """compose组"""

    class Meta:
        db_table = "compose_group"

    group_id = models.IntegerField(help_text=u"compose组关联的组id")
    team_id = models.CharField(max_length=32, help_text=u"团队 id")
    region = models.CharField(max_length=15, help_text=u"服务所属数据中心")
    compose_content = models.TextField(null=True, blank=True, help_text=u"compose文件内容")
    compose_id = models.CharField(max_length=32, unique=True, help_text=u"compose id")
    create_status = models.CharField(max_length=15, null=True, blank=True,
                                     help_text=u"compose组创建状态 creating|checking|checked|complete")
    check_uuid = models.CharField(
        max_length=36, blank=True, null=True, default="", help_text=u"compose检测ID")
    check_event_id = models.CharField(
        max_length=32, blank=True, null=True, default="", help_text=u"compose检测事件ID")

    create_time = models.DateTimeField(auto_now_add=True, null=True, blank=True, help_text=u"创建时间")


class ComposeServiceRelation(BaseModel):
    """compose组和服务的关系"""

    class Meta:
        db_table = "compose_service_relation"

    team_id = models.CharField(max_length=32, help_text=u"团队 id")
    service_id = models.CharField(max_length=32, help_text=u"服务 id")
    compose_id = models.CharField(max_length=32, help_text=u"compose id")
    create_time = models.DateTimeField(auto_now_add=True, null=True, blank=True, help_text=u"创建时间")


class ServiceSourceInfo(BaseModel):
    """服务源信息"""

    class Meta:
        db_table = "service_source"

    service_id = models.CharField(max_length=32, help_text=u"服务ID")
    team_id = models.CharField(max_length=32, help_text=u"服务所在团队ID")
    user_name = models.CharField(max_length=32, null=True, blank=True, help_text=u"用户名")
    password = models.CharField(max_length=32, null=True, blank=True, help_text=u"密码")
    extend_info = models.CharField(max_length=1024, null=True, blank=True, default="", help_text=u"扩展信息")
    create_time = models.DateTimeField(auto_now_add=True, null=True, blank=True, help_text=u"创建时间")


class TeamGitlabInfo(BaseModel):
    class Meta:
        db_table = "team_gitlab_info"

    team_id = models.CharField(max_length=32, help_text=u"团队ID")
    repo_name = models.CharField(max_length=100, help_text=u"代码仓库名称")
    respo_url = models.CharField(
        max_length=100, null=True, blank=True, help_text=u"code代码仓库")
    git_project_id = models.IntegerField(help_text=u"gitlab 中项目id", default=0)
    code_version = models.CharField(
        max_length=100, null=True, blank=True, help_text=u"代码版本")
    create_time = models.DateTimeField(
        auto_now_add=True, blank=True, help_text=u"创建时间")


class ServiceRecycleBin(BaseModel):
    class Meta:
        db_table = 'tenant_service_recycle_bin'
        unique_together = ('tenant_id', 'service_alias')

    service_id = models.CharField(
        max_length=32, unique=True, help_text=u"服务id")
    tenant_id = models.CharField(max_length=32, help_text=u"租户id")
    service_key = models.CharField(max_length=32, help_text=u"服务key")
    service_alias = models.CharField(max_length=100, help_text=u"服务别名")
    service_cname = models.CharField(
        max_length=100, default='', help_text=u"服务名")
    service_region = models.CharField(max_length=15, help_text=u"服务所属区")
    desc = models.CharField(
        max_length=200, null=True, blank=True, help_text=u"描述")
    category = models.CharField(
        max_length=15, help_text=u"服务分类：application,cache,store")
    service_port = models.IntegerField(help_text=u"服务端口", default=0)
    is_web_service = models.BooleanField(
        default=False, blank=True, help_text=u"是否web服务")
    version = models.CharField(max_length=20, help_text=u"版本")
    update_version = models.IntegerField(default=1, help_text=u"内部发布次数")
    image = models.CharField(max_length=100, help_text=u"镜像")
    cmd = models.CharField(
        max_length=2048, null=True, blank=True, help_text=u"启动参数")
    setting = models.CharField(
        max_length=100, null=True, blank=True, help_text=u"设置项")
    extend_method = models.CharField(
        max_length=15,
        default='stateless',
        help_text=u"伸缩方式")
    env = models.CharField(
        max_length=200, null=True, blank=True, help_text=u"环境变量")
    min_node = models.IntegerField(help_text=u"启动个数", default=1)
    min_cpu = models.IntegerField(help_text=u"cpu个数", default=500)
    min_memory = models.IntegerField(help_text=u"内存大小单位（M）", default=256)
    inner_port = models.IntegerField(help_text=u"内部端口", default=0)
    volume_mount_path = models.CharField(
        max_length=50, null=True, blank=True, help_text=u"mount目录")
    host_path = models.CharField(
        max_length=300, null=True, blank=True, help_text=u"mount目录")
    deploy_version = models.CharField(
        max_length=20, null=True, blank=True, help_text=u"部署版本")
    code_from = models.CharField(
        max_length=20, null=True, blank=True, help_text=u"代码来源:gitlab,github")
    git_url = models.CharField(
        max_length=100, null=True, blank=True, help_text=u"code代码仓库")
    create_time = models.DateTimeField(
        auto_now_add=True, blank=True, help_text=u"创建时间")
    git_project_id = models.IntegerField(help_text=u"gitlab 中项目id", default=0)
    is_code_upload = models.BooleanField(
        default=False, blank=True, help_text=u"是否上传代码")
    code_version = models.CharField(
        max_length=100, null=True, blank=True, help_text=u"代码版本")
    service_type = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text=u"服务类型:web,mysql,redis,mongodb,phpadmin")
    creater = models.IntegerField(help_text=u"服务创建者", default=0)
    language = models.CharField(
        max_length=40, null=True, blank=True, help_text=u"代码语言")
    protocol = models.CharField(
        max_length=15, default='', help_text=u"服务协议：http,stream")
    total_memory = models.IntegerField(help_text=u"内存使用M", default=0)
    is_service = models.BooleanField(
        default=False, blank=True, help_text=u"是否inner服务")
    namespace = models.CharField(
        max_length=100, default='', help_text=u"镜像发布云帮的区间")

    volume_type = models.CharField(
        max_length=15, default='shared', help_text=u"共享类型shared、exclusive")
    port_type = models.CharField(
        max_length=15,
        default='multi_outer',
        help_text=u"端口类型，one_outer;dif_protocol;multi_outer")
    # 服务创建类型,cloud、assistant
    service_origin = models.CharField(
        max_length=15,
        default='assistant',
        help_text=u"服务创建类型cloud云市服务,assistant云帮服务")
    expired_time = models.DateTimeField(null=True, help_text=u"过期时间")
    tenant_service_group_id = models.IntegerField(default=0, help_text=u"应用归属的服务组id")

    service_source = models.CharField(max_length=15, default="", null=True, blank=True,
                                      help_text=u"应用来源(source_code, market, docker_run, docker_compose)")
    create_status = models.CharField(max_length=15, null=True, blank=True, help_text=u"应用创建状态 creating|complete")
    update_time = models.DateTimeField(auto_now_add=True, blank=True, help_text=u"更新时间")
    check_uuid = models.CharField(
        max_length=36, blank=True, null=True, default="", help_text=u"应用检测ID")
    check_event_id = models.CharField(
        max_length=32, blank=True, null=True, default="", help_text=u"应用检测事件ID")
    docker_cmd = models.CharField(
        max_length=1024, null=True, blank=True, help_text=u"镜像创建命令")


class ServiceRelationRecycleBin(BaseModel):
    class Meta:
        db_table = 'tenant_service_relation_recycle_bin'
        unique_together = ('service_id', 'dep_service_id')

    tenant_id = models.CharField(max_length=32, help_text=u"租户id")
    service_id = models.CharField(max_length=32, help_text=u"服务id")
    dep_service_id = models.CharField(max_length=32, help_text=u"依赖服务id")
    dep_service_type = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text=u"服务类型:web,mysql,redis,mongodb,phpadmin")
    dep_order = models.IntegerField(help_text=u"依赖顺序")


class EnterpriseUserPerm(BaseModel):
    """用户在企业的权限"""

    class Meta:
        db_table = 'enterprise_user_perm'

    user_id = models.IntegerField(help_text=u"用户id")
    enterprise_id = models.CharField(max_length=32, help_text=u"企业id")
    identity = models.CharField(
        max_length=15, choices=user_identity, help_text=u"用户在企业的身份")


class TenantUserRole(BaseModel):
    """用户在一个团队中的角色"""

    class Meta:
        db_table = 'tenant_user_role'
        unique_together = (('role_name', 'tenant_id'),)

    role_name = models.CharField(max_length=32, help_text=u'角色名称')
    tenant_id = models.IntegerField(null=True, blank=True, help_text=u'团队id')
    is_default = models.BooleanField(default=False)

    def __unicode__(self):
        return self.to_dict()


class TenantUserPermission(BaseModel):
    """权限及对应的操作"""

    class Meta:
        db_table = 'tenant_user_permission'
        unique_together = (('codename', 'per_info'),)

    codename = models.CharField(max_length=32, help_text=u'权限名称')
    per_info = models.CharField(max_length=32, help_text=u'权限对应的操作信息')
    is_select = models.BooleanField(default=True, help_text=u'自定义权限时是否可以做选项')
    group = models.IntegerField(help_text=u'这个权限属于哪个权限组', null=True, blank=True)
    per_explanation = models.CharField(max_length=132, null=True, blank=True, help_text=u'这一条权限操作的具体说明')

    def __unicode__(self):
        return self.to_dict()


class TenantUserRolePermission(BaseModel):
    """团队中一个角色与权限的关系对应表"""

    class Meta:
        db_table = 'tenant_user_role_permission'

    role_id = models.IntegerField(help_text=u'团队中的一个角色的id')
    per_id = models.IntegerField(help_text=u'一个权限操作的id')

    def __unicode__(self):
        return self.to_dict()


class PermGroup(BaseModel):
    """权限组，用于给权限分组分类"""

    class Meta:
        db_table = 'tenant_permission_group'

    group_name = models.CharField(max_length=64, help_text=u'组名')

    def __unicode__(self):
        return self.to_dict()


class ServiceRelPerms(BaseModel):
    """一个用户在一个应用下的权限"""

    class Meta:
        db_table = 'service_user_perms'

    user_id = models.IntegerField(help_text=u"用户id")
    service_id = models.IntegerField(help_text=u"服务id")
    perm_id = models.IntegerField(help_text=u'权限id')

    def __unicode__(self):
        return self.to_dict()


class AppExportRecord(BaseModel):
    """应用导出"""

    class Meta:
        db_table = 'app_export_record'

    group_key = models.CharField(max_length=32, help_text=u"导出应用的key")
    version = models.CharField(max_length=20, help_text=u"导出应用的版本")
    format = models.CharField(max_length=15, help_text=u"导出应用的格式")
    event_id = models.CharField(max_length=32, null=True, blank=True, help_text=u"事件id")
    status = models.CharField(max_length=10, null=True, blank=True, help_text=u"时间请求状态")
    file_path = models.CharField(max_length=256, null=True, blank=True, help_text=u"文件地址")
    create_time = models.DateTimeField(auto_now_add=True, null=True, blank=True, help_text=u"创建时间")
    update_time = models.DateTimeField(auto_now_add=True, null=True, blank=True, help_text=u"更新时间")
    enterprise_id = models.CharField(max_length=32, help_text=u"企业ID")


class UserMessage(BaseModel):
    """用户站内信"""

    class Meta:
        db_table = 'user_message'

    message_id = models.CharField(max_length=32, help_text=u"消息ID")
    receiver_id = models.IntegerField(help_text=u"接受消息用户ID")
    content = models.CharField(max_length=1000, help_text=u"消息内容")
    is_read = models.BooleanField(default=False, help_text=u"是否已读")
    create_time = models.DateTimeField(auto_now=True, null=True, blank=True, help_text=u"创建时间")
    update_time = models.DateTimeField(auto_now=True, null=True, blank=True, help_text=u"更新时间")
    msg_type = models.CharField(max_length=32, help_text=u"消息类型")
    announcement_id = models.CharField(max_length=32, null=True, blank=True, help_text=u"公告ID")
    title = models.CharField(max_length=64, help_text=u"消息标题", default=u"title")
    level = models.CharField(max_length=32, default="low", help_text=u"通知的等级")


class AppImportRecord(BaseModel):
    class Meta:
        db_table = 'app_import_record'

    event_id = models.CharField(max_length=32, null=True, blank=True, help_text=u"事件id")
    status = models.CharField(max_length=15, null=True, blank=True, help_text=u"导入状态")
    scope = models.CharField(max_length=10, null=True, blank=True, default="", help_text=u"导入范围")
    format = models.CharField(max_length=15, null=True, blank=True, default="", help_text=u"类型")
    source_dir = models.CharField(max_length=256, null=True, blank=True, default="", help_text=u"目录地址")
    create_time = models.DateTimeField(auto_now_add=True, null=True, blank=True, help_text=u"创建时间")
    update_time = models.DateTimeField(auto_now_add=True, null=True, blank=True, help_text=u"更新时间")
    team_name = models.CharField(max_length=32, null=True, blank=True, help_text=u"正在导入的团队名称")
    region = models.CharField(max_length=32, null=True, blank=True, help_text=u"数据中心")
    user_name = models.CharField(max_length=24, null=True, blank=True, help_text=u"操作人")


class GroupAppBackupRecord(BaseModel):
    class Meta:
        db_table = 'groupapp_backup'

    group_id = models.IntegerField(help_text=u"组ID")
    event_id = models.CharField(max_length=32, null=True, blank=True, help_text=u"事件id")
    group_uuid = models.CharField(max_length=32, null=True, blank=True, help_text=u"group UUID")
    version = models.CharField(max_length=32, null=True, blank=True, help_text=u"备份版本")
    backup_id = models.CharField(max_length=36, null=True, blank=True, help_text=u"备份ID")
    team_id = models.CharField(max_length=32, null=True, blank=True, help_text=u"团队ID")
    user = models.CharField(max_length=20, null=True, blank=True, help_text=u"备份人")
    region = models.CharField(max_length=15, null=True, blank=True, help_text=u"数据中心")
    status = models.CharField(max_length=15, null=True, blank=True, help_text=u"时间请求状态")
    note = models.CharField(max_length=128, null=True, blank=True, default="", help_text=u"备份说明")
    mode = models.CharField(max_length=15, null=True, blank=True, default="", help_text=u"备份类型")
    source_dir = models.CharField(max_length=256, null=True, blank=True, default="", help_text=u"目录地址")
    backup_size = models.IntegerField(help_text=u"备份文件大小")
    create_time = models.DateTimeField(auto_now_add=True, null=True, blank=True, help_text=u"创建时间")
    total_memory = models.IntegerField(help_text=u"备份应用的总内存")
    backup_server_info = models.CharField(max_length=400, null=True, blank=True, default="", help_text=u"备份服务信息")
    source_type = models.CharField(max_length=32, null=True, blank=True, help_text=u"源类型")


class GroupAppMigrateRecord(BaseModel):
    class Meta:
        db_table = 'groupapp_migrate'

    group_id = models.IntegerField(help_text=u"组ID")
    event_id = models.CharField(max_length=32, null=True, blank=True, help_text=u"事件id")
    group_uuid = models.CharField(max_length=32, null=True, blank=True, help_text=u"group UUID")
    version = models.CharField(max_length=32, null=True, blank=True, help_text=u"迁移的版本")
    backup_id = models.CharField(max_length=36, null=True, blank=True, help_text=u"备份ID")
    migrate_team = models.CharField(max_length=32, null=True, blank=True, help_text=u"迁移的团队名称")
    user = models.CharField(max_length=20, null=True, blank=True, help_text=u"恢复人")
    migrate_region = models.CharField(max_length=15, null=True, blank=True, help_text=u"迁移的数据中心")
    status = models.CharField(max_length=15, null=True, blank=True, help_text=u"时间请求状态")
    migrate_type = models.CharField(max_length=15, default="migrate", help_text=u"类型")
    restore_id = models.CharField(max_length=36, null=True, blank=True, help_text=u"恢复ID")
    create_time = models.DateTimeField(auto_now_add=True, null=True, blank=True, help_text=u"创建时间")
    original_group_id = models.IntegerField(help_text=u"原始组ID")
    original_group_uuid = models.CharField(max_length=32, null=True, blank=True, help_text=u"原始group UUID")


class GroupAppBackupImportRecord(BaseModel):
    class Meta:
        db_table = 'groupapp_backup_import'

    event_id = models.CharField(max_length=32, null=True, blank=True, help_text=u"事件id")
    status = models.CharField(max_length=15, null=True, blank=True, help_text=u"时间请求状态")
    file_temp_dir = models.CharField(max_length=256, null=True, blank=True, default="", help_text=u"目录地址")
    create_time = models.DateTimeField(auto_now_add=True, null=True, blank=True, help_text=u"创建时间")
    update_time = models.DateTimeField(auto_now_add=True, null=True, blank=True, help_text=u"更新时间")
    team_name = models.CharField(max_length=32, null=True, blank=True, help_text=u"正在导入的团队名称")
    region = models.CharField(max_length=32, null=True, blank=True, help_text=u"数据中心")


class Applicants(BaseModel):
    class Meta:
        db_table = 'applicants'

    # 用户ID
    user_id = models.IntegerField(help_text=u'申请用户ID')
    user_name = models.CharField(max_length=20, null=False, help_text=u"申请用户名")
    # 团队
    team_id = models.CharField(max_length=33, help_text=u'所属团队id')
    team_name = models.CharField(max_length=20,null=False, help_text=u"申请组名")
    # 申请时间
    apply_time = models.DateTimeField(auto_now_add=True, null=True, blank=True, help_text=u"申请时间")
    # is_pass是否通过
    is_pass = models.IntegerField(default=0, help_text=u'0表示审核中，1表示通过审核，2表示审核未通过')
    # 团队名
    team_alias = models.CharField(max_length=30, null=False, help_text=u"团队名")


class DeployRelation(BaseModel):
    class Meta:
        db_table = "deploy_relation"

    # 应用服务id
    service_id = models.CharField(
        max_length=32, unique=True, help_text=u"服务id")
    key_type = models.CharField(max_length=10, help_text=u"密钥类型")
    secret_key = models.CharField(max_length=200, help_text=u"密钥")