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


class Region(BaseModel):
    class Meta:
        db_table = "region"

    name = models.CharField(max_length=32, help_text=u"数据中心缩写")
    show_name = models.CharField(max_length=32, help_text=u"数据中心名称")
    provider_name = models.CharField(max_length=32, help_text=u"提供商简称")
    work_status = models.CharField(max_length=16, default='prepared',
                                     help_text=u"数据中心工作状态,prepared|installed|authed|ready|work|stop")
    api_secret = models.CharField(max_length=32, default='', help_text=u"数据中心操作密钥")
    api_sign = models.CharField(max_length=32, default='', help_text=u"数据中心api签名")
    install_secret_key = models.CharField(max_length=32, default='', help_text=u"数据中心安装密钥")
    create_time = models.DateTimeField(auto_now_add=True, blank=True, help_text=u"创建时间")


class RegionProvider(BaseModel):
    class Meta:
        db_table = "region_provider"

    provider_name = models.CharField(max_length=32, null=True, default='', help_text=u"提供简称")
    enter_name = models.CharField(max_length=32, default='', help_text=u"企业名称")
    user_id = models.IntegerField(help_text=u"提供商")
    is_identify = models.IntegerField(default=0, help_text=u"是否已认证")
    business_prove = models.CharField(max_length=64, null=True, help_text=u"营业执照照片")
    remark = models.CharField(max_length=128, null=True, help_text=u"备注信息")
    status = models.IntegerField(default=0, help_text=u"0:注册未激活 1:已激活 2:锁定 3:注销")
    create_time = models.DateTimeField(auto_now_add=True, blank=True, help_text=u"创建时间")
    auth_time = models.DateTimeField(blank=True, null=True, help_text=u"认证时间")


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
    create_time = models.DateTimeField(auto_now_add=True, blank=True, help_text=u"创建时间")


class RegionResourceProviderSettle(BaseModel):
    class Meta:
        db_table = "region_resource_provider_settle"

    date = models.CharField(max_length=16, null=False, help_text=u"结算月份")
    region = models.CharField(max_length=16, null=False, help_text=u"数据中心")
    provider = models.CharField(max_length=32, help_text=u"提供商")

    used_tenant = models.IntegerField(help_text=u"按需使用租户")
    used_memory = models.IntegerField(help_text=u"按需使用内存")
    used_disk = models.IntegerField(help_text=u"按需使用磁盘")
    used_net = models.IntegerField(help_text=u"按需使用网络")
    used_resource_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text=u"按需资源费用")

    package_tenant = models.IntegerField(help_text=u"包月使用租户")
    package_day = models.IntegerField(help_text=u"包月使用内存")
    package_memory = models.IntegerField(help_text=u"包月使用内存")
    package_disk = models.IntegerField(help_text=u"包月使用磁盘")
    package_net = models.IntegerField(help_text=u"包月使用网络")
    package_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text=u"包月费用")
    package_resource_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text=u"包月资源超额费用")

    total_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text=u"待结算总费用")
    settle_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text=u"结算比率")
    settle_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text=u"实际结算费用")

    create_time = models.DateTimeField(auto_now_add=True, blank=True, help_text=u"创建时间")


class RegionProperty(BaseModel):
    class Meta:
        db_table = "region_property"

    region = models.CharField(max_length=16, null=False, help_text=u"数据中心")
    property = models.CharField(max_length=32, help_text=u"属性名")
    value = models.CharField(max_length=64, help_text=u"属性值")