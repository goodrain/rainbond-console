# -*- coding: utf8 -*-
from django.db import models
import django.db.models.options as options
options.DEFAULT_NAMES = options.DEFAULT_NAMES + ('in_db',)

from .main import BaseModel


class App(BaseModel):

    class Meta:
        in_db = 'stack'
        db_table = 'app'

    name = models.CharField(max_length=20, unique=True, help_text=u"名称")
    description = models.CharField(max_length=400, null=True, blank=True, help_text=u"描述")
    service_key = models.CharField(max_length=32, db_index=True, null=True, blank=True, help_text=u"关联的已发布服务")
    category_id = models.IntegerField(help_text=u"分类ID")
    pay_type = models.CharField(max_length=10, default="unpay", blank=True, help_text=u"付费类型")
    logo = models.URLField(max_length=100, null=True, blank=True, help_text=u"logo")
    website = models.URLField(max_length=100, null=True, blank=True, help_text=u"应用首页")
    using = models.IntegerField(help_text=u"应用使用人次")
    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)
    creater = models.IntegerField(null=True, help_text=u"创建人")


class AppUsing(BaseModel):

    class Meta:
        in_db = 'stack'
        db_table = 'app_using'

    app_id = models.IntegerField(db_index=True, help_text=u'app_id')
    user_id = models.IntegerField(help_text=u"用户id")
    install_count = models.SmallIntegerField(default=0, help_text=u"用户安装次数")


class Category(BaseModel):

    class Meta:
        in_db = 'stack'
        db_table = 'category'

    name = models.CharField(max_length=20, unique=True, help_text=u"名称")
    level = models.CharField(max_length=20, help_text=u"分类级别")
    parent = models.IntegerField(db_index=True, default=0, help_text=u"父分类")
    root = models.IntegerField(db_index=True, default=0, help_text=u"根分类")
