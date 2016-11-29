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


class RegionProvider(BaseModel):
    class Meta:
        db_table = "region_provider"

    provider_name = models.CharField(max_length=32, help_text=u"提供商")
    user_id = models.IntegerField(help_text=u"提供商")

class RegionResourceProviderPrice(BaseModel):
    class Meta:
        db_table = "region_resource_provider_price"

    region = models.CharField(max_length=16, null=False, help_text=u"数据中心")
    provider = models.CharField(max_length=32, help_text=u"提供商")
    memory_price = models.DecimalField(max_digits=10, decimal_places=4, default=0.0000, help_text=u"内存单价(G)")
    disk_price = models.DecimalField(max_digits=10, decimal_places=4, default=0.0000, help_text=u"磁盘单价(G)")
    net_price = models.DecimalField(max_digits=10, decimal_places=4, default=0.0000, help_text=u"网络单价(G)")


class RegionResourceSalesPrice(BaseModel):
    class Meta:
        db_table = "region_resource_sales_price"

    region = models.CharField(max_length=16, null=False, help_text=u"数据中心")
    provider = models.CharField(max_length=32, help_text=u"提供商")
    saler = models.CharField(max_length=32, default="goodrain", help_text=u"销售方")
    saler_channel = models.CharField(max_length=32, help_text=u"销售渠道")
    memory_price = models.DecimalField(max_digits=10, decimal_places=4, default=0.0000, help_text=u"内存按需单价(G)")
    memory_package_price = models.DecimalField(max_digits=10, decimal_places=4, default=0.0000, help_text=u"内存包量单价(G)")
    disk_price = models.DecimalField(max_digits=10, decimal_places=4, default=0.0000, help_text=u"磁盘按需单价(G)")
    disk_package_price = models.DecimalField(max_digits=10, decimal_places=4, default=0.0000, help_text=u"磁盘包量单价(G)")
    net_price = models.DecimalField(max_digits=10, decimal_places=4, default=0.0000, help_text=u"网络按需单价(G)")
    net_package_price = models.DecimalField(max_digits=10, decimal_places=4, default=0.0000, help_text=u"网络包量单价(G)")