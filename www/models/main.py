# -*- coding: utf8 -*-
from datetime import datetime

import re
from django.conf import settings
from django.db import models
from django.db.models.fields import DateTimeField
from django.utils.crypto import salted_hmac

from www.utils.crypt import encrypt_passwd, make_tenant_id, make_uuid
from django.db.models.fields import DateTimeField
from datetime import datetime
from django.db.models.fields.files import FileField
from django.conf import settings
import logging

logger = logging.getLogger("default")

# Create your models here.

user_origion = ((u"自主注册", "registration"), (u"邀请注册", "invitation"))

tenant_type = ((u"免费租户", "free"), (u"付费租户", "payed"))

service_identity = ((u"管理员", "admin"), (u"开发者", "developer"), (u"观察者", "viewer"))

tenant_identity = ((u"拥有者", "owner"), (u"管理员", "admin"), (u"开发者", "developer"),
                   (u"观察者", "viewer"), (u"访问", "access"))

app_pay_choices = ((u'免费', "free"), (u'付费', "pay"))

pay_method = ((u'预付费提前采购', "prepaid"), (u'按使用后付费', "postpaid"))


def compose_file_path(instance, filename):
    suffix = filename.split('.')[-1]
    return '{0}/compose-file/{1}.{2}'.format(settings.MEDIA_ROOT,
                                             make_uuid(), suffix)


class AnonymousUser(object):
    id = None
    pk = None
    username = ''

    def __init__(self):
        pass

    def __str__(self):
        return 'AnonymousUser'

    def __eq__(self, other):
        return isinstance(other, self.__class__)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return 1  # instances always return the same hash value

    def save(self):
        raise NotImplementedError(
            "Django doesn't provide a DB representation for AnonymousUser.")

    def delete(self):
        raise NotImplementedError(
            "Django doesn't provide a DB representation for AnonymousUser.")

    def set_password(self, raw_password):
        raise NotImplementedError(
            "Django doesn't provide a DB representation for AnonymousUser.")

    def check_password(self, raw_password):
        raise NotImplementedError(
            "Django doesn't provide a DB representation for AnonymousUser.")

    def get_group_permissions(self, obj=None):
        return set()

    def is_anonymous(self):
        return True

    def is_authenticated(self):
        return False


class WeChatConfig(models.Model):
    """微信的accesstoken"""

    class Meta:
        db_table = "wechat_config"

    MOBILE = "mobile"
    WEB = "web"
    BIZ = "biz"
    BIZPLUGIN = "bizplugin"

    OPEN_TYPE = ((MOBILE, "移动应用"), (WEB, "网站应用"), (BIZ, "公众帐号"), (BIZPLUGIN,
                                                                  "公众号第三方平台"))

    config = models.CharField(
        unique=True, max_length=100, help_text=u'微信应用的名称')
    app_id = models.CharField(max_length=200, help_text=u'app_id')
    app_secret = models.CharField(max_length=200, help_text=u'app_secret')
    token = models.CharField(max_length=200, help_text=u'token')
    encrypt_mode = models.CharField(max_length=200, help_text=u'encrypt_mode')
    encoding_aes_key = models.CharField(max_length=200, help_text=u'aes_key')
    access_token = models.CharField(max_length=200, help_text=u'access_token')
    access_token_expires_at = models.IntegerField(help_text=u"token过期时间")
    refresh_token = models.CharField(
        max_length=200, help_text=u'refresh_token,只对网页授权有效')
    app_type = models.CharField(
        max_length=200, choices=OPEN_TYPE, help_text=u'公众平台or网站')


class WeChatUser(models.Model):
    """微信用户表格"""

    class Meta:
        db_table = "wechat_user_info"

    open_id = models.CharField(
        primary_key=True, max_length=200, help_text=u'微信用户open_id')
    nick_name = models.CharField(max_length=100, help_text=u"微信用户昵称")
    sex = models.IntegerField(help_text=u'性别')
    city = models.CharField(max_length=100, help_text=u'城市')
    province = models.CharField(max_length=100, help_text=u'省地区')
    country = models.CharField(max_length=100, help_text=u'国家')
    headimgurl = models.CharField(max_length=200, help_text=u'头像')
    union_id = models.CharField(max_length=200, help_text=u'微信用户union_id')
    config = models.CharField(max_length=100, help_text=u'所属的微信应用')

    def is_authenticated(self):
        return True

    @property
    def is_sys_admin(self):
        admins = ('ertyuiofghjklasdfas',)
        return bool(self.unionid in admins)

    def get_session_auth_hash(self):
        key_salt = "goodrain.com.models.get_session_auth_hash"
        return salted_hmac(key_salt, self.user_id).hexdigest()

    def to_dict(self):
        opts = self._meta
        data = {}
        for f in opts.concrete_fields:
            value = f.value_from_object(self)
            if isinstance(value, datetime):
                value = value.strftime('%Y-%m-%d %H:%M:%S')
            data[f.name] = value
        return data


class WeChatUnBind(models.Model):
    """解绑用户的映射关系"""

    class Meta:
        db_table = 'wechat_unbind'

    user_id = models.IntegerField(help_text=u"用户的user_id")
    union_id = models.CharField(max_length=200, help_text=u'微信用户union_id')
    status = models.IntegerField(help_text=u'用户解绑的状态')


class WeChatState(models.Model):
    """微信state过长存储表格"""

    class Meta:
        db_table = 'wechat_state'

    ID = models.AutoField(primary_key=True, max_length=10)
    state = models.CharField(max_length=5000, help_text=u'微信登录state')
    create_time = models.DateTimeField(
        auto_now_add=True, blank=True, help_text=u"创建时间")
    update_time = models.DateTimeField(auto_now=True, help_text=u"更新时间")

    def to_dict(self):
        opts = self._meta
        data = {}
        for f in opts.concrete_fields:
            value = f.value_from_object(self)
            if isinstance(value, datetime):
                value = value.strftime('%Y-%m-%d %H:%M:%S')
            data[f.name] = value
        return data


class SuperAdminUser(models.Model):
    """超级管理员"""

    class Meta:
        db_table = "user_administrator"

    user_id = models.IntegerField(unique=True, help_text=u"用户ID")
    email = models.EmailField(max_length=35, null=True, blank=True, help_text=u"邮件地址")


