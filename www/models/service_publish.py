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
from datetime import date, datetime
import json
# Create your models here.


app_status = (
    ('show', u'显示'), ("hidden", u'隐藏'),
)


def logo_path(instance, filename):
    suffix = filename.split('.')[-1]
    return '{0}/logo/{1}.{2}'.format(settings.MEDIA_ROOT, make_uuid(), suffix)

    
class ServiceExtendMethod(BaseModel):

    class Meta:
        db_table = 'app_service_extend_method'

    service_key = models.CharField(max_length=32, help_text=u"服务key")
    app_version = models.CharField(max_length=20, null=False, help_text=u"当前最新版本")
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


class AppServiceVolume(BaseModel):
    """发布数据持久化表格"""
    class Meta:
        db_table = 'app_service_volume'
    service_key = models.CharField(max_length=32, help_text=u"服务key")
    app_version = models.CharField(max_length=20, null=False, help_text=u"当前最新版本")
    category = models.CharField(max_length=50, null=True, blank=True, help_text=u"服务类型")
    volume_path = models.CharField(max_length=400, help_text=u"容器内路径,application为相对;其他为绝对")
    volume_type = models.CharField(max_length=30, blank=True, null=True)
    volume_name = models.CharField(max_length=100, blank=True, null=True)

    def to_dict(self):
        opts = self._meta
        data = {}
        for f in opts.concrete_fields:
            value = f.value_from_object(self)
            if isinstance(value, datetime):
                value = value.strftime('%Y-%m-%d %H:%M:%S')
            data[f.name] = value
        return data


class AppServiceShareInfo(BaseModel):
    """普通发布存储环境是否可修改信息"""
    class Meta:
        db_table = 'app_service_share'
    tenant_id = models.CharField(max_length=32, help_text=u"租户id")
    service_id = models.CharField(max_length=32, help_text=u"服务id")

    tenant_env_id = models.IntegerField(help_text=u"服务的环境id")
    is_change = models.BooleanField(default=False, help_text=u"是否可改变")


class AppServiceImages(BaseModel):
    class Meta:
        db_table = 'app_service_images'

    service_id = models.CharField(max_length=32, help_text=u"服务id")
    logo = models.FileField(upload_to=logo_path, null=True, blank=True, help_text=u"logo")
    create_time = models.DateTimeField(auto_now_add=True, help_text=u"创建时间")


class AppServicePackages(BaseModel):
    """服务套餐信息"""
    class Meta:
        db_table = 'app_service_packages'

    service_key = models.CharField(max_length=32, help_text=u"服务key")
    app_version = models.CharField(max_length=20, null=False, help_text=u"当前最新版本")
    name = models.CharField(max_length=100, help_text=u"套餐名称")
    memory = models.IntegerField(help_text=u"内存数")
    node = models.IntegerField(help_text=u"节点数")
    trial = models.IntegerField(help_text=u"试用时长")
    price = models.FloatField(help_text=u"定价元/月")
    total_price = models.FloatField(help_text=u"定价元/月")
    dep_info = models.CharField(max_length=2000, default='[]', help_text=u"依赖服务内存、节点信息")

group_publish_type = (
    ('services_group', u'应用组'), ("cloud_frame", u'云框架'),
)


class AppServiceGroup(BaseModel):
    """服务组分享记录"""

    class Meta:
        db_table = "app_service_group"
        unique_together = ('group_share_id', 'group_version')

    tenant_id = models.CharField(max_length=32, help_text=u"租户id")
    group_share_id = models.CharField(max_length=32, unique=True, help_text=u"服务组发布id")
    group_share_alias = models.CharField(max_length=100, help_text=u"服务组发布名称")
    group_id = models.CharField(max_length=100, help_text=u"对应的服务分类ID,为0表示不是导入或者同步的数据")
    service_ids = models.CharField(max_length=1024, null=False, help_text=u"对应的服务id")
    is_success = models.BooleanField(default=False, help_text=u"发布是否成功")
    step = models.IntegerField(default=0, help_text=u"当前发布进度")
    publish_type = models.CharField(max_length=16, default="services_group", choices=group_publish_type, help_text=u"发布的应用组类型")
    group_version = models.CharField(max_length=20, null=False, default="0.0.1", help_text=u"服务组版本")
    is_market = models.BooleanField(default=False, blank=True, help_text=u"是否发布到公有市场")
    desc = models.CharField(max_length=400, null=True, blank=True, help_text=u"更新说明")
    installable = models.BooleanField(default=True, blank=True, help_text=u"发布到云市后是否允许安装")
    create_time = models.DateTimeField(auto_now_add=True, help_text=u"创建时间")
    update_time = models.DateTimeField(auto_now_add=True, help_text=u"更新时间")
    deploy_time = models.DateTimeField(auto_now_add=True, help_text=u"最后一次被部署的时间")
    installed_count = models.IntegerField(default=0, help_text=u"部署次数")
    source = models.CharField(max_length=32, default='local', null=False, blank=True, help_text=u"应用组数据来源")
    enterprise_id = models.IntegerField(default=0, help_text=u"应用组的企业id")
    share_scope = models.CharField(max_length=20, null=False, help_text=u"分享范围")
    is_publish_to_market = models.BooleanField(default=False, blank=True, help_text=u"判断该版本应用组是否之前发布过公有市场")


class PublishedGroupServiceRelation(BaseModel):
    """分享的服务组和服务的关系"""

    class Meta:
        db_table = "publish_group_service_relation"

    group_pk = models.IntegerField()
    service_id = models.CharField(max_length=32, help_text=u"服务id")
    service_key = models.CharField(max_length=32, help_text=u"服务key")
    version = models.CharField(max_length=20, help_text=u"当前最新版本")
