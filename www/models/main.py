# -*- coding: utf8 -*-
import logging
import re
from datetime import datetime
from enum import Enum

from console.enum.app import GovernanceModeEnum
from console.enum.component_enum import ComponentSource
from console.utils import runner_util
from django.conf import settings
from django.db import models
from django.db.models.fields import (AutoField, BooleanField, CharField, DateTimeField, DecimalField, IntegerField)
from django.db.models.fields.files import FileField
from django.utils.crypto import salted_hmac
from www.utils.crypt import encrypt_passwd, make_tenant_id, make_uuid

logger = logging.getLogger("default")

# Create your models here.

user_origion = (("自主注册", "registration"), ("邀请注册", "invitation"))

tenant_type = (("免费租户", "free"), ("付费租户", "payed"))

service_identity = (("管理员", "admin"), ("开发者", "developer"), ("观察者", "viewer"))

tenant_identity = (("拥有者", "owner"), ("管理员", "admin"), ("开发者", "developer"), ("观察者", "viewer"), ("访问", "access"))

app_pay_choices = (('免费', "free"), ('付费', "pay"))

pay_method = (('预付费提前采购', "prepaid"), ('按使用后付费', "postpaid"))


def compose_file_path(instance, filename):
    suffix = filename.split('.')[-1]
    return '{0}/compose-file/{1}.{2}'.format(settings.MEDIA_ROOT, make_uuid(), suffix)


class AnonymousUser(object):
    id = None
    pk = None
    username = ''
    is_active = False

    def __str__(self):
        return 'AnonymousUser'

    def __eq__(self, other):
        return isinstance(other, self.__class__)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return 1  # instances always return the same hash value

    def save(self):
        raise NotImplementedError("Django doesn't provide a DB representation for AnonymousUser.")

    def delete(self):
        raise NotImplementedError("Django doesn't provide a DB representation for AnonymousUser.")

    def set_password(self, raw_password):
        raise NotImplementedError("Django doesn't provide a DB representation for AnonymousUser.")

    def check_password(self, raw_password):
        raise NotImplementedError("Django doesn't provide a DB representation for AnonymousUser.")

    def get_group_permissions(self, obj=None):
        return set()

    def is_anonymous(self):
        return True

    def is_authenticated(self):
        return False



class SuperAdminUser(models.Model):
    """超级管理员"""

    class Meta:
        db_table = "user_administrator"

    user_id = models.IntegerField(unique=True, help_text="用户ID")
    email = models.EmailField(max_length=35, null=True, blank=True, help_text="邮件地址")


class Users(models.Model):
    USERNAME_FIELD = 'nick_name'

    class Meta:
        db_table = 'user_info'

    user_id = models.AutoField(primary_key=True, max_length=10)
    email = models.EmailField(max_length=128, help_text="邮件地址")
    nick_name = models.CharField(max_length=64, null=True, blank=True, help_text="账号")
    real_name = models.CharField(max_length=64, null=True, blank=True, help_text="姓名")
    password = models.CharField(max_length=64, help_text="密码")
    phone = models.CharField(max_length=15, null=True, blank=True, help_text="手机号码")
    is_active = models.BooleanField(default=False, help_text="激活状态")
    create_time = models.DateTimeField(auto_now_add=True, blank=True, help_text="创建时间")
    sys_admin = models.BooleanField(default=False, help_text="超级管理员")
    enterprise_id = models.CharField(max_length=32, null=True, blank=True, default='', help_text="统一认证中心的enterprise_id")
    logo = models.CharField(max_length=2048, null=True, help_text="用户头像")

    def set_password(self, raw_password):
        self.password = encrypt_passwd(self.email + raw_password)

    def check_password(self, raw_password):
        return bool(encrypt_passwd(self.email + raw_password) == self.password)

    @property
    def username(self):
        return self.nick_name

    def is_anonymous(self):
        return False

    def is_authenticated(self):
        return True

    def get_name(self):
        if self.real_name:
            return self.real_name
        return self.nick_name

    @property
    def is_sys_admin(self):
        """
        是否是系统管理员
        :return: True/False
        """
        if self.sys_admin:
            return True
        return False

    def get_session_auth_hash(self):
        """
        Returns an HMAC of the password field.
        """
        key_salt = "goodrain.com.models.get_session_auth_hash"
        return salted_hmac(key_salt, self.password).hexdigest()

    def __unicode__(self):
        return self.nick_name or self.email

    def to_dict(self):
        opts = self._meta
        data = {}
        for f in opts.concrete_fields:
            value = f.value_from_object(self)
            if isinstance(value, datetime):
                value = value.strftime('%Y-%m-%d %H:%M:%S')
            data[f.name] = value
        return data

    def get_username(self):
        return self.nick_name


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


class Tenants(BaseModel):
    """
    租户表
    """

    class Meta:
        db_table = 'tenant_info'

    tenant_id = models.CharField(max_length=33, unique=True, default=make_tenant_id, help_text="租户id")
    tenant_name = models.CharField(max_length=64, unique=True, help_text="租户名称")
    is_active = models.BooleanField(default=True, help_text="激活状态")
    create_time = models.DateTimeField(auto_now_add=True, blank=True, help_text="创建时间")
    creater = models.IntegerField(help_text="租户创建者", default=0)
    limit_memory = models.IntegerField(help_text="内存大小单位（M）", default=1024)
    update_time = models.DateTimeField(auto_now=True, help_text="更新时间")
    tenant_alias = models.CharField(max_length=64, null=True, blank=True, default='', help_text="团队别名")
    enterprise_id = models.CharField(max_length=32, null=True, blank=True, default='', help_text="企业id")
    namespace = models.CharField(max_length=33, unique=True, help_text="团队的命名空间")
    logo = models.CharField(max_length=2048, null=True, help_text="团队头像")

    def __unicode__(self):
        return self.tenant_name


class HelmRepoInfo(BaseModel):
    class Meta:
        db_table = "helm_repo"

    repo_id = models.CharField(max_length=33, unique=True, help_text="Helm仓库id")
    repo_name = models.CharField(max_length=64, unique=True, help_text="仓库名称")
    repo_url = models.CharField(max_length=128, help_text="仓库地址")
    username = models.CharField(max_length=128, default="", help_text="仓库用户名")
    password = models.CharField(max_length=128, default="", help_text="仓库密码")


class TenantRegionInfo(BaseModel):
    class Meta:
        db_table = 'tenant_region'
        unique_together = (('tenant_id', 'region_name'), )

    tenant_id = models.CharField(max_length=33, db_index=True, help_text="租户id")
    region_name = models.CharField(max_length=64, help_text="集群ID")
    is_active = models.BooleanField(default=True, help_text="是否已激活")
    is_init = models.BooleanField(default=False, help_text='是否创建租户网络')
    service_status = models.IntegerField(help_text="组件状态0:暂停，1:运行，2:关闭", default=1)
    create_time = models.DateTimeField(auto_now_add=True, blank=True, help_text="创建时间")
    update_time = models.DateTimeField(auto_now=True, help_text="更新时间")
    region_tenant_name = models.CharField(max_length=64, null=True, blank=True, default='', help_text="数据中心租户名")
    region_tenant_id = models.CharField(max_length=32, null=True, blank=True, default='', help_text="数据中心租户id")
    region_scope = models.CharField(max_length=32, null=True, blank=True, default='', help_text="数据中心类型 private/public")
    enterprise_id = models.CharField(max_length=32, null=True, blank=True, default='', help_text="企业id")


service_status = (
    ("已发布", 'published'),
    ("测试中", "test"),
)

extend_method = (("不伸缩", 'stateless'), ("垂直伸缩", 'vertical'))


class TenantServiceInfo(BaseModel):
    class Meta:
        db_table = 'tenant_service'
        unique_together = ('tenant_id', 'service_alias')

    service_id = models.CharField(max_length=32, unique=True, help_text="组件id")
    tenant_id = models.CharField(max_length=32, help_text="租户id")
    service_key = models.CharField(max_length=32, help_text="组件key")
    service_alias = models.CharField(max_length=100, help_text="组件别名")
    service_cname = models.CharField(max_length=100, default='', help_text="组件名")
    service_region = models.CharField(max_length=64, help_text="组件所属区")
    desc = models.CharField(max_length=200, null=True, blank=True, help_text="描述")
    category = models.CharField(max_length=15, help_text="组件分类：application,cache,store")
    service_port = models.IntegerField(help_text="组件端口", default=0)
    is_web_service = models.BooleanField(default=False, blank=True, help_text="是否web组件")
    version = models.CharField(max_length=255, help_text="版本")
    update_version = models.IntegerField(default=1, help_text="内部发布次数")
    image = models.CharField(max_length=200, help_text="镜像")
    cmd = models.CharField(max_length=2048, null=True, blank=True, help_text="启动参数")
    min_node = models.IntegerField(help_text="实例数量", default=1)
    min_cpu = models.IntegerField(help_text="cpu分配额 1000=1core", default=500)
    container_gpu = models.IntegerField(help_text="gpu显存数量", default=0)
    min_memory = models.IntegerField(help_text="内存大小单位（M）", default=256)

    # deprecated
    setting = models.CharField(max_length=200, null=True, blank=True, help_text="设置项")
    extend_method = models.CharField(max_length=32, default='stateless_multiple', help_text="组件部署类型,stateless or state")
    # deprecated
    env = models.CharField(max_length=200, null=True, blank=True, help_text="环境变量")
    # deprecated
    inner_port = models.IntegerField(help_text="内部端口", default=0)
    # deprecated
    volume_mount_path = models.CharField(max_length=200, null=True, blank=True, help_text="mount目录")
    # deprecated
    host_path = models.CharField(max_length=300, null=True, blank=True, help_text="mount目录")
    # deprecated
    deploy_version = models.CharField(max_length=20, null=True, blank=True, help_text="仅用于云市创建应用表示构建源的部署版版-小版本")
    code_from = models.CharField(max_length=20, null=True, blank=True, help_text="代码来源:gitlab,github")
    git_url = models.CharField(max_length=2047, null=True, blank=True, help_text="code代码仓库")
    create_time = models.DateTimeField(auto_now_add=True, blank=True, help_text="创建时间")
    git_project_id = models.IntegerField(help_text="gitlab 中项目id", default=0)
    # deprecated
    is_code_upload = models.BooleanField(default=False, blank=True, help_text="是否上传代码")
    # deprecated
    code_version = models.CharField(max_length=100, null=True, blank=True, help_text="代码版本")
    service_type = models.CharField(max_length=50, null=True, blank=True, help_text="组件类型:web,mysql,redis,mongodb,phpadmin")
    creater = models.IntegerField(help_text="组件创建者", default=0)
    language = models.CharField(max_length=40, null=True, blank=True, help_text="代码语言")
    # deprecated
    protocol = models.CharField(max_length=15, default='', help_text="服务协议：http,stream")
    # deprecated
    total_memory = models.IntegerField(help_text="内存使用M", default=0)
    # deprecated
    is_service = models.BooleanField(default=False, blank=True, help_text="是否inner组件")
    # deprecated
    namespace = models.CharField(max_length=100, default='', help_text="镜像发布云帮的区间")
    # deprecated
    volume_type = models.CharField(max_length=64, default='shared', help_text="共享类型shared、exclusive")
    # deprecated
    port_type = models.CharField(max_length=15, default='multi_outer', help_text="端口类型，one_outer;dif_protocol;multi_outer")
    # 组件创建类型,cloud、assistant
    service_origin = models.CharField(max_length=15, default='assistant', help_text="组件创建类型cloud云市组件,assistant云帮组件")
    # 组件所属关系，从模型安装的多个组件所属一致。
    tenant_service_group_id = models.IntegerField(default=0, help_text="组件归属的组件组id，从应用模版安装的组件该字段需要赋值")
    # deprecated
    expired_time = models.DateTimeField(null=True, help_text="过期时间")
    open_webhooks = models.BooleanField(default=False, help_text='是否开启自动触发部署功能（兼容老版本组件）')
    service_source = models.CharField(
        max_length=15, default="", null=True, blank=True, help_text="组件来源(source_code, market, docker_run, docker_compose)")
    create_status = models.CharField(max_length=15, null=True, blank=True, help_text="组件创建状态 creating|complete")
    update_time = models.DateTimeField(auto_now=True, blank=True, help_text="更新时间")
    check_uuid = models.CharField(max_length=36, blank=True, null=True, default="", help_text="组件检测ID")
    check_event_id = models.CharField(max_length=32, blank=True, null=True, default="", help_text="组件检测事件ID")
    docker_cmd = models.CharField(max_length=1024, null=True, blank=True, help_text="镜像创建命令")
    secret = models.CharField(max_length=64, null=True, blank=True, help_text="webhooks验证密码")
    server_type = models.CharField(max_length=5, default='git', help_text="源码仓库类型")
    is_upgrate = models.BooleanField(default=False, help_text='是否可以更新')
    build_upgrade = models.BooleanField(default=True, help_text='组件构建后是否升级')
    service_name = models.CharField(max_length=100, default='', help_text="组件名称（新加属性，数据中心使用）")
    oauth_service_id = models.IntegerField(default=None, null=True, blank=True, help_text="拉取源码所用的OAuth服务id")
    git_full_name = models.CharField(max_length=64, null=True, blank=True, default=None, help_text="git项目的fullname")
    k8s_component_name = models.CharField(max_length=100, help_text="集群组件名称")
    job_strategy = models.CharField(max_length=2047, null=True, default="", help_text="job任务策略")
    arch = models.CharField(max_length=32, null=True, default="amd64", help_text="架构")

    def __unicode__(self):
        return self.service_alias

    def toJSON(self):
        data = {}
        for f in self._meta.fields:
            obj = getattr(self, f.name)
            if type(f.name) == DateTimeField:
                data[f.name] = obj.strftime('%Y-%m-%d %H:%M:%S')
            else:
                data[f.name] = obj
        return data

    @property
    def component_id(self):
        return self.service_id

    @property
    def upgrade_group_id(self):
        return self.tenant_service_group_id

    @property
    def clone_url(self):
        if self.code_from == "github":
            code_user = self.git_url.split("/")[3]
            code_project_name = self.git_url.split("/")[4].split(".")[0]
            createUser = Users.objects.get(user_id=self.creater)
            git_url = "https://{github_token}@github.com/{code_user}/{code_project_name}.git".format(
                github_token=createUser.github_token, code_user=code_user, code_project_name=code_project_name)
            return git_url
        else:
            return self.git_url

    def is_slug(self):
        return bool(self.image.endswith('/runner')) or bool('/runner:' in self.image)

    def is_third_party(self):
        if self.service_source == ComponentSource.THIRD_PARTY.value:
            return True
        return False


class TenantServiceInfoDelete(BaseModel):
    class Meta:
        db_table = 'tenant_service_delete'

    service_id = models.CharField(max_length=32, unique=True, help_text="组件id")
    tenant_id = models.CharField(max_length=32, help_text="租户id")
    service_key = models.CharField(max_length=32, help_text="组件key")
    service_alias = models.CharField(max_length=100, help_text="组件别名")
    service_cname = models.CharField(max_length=100, default='', help_text="组件名")
    service_region = models.CharField(max_length=64, help_text="组件所属区")
    desc = models.CharField(max_length=200, null=True, blank=True, help_text="描述")
    category = models.CharField(max_length=15, help_text="组件分类：application,cache,store")
    service_port = models.IntegerField(help_text="组件端口", default=8000)
    is_web_service = models.BooleanField(default=False, blank=True, help_text="是否web组件")
    version = models.CharField(max_length=255, help_text="版本")
    update_version = models.IntegerField(default=1, help_text="内部发布次数")
    image = models.CharField(max_length=200, help_text="镜像")
    cmd = models.CharField(max_length=2048, null=True, blank=True, help_text="启动参数")
    setting = models.CharField(max_length=200, null=True, blank=True, help_text="设置项")
    extend_method = models.CharField(max_length=32, default='stateless', help_text="伸缩方式")
    env = models.CharField(max_length=200, null=True, blank=True, help_text="环境变量")
    min_node = models.IntegerField(help_text="启动个数", default=1)
    min_cpu = models.IntegerField(help_text="cpu个数", default=500)
    min_memory = models.IntegerField(help_text="内存大小单位（M）", default=256)
    container_gpu = models.IntegerField(help_text="gpu显存数量", default=0)
    inner_port = models.IntegerField(help_text="内部端口")
    volume_mount_path = models.CharField(max_length=200, null=True, blank=True, help_text="mount目录")
    host_path = models.CharField(max_length=300, null=True, blank=True, help_text="mount目录")
    deploy_version = models.CharField(max_length=20, null=True, blank=True, help_text="部署版本")
    code_from = models.CharField(max_length=20, null=True, blank=True, help_text="代码来源:gitlab,github")
    git_url = models.CharField(max_length=200, null=True, blank=True, help_text="code代码仓库")
    create_time = models.DateTimeField(auto_now_add=True, blank=True, help_text="创建时间")
    git_project_id = models.IntegerField(help_text="gitlab 中项目id", default=0)
    is_code_upload = models.BooleanField(default=False, blank=True, help_text="是否上传代码")
    code_version = models.CharField(max_length=100, null=True, blank=True, help_text="代码版本")
    service_type = models.CharField(max_length=50, null=True, blank=True, help_text="组件类型:web,mysql,redis,mongodb,phpadmin")
    delete_time = models.DateTimeField(auto_now_add=True)
    creater = models.IntegerField(help_text="组件创建者", default=0)
    language = models.CharField(max_length=40, null=True, blank=True, help_text="代码语言")
    protocol = models.CharField(max_length=15, help_text="服务协议：http,stream")
    total_memory = models.IntegerField(help_text="内存使用M", default=0)
    is_service = models.BooleanField(default=False, blank=True, help_text="是否inner组件")
    namespace = models.CharField(max_length=100, default='', help_text="镜像发布云帮的区间")
    volume_type = models.CharField(max_length=64, default='shared', help_text="共享类型shared、exclusive")
    port_type = models.CharField(max_length=15, default='multi_outer', help_text="端口类型，one_outer;dif_protocol;multi_outer")
    # 组件创建类型,cloud、assistant
    service_origin = models.CharField(max_length=15, default='assistant', help_text="组件创建类型cloud云市组件,assistant云帮组件")
    expired_time = models.DateTimeField(null=True, help_text="过期时间")
    service_source = models.CharField(max_length=15, default="source_code", null=True, blank=True, help_text="组件来源")
    create_status = models.CharField(max_length=15, null=True, blank=True, help_text="组件创建状态 creating|complete")
    update_time = models.DateTimeField(auto_now_add=True, blank=True, help_text="更新时间")
    tenant_service_group_id = models.IntegerField(default=0, help_text="组件归属的组件组id")
    open_webhooks = models.BooleanField(default=False, help_text='是否开启自动触发部署功能(兼容老版本组件)')
    check_uuid = models.CharField(max_length=36, blank=True, null=True, default="", help_text="组件id")
    check_event_id = models.CharField(max_length=32, blank=True, null=True, default="", help_text="组件检测事件ID")
    docker_cmd = models.CharField(max_length=1024, null=True, blank=True, help_text="镜像创建命令")
    secret = models.CharField(max_length=64, null=True, blank=True, help_text="webhooks验证密码")
    server_type = models.CharField(max_length=5, default='git', help_text="源码仓库类型")
    is_upgrate = models.BooleanField(default=False, help_text='是否可以更新')
    build_upgrade = models.BooleanField(default=True, help_text='组件构建后是否升级')
    service_name = models.CharField(max_length=100, default='', help_text="组件名称（新加属性，数据中心使用）")
    k8s_component_name = models.CharField(max_length=100, help_text="集群组件名称")
    job_strategy = models.CharField(max_length=2047, null=True, default="", help_text="job任务策略")
    exec_user = models.CharField(max_length=128, default="", help_text="执行删除的用户")
    app_name = models.CharField(max_length=128, default="", help_text="应用名称")
    app_id = models.IntegerField(default=0, help_text="应用id")


class TenantServiceRelation(BaseModel):
    class Meta:
        db_table = 'tenant_service_relation'
        unique_together = ('service_id', 'dep_service_id')

    tenant_id = models.CharField(max_length=32, help_text="租户id")
    service_id = models.CharField(max_length=32, help_text="组件id")
    dep_service_id = models.CharField(max_length=32, help_text="依赖组件id")
    dep_service_type = models.CharField(max_length=50, null=True, blank=True, help_text="组件类型:web,mysql,redis,mongodb,phpadmin")
    dep_order = models.IntegerField(help_text="依赖顺序")


class TenantServiceEnv(BaseModel):
    class Meta:
        db_table = 'tenant_service_env'

    service_id = models.CharField(max_length=32, help_text="组件id")
    language = models.CharField(max_length=40, null=True, blank=True, help_text="代码语言")
    check_dependency = models.CharField(max_length=100, null=True, blank=True, help_text="检测运行环境依赖")
    user_dependency = models.CharField(max_length=1000, null=True, blank=True, help_text="用户自定义运行环境依赖")
    create_time = models.DateTimeField(auto_now_add=True, blank=True, help_text="创建时间")


class TenantServiceAuth(BaseModel):
    class Meta:
        db_table = 'tenant_service_auth'

    service_id = models.CharField(max_length=32, help_text="组件id")
    user = models.CharField(max_length=64, null=True, blank=True, help_text="用户")
    password = models.CharField(max_length=200, null=True, blank=True, help_text="密码")
    create_time = models.DateTimeField(auto_now_add=True, blank=True, help_text="创建时间")