class Users(models.Model):
    USERNAME_FIELD = 'nick_name'

    class Meta:
        db_table = 'user_info'

    user_id = models.AutoField(primary_key=True, max_length=10)
    email = models.EmailField(max_length=35, help_text=u"邮件地址")
    nick_name = models.CharField(
        max_length=24, unique=True, null=True, blank=True, help_text=u"用户昵称")
    password = models.CharField(max_length=16, help_text=u"密码")
    phone = models.CharField(
        max_length=11, null=True, blank=True, help_text=u"手机号码")
    is_active = models.BooleanField(default=False, help_text=u"激活状态")
    origion = models.CharField(
        max_length=12, choices=user_origion, help_text=u"用户来源")
    create_time = models.DateTimeField(
        auto_now_add=True, blank=True, help_text=u"创建时间")
    git_user_id = models.IntegerField(help_text=u"gitlab 用户id", default=0)
    github_token = models.CharField(max_length=60, help_text=u"github token")
    client_ip = models.CharField(max_length=20, help_text=u"注册ip")
    rf = models.CharField(max_length=60, help_text=u"register from")
    # 0:普通注册,未绑定微信
    # 1:普通注册,绑定微信
    # 2:微信注册,绑定微信,未补充信息
    # 3:微信注册,绑定微信,已补充信息
    # 4:微信注册,解除微信绑定,已补充信息
    status = models.IntegerField(default=0, help_text=u'用户类型 0:普通注册,未绑定微信')
    union_id = models.CharField(max_length=100, help_text=u'绑定微信的union_id')
    sso_user_id = models.CharField(max_length=32, null=True, blank=True, default='', help_text=u"统一认证中心的user_id")
    sso_user_token = models.CharField(max_length=256, null=True, blank=True, default='', help_text=u"统一认证中心的user_id")
    enterprise_id = models.CharField(max_length=32, null=True, blank=True, default='',
                                     help_text=u"统一认证中心的enterprise_id")

    def set_password(self, raw_password):
        self.password = encrypt_passwd(self.email + raw_password)

    def check_password(self, raw_password):
        return bool(encrypt_passwd(self.email + raw_password) == self.password)

    def is_anonymous(self):
        return False

    def is_authenticated(self):
        return True

    @property
    def is_sys_admin(self):
        """
        是否是系统管理员
        :return: True/False
        """
        # admins = ('liufan@gmail.com', 'messi@goodrain.com', 'elviszhang@163.com', 'rhino@goodrain.com',
        #           'ethan@goodrain.com', 'fanfan@goodrain.com', 'wangjiajun33wjj@126.com', 'linmu0001@126.com')
        # return bool(self.email in admins)
        if self.user_id:
            try:
                SuperAdminUser.objects.get(user_id=self.user_id)
                return True
            except SuperAdminUser.DoesNotExist:
                pass
        return False

    def get_session_auth_hash(self):
        """
        Returns an HMAC of the password field.
        """
        key_salt = "goodrain.com.models.get_session_auth_hash"
        return salted_hmac(key_salt, self.password).hexdigest()

    @property
    def safe_email(self):
        return re.sub(r'(?<=\w{2}).*(?=\w@.*)', 'xxxx', self.email)

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


class Tenants(BaseModel):
    """
    租户表
    """
    class Meta:
        db_table = 'tenant_info'

    tenant_id = models.CharField(
        max_length=33, unique=True, default=make_tenant_id, help_text=u"租户id")
    tenant_name = models.CharField(
        max_length=40, unique=True, help_text=u"租户名称")
    region = models.CharField(
        max_length=30, default='', help_text=u"区域中心")
    is_active = models.BooleanField(default=True, help_text=u"激活状态")
    pay_type = models.CharField(
        max_length=5, choices=tenant_type, help_text=u"付费状态")
    balance = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00, help_text=u"账户余额")
    create_time = models.DateTimeField(
        auto_now_add=True, blank=True, help_text=u"创建时间")
    creater = models.IntegerField(help_text=u"租户创建者", default=0)
    limit_memory = models.IntegerField(help_text=u"内存大小单位（M）", default=1024)
    update_time = models.DateTimeField(auto_now=True, help_text=u"更新时间")
    pay_level = models.CharField(
        max_length=30, default='free', help_text=u"付费级别:free,personal,company")
    expired_time = models.DateTimeField(null=True, help_text=u"过期时间")
    tenant_alias = models.CharField(max_length=64, null=True, blank=True, default='', help_text=u"团队别名")
    enterprise_id = models.CharField(max_length=32, null=True, blank=True, default='', help_text=u"企业id")

    def __unicode__(self):
        return self.tenant_name


class TenantRegionInfo(BaseModel):
    class Meta:
        db_table = 'tenant_region'
        unique_together = (('tenant_id', 'region_name'),)

    tenant_id = models.CharField(
        max_length=33, db_index=True, help_text=u"租户id")
    region_name = models.CharField(max_length=20, help_text=u"区域中心名称")
    is_active = models.BooleanField(default=True, help_text=u"是否已激活")
    is_init = models.BooleanField(default=False, help_text=u'是否创建租户网络')
    service_status = models.IntegerField(
        help_text=u"服务状态0:暂停，1:运行，2:关闭", default=1)
    create_time = models.DateTimeField(
        auto_now_add=True, blank=True, help_text=u"创建时间")
    update_time = models.DateTimeField(auto_now=True, help_text=u"更新时间")
    region_tenant_name = models.CharField(max_length=32, null=True, blank=True, default='', help_text=u"数据中心租户名")
    region_tenant_id = models.CharField(max_length=32, null=True, blank=True, default='', help_text=u"数据中心租户id")
    region_scope = models.CharField(max_length=32, null=True, blank=True, default='',
                                    help_text=u"数据中心类型 private/public")
    enterprise_id = models.CharField(max_length=32, null=True, blank=True, default='', help_text=u"企业id")


class TenantRegionResource(BaseModel):
    class Meta:
        db_table = 'tenant_region_resource'
        unique_together = (('tenant_id', 'region_name'),)

    enterprise_id = models.CharField(max_length=32, help_text=u"企业id")
    tenant_id = models.CharField(max_length=33, help_text=u"租户id")
    region_name = models.CharField(max_length=20, help_text=u"区域中心名称")
    memory_limit = models.IntegerField(help_text=u"内存使用上限(M)", default=0)
    memory_expire_date = models.DateTimeField(null=True, blank=True, help_text=u"内存有效期时间")
    disk_limit = models.IntegerField(help_text=u"磁盘使用上限(M)", default=0)
    disk_expire_date = models.DateTimeField(null=True, blank=True, help_text=u"磁盘有效期时间")
    net_limit = models.IntegerField(help_text=u"磁盘使用上限(M)", default=0)
    net_stock = models.IntegerField(help_text=u"磁盘使用余量(M)", default=0)
    create_time = models.DateTimeField(auto_now_add=True, blank=True, help_text=u"创建时间")
    update_time = models.DateTimeField(auto_now=True, help_text=u"更新时间")

service_status = ((u"已发布", 'published'), (u"测试中", "test"),)

service_category = ((u"应用", 'application'), (u"缓存", 'cache'), (u"存储", 'store'))

extend_method = ((u"不伸缩", 'stateless'), (u"垂直伸缩", 'vertical'))


class ServiceExec(BaseModel):
    """ 容器运行命令 """

    class Meta:
        db_table = 'service_exec'

    tenant_id = models.CharField(max_length=33, db_index=True, help_text=u"租户id")
    service_id = models.CharField(max_length=32, unique=True, help_text=u"服务id")
    run_exec = models.CharField(max_length=2048, null=True, help_text=u"容器运行命令")


class ServiceInfo(BaseModel):
    """ 服务发布表格 """

    class Meta:
        db_table = 'service'
        unique_together = ('service_key', 'version')

    service_key = models.CharField(max_length=32, help_text=u"服务key")
    publisher = models.EmailField(max_length=35, help_text=u"邮件地址")
    service_name = models.CharField(max_length=100, help_text=u"服务发布名称")
    pic = models.CharField(
        max_length=100, null=True, blank=True, help_text=u"logo")
    info = models.CharField(
        max_length=100, null=True, blank=True, help_text=u"简介")
    desc = models.CharField(
        max_length=400, null=True, blank=True, help_text=u"描述")
    status = models.CharField(
        max_length=15, choices=service_status, help_text=u"服务状态：发布后显示还是隐藏")
    category = models.CharField(
        max_length=15, help_text=u"服务分类：application,cache,store")
    is_service = models.BooleanField(
        default=False, blank=True, help_text=u"是否inner服务")
    is_web_service = models.BooleanField(
        default=False, blank=True, help_text=u"是否web服务")
    version = models.CharField(max_length=20, null=False, help_text=u"当前最新版本")
    update_version = models.IntegerField(default=1, help_text=u"内部发布次数")
    image = models.CharField(max_length=100, help_text=u"镜像")
    namespace = models.CharField(
        max_length=100, default='', help_text=u"镜像发布云帮的区间")
    slug = models.CharField(max_length=200, help_text=u"slug包路径", default="")
    extend_method = models.CharField(
        max_length=15,
        choices=extend_method,
        default='stateless',
        help_text=u"伸缩方式")
    cmd = models.CharField(
        max_length=2048, null=True, blank=True, help_text=u"启动参数")
    setting = models.CharField(
        max_length=100, null=True, blank=True, help_text=u"设置项")
    env = models.CharField(
        max_length=200, null=True, blank=True, help_text=u"环境变量")
    dependecy = models.CharField(
        max_length=100, default="", help_text=u"依赖服务--service_key待确认")
    min_node = models.IntegerField(help_text=u"启动个数", default=1)
    min_cpu = models.IntegerField(help_text=u"cpu个数", default=500)
    min_memory = models.IntegerField(help_text=u"内存大小单位（M）", default=256)
    inner_port = models.IntegerField(help_text=u"内部端口", default=0)
    publish_time = models.DateTimeField(
        auto_now_add=True, blank=True, help_text=u"创建时间")
    volume_mount_path = models.CharField(
        max_length=50, null=True, blank=True, help_text=u"mount目录")
    service_type = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text=u"服务类型:web,mysql,redis,mongodb,phpadmin")
    is_init_accout = models.BooleanField(
        default=False, blank=True, help_text=u"是否初始化账户")
    creater = models.IntegerField(null=True, help_text=u"创建人")
    publish_type = models.CharField(
        max_length=10, default="single", help_text=u"判断服务是否属于组")

    def is_slug(self):
        return bool(self.image.startswith('goodrain.me/runner'))
        # return bool(self.image.endswith('/runner')) or bool(self.image.search('/runner:+'))

    def is_image(self):
        return not self.is_slug()


class TenantServiceInfo(BaseModel):
    class Meta:
        db_table = 'tenant_service'
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
        choices=extend_method,
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
    def clone_url(self):
        if self.code_from == "github":
            code_user = self.git_url.split("/")[3]
            code_project_name = self.git_url.split("/")[4].split(".")[0]
            createUser = Users.objects.get(user_id=self.creater)
            git_url = "https://" + createUser.github_token + "@github.com/" + code_user + "/" + code_project_name + ".git"
            return git_url
        else:
            return self.git_url

    def is_slug(self):
        # return bool(self.image.startswith('goodrain.me/runner'))
        return bool(self.image.endswith('/runner')) or bool(
            '/runner:' in self.image)


class TenantServiceInfoDelete(BaseModel):
    class Meta:
        db_table = 'tenant_service_delete'

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
    service_port = models.IntegerField(help_text=u"服务端口", default=8000)
    is_web_service = models.BooleanField(
        default=False, blank=True, help_text=u"是否web服务")
    version = models.CharField(max_length=20, help_text=u"版本")
    update_version = models.IntegerField(default=1, help_text=u"内部发布次数")
    image = models.CharField(max_length=100, help_text=u"镜像")
    cmd = models.CharField(
        max_length=100, null=True, blank=True, help_text=u"启动参数")
    setting = models.CharField(
        max_length=100, null=True, blank=True, help_text=u"设置项")
    extend_method = models.CharField(
        max_length=15,
        choices=extend_method,
        default='stateless',
        help_text=u"伸缩方式")
    env = models.CharField(
        max_length=200, null=True, blank=True, help_text=u"环境变量")
    min_node = models.IntegerField(help_text=u"启动个数", default=1)
    min_cpu = models.IntegerField(help_text=u"cpu个数", default=500)
    min_memory = models.IntegerField(help_text=u"内存大小单位（M）", default=256)
    inner_port = models.IntegerField(help_text=u"内部端口")
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
    delete_time = models.DateTimeField(auto_now_add=True)
    creater = models.IntegerField(help_text=u"服务创建者", default=0)
    language = models.CharField(
        max_length=40, null=True, blank=True, help_text=u"代码语言")
    protocol = models.CharField(max_length=15, help_text=u"服务协议：http,stream")
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
    service_source = models.CharField(max_length=15, default="source_code", null=True, blank=True, help_text=u"应用来源")
    create_status = models.CharField(max_length=15, null=True, blank=True, help_text=u"应用创建状态 creating|complete")
    update_time = models.DateTimeField(auto_now_add=True, blank=True, help_text=u"更新时间")
    tenant_service_group_id = models.IntegerField(default=0, help_text=u"应用归属的服务组id")
    check_uuid = models.CharField(
        max_length=36, blank=True, null=True, default="", help_text=u"服务id")
    check_event_id = models.CharField(
        max_length=32, blank=True, null=True, default="", help_text=u"应用检测事件ID")
    docker_cmd = models.CharField(
        max_length=1024, null=True, blank=True, help_text=u"镜像创建命令")


class TenantServiceLog(BaseModel):
    class Meta:
        db_table = 'tenant_service_log'

    user_id = models.IntegerField(help_text=u"用户id")
    user_name = models.CharField(max_length=40, help_text=u"用户名")
    service_id = models.CharField(max_length=32, help_text=u"服务id")
    tenant_id = models.CharField(max_length=32, help_text=u"租户id")
    action = models.CharField(
        max_length=15, help_text=u"分类：deploy,stop,restart")
    create_time = models.DateTimeField(auto_now=True, help_text=u"创建时间")


class TenantServiceRelation(BaseModel):
    class Meta:
        db_table = 'tenant_service_relation'
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


class TenantServiceEnv(BaseModel):
    class Meta:
        db_table = 'tenant_service_env'

    service_id = models.CharField(max_length=32, help_text=u"服务id")
    language = models.CharField(
        max_length=40, null=True, blank=True, help_text=u"代码语言")
    check_dependency = models.CharField(
        max_length=100, null=True, blank=True, help_text=u"服务运行环境依赖")
    user_dependency = models.CharField(
        max_length=1000, null=True, blank=True, help_text=u"服务运行环境依赖")
    create_time = models.DateTimeField(
        auto_now_add=True, blank=True, help_text=u"创建时间")


class TenantServiceAuth(BaseModel):
    class Meta:
        db_table = 'tenant_service_auth'

    service_id = models.CharField(max_length=32, help_text=u"服务id")
    user = models.CharField(
        max_length=40, null=True, blank=True, help_text=u"代码语言")
    password = models.CharField(
        max_length=100, null=True, blank=True, help_text=u"服务运行环境依赖")
    create_time = models.DateTimeField(
        auto_now_add=True, blank=True, help_text=u"创建时间")


class TenantServiceExtendMethod(BaseModel):

    class Meta:
        db_table = 'tenant_service_extend_method'

    service_key = models.CharField(max_length=32, help_text=u"服务key")
    version = models.CharField(max_length=20, null=False, help_text=u"当前最新版本")
    min_node = models.IntegerField(default=1, help_text=u"最小节点")
    max_node = models.IntegerField(default=20, help_text=u"最大节点")
    step_node = models.IntegerField(default=1, help_text=u"节点步长")
    min_memory = models.IntegerField(default=1, help_text=u"最小内存")
    max_memory = models.IntegerField(default=20, help_text=u"最大内存")
    step_memory = models.IntegerField(default=1, help_text=u"内存步长")
    is_restart = models.BooleanField(default=False, blank=True, help_text=u"是否重启")

    def to_dict(self):
        opts = self._meta
        data = {}
        for f in opts.concrete_fields:
            value = f.value_from_object(self)
            if isinstance(value, datetime):
                value = value.strftime('%Y-%m-%d %H:%M:%S')
            data[f.name] = value
        return data


class ServiceDomain(BaseModel):
    class Meta:
        db_table = 'service_domain'

    service_id = models.CharField(max_length=32, help_text=u"服务id")
    service_name = models.CharField(max_length=32, help_text=u"服务名")
    domain_name = models.CharField(max_length=256, help_text=u"域名")
    create_time = models.DateTimeField(
        auto_now_add=True, blank=True, help_text=u"创建时间")
    container_port = models.IntegerField(default=0, help_text=u"容器端口")
    protocol = models.CharField(max_length=15, default='http', help_text=u"域名类型 http https httptphttps httpandhttps")
    certificate_id = models.IntegerField(default=0, help_text=u'证书ID')

    def __unicode__(self):
        return self.domain_name


class ServiceDomainCertificate(BaseModel):
    class Meta:
        db_table = 'service_domain_certificate'

    tenant_id = models.CharField(max_length=32, help_text=u"租户id")
    private_key = models.TextField(default='', help_text=u"证书key")
    certificate = models.TextField(default='', help_text=u'证书')
    create_time = models.DateTimeField(
        auto_now_add=True, blank=True, help_text=u"创建时间")
    alias = models.CharField(max_length=32, help_text=u"证书别名")

    def __unicode__(self):
        return "private_key:{} certificate:{}".format(self.private_key, self.certificate)


class PermRelService(BaseModel):
    """
    用户和服务关系表/用户在一个服务中的角色
    """
    class Meta:
        db_table = 'service_perms'

    user_id = models.IntegerField(help_text=u"用户id")
    service_id = models.IntegerField(help_text=u"服务id")
    identity = models.CharField(
        max_length=15, choices=service_identity, help_text=u"服务身份", null=True, blank=True)
    role_id = models.IntegerField(help_text=u'角色', null=True, blank=True)


class PermRelTenant(BaseModel):
    """
    用户和团队的关系表
    identity ：租户权限
    """
    class Meta:
        db_table = 'tenant_perms'

    user_id = models.IntegerField(help_text=u"关联用户")
    tenant_id = models.IntegerField(help_text=u"关联租户")
    identity = models.CharField(
        max_length=15, choices=tenant_identity, help_text=u"租户身份", null=True, blank=True)
    enterprise_id = models.IntegerField(help_text=u"关联企业")
    role_id = models.IntegerField(help_text=u'角色', null=True, blank=True)


class TenantRecharge(BaseModel):
    class Meta:
        db_table = 'tenant_recharge'

    tenant_id = models.CharField(max_length=32, help_text=u"租户id")
    user_id = models.IntegerField(help_text=u"充值用户")
    user_name = models.CharField(max_length=40, help_text=u"用户名")
    order_no = models.CharField(max_length=60, help_text=u"订单号")
    recharge_type = models.CharField(max_length=40, help_text=u"充值类型")
    money = models.DecimalField(
        max_digits=9, decimal_places=2, help_text=u"充值金额")
    subject = models.CharField(max_length=40, help_text=u"主题")
    body = models.CharField(max_length=80, help_text=u"详情")
    show_url = models.CharField(max_length=100, help_text=u"详情url")
    status = models.CharField(max_length=30, help_text=u"充值状态")
    trade_no = models.CharField(max_length=64, help_text=u"支付宝交易号")
    time = models.DateTimeField(
        auto_now_add=True, blank=True, help_text=u"创建时间")


class TenantServiceStatics(BaseModel):
    class Meta:
        db_table = 'tenant_service_statics'
        unique_together = ('service_id', 'time_stamp')
        get_latest_by = 'ID'

    tenant_id = models.CharField(max_length=32, help_text=u"租户id")
    service_id = models.CharField(max_length=32, help_text=u"服务id")
    pod_id = models.CharField(max_length=32, help_text=u"服务id")
    node_num = models.IntegerField(help_text=u"节点个数", default=0)
    node_memory = models.IntegerField(help_text=u"节点内存k", default=0)
    container_cpu = models.IntegerField(help_text=u"cpu使用", default=0)
    container_memory = models.IntegerField(help_text=u"内存使用K", default=0)
    container_memory_working = models.IntegerField(
        help_text=u"正在使用内存K", default=0)
    pod_cpu = models.IntegerField(help_text=u"cpu使用", default=0)
    pod_memory = models.IntegerField(help_text=u"内存使用K", default=0)
    pod_memory_working = models.IntegerField(help_text=u"正在使用内存K", default=0)
    container_disk = models.IntegerField(help_text=u"磁盘使用K", default=0)
    storage_disk = models.IntegerField(help_text=u"磁盘使用K", default=0)
    net_in = models.IntegerField(help_text=u"网络使用K", default=0)
    net_out = models.IntegerField(help_text=u"网络使用K", default=0)
    flow = models.IntegerField(help_text=u"网络下载量", default=0)
    time_stamp = models.IntegerField(help_text=u"时间戳", default=0)
    status = models.IntegerField(default=0, help_text=u"0:无效；1:有效；2:操作中")
    region = models.CharField(max_length=15, help_text=u"服务所属区")
    time = models.DateTimeField(
        auto_now_add=True, blank=True, help_text=u"创建时间")


class TenantConsumeDetail(BaseModel):
    class Meta:
        db_table = 'tenant_consume_detail'

    tenant_id = models.CharField(max_length=32, help_text=u"租户id")
    service_id = models.CharField(max_length=32, help_text=u"服务id")
    service_alias = models.CharField(max_length=100, help_text=u"服务别名")
    node_num = models.IntegerField(help_text=u"节点个数", default=0)
    cpu = models.IntegerField(help_text=u"cpu使用", default=0)
    memory = models.IntegerField(help_text=u"内存使用K", default=0)
    disk = models.IntegerField(help_text=u"磁盘使用K", default=0)
    net = models.IntegerField(help_text=u"网络使用K", default=0)
    money = models.DecimalField(
        max_digits=9, decimal_places=2, help_text=u"消费金额", default=0)
    total_memory = models.IntegerField(help_text=u"内存使用K", default=0)
    fee_rule = models.CharField(max_length=60, help_text=u"计费规则")
    pay_status = models.CharField(
        max_length=10, help_text=u"扣费状态；payed,unpayed")
    region = models.CharField(max_length=15, help_text=u"服务所属区")
    status = models.IntegerField(help_text=u"服务状态", default=1)
    time = models.DateTimeField(
        auto_now_add=True, blank=True, help_text=u"创建时间")


class TenantConsume(BaseModel):
    class Meta:
        db_table = 'tenant_consume'

    tenant_id = models.CharField(max_length=32, help_text=u"租户id")
    total_memory = models.IntegerField(help_text=u"内存使用K", default=0)
    cost_money = models.DecimalField(
        max_digits=9, decimal_places=2, help_text=u"消费金额", default=0)
    payed_money = models.DecimalField(
        max_digits=9, decimal_places=2, help_text=u"消费金额", default=0)
    pay_status = models.CharField(
        max_length=10, help_text=u"扣费状态；payed,unpayed")
    time = models.DateTimeField(
        auto_now_add=True, blank=True, help_text=u"创建时间")


class TenantFeeBill(BaseModel):
    class Meta:
        db_table = 'tenant_fee_bill'

    tenant_id = models.CharField(max_length=32, help_text=u"租户id")
    bill_title = models.CharField(max_length=100, help_text=u"发票标题")
    bill_type = models.CharField(max_length=10, help_text=u"公司或个人")
    bill_address = models.CharField(max_length=100, help_text=u"邮寄地址")
    bill_phone = models.CharField(max_length=100, help_text=u"邮寄电话")
    money = models.DecimalField(
        max_digits=9, decimal_places=2, help_text=u"发票金额")
    status = models.CharField(
        max_length=10, help_text=u"审核状态:已审核(approved)，未审核(unapproved)")
    time = models.DateTimeField(
        auto_now_add=True, blank=True, help_text=u"创建时间")


class TenantPaymentNotify(BaseModel):
    class Meta:
        db_table = 'tenant_payment_notify'

    tenant_id = models.CharField(max_length=32, help_text=u"租户id")
    notify_type = models.CharField(
        max_length=10, help_text=u"通知类型：余额不足，欠费,资源已超限")
    notify_content = models.CharField(max_length=200, help_text=u"通知类容")
    send_person = models.CharField(max_length=20, help_text=u"通知人")
    time = models.DateTimeField(
        auto_now_add=True, blank=True, help_text=u"创建时间")
    status = models.CharField(
        max_length=10, help_text=u"有效(valid),无效(unvalid)")


class PhoneCode(BaseModel):
    class Meta:
        db_table = 'phone_code'

    phone = models.CharField(max_length=11, help_text=u"手机号码")
    type = models.CharField(max_length=10, help_text=u"类型")
    code = models.CharField(max_length=10, help_text=u"类型")
    message_id = models.CharField(
        max_length=100, help_text=u"aliyun发送的message_id")
    status = models.IntegerField(help_text=u'发送状态0已发送1发送成功2发送失败', default=0)
    create_time = models.DateTimeField(
        auto_now_add=True, blank=True, help_text=u"创建时间")


class TenantRegionPayModel(BaseModel):
    class Meta:
        db_table = 'tenant_region_pay_model'

    tenant_id = models.CharField(max_length=32, help_text=u"租户id")
    region_name = models.CharField(max_length=20, help_text=u"区域中心名称")
    pay_model = models.CharField(
        max_length=10, default='hour', help_text=u"付费模式:hour,month,year")
    buy_period = models.IntegerField(help_text=u"购买周期", default=0)
    buy_memory = models.IntegerField(help_text=u"购买内存", default=0)
    buy_disk = models.IntegerField(help_text=u"购买磁盘", default=0)
    buy_net = models.IntegerField(help_text=u"购买流量", default=0)
    buy_start_time = models.DateTimeField(help_text=u"购买开始时间")
    buy_end_time = models.DateTimeField(help_text=u"购买结束时间")
    buy_money = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00, help_text=u"购买金额")
    create_time = models.DateTimeField(
        auto_now_add=True, blank=True, help_text=u"创建时间")


class TenantServiceL7Info(BaseModel):
    class Meta:
        db_table = 'tenant_l7_info'

    tenant_id = models.CharField(max_length=32, help_text=u"租户id")
    service_id = models.CharField(
        max_length=32, db_index=True, help_text=u"服务id")
    dep_service_id = models.CharField(max_length=32, help_text=u"依赖服务id")
    l7_json = models.CharField(max_length=255, help_text=u"高级应用特性信息")


class TenantServiceEnvVar(BaseModel):
    class Meta:
        db_table = 'tenant_service_env_var'

    tenant_id = models.CharField(max_length=32, help_text=u"租户id")
    service_id = models.CharField(
        max_length=32, db_index=True, help_text=u"服务id")
    container_port = models.IntegerField(default=0, help_text=u"端口")
    name = models.CharField(max_length=100, blank=True, help_text=u"名称")
    attr_name = models.CharField(max_length=100, help_text=u"属性")
    attr_value = models.CharField(max_length=512, help_text=u"值")
    is_change = models.BooleanField(
        default=False, blank=True, help_text=u"是否可改变")
    scope = models.CharField(max_length=10, help_text=u"范围", default="outer")
    create_time = models.DateTimeField(auto_now_add=True, help_text=u"创建时间")

    def __unicode__(self):
        return self.name


class TenantServicesPort(BaseModel):
    class Meta:
        db_table = 'tenant_services_port'
        unique_together = ('service_id', 'container_port')

    tenant_id = models.CharField(
        max_length=32, null=True, blank=True, help_text=u'租户id')
    service_id = models.CharField(
        max_length=32, db_index=True, help_text=u"服务ID")
    container_port = models.IntegerField(default=0, help_text=u"容器端口")
    mapping_port = models.IntegerField(default=0, help_text=u"映射端口")
    lb_mapping_port = models.IntegerField(default=0, help_text=u"负载均衡映射端口")
    protocol = models.CharField(
        max_length=15, default='', blank=True, help_text=u"服务协议：http,stream")
    port_alias = models.CharField(
        max_length=30, default='', blank=True, help_text=u"port别名")
    is_inner_service = models.BooleanField(
        default=False, blank=True, help_text=u"是否内部服务；0:不绑定；1:绑定")
    is_outer_service = models.BooleanField(
        default=False, blank=True, help_text=u"是否外部服务；0:不绑定；1:绑定")


class TenantServiceMountRelation(BaseModel):
    class Meta:
        db_table = 'tenant_service_mnt_relation'
        unique_together = ('service_id', 'dep_service_id', 'mnt_name')

    tenant_id = models.CharField(max_length=32, help_text=u"租户id")
    service_id = models.CharField(max_length=32, help_text=u"服务id")
    dep_service_id = models.CharField(max_length=32, help_text=u"依赖服务id")
    mnt_name = models.CharField(max_length=100, help_text=u"mnt name")
    mnt_dir = models.CharField(max_length=400, help_text=u"mnt dir")


class TenantServiceVolume(BaseModel):
    """数据持久化表格"""

    class Meta:
        db_table = 'tenant_service_volume'

    SHARE = 'share-file'
    LOCAL = 'local'
    TMPFS = 'memoryfs'

    service_id = models.CharField(max_length=32, help_text=u"服务id")
    category = models.CharField(max_length=50, null=True, blank=True, help_text=u"服务类型")
    host_path = models.CharField(max_length=400, help_text=u"物理机的路径,绝对路径")
    volume_type = models.CharField(max_length=30, blank=True, null=True)
    volume_path = models.CharField(max_length=400, help_text=u"容器内路径,application为相对;其他为绝对")
    volume_name = models.CharField(max_length=100, blank=True, null=True)


class ServiceGroup(BaseModel):
    """服务分组"""

    class Meta:
        db_table = 'service_group'

    tenant_id = models.CharField(max_length=32, help_text=u"租户id")
    group_name = models.CharField(max_length=32, help_text=u"组名")
    region_name = models.CharField(max_length=20, help_text=u"区域中心名称")


class ServiceGroupRelation(BaseModel):
    """服务与分组关系"""

    class Meta:
        db_table = 'service_group_relation'

    service_id = models.CharField(max_length=32, help_text=u"服务id")
    group_id = models.IntegerField()
    tenant_id = models.CharField(max_length=32, help_text=u"租户id")
    region_name = models.CharField(max_length=20, help_text=u"区域中心名称")


class ImageServiceRelation(BaseModel):
    """image_url拉取的service的对应关系"""

    class Meta:
        db_table = 'tenant_service_image_relation'

    tenant_id = models.CharField(max_length=32, help_text=u"租户id")
    service_id = models.CharField(max_length=32, help_text=u"服务id")
    image_url = models.CharField(max_length=100, help_text=u"镜像地址")
    service_cname = models.CharField(
        max_length=100, default='', help_text=u"服务名")


class ComposeServiceRelation(BaseModel):
    """docker compose 文件"""

    class Meta:
        db_table = 'tenant_compose_file'

    tenant_id = models.CharField(max_length=32, help_text=u"租户id")
    compose_file_id = models.CharField(max_length=32, help_text=u"compose文件id")
    compose_file = models.FileField(
        upload_to=compose_file_path,
        null=True,
        blank=True,
        help_text=u"compose file")


class ServiceRule(BaseModel):
    """用户服务自动伸缩规则 """

    class Meta:
        db_table = 'tenant_service_rule'

    tenant_id = models.CharField(max_length=32, help_text=u"租户id")
    tenant_name = models.CharField(
        max_length=40, unique=True, help_text=u"租户名称")
    service_id = models.CharField(max_length=32, help_text=u"服务id")
    service_alias = models.CharField(max_length=100, help_text=u"服务别名")
    service_region = models.CharField(max_length=32, help_text=u"数据中心")
    item = models.CharField(max_length=50, help_text=u"规则项目")
    maxvalue = models.IntegerField(default=0)
    minvalue = models.IntegerField(default=0)
    status = models.BooleanField(
        default=False, blank=True, help_text=u"是否生效；0:停止；1:生效")
    count = models.IntegerField(default=0)
    node_number = models.IntegerField(help_text=u"实例启动个数", default=1)
    port = models.CharField(max_length=10)
    port_type = models.CharField(
        max_length=15,
        default='multi_outer',
        help_text=u"端口类型，one_outer;dif_protocol;multi_outer")


class ServiceRuleHistory(BaseModel):
    """用户服务自动伸缩规则触发历史 """

    class Meta:
        db_table = 'tenant_service_rule_history'

    rule_id = models.CharField(max_length=32, help_text=u"规则id")
    trigger_time = models.CharField(max_length=100, help_text=u"触发时间")
    action = models.CharField(max_length=10, help_text=u"触发动作")
    message = models.CharField(max_length=1024, help_text=u"描述")


class ServiceAttachInfo(BaseModel):
    """应用配套信息"""

    class Meta:
        db_table = 'service_attach_info'

    tenant_id = models.CharField(max_length=32, help_text=u"租户id")
    service_id = models.CharField(max_length=32, help_text=u"服务id")
    memory_pay_method = models.CharField(max_length=32, choices=pay_method)
    disk_pay_method = models.CharField(max_length=32, choices=pay_method)
    min_memory = models.IntegerField(help_text=u"内存大小单位（M）", default=128)
    min_node = models.IntegerField(help_text=u"节点个数", default=1)
    disk = models.IntegerField(help_text=u'磁盘大小')
    pre_paid_period = models.IntegerField(
        help_text=u"预付费项目购买时长(单位:月)", default=0)
    pre_paid_money = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00, help_text=u"预付费金额")
    buy_start_time = models.DateTimeField(help_text=u"购买开始时间")
    buy_end_time = models.DateTimeField(help_text=u"购买结束时间")
    create_time = models.DateTimeField(auto_now_add=True, help_text=u"创建时间")
    region = models.CharField(max_length=32, help_text=u"数据中心")

    def toJSON(self):
        data = {}
        for f in self._meta.fields:
            obj = getattr(self, f.name)
            if type(f.name) == DateTimeField:
                data[f.name] = obj.strftime('%Y-%m-%d %H:%M:%S')
            else:
                data[f.name] = obj
        return data


class ServiceCreateStep(BaseModel):
    class Meta:
        db_table = 'service_create_step'

    tenant_id = models.CharField(max_length=32, help_text=u"租户id")
    service_id = models.CharField(max_length=32, help_text=u"服务id")
    app_step = models.IntegerField(default=1, help_text=u"创建应用的步数")


class ThirdAppInfo(BaseModel):
    class Meta:
        db_table = 'third_app_info'

    tenant_id = models.CharField(max_length=32, help_text=u"租户id")
    service_id = models.CharField(max_length=32, help_text=u"服务id")
    bucket_name = models.CharField(max_length=32, help_text=u"空间名")
    app_type = models.CharField(max_length=32, help_text=u"第三方应用类型")
    create_time = models.DateTimeField(auto_now_add=True, help_text=u"创建时间")
    name = models.CharField(max_length=32, help_text=u"应用名称")
    bill_type = models.CharField(
        default="demand", max_length=10, help_text=u"计费方式，流量包packet或者demand需求")
    open = models.BooleanField(default=1, help_text=u"是否开启状态")
    delete = models.BooleanField(default=0, help_text=u"是否删除状态")
    create_user = models.IntegerField(help_text=u"创建的用户的user_id")


class CDNTrafficRecord(BaseModel):
    class Meta:
        db_table = 'cdn_traffic_record'

    order_id = models.CharField(max_length=32, help_text=u"订单id")
    tenant_id = models.CharField(max_length=32, help_text=u"租户id")
    service_id = models.CharField(max_length=32, help_text=u"服务id")
    bucket_name = models.CharField(max_length=32, help_text=u"空间名")
    traffic_size = models.IntegerField(help_text=u"流量包大小")
    traffic_price = models.IntegerField(help_text=u"流量包价格")
    buy_time = models.DateTimeField(auto_now_add=True, help_text=u"购买时间")
    payment_status = models.CharField(
        default=0, max_length=1, help_text=u"支付状态")


class CDNTrafficHourRecord(BaseModel):
    class Meta:
        db_table = 'cdn_traffic_hour_record'

    tenant_id = models.CharField(max_length=32, help_text=u"租户id")
    service_id = models.CharField(max_length=32, help_text=u"服务id")
    bucket_name = models.CharField(max_length=32, help_text=u"空间名")
    start_time = models.DateTimeField(help_text=u"订单开始时间")
    end_time = models.DateTimeField(help_text=u"订单结束时间")
    traffic_number = models.IntegerField(help_text=u"流量消费数量")
    balance = models.IntegerField(help_text=u"流量包余额")
    create_time = models.DateTimeField(auto_now_add=True, help_text=u"创建时间")
    order_id = models.CharField(max_length=32, help_text=u"扣除流量的订单id")


class ThirdAppOperator(BaseModel):
    class Meta:
        db_table = 'third_app_operator'

    service_id = models.CharField(max_length=32, help_text=u"服务id")
    bucket_name = models.CharField(max_length=32, help_text=u"空间名")
    operator_name = models.CharField(max_length=100, help_text=u"用户名")
    real_name = models.CharField(max_length=100, help_text=u"真实姓名")
    password = models.CharField(max_length=100, help_text=u"密码")


class ThirdAppOrder(BaseModel):
    class Meta:
        db_table = 'third_app_order'

    order_id = models.CharField(max_length=32, help_text=u"订单id")
    tenant_id = models.CharField(max_length=32, help_text=u"租户id")
    service_id = models.CharField(max_length=32, help_text=u"服务id")
    bucket_name = models.CharField(max_length=32, help_text=u"空间名")
    start_time = models.DateTimeField(help_text=u"订单开始时间")
    end_time = models.DateTimeField(help_text=u"订单结束时间")
    create_time = models.DateTimeField(auto_now_add=True, help_text=u"创建时间")
    traffic_size = models.IntegerField(default=0, help_text=u"流量使用大小")
    oos_size = models.IntegerField(default=0, help_text=u"存储使用大小")
    request_size = models.IntegerField(default=0, help_text=u"请求次数")
    bill_type = models.CharField(
        default="demand", max_length=10, help_text=u"计费方式，流量包packet或者demand需求")
    total_cost = models.FloatField(default=0.00, help_text=u"费用总计")
    total_traffic_cost = models.IntegerField(default=0, help_text=u"月度套餐外流量总计")


pay_status = ((u"已发布", 'payed'), (u"测试中", "unpayed"),)


class ServiceFeeBill(BaseModel):
    class Meta:
        db_table = 'service_fee_bill'

    tenant_id = models.CharField(max_length=32, help_text=u"租户id")
    service_id = models.CharField(max_length=32, help_text=u"服务id")
    prepaid_money = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00, help_text=u"付费金额")
    pay_status = models.CharField(
        max_length=15, choices=pay_status, help_text=u"付费状态")
    cost_type = models.CharField(max_length=15, help_text=u"消费类型")
    node_memory = models.IntegerField(help_text=u"内存大小单位（M）", default=128)
    node_num = models.IntegerField(help_text=u"节点个数", default=1)
    disk = models.IntegerField(help_text=u'磁盘大小')
    buy_period = models.IntegerField(help_text=u"预付费时长(单位:小时)", default=0)
    create_time = models.DateTimeField(auto_now_add=True, help_text=u"创建时间")
    pay_time = models.DateTimeField(auto_now_add=True, help_text=u"支付时间")


class ServiceConsume(BaseModel):
    class Meta:
        db_table = 'service_consume'

    tenant_id = models.CharField(max_length=32, help_text=u"租户id")
    service_id = models.CharField(max_length=32, help_text=u"服务id")
    memory = models.IntegerField(help_text=u"内存大小单位（M）", default=0)
    node_num = models.IntegerField(help_text=u"节点个数", default=1)
    disk = models.IntegerField(help_text=u'磁盘大小', default=0)
    net = models.IntegerField(help_text=u"网络使用K", default=0)
    memory_money = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00, help_text=u"内存金额")
    disk_money = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00, help_text=u"磁盘金额")
    net_money = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00, help_text=u"网络金额")
    pay_money = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00, help_text=u"实际付费金额")
    pay_status = models.CharField(
        max_length=15, choices=pay_status, help_text=u"付费状态")
    region = models.CharField(max_length=32, help_text=u"数据中心")
    status = models.IntegerField(default=0, help_text=u"0:无效；1:有效；2:操作中")
    time = models.DateTimeField(help_text=u"创建时间")
    real_memory_money = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00, help_text=u"内存按需金额")
    real_disk_money = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00, help_text=u"磁盘按需金额")


class ServiceEvent(BaseModel):
    class Meta:
        db_table = 'service_event'

    event_id = models.CharField(max_length=32, help_text=u"操作id")
    tenant_id = models.CharField(max_length=32, help_text=u"租户id")
    service_id = models.CharField(max_length=32, help_text=u"服务id")
    user_name = models.CharField(max_length=50, help_text=u"操作用户")
    start_time = models.DateTimeField(help_text=u"操作开始时间")
    end_time = models.DateTimeField(help_text=u"操作结束时间", null=True)
    type = models.CharField(max_length=20, help_text=u"操作类型")
    status = models.CharField(
        max_length=20, help_text=u"操作处理状态 success failure")
    final_status = models.CharField(
        max_length=20,
        default="",
        help_text=u"操作状态，complete or timeout or null")
    message = models.CharField(max_length=200, help_text=u"操作说明")
    deploy_version = models.CharField(max_length=20, help_text=u"部署版本")
    old_deploy_version = models.CharField(max_length=20, help_text=u"部署版本")
    code_version = models.CharField(max_length=200, help_text=u"部署代码版本")
    old_code_version = models.CharField(max_length=200, help_text=u"历史部署代码版本")


class GroupCreateTemp(BaseModel):
    class Meta:
        db_table = 'group_create_temp'

    tenant_id = models.CharField(max_length=32, help_text=u"租户id")
    service_id = models.CharField(max_length=32, help_text=u"服务id")
    service_key = models.CharField(max_length=32, help_text=u"服务key")
    share_group_id = models.IntegerField(help_text=u"服务组发布id")
    service_group_id = models.IntegerField(help_text=u"服务所属组")
    service_cname = models.CharField(
        max_length=100, default='', help_text=u"服务名")


class BackServiceInstallTemp(BaseModel):
    class Meta:
        db_table = "back_service_install_temp"

    group_share_id = models.CharField(
        max_length=32, unique=True, help_text=u"服务组发布id")
    share_pk = models.IntegerField(
        help_text=u"发布的服务组PK 对应app_service_group中的ID")
    group_pk = models.IntegerField(help_text=u"服务所在组ID")
    success = models.BooleanField(default=True, help_text=u"成功安装")


class ServiceProbe(BaseModel):
    class Meta:
        db_table = 'service_probe'

    service_id = models.CharField(max_length=32, help_text=u"服务id")
    probe_id = models.CharField(max_length=32, help_text=u"探针id")
    mode = models.CharField(max_length=10, help_text=u"探针模式")
    scheme = models.CharField(
        max_length=10, default="tcp", help_text=u"探针使用协议,tcp,http,cmd")
    path = models.CharField(max_length=50, default="", help_text=u"路径")
    port = models.IntegerField(default=80, help_text=u"检测端口")
    cmd = models.CharField(max_length=150, default="", help_text=u"cmd 命令")
    http_header = models.CharField(
        max_length=300,
        blank=True,
        default="",
        help_text=u"http请求头，key=value,key2=value2")
    initial_delay_second = models.IntegerField(default=1, help_text=u"初始化等候时间")
    period_second = models.IntegerField(default=3, help_text=u"检测间隔时间")
    timeout_second = models.IntegerField(default=30, help_text=u"检测超时时间")
    failure_threshold = models.IntegerField(default=3, help_text=u"标志为失败的检测次数")
    success_threshold = models.IntegerField(default=1, help_text=u"标志为成功的检测次数")
    is_used = models.BooleanField(default=1, help_text=u"是否启用")


class ConsoleConfig(BaseModel):
    class Meta:
        db_table = 'console_config'

    key = models.CharField(max_length=50, help_text=u"配置名称")
    value = models.CharField(max_length=1000, help_text=u"配置值")
    description = models.TextField(null=True, blank=True, default="", help_text=u"说明")
    update_time = models.DateTimeField(help_text=u"更新时间", null=True)


class ServicePaymentNotify(BaseModel):
    class Meta:
        db_table = "service_payment_notify"

    tenant_id = models.CharField(max_length=32, help_text=u"租户id")
    service_id = models.CharField(max_length=32, help_text=u"服务id")
    notify_type = models.CharField(max_length=10, help_text=u"通知类型")
    notify_content = models.CharField(max_length=200, help_text=u"通知内容")
    send_person = models.CharField(max_length=20, help_text=u"通知内容")
    time = models.DateTimeField(
        auto_now_add=True, blank=True, help_text=u"创建时间")
    end_time = models.DateTimeField(blank=True, help_text=u"删除截止时间")
    status = models.CharField(max_length=10, help_text=u"状态")


class TenantEnterprise(BaseModel):
    class Meta:
        db_table = 'tenant_enterprise'

    enterprise_id = models.CharField(max_length=32, unique=True, help_text=u"企业id")
    enterprise_name = models.CharField(max_length=64, help_text=u"企业名称")
    enterprise_alias = models.CharField(max_length=64, blank=True, null=True, default='', help_text=u"企业别名")
    create_time = models.DateTimeField(auto_now_add=True, blank=True, null=True, help_text=u"创建时间")
    enterprise_token = models.CharField(max_length=256, blank=True, null=True, default='', help_text=u"企业身份token")
    is_active = models.IntegerField(default=0, help_text=u"是否在云市上激活, 0:未激活, 1:已激活")

    def __unicode__(self):
        return self.to_dict()


class TenantEnterpriseToken(BaseModel):
    class Meta:
        db_table = 'tenant_enterprise_token'
        unique_together = ('enterprise_id', 'access_target')

    enterprise_id = models.IntegerField(default=0, help_text=u"企业id")
    access_target = models.CharField(max_length=32, blank=True, null=True, default='', help_text=u"要访问的目标服务名称")
    access_url = models.CharField(max_length=255,  help_text=u"需要访问的api地址")
    access_id = models.CharField(max_length=32, help_text=u"target分配给客户端的ID")
    access_token = models.CharField(max_length=256, blank=True, null=True, default='', help_text=u"客户端token")
    crt = models.TextField(default='', blank=True, null=True, help_text=u"客户端证书")
    key = models.TextField(default='', blank=True, null=True, help_text=u"客户端证书key")
    create_time = models.DateTimeField(auto_now_add=True, blank=True, null=True, help_text=u"创建时间")
    update_time = models.DateTimeField(auto_now_add=True, blank=True, null=True, help_text=u"更新时间")

    def __unicode__(self):
        return self.to_dict()


class TenantServiceGroup(BaseModel):
    """应用组实体"""

    class Meta:
        db_table = 'tenant_service_group'

    tenant_id = models.CharField(max_length=32, help_text=u"租户id")
    group_name = models.CharField(max_length=64, help_text=u"服务组名")
    group_alias = models.CharField(max_length=64, help_text=u"服务组名")
    group_key = models.CharField(max_length=32, help_text=u"服务组id")
    group_version = models.CharField(max_length=32, help_text=u"服务组版本")
    region_name = models.CharField(max_length=20, help_text=u"区域中心名称")
    service_group_id = models.IntegerField(default=0, help_text=u"ServiceGroup主键, 应用分类ID")

