# -*- coding: utf8 -*-
from datetime import datetime

from django.conf import settings
from django.db import models
from www.utils.crypt import make_uuid

from .main import BaseModel

# Create your models here.

app_status = (
    ('show', '显示'),
    ("hidden", '隐藏'),
)


def logo_path(instance, filename):
    suffix = filename.split('.')[-1]
    return '{0}/logo/{1}.{2}'.format(settings.MEDIA_ROOT, make_uuid(), suffix)


class ServiceExtendMethod(BaseModel):
    class Meta:
        db_table = 'app_service_extend_method'

    service_key = models.CharField(max_length=32, help_text="组件key")
    app_version = models.CharField(max_length=64, null=False, help_text="当前最新版本")
    min_node = models.IntegerField(default=1, help_text="最小节点")
    max_node = models.IntegerField(default=20, help_text="最大节点")
    step_node = models.IntegerField(default=1, help_text="节点步长")
    min_memory = models.IntegerField(default=1, help_text="最小内存")
    max_memory = models.IntegerField(default=20, help_text="最大内存")
    step_memory = models.IntegerField(default=1, help_text="内存步长")
    is_restart = models.BooleanField(default=False, blank=True, help_text="是否重启")

    def to_dict(self):
        opts = self._meta
        data = {}
        for f in opts.concrete_fields:
            value = f.value_from_object(self)
            if isinstance(value, datetime):
                value = value.strftime('%Y-%m-%d %H:%M:%S')
            data[f.name] = value
        return data


class AppServiceGroup(BaseModel):
    """组件组分享记录"""

    class Meta:
        db_table = "app_service_group"
        unique_together = ('group_share_id', 'group_version')

    tenant_id = models.CharField(max_length=32, help_text="租户id")
    group_share_id = models.CharField(max_length=32, unique=True, help_text="应用组发布id")
    group_share_alias = models.CharField(max_length=100, help_text="应用组发布名称")
    group_id = models.CharField(max_length=100, help_text="对应的应用分类ID,为0表示不是导入或者同步的数据")
    service_ids = models.CharField(max_length=1024, null=False, help_text="对应的组件id")
    is_success = models.BooleanField(default=False, help_text="发布是否成功")
    step = models.IntegerField(default=0, help_text="当前发布进度")
    publish_type = models.CharField(max_length=16, default="services_group", help_text="发布的应用组类型")
    group_version = models.CharField(max_length=20, null=False, default="0.0.1", help_text="应用组版本")
    is_market = models.BooleanField(default=False, blank=True, help_text="是否发布到公有市场")
    desc = models.CharField(max_length=400, null=True, blank=True, help_text="更新说明")
    installable = models.BooleanField(default=True, blank=True, help_text="发布到云市后是否允许安装")
    create_time = models.DateTimeField(auto_now_add=True, help_text="创建时间")
    update_time = models.DateTimeField(auto_now_add=True, help_text="更新时间")
    deploy_time = models.DateTimeField(auto_now_add=True, help_text="最后一次被部署的时间")
    installed_count = models.IntegerField(default=0, help_text="部署次数")
    source = models.CharField(max_length=32, default='local', null=False, blank=True, help_text="应用组数据来源")
    enterprise_id = models.IntegerField(default=0, help_text="应用组的企业id")
    share_scope = models.CharField(max_length=20, null=False, help_text="分享范围")
    is_publish_to_market = models.BooleanField(default=False, blank=True, help_text="判断该版本应用组是否之前发布过公有市场")


class PublishedGroupServiceRelation(BaseModel):
    """分享的服务组和组件的关系"""

    class Meta:
        db_table = "publish_group_service_relation"

    group_pk = models.IntegerField()
    service_id = models.CharField(max_length=32, help_text="组件id")
    service_key = models.CharField(max_length=32, help_text="组件key")
    version = models.CharField(max_length=20, help_text="当前最新版本")