class ServiceDomain(BaseModel):
    class Meta:
        db_table = 'service_domain'

    http_rule_id = models.CharField(max_length=128, unique=True, help_text="http_rule_id")
    region_id = models.CharField(max_length=36, help_text="region id")
    tenant_id = models.CharField(max_length=32, help_text="租户id")
    service_id = models.CharField(max_length=32, help_text="组件id")
    service_name = models.CharField(max_length=64, help_text="组件名")
    domain_name = models.CharField(max_length=128, help_text="域名")
    create_time = models.DateTimeField(auto_now_add=True, blank=True, help_text="创建时间")
    container_port = models.IntegerField(default=0, help_text="容器端口")
    protocol = models.CharField(max_length=15, default='http', help_text="域名类型 http https httptphttps httpandhttps")
    certificate_id = models.IntegerField(default=0, help_text='证书ID')
    domain_type = models.CharField(max_length=20, default='www', help_text="组件域名类型")
    service_alias = models.CharField(max_length=64, default='', help_text="组件别名")
    is_senior = models.BooleanField(default=False, help_text='是否有高级路由')
    domain_path = models.TextField(blank=True, help_text="域名path")
    domain_cookie = models.TextField(blank=True, help_text="域名cookie")
    domain_heander = models.TextField(blank=True, help_text="域名heander")
    type = models.IntegerField(default=0, help_text="类型（默认：0， 自定义：1）")
    the_weight = models.IntegerField(default=100, help_text="权重")
    rule_extensions = models.TextField(blank=True, help_text="扩展功能")
    is_outer_service = models.BooleanField(default=True, help_text="是否已开启对外端口")
    auto_ssl = models.BooleanField(default=False, help_text="是否自动匹配证书，升级为https，如果开启，由外部服务完成升级")
    auto_ssl_config = models.CharField(max_length=32, null=True, default=None, blank=True, help_text="自动分发证书配置")
    path_rewrite = models.BooleanField(default=False, help_text="是否开启简单路由重写")
    rewrites = models.TextField(blank=True, help_text="复杂路由重写配置")

    def __unicode__(self):
        return self.domain_name

    @property
    def load_balancing(self):
        for ext in self.rule_extensions.split(","):
            ext = ext.split(":")
            if len(ext) != 2 or ext[0] == "" or ext[1] == "":
                continue
            if ext[0] == "lb-type":
                return ext[1]
        # round-robin is the default value of load balancing
        return "round-robin"


class ServiceDomainCertificate(BaseModel):
    class Meta:
        db_table = 'service_domain_certificate'

    tenant_id = models.CharField(max_length=32, help_text="租户id")
    certificate_id = models.CharField(max_length=50, help_text="证书的唯一uuid")
    private_key = models.TextField(default='', help_text="证书key")
    certificate = models.TextField(default='', help_text='证书')
    certificate_type = models.TextField(default='', help_text='证书类型')
    create_time = models.DateTimeField(auto_now_add=True, blank=True, help_text="创建时间")
    alias = models.CharField(max_length=64, help_text="证书别名")

    def __unicode__(self):
        return "private_key:{} certificate:{}".format(self.private_key, self.certificate)


class PermRelService(BaseModel):
    """
    用户和组件关系表/用户在一个组件中的角色
    """

    class Meta:
        db_table = 'service_perms'

    user_id = models.IntegerField(help_text="用户id")
    service_id = models.IntegerField(help_text="组件id")
    identity = models.CharField(max_length=15, choices=service_identity, help_text="组件身份", null=True, blank=True)
    role_id = models.IntegerField(help_text='角色', null=True, blank=True)


class PermRelTenant(BaseModel):
    """
    用户和团队的关系表
    identity ：租户权限
    """

    class Meta:
        db_table = 'tenant_perms'

    user_id = models.IntegerField(help_text="关联用户")
    tenant_id = models.IntegerField(help_text="团队id")
    identity = models.CharField(max_length=15, choices=tenant_identity, help_text="租户身份", null=True, blank=True)
    enterprise_id = models.IntegerField(help_text="关联企业")
    role_id = models.IntegerField(help_text='角色', null=True, blank=True)


class TenantServiceEnvVar(BaseModel):
    class Meta:
        db_table = 'tenant_service_env_var'

    class ScopeType(Enum):
        """范围"""
        OUTER = "outer"
        INNER = "inner"

    tenant_id = models.CharField(max_length=32, help_text="租户id")
    service_id = models.CharField(max_length=32, db_index=True, help_text="组件id")
    container_port = models.IntegerField(default=0, help_text="端口")
    name = models.CharField(max_length=1024, blank=True, help_text="名称")
    attr_name = models.CharField(max_length=1024, help_text="属性")
    attr_value = models.TextField(help_text="值")
    is_change = models.BooleanField(default=False, blank=True, help_text="是否可改变")
    scope = models.CharField(max_length=10, help_text="范围", default=ScopeType.OUTER.value)
    create_time = models.DateTimeField(auto_now_add=True, help_text="创建时间")

    def __unicode__(self):
        return self.name

    def is_port_env(self):
        return self.container_port != 0

    def is_host_env(self):
        return self.container_port != 0 and self.attr_name.endswith("_HOST")


class TenantServicesPort(BaseModel):
    class Meta:
        db_table = 'tenant_services_port'
        unique_together = ('service_id', 'container_port')

    tenant_id = models.CharField(max_length=32, null=True, blank=True, help_text='租户id')
    service_id = models.CharField(max_length=32, db_index=True, help_text="组件ID")
    container_port = models.IntegerField(default=0, help_text="容器端口")
    mapping_port = models.IntegerField(default=0, help_text="映射端口")
    lb_mapping_port = models.IntegerField(default=0, help_text="负载均衡映射端口")
    protocol = models.CharField(max_length=15, default='', blank=True, help_text="组件协议：http,stream")
    port_alias = models.CharField(max_length=64, default='', blank=True, help_text="port别名")
    is_inner_service = models.BooleanField(default=False, blank=True, help_text="是否内部组件；0:不绑定；1:绑定")
    is_outer_service = models.BooleanField(default=False, blank=True, help_text="是否外部组件；0:不绑定；1:绑定")
    k8s_service_name = models.CharField(max_length=63, blank=True, help_text="the name of kubernetes service")
    name = models.CharField(max_length=64, blank=True, null=True, help_text="端口名称")


class TenantServiceMountRelation(BaseModel):
    class Meta:
        db_table = 'tenant_service_mnt_relation'
        unique_together = ('service_id', 'dep_service_id', 'mnt_name')

    tenant_id = models.CharField(max_length=32, help_text="租户id")
    service_id = models.CharField(max_length=32, help_text="组件id")
    dep_service_id = models.CharField(max_length=32, help_text="依赖组件id")
    mnt_name = models.CharField(max_length=100, help_text="mnt name")
    mnt_dir = models.CharField(max_length=400, help_text="mnt dir")

    def key(self):
        return self.service_id + self.dep_service_id + self.mnt_name


class TenantServiceVolume(BaseModel):
    """数据持久化表格"""

    class Meta:
        db_table = 'tenant_service_volume'

    SHARE = 'share-file'
    LOCAL = 'local'
    TMPFS = 'memoryfs'
    CONFIGFILE = 'config-file'

    service_id = models.CharField(max_length=32, help_text="组件id")
    category = models.CharField(max_length=50, blank=True, help_text="组件类型")
    host_path = models.CharField(max_length=400, help_text="物理机的路径,绝对路径")
    volume_type = models.CharField(max_length=64, blank=True)
    volume_path = models.CharField(max_length=400, help_text="容器内路径,application为相对;其他为绝对")
    volume_name = models.CharField(max_length=100, blank=True)
    volume_capacity = models.IntegerField(default=0, help_text="存储大小，单位(Mi)")
    volume_provider_name = models.CharField(max_length=100, null=True, blank=True, help_text="存储驱动名字")
    access_mode = models.CharField(max_length=100, null=True, blank=True, help_text="读写模式：RWO、ROX、RWX")
    share_policy = models.CharField(max_length=100, null=True, default='', blank=True, help_text="共享模式")
    backup_policy = models.CharField(max_length=100, null=True, default='', blank=True, help_text="备份策略")
    reclaim_policy = models.CharField(max_length=100, null=True, default='', blank=True, help_text="回收策略")
    allow_expansion = models.NullBooleanField(max_length=100, null=True, default=0, blank=True, help_text="只是支持控制扩展，0：不支持；1：支持")
    mode = models.IntegerField(null=True, help_text="存储权限")


class TenantServiceConfigurationFile(BaseModel):
    """组件配置文件"""

    class Meta:
        db_table = 'tenant_service_config'

    service_id = models.CharField(max_length=32, help_text="组件id")
    volume_id = models.IntegerField(null=True, help_text="存储id")
    volume_name = models.CharField(max_length=32, null=True, help_text="组件名称, 唯一标识")
    file_content = models.TextField(blank=True, help_text="配置文件内容")


class ServiceGroup(BaseModel):
    """组件分组（应用）"""

    class Meta:
        db_table = 'service_group'

    tenant_id = models.CharField(max_length=32, help_text="租户id")
    group_name = models.CharField(max_length=128, help_text="组名")
    region_name = models.CharField(max_length=64, help_text="区域中心名称")
    is_default = models.BooleanField(default=False, help_text="默认组件")
    order_index = models.IntegerField(default=0, help_text="应用排序")
    note = models.CharField(max_length=2048, null=True, blank=True, help_text="备注")
    username = models.CharField(max_length=255, null=True, blank=True, help_text="the username of principal")
    governance_mode = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        default=GovernanceModeEnum.KUBERNETES_NATIVE_SERVICE.name,
        help_text="governance mode")
    create_time = models.DateTimeField(help_text="创建时间")
    update_time = models.DateTimeField(help_text="更新时间")
    app_type = models.CharField(max_length=255, default="rainbond", help_text="应用类型")
    app_store_name = models.CharField(max_length=255, null=True, blank=True, help_text="应用商店名称")
    app_store_url = models.CharField(max_length=255, null=True, blank=True, help_text="应用商店 URL")
    app_template_name = models.CharField(max_length=255, null=True, blank=True, help_text="应用模板名称")
    version = models.CharField(max_length=255, null=True, blank=True, help_text="Helm 应用版本")
    logo = models.CharField(max_length=255, blank=True, null=True, default='', help_text="应用logo")
    k8s_app = models.CharField(max_length=64, default='', help_text="集群内应用名称")

    @property
    def app_id(self):
        return self.ID

    @property
    def app_name(self):
        return self.group_name


class ServiceGroupRelation(BaseModel):
    """组件与分组关系"""

    class Meta:
        db_table = 'service_group_relation'

    service_id = models.CharField(max_length=32, help_text="组件id")
    group_id = models.IntegerField()
    tenant_id = models.CharField(max_length=32, help_text="租户id")
    region_name = models.CharField(max_length=64, help_text="区域中心名称")


class RegionApp(BaseModel):
    """the dependencies between region app and console app"""

    class Meta:
        db_table = 'region_app'
        unique_together = ('region_name', 'region_app_id', 'app_id')

    region_name = models.CharField(max_length=64, help_text="region name")
    region_app_id = models.CharField(max_length=32, help_text="region app id")
    app_id = models.IntegerField()


pay_status = (
    ("已发布", 'payed'),
    ("测试中", "unpayed"),
)


class ServiceEvent(BaseModel):
    class Meta:
        db_table = 'service_event'

    event_id = models.CharField(max_length=32, help_text="操作id")
    tenant_id = models.CharField(max_length=32, help_text="租户id")
    service_id = models.CharField(max_length=32, help_text="组件id")
    user_name = models.CharField(max_length=64, help_text="操作用户")
    start_time = models.DateTimeField(help_text="操作开始时间")
    end_time = models.DateTimeField(help_text="操作结束时间", null=True)
    type = models.CharField(max_length=20, help_text="操作类型")
    status = models.CharField(max_length=20, help_text="操作处理状态 success failure")
    final_status = models.CharField(max_length=20, default="", help_text="操作状态，complete or timeout or null")
    message = models.TextField(help_text="操作说明")
    deploy_version = models.CharField(max_length=20, help_text="部署版本")
    old_deploy_version = models.CharField(max_length=20, help_text="历史部署版本")
    code_version = models.CharField(max_length=200, help_text="部署代码版本")
    old_code_version = models.CharField(max_length=200, help_text="历史部署代码版本")
    region = models.CharField(max_length=64, default="", help_text="组件所属数据中心")


class ServiceProbe(BaseModel):
    class Meta:
        db_table = 'service_probe'

    service_id = models.CharField(max_length=32, help_text="组件id")
    probe_id = models.CharField(max_length=32, help_text="探针id")
    mode = models.CharField(max_length=20, help_text="不健康处理方式readiness（下线）或liveness（重启）或ignore（忽略）")
    scheme = models.CharField(max_length=10, default="tcp", help_text="探针使用协议,tcp,http,cmd")
    path = models.CharField(max_length=200, default="", help_text="路径")
    port = models.IntegerField(default=80, help_text="检测端口")
    cmd = models.CharField(max_length=1024, default="", help_text="cmd 命令")
    http_header = models.CharField(max_length=300, blank=True, default="", help_text="http请求头，key=value,key2=value2")
    initial_delay_second = models.IntegerField(default=4, help_text="初始化等候时间")
    period_second = models.IntegerField(default=3, help_text="检测间隔时间")
    timeout_second = models.IntegerField(default=5, help_text="检测超时时间")
    failure_threshold = models.IntegerField(default=3, help_text="标志为失败的检测次数")
    success_threshold = models.IntegerField(default=1, help_text="标志为成功的检测次数")
    is_used = models.BooleanField(default=1, help_text="是否启用")


class ConsoleConfig(BaseModel):
    class Meta:
        db_table = 'console_config'

    key = models.CharField(max_length=100, help_text="配置名称")
    value = models.CharField(max_length=1000, help_text="配置值")
    description = models.TextField(null=True, blank=True, default="", help_text="说明")
    update_time = models.DateTimeField(help_text="更新时间", null=True)
    user_nick_name = models.CharField(max_length=64, help_text="用户名称", default="")


class TenantEnterprise(BaseModel):
    class Meta:
        db_table = 'tenant_enterprise'

    enterprise_id = models.CharField(max_length=32, unique=True, help_text="企业id")
    enterprise_name = models.CharField(max_length=64, help_text="企业名称")
    enterprise_alias = models.CharField(max_length=64, blank=True, null=True, default='', help_text="企业别名")
    create_time = models.DateTimeField(auto_now_add=True, blank=True, null=True, help_text="创建时间")
    enterprise_token = models.CharField(max_length=256, blank=True, null=True, default='', help_text="企业身份token")
    is_active = models.IntegerField(default=0, help_text="是否在云市上激活, 0:未激活, 1:已激活")
    logo = models.CharField(max_length=128, blank=True, null=True, default='', help_text="企业logo")

    def __unicode__(self):
        return self.to_dict()


class TenantEnterpriseToken(BaseModel):
    class Meta:
        db_table = 'tenant_enterprise_token'
        unique_together = ('enterprise_id', 'access_target')

    enterprise_id = models.IntegerField(default=0, help_text="企业id")
    access_target = models.CharField(max_length=32, blank=True, null=True, default='', help_text="要访问的目标组件名称")
    access_url = models.CharField(max_length=255, help_text="需要访问的api地址")
    access_id = models.CharField(max_length=32, help_text="target分配给客户端的ID")
    access_token = models.CharField(max_length=256, blank=True, null=True, default='', help_text="客户端token")
    crt = models.TextField(default='', blank=True, null=True, help_text="客户端证书")
    key = models.TextField(default='', blank=True, null=True, help_text="客户端证书key")
    create_time = models.DateTimeField(auto_now_add=True, blank=True, null=True, help_text="创建时间")
    update_time = models.DateTimeField(auto_now_add=True, blank=True, null=True, help_text="更新时间")

    def __unicode__(self):
        return self.to_dict()


class TenantServiceGroup(BaseModel):
    """从应用模型安装的组件从属关系记录"""

    class Meta:
        db_table = 'tenant_service_group'

    tenant_id = models.CharField(max_length=32, help_text="租户id")
    group_name = models.CharField(max_length=64, help_text="组件组名")
    group_alias = models.CharField(max_length=64, help_text="组件别名")
    group_key = models.CharField(max_length=32, help_text="组件组id")
    group_version = models.CharField(max_length=32, help_text="组件组版本")
    region_name = models.CharField(max_length=64, help_text="区域中心名称")
    service_group_id = models.IntegerField(default=0, help_text="安装时所属应用的主键ID")


class ServiceTcpDomain(BaseModel):
    """Tcp/Udp策略"""

    class Meta:
        db_table = 'service_tcp_domain'

    tcp_rule_id = models.CharField(max_length=128, unique=True, help_text="tcp_rule_id")
    region_id = models.CharField(max_length=36, help_text="region id")
    tenant_id = models.CharField(max_length=32, help_text="租户id")
    service_id = models.CharField(max_length=32, help_text="组件id")
    service_name = models.CharField(max_length=64, help_text="组件名")
    end_point = models.CharField(max_length=256, help_text="ip+port")
    create_time = models.DateTimeField(auto_now_add=True, blank=True, help_text="创建时间")
    protocol = models.CharField(max_length=15, default='', blank=True, help_text="服务协议：tcp,udp")
    container_port = models.IntegerField(default=0, help_text="容器端口")
    service_alias = models.CharField(max_length=64, default='', help_text="组件别名")
    type = models.IntegerField(default=0, help_text="类型（默认：0， 自定义：1）")
    rule_extensions = models.TextField(null=True, blank=True, help_text="扩展功能")
    is_outer_service = models.BooleanField(default=True, help_text="是否已开启对外端口")

    @property
    def load_balancing(self):
        for ext in self.rule_extensions.split(","):
            ext = ext.split(":")
            if len(ext) != 2 or ext[0] == "" or ext[1] == "":
                continue
            if ext[0] == "lb-type":
                return ext[1]
        # round-robin is the default value of load balancing
        return "round-robin"


class ThirdPartyServiceEndpoints(BaseModel):
    """第三方组件endpoints"""

    class Meta:
        db_table = 'third_party_service_endpoints'

    tenant_id = models.CharField(max_length=32, help_text="租户id")
    service_id = models.CharField(max_length=32, help_text="组件id")
    service_cname = models.CharField(max_length=128, help_text="组件名")
    endpoints_info = models.TextField(help_text="endpoints信息")
    endpoints_type = models.CharField(max_length=32, help_text="类型（static-静态， api， discovery-服务发现）")


class ServiceWebhooks(BaseModel):
    """组件的自动部署属性"""

    class Meta:
        db_table = 'service_webhooks'

    service_id = models.CharField(max_length=32, help_text="组件id")
    state = models.BooleanField(default=False, help_text="状态（开启，关闭）")
    webhooks_type = models.CharField(max_length=128, help_text="webhooks类型（image_webhooks, code_webhooks, api_webhooks）")
    deploy_keyword = models.CharField(max_length=128, default='deploy', help_text="触发自动部署关键字")
    trigger = models.CharField(max_length=256, default='', help_text="触发正则表达式")


class GatewayCustomConfiguration(BaseModel):
    """网关自定义参数配置"""

    class Meta:
        db_table = 'gateway_custom_configuration'

    rule_id = models.CharField(max_length=32, unique=True, help_text="规则id")
    value = models.TextField(help_text="配置value")


class Menus(models.Model):
    """菜单管理"""

    class Meta:
        db_table = "menus"

    eid = models.CharField(max_length=32, null=True, blank=True, default='', help_text="企业id")
    title = models.CharField(max_length=64, null=True, blank=True, default='', help_text="菜单标题")
    path = models.TextField(help_text="菜单链接")
    parent_id = models.IntegerField(default=0, help_text="父级id")
    iframe = models.BooleanField(default=False, help_text="true:新开窗口; false:当前窗口")
    sequence = models.IntegerField(default=0, help_text="")


class VirtualMachineImage(BaseModel):
    """虚拟机镜像管理"""

    class Meta:
        db_table = "virtual_machine_image"

    tenant_id = models.CharField(max_length=32, help_text="租户id")
    name = models.CharField(max_length=64, help_text="镜像名称")
    image_url = models.CharField(max_length=200, help_text="镜像地址")


class TaskEvent(BaseModel):
    class Meta:
        db_table = 'task_event'

    task_id = models.CharField(max_length=255)  # 对应 TaskID
    enterprise_id = models.CharField(max_length=255)  # 对应 EnterpriseID
    step_type = models.CharField(max_length=255)  # 对应 StepType
    message = models.CharField(max_length=512)  # 对应 Message
    status = models.CharField(max_length=255)  # 对应 Status
    event_id = models.CharField(max_length=255)  # 对应 EventID
    reason = models.CharField(max_length=255)  # 对应 Reason


class TeamInvitation(BaseModel):
    """团队邀请信息"""
    
    class Meta:
        db_table = 'team_invitation'
        
    invitation_id = models.CharField(max_length=32, unique=True, help_text="邀请ID")
    tenant_id = models.CharField(max_length=32, help_text="团队ID") 
    inviter_id = models.IntegerField(help_text="邀请人ID")
    role_id = models.IntegerField(help_text="角色ID", null=True, blank=True)
    expired_time = models.DateTimeField(help_text="过期时间")
    is_accepted = models.BooleanField(default=False, help_text="是否已接受邀请")
    create_time = models.DateTimeField(auto_now_add=True, help_text="创建时间")
