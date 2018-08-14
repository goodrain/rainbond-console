# -*- coding: utf8 -*-
import re
from django.db import models
from django.utils.crypto import salted_hmac
from www.utils.crypt import encrypt_passwd, make_tenant_id
from django.db.models.fields import DateTimeField
from datetime import datetime


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


class ConsoleSysConfig(BaseModel):
    class Meta:
        db_table = 'console_sys_config'

    key = models.CharField(max_length=32, help_text=u"key")
    type = models.CharField(max_length=32, help_text=u"类型")
    value = models.CharField(max_length=4096, help_text=u"value")
    desc = models.CharField(max_length=40, null=True, blank=True, default="", help_text=u"描述")
    enable = models.BooleanField(default=True, help_text=u"是否生效")
    create_time = models.DateTimeField(auto_now_add=True, blank=True, help_text=u"创建时间")


class ConsoleSysConfigAttr(BaseModel):
    class Meta:
        db_table = 'console_sys_config_attr'

    attr_name = models.CharField(max_length=40, help_text=u"key")
    attr_val = models.CharField(max_length=256, help_text=u"key")
    attr_type = models.CharField(max_length=40, default='string', help_text=u"type")
    attr_desc = models.CharField(max_length=40, help_text=u"说明")
    config_id = models.IntegerField(help_text=u"配置项id：")
