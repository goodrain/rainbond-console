# -*- coding: utf8 -*-
from datetime import datetime

from django.db import models


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


class RegionClusterInfo(BaseModel):
    class Meta:
        db_table = 'region_cluster_info'

    region_id = models.CharField(max_length=32, help_text=u"对应的region_id")
    cluster_name = models.CharField(max_length=32, help_text=u"数据中心名称")
    cluster_id = models.CharField(max_length=32, help_text=u"集群cluster_id")
    cluster_alias = models.CharField(max_length=32, help_text=u"数据中心别名")
    enable = models.BooleanField(default=False, help_text=u"集群是否启用")
    create_time = models.DateTimeField(auto_now_add=True, blank=True, help_text=u"创建时间")


class NodeInstallInfo(BaseModel):
    class Meta:
        db_table = "node_info"

    region_id = models.CharField(max_length=32, help_text=u"对应的region_id")
    node_ip = models.CharField(max_length=32, null=False, help_text=u"节点ip")
    init_status = models.CharField(max_length=15, null=False, help_text=u"节点初始化状态 uninit,initing,inited")
    install_status = models.CharField(max_length=15, null=False, help_text=u"节点安装状态 uninstall,installing,installed")
    create_time = models.DateTimeField(auto_now_add=True, blank=True, help_text=u"创建时间")
