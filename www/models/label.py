# -*- coding: utf8 -*-

from django.db import models

from .main import BaseModel


class Labels(BaseModel):
    class Meta:
        db_table = "labels"

    label_id = models.CharField(max_length=32, help_text="标签id")
    label_name = models.CharField(max_length=128, help_text="标签名(汉语拼音)")
    label_alias = models.CharField(max_length=15, help_text="标签名(汉字)")
    category = models.CharField(max_length=20, default="", help_text="标签分类")
    create_time = models.DateTimeField(auto_now_add=True, help_text="创建时间")


class ServiceLabels(BaseModel):
    class Meta:
        db_table = "service_labels"

    tenant_id = models.CharField(max_length=32, help_text="租户id")
    service_id = models.CharField(max_length=32, help_text="服务id")
    label_id = models.CharField(max_length=32, help_text="标签id")
    region = models.CharField(max_length=30, help_text="区域中心")
    create_time = models.DateTimeField(auto_now_add=True, help_text="创建时间")


class NodeLabels(BaseModel):
    class Meta:
        db_table = "node_labels"

    region_id = models.CharField(max_length=36, help_text="数据中心 id")
    node_uuid = models.CharField(max_length=36, help_text="节点uuid")
    label_id = models.CharField(max_length=32, help_text="标签id")
    create_time = models.DateTimeField(auto_now_add=True, help_text="创建时间")
