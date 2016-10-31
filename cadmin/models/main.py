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
    type = models.CharField(max_length=40, help_text=u"类型:string,json,int,bool,list")
    value = models.CharField(max_length=400, help_text=u"value")
    category = models.CharField(max_length=40, help_text=u"分类：")
    create_time = models.DateTimeField(auto_now_add=True, blank=True, help_text=u"创建时间")
