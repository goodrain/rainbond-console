# -*- coding: utf8 -*-
import re
from django.db import models
from django.utils.crypto import salted_hmac
from www.utils.crypt import encrypt_passwd, make_tenant_id
from django.db.models.fields import DateTimeField
from .fields import GrOptionsCharField
from .main import BaseModel, extend_method, app_pay_choices
from www.utils.crypt import make_uuid
from django.conf import settings
# Create your models here.


app_status = (
    ('show', u'显示'), ("hidden", u'隐藏'),
)


# 服务--app关系表格
class AppService(BaseModel):
    """ 服务发布表格 """
    class Meta:
        db_table = 'app_service'
        unique_together = ('service_key', 'app_version')

    tenant_id = models.CharField(max_length=32, help_text=u"租户id")
    service_id = models.CharField(max_length=32, help_text=u"服务id")
    service_key = models.CharField(max_length=32, unique=True, help_text=u"服务key")
    app_version = models.CharField(max_length=20, null=False, help_text=u"当前最新版本")
    app_alias = models.CharField(max_length=100, help_text=u"服务发布名称")
    logo = models.FileField(upload_to=logo_path, null=True, blank=True, help_text=u"logo")
    info = models.CharField(max_length=100, null=True, blank=True, help_text=u"简介")
    desc = models.CharField(max_length=400, null=True, blank=True, help_text=u"描述")
    status = models.CharField(max_length=15, choices=app_status, help_text=u"服务状态：发布后显示还是隐藏")
    category = models.CharField(max_length=15, help_text=u"服务分类：application,cache,store")
    is_service = models.BooleanField(default=False, blank=True, help_text=u"是否inner服务")
    is_web_service = models.BooleanField(default=False, blank=True, help_text=u"是否web服务")
    image = models.CharField(max_length=100, help_text=u"镜像")
    slug = models.CharField(max_length=200, help_text=u"slug包路径",default="")
    extend_method = models.CharField(max_length=15, choices=extend_method, default='stateless', help_text=u"伸缩方式")
    cmd = models.CharField(max_length=100, null=True, blank=True, help_text=u"启动参数")
    env = models.CharField(max_length=200, null=True, blank=True, help_text=u"环境变量")
    min_node = models.IntegerField(help_text=u"启动个数", default=1)
    min_cpu = models.IntegerField(help_text=u"cpu个数", default=500)
    min_memory = models.IntegerField(help_text=u"内存大小单位（M）", default=256)
    inner_port = models.IntegerField(help_text=u"内部端口", default=0)
    volume_mount_path = models.CharField(max_length=50, null=True, blank=True, help_text=u"mount目录")
    service_type = models.CharField(max_length=50, null=True, blank=True, help_text=u"服务类型:web,mysql,redis,mongodb,phpadmin")
    is_init_accout = models.BooleanField(default=False, blank=True, help_text=u"是否初始化账户")
    is_base = models.BooleanField(default=False, blank=True, help_text=u"是否基础服务")
    is_outer = models.BooleanField(default=False, blank=True, help_text=u"是否发布到公有市场")
    is_ok = models.BooleanField(help_text=u'发布是否成功', default=True)
    creater = models.IntegerField(null=True, help_text=u"创建人")
    publisher = models.EmailField(max_length=35, unique=True, help_text=u"邮件地址")
    
    def is_slug(self):
        # return bool(self.image.startswith('goodrain.me/runner'))
        return bool(self.image.endswith('/runner')) or bool(self.image.search('/runner:+'))

    def is_image(self):
        return not self.is_slug(self)

    def __unicode__(self):
        return u"{0}({1})".format(self.service_id, self.service_key)


class AppServiceEnv(BaseModel):
    """ 服务环境配置 """
    class Meta:
        db_table = 'app_service_env_var'

    service_key = models.CharField(max_length=32, unique=True, help_text=u"服务key")
    app_version = models.CharField(max_length=20, null=False, help_text=u"当前最新版本")
    container_port = models.IntegerField(default=0, help_text=u"端口")
    name = models.CharField(max_length=100, blank=True, help_text=u"名称")
    attr_name = models.CharField(max_length=100, help_text=u"属性")
    attr_value = models.CharField(max_length=200, help_text=u"值")
    is_change = models.BooleanField(default=False, blank=True, help_text=u"是否可改变")
    scope = models.CharField(max_length=10, help_text=u"范围", default="outer")
    options = GrOptionsCharField(max_length=100, help_text=u"参数选项", default="readonly")
    create_time = models.DateTimeField(auto_now_add=True, help_text=u"创建时间")

    def __unicode__(self):
        return self.name


class AppServicePort(BaseModel):
    """ 服务端口配置 """
    class Meta:
        db_table = 'app_service_port'

    service_key = models.CharField(max_length=32, unique=True, help_text=u"服务key")
    app_version = models.CharField(max_length=20, null=False, help_text=u"当前最新版本")
    container_port = models.IntegerField(default=0, help_text=u"容器端口")
    protocol = models.CharField(max_length=15, default='', blank=True, help_text=u"服务协议：http,stream")
    port_alias = models.CharField(max_length=30, default='', blank=True, help_text=u"port别名")
    is_inner_service = models.BooleanField(default=False, blank=True, help_text=u"是否内部服务；0:不绑定；1:绑定")
    is_outer_service = models.BooleanField(default=False, blank=True, help_text=u"是否外部服务；0:不绑定；1:绑定")


class AppServiceRelation(BaseModel):
    """ 服务依赖关系 """
    class Meta:
        db_table = 'app_service_relation'

    service_key = models.CharField(max_length=32, unique=True, help_text=u"服务key")
    app_version = models.CharField(max_length=20, null=False, help_text=u"当前最新版本")
    dep_service_key = models.CharField(max_length=32, unique=True, help_text=u"服务key")
    dep_app_version = models.CharField(max_length=20, null=False, help_text=u"当前最新版本")

level_choice = (
    ('end', 'end'), ('secondary', 'secondary'), ('root', 'root')
)


class AppServiceCategory(BaseModel):

    class Meta:
        db_table = 'app_service_category'

    name = models.CharField(max_length=20, unique=True, help_text=u"名称")
    level = models.CharField(max_length=20, choices=level_choice, help_text=u"分类级别")
    parent = models.IntegerField(db_index=True, default=0, help_text=u"父分类")
    root = models.IntegerField(db_index=True, default=0, help_text=u"根分类")
    
    
class ServiceExtendMethod(BaseModel):

    class Meta:
        db_table = 'app_service_extend_method'

    service_key = models.CharField(max_length=32, unique=True, help_text=u"服务key")
    is_vertical = models.IntegerField(db_index=True, default=0, help_text=u"是否垂直伸缩")
    vertical_range = models.CharField(max_length=200, default='', help_text=u"垂直伸缩的范围")
    is_horizontal = models.IntegerField(db_index=True, default=0, help_text=u"是否水平伸缩")
    horizontal_range = models.CharField(max_length=200, default='', help_text=u"水平伸缩的范围")