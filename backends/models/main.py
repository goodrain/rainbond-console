# -*- coding: utf8 -*-
from datetime import datetime
from django.db import models
from www.utils.crypt import make_uuid
from django.conf import settings


def logo_path(instance, filename):
    suffix = filename.split('.')[-1]
    return '{0}/logo/{1}.{2}'.format(settings.MEDIA_ROOT, make_uuid(), suffix)


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
            data[f.name] = value
        return data


class BackendAdminUser(models.Model):
    """超级管理员"""

    class Meta:
        db_table = "backend_admin"

    user_id = models.AutoField(primary_key=True, max_length=10)
    username = models.CharField(max_length=15, unique=True, help_text=u"登录名")
    password = models.CharField(max_length=60, help_text=u"密码")
    create_time = models.DateTimeField(auto_now_add=True, blank=True, help_text=u"创建时间")


class CloundBangImages(BaseModel):
    class Meta:
        db_table = 'clound_bang_images'

    identify = models.CharField(max_length=32, help_text='标识')
    logo = models.FileField(upload_to=logo_path, null=True, blank=True, help_text=u"logo")
    create_time = models.DateTimeField(auto_now_add=True, help_text=u"创建时间")


class RegionConfig(BaseModel):
    class Meta:
        db_table = 'region_info'

    region_id = models.CharField(max_length=32, unique=True, help_text=u"region id")
    region_name = models.CharField(max_length=32, unique=True, help_text=u"数据中心名称")
    region_alias = models.CharField(max_length=32, help_text=u"数据中心别名")
    url = models.CharField(max_length=256, help_text=u"数据中心API url")
    wsurl = models.CharField(max_length=256, help_text=u"数据中心Websocket url")
    httpdomain = models.CharField(max_length=256, help_text=u"数据中心http应用访问根域名")
    tcpdomain = models.CharField(max_length=256, help_text=u"数据中心tcp应用访问根域名")
    token = models.CharField(max_length=40, null=True, blank=True, default="", help_text=u"数据中心token")
    status = models.CharField(max_length=2, help_text=u"数据中心状态 0：编辑中 1:启用 2：停用 3:维护中")
    create_time = models.DateTimeField(auto_now_add=True, blank=True, help_text=u"创建时间")
    desc = models.CharField(max_length=128, blank=True, help_text=u"数据中心描述")
    scope = models.CharField(max_length=10, default="private", help_text=u"数据中心范围 private|public")


class RegionClusterInfo(BaseModel):
    class Meta:
        db_table = 'region_cluster_info'

    region_id = models.CharField(max_length=32, help_text=u"对应的region_id")
    cluster_name = models.CharField(max_length=32, help_text=u"数据中心名称")
    cluster_id = models.CharField(max_length=32, help_text=u"集群cluster_id")
    cluster_alias = models.CharField(max_length=32, help_text=u"数据中心别名")
    enable = models.BooleanField(default=False, help_text=u"集群是否启用")
    create_time = models.DateTimeField(auto_now_add=True, blank=True, help_text=u"创建时间")


class Announcement(BaseModel):
    class Meta:
        db_table = "announcement"

    announcement_id = models.CharField(max_length=32, null=False, help_text=u"通知id")
    content = models.CharField(max_length=256, help_text=u"通知内容")
    a_tag = models.CharField(max_length=256, null=True, blank=True, default="", help_text=u"A标签文字")
    a_tag_url = models.CharField(max_length=1024, null=True, blank=True, default="", help_text=u"a标签跳转地址")
    type = models.CharField(max_length=15, null=True, blank=True, default="all", help_text=u"通知类型")
    active = models.BooleanField(default=True, help_text=u"通知是否启用")
    create_time = models.DateTimeField(auto_now_add=True, blank=True, help_text=u"创建时间")


class NodeInstallInfo(BaseModel):
    class Meta:
        db_table = "node_info"

    region_id = models.CharField(max_length=32, help_text=u"对应的region_id")
    node_ip = models.CharField(max_length=32, null=False, help_text=u"节点ip")
    init_status = models.CharField(max_length=15, null=False, help_text=u"节点初始化状态 uninit,initing,inited")
    install_status = models.CharField(max_length=15, null=False, help_text=u"节点安装状态 uninstall,installing,installed")
    create_time = models.DateTimeField(auto_now_add=True, blank=True, help_text=u"创建时间")