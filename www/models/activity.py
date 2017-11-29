# -*- coding: utf8 -*-
from main import BaseModel
from django.db import models


class TenantActivity(BaseModel):
    """活动租户记录"""
    class Meta:
        db_table = 'tenant_activity'
    tenant_id = models.CharField(max_length=32, help_text=u"租户id")
    activity_id = models.CharField(max_length=32, default='998', help_text=u"活动id")
    create_time = models.DateTimeField(auto_now_add=True, blank=True, help_text=u"创建时间")

