# -*- coding: utf8 -*-
from django.db import models
from django.utils.crypto import salted_hmac
from www.utils.crypt import encrypt_passwd, make_tenant_id
from django.db.models.fields import DateTimeField

# Create your models here.

user_origion = (
    (u"自主注册", "registration"), (u"邀请注册", "invitation")
)

tenant_type = (
    (u"免费租户", "free"), (u"付费租户", "paid")
)

service_identity = (
    (u"管理员", "admin"), (u"开发者", "developer"), (u"观察者", "viewer")
)

tenant_identity = (
    (u"管理员", "admin"), (u"开发者", "developer"), (u"观察者", "viewer"), (u"访问", "access")
)


class AnonymousUser(object):
    id = None
    pk = None
    username = ''

    def __init__(self):
        pass

    def __str__(self):
        return 'AnonymousUser'

    def __eq__(self, other):
        return isinstance(other, self.__class__)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return 1  # instances always return the same hash value

    def save(self):
        raise NotImplementedError("Django doesn't provide a DB representation for AnonymousUser.")

    def delete(self):
        raise NotImplementedError("Django doesn't provide a DB representation for AnonymousUser.")

    def set_password(self, raw_password):
        raise NotImplementedError("Django doesn't provide a DB representation for AnonymousUser.")

    def check_password(self, raw_password):
        raise NotImplementedError("Django doesn't provide a DB representation for AnonymousUser.")

    def get_group_permissions(self, obj=None):
        return set()

    def is_anonymous(self):
        return True

    def is_authenticated(self):
        return False


class Users(models.Model):
    class Meta:
        db_table = 'user_info'

    user_id = models.AutoField(primary_key=True, max_length=10)
    email = models.EmailField(max_length=35, unique=True, help_text=u"邮件地址")
    nick_name = models.CharField(max_length=24, unique=True, null=True, blank=True, help_text=u"用户昵称")
    password = models.CharField(max_length=16, help_text=u"密码")
    phone = models.CharField(max_length=11, null=True, blank=True, help_text=u"手机号码")
    is_active = models.BooleanField(default=True, help_text=u"激活状态")
    origion = models.CharField(max_length=12, choices=user_origion, help_text=u"用户来源")
    create_time = models.DateTimeField(auto_now_add=True, blank=True, help_text=u"创建时间")
    git_user_id = models.IntegerField(help_text=u"gitlab 用户id", default=0)
    github_token = models.CharField(max_length=60, help_text=u"github token")

    def set_password(self, raw_password):
        self.password = encrypt_passwd(self.email + raw_password)

    def check_password(self, raw_password):
        return bool(encrypt_passwd(self.email + raw_password) == self.password)

    def is_anonymous(self):
        return False

    def is_authenticated(self):
        return True

    def get_session_auth_hash(self):
        """
        Returns an HMAC of the password field.
        """
        key_salt = "goodrain.com.models.get_session_auth_hash"
        return salted_hmac(key_salt, self.password).hexdigest()

    def __unicode__(self):
        return self.nick_name or self.email


class Tenants(models.Model):
    class Meta:
        db_table = 'tenant_info'

    ID = models.AutoField(primary_key=True, max_length=10)
    tenant_id = models.CharField(max_length=33, unique=True, default=make_tenant_id, help_text=u"租户id")
    tenant_name = models.CharField(max_length=40, unique=True, help_text=u"租户名称")
    region = models.CharField(max_length=10, default='test', help_text=u"区域中心")
    is_active = models.BooleanField(default=True, help_text=u"激活状态")
    pay_type = models.CharField(max_length=5, choices=tenant_type, help_text=u"付费状态")
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text=u"账户余额")
    create_time = models.DateTimeField(auto_now_add=True, blank=True, help_text=u"创建时间")

    def __unicode__(self):
        return self.tenant_name


class BaseModel(models.Model):
    class Meta:
        abstract = True

    ID = models.AutoField(primary_key=True, max_length=10)

service_status = (
    (u"已发布", 'published'), (u"测试中", "test"),
)

service_category = (
    (u"应用", 'application'), (u"缓存", 'cache'), (u"存储", 'store')
)

extend_method = (
    (u"不伸缩", 'stateless'), (u"垂直伸缩", 'vertical')
)


class ServiceInfo(BaseModel):
    class Meta:
        db_table = 'service'

    service_key = models.CharField(max_length=32, unique=True, help_text=u"服务key")
    publisher = models.CharField(max_length=40, help_text=u"发布者")
    service_name = models.CharField(max_length=40, help_text=u"服务名")
    pic = models.CharField(max_length=100, null=True, blank=True, help_text=u"服务图片")
    info = models.CharField(max_length=100, null=True, blank=True, help_text=u"简介")
    desc = models.CharField(max_length=400, null=True, blank=True, help_text=u"描述")
    status = models.CharField(max_length=15, choices=service_status, help_text=u"服务状态：published")
    category = models.CharField(max_length=15, choices=service_category, help_text=u"服务分类：application,cache,store")
    is_service = models.BooleanField(default=False, blank=True, help_text=u"是否service")
    is_web_service = models.BooleanField(default=False, blank=True, help_text=u"是否web服务")
    version = models.CharField(max_length=20, help_text=u"版本")
    image = models.CharField(max_length=50, help_text=u"镜像")
    extend_method = models.CharField(max_length=15, choices=extend_method, default='stateless', help_text=u"伸缩方式")
    cmd = models.CharField(max_length=100, null=True, blank=True, help_text=u"启动参数")
    setting = models.CharField(max_length=100, null=True, blank=True, help_text=u"设置项")
    env = models.CharField(max_length=200, null=True, blank=True, help_text=u"环境变量")
    dependecy = models.CharField(max_length=100, null=True, blank=True, help_text=u"依赖服务--service_key待确认")
    min_node = models.IntegerField(help_text=u"启动个数", default=1)
    min_cpu = models.IntegerField(help_text=u"cpu个数", default=500)
    min_memory = models.IntegerField(help_text=u"内存大小单位（M）", default=256)
    inner_port = models.IntegerField(help_text=u"内部端口")
    publish_time = models.DateTimeField(help_text=u"发布时间", auto_now=True)
    volume_mount_path = models.CharField(max_length=50, null=True, blank=True, help_text=u"mount目录")    
    service_type = models.CharField(max_length=50, null=True, blank=True, help_text=u"服务类型:web,mysql,redis,mongodb,phpadmin")

    def __unicode__(self):
        return self.service_key


class TenantServiceInfo(BaseModel):
    class Meta:
        db_table = 'tenant_service'
        unique_together = ('tenant_id', 'service_alias')

    service_id = models.CharField(max_length=32, unique=True, help_text=u"服务id")
    tenant_id = models.CharField(max_length=32, help_text=u"租户id")
    service_key = models.CharField(max_length=32, help_text=u"服务key")
    service_alias = models.CharField(max_length=100, help_text=u"服务别名")
    service_region = models.CharField(max_length=15, help_text=u"服务所属区")
    desc = models.CharField(max_length=200, null=True, blank=True, help_text=u"描述")
    category = models.CharField(max_length=15, help_text=u"服务分类：application,cache,store")
    service_port = models.IntegerField(help_text=u"服务端口", default=8000)
    is_web_service = models.BooleanField(default=False, blank=True, help_text=u"是否web服务")
    version = models.CharField(max_length=20, help_text=u"版本")
    image = models.CharField(max_length=50, help_text=u"镜像")
    cmd = models.CharField(max_length=100, null=True, blank=True, help_text=u"启动参数")
    setting = models.CharField(max_length=100, null=True, blank=True, help_text=u"设置项")
    env = models.CharField(max_length=200, null=True, blank=True, help_text=u"环境变量")
    min_node = models.IntegerField(help_text=u"启动个数", default=1)
    min_cpu = models.IntegerField(help_text=u"cpu个数", default=500)
    min_memory = models.IntegerField(help_text=u"内存大小单位（M）", default=256)
    inner_port = models.IntegerField(help_text=u"内部端口")
    volume_mount_path = models.CharField(max_length=50, null=True, blank=True, help_text=u"mount目录")
    host_path = models.CharField(max_length=300, null=True, blank=True, help_text=u"mount目录")
    deploy_version = models.CharField(max_length=20, null=True, blank=True, help_text=u"部署版本")
    code_from = models.CharField(max_length=20, null=True, blank=True, help_text=u"代码来源:gitlab,github")
    git_url = models.CharField(max_length=100, null=True, blank=True, help_text=u"code代码仓库")
    create_time = models.DateTimeField(auto_now=True, help_text=u"创建时间")
    git_project_id = models.IntegerField(help_text=u"gitlab 中项目id", default=0)
    is_code_upload = models.BooleanField(default=False, blank=True, help_text=u"是否上传代码")
    code_version = models.CharField(max_length=100, null=True, blank=True, help_text=u"代码版本")
    service_type = models.CharField(max_length=50, null=True, blank=True, help_text=u"服务类型:web,mysql,redis,mongodb,phpadmin")

    def __unicode__(self):
        return self.service_alias
        
    def toJSON(self):
        data = {}
        for f in self._meta.fields:
            obj = getattr(self, f.name)
            if type(f.name) == DateTimeField:                
                data[f.name] = obj.strftime('%Y-%m-%d %H:%M:%S')
            else:
                data[f.name] = obj
        return data

class TenantServiceInfoDelete(BaseModel):
    class Meta:
        db_table = 'tenant_service_delete'
        
    service_id = models.CharField(max_length=32, unique=True, help_text=u"服务id")
    tenant_id = models.CharField(max_length=32, help_text=u"租户id")
    service_key = models.CharField(max_length=32, help_text=u"服务key")
    service_alias = models.CharField(max_length=100, help_text=u"服务别名")
    service_region = models.CharField(max_length=15, help_text=u"服务所属区")
    desc = models.CharField(max_length=200, null=True, blank=True, help_text=u"描述")
    category = models.CharField(max_length=15, help_text=u"服务分类：application,cache,store")
    service_port = models.IntegerField(help_text=u"服务端口", default=8000)
    is_web_service = models.BooleanField(default=False, blank=True, help_text=u"是否web服务")
    version = models.CharField(max_length=20, help_text=u"版本")
    image = models.CharField(max_length=50, help_text=u"镜像")
    cmd = models.CharField(max_length=100, null=True, blank=True, help_text=u"启动参数")
    setting = models.CharField(max_length=100, null=True, blank=True, help_text=u"设置项")
    env = models.CharField(max_length=200, null=True, blank=True, help_text=u"环境变量")
    min_node = models.IntegerField(help_text=u"启动个数", default=1)
    min_cpu = models.IntegerField(help_text=u"cpu个数", default=500)
    min_memory = models.IntegerField(help_text=u"内存大小单位（M）", default=256)
    inner_port = models.IntegerField(help_text=u"内部端口")
    volume_mount_path = models.CharField(max_length=50, null=True, blank=True, help_text=u"mount目录")
    host_path = models.CharField(max_length=300, null=True, blank=True, help_text=u"mount目录")
    deploy_version = models.CharField(max_length=20, null=True, blank=True, help_text=u"部署版本")
    git_url = models.CharField(max_length=100, null=True, blank=True, help_text=u"git代码仓库")
    create_time = models.DateTimeField(auto_now=True, help_text=u"创建时间")
    git_project_id = models.IntegerField(help_text=u"gitlab 中项目id", default=0)
    is_code_upload = models.BooleanField(default=False, blank=True, help_text=u"是否web服务")
    service_type = models.CharField(max_length=50, null=True, blank=True, help_text=u"服务类型:web,mysql,redis,mongodb,phpadmin")
    delete_time = models.DateTimeField(auto_now_add=True)
    
class TenantServiceLog(BaseModel):
    class Meta:
        db_table = 'tenant_service_log'

    user_id = models.IntegerField(help_text=u"用户id")
    user_name = models.CharField(max_length=40, help_text=u"用户名")
    service_id = models.CharField(max_length=32, help_text=u"服务id")
    tenant_id = models.CharField(max_length=32, help_text=u"租户id")
    action = models.CharField(max_length=15, help_text=u"分类：deploy,stop,restart")
    create_time = models.DateTimeField(auto_now=True, help_text=u"创建时间")
    
class TenantServiceRelation(BaseModel):
    class Meta:
        db_table = 'tenant_service_relation'
        unique_together = ('service_id', 'dep_service_id')
    tenant_id = models.CharField(max_length=32, help_text=u"租户id")
    service_id = models.CharField(max_length=32, help_text=u"服务id")
    dep_service_id = models.CharField(max_length=32, help_text=u"依赖服务id")
    dep_service_type = models.CharField(max_length=50, null=True, blank=True, help_text=u"服务类型:web,mysql,redis,mongodb,phpadmin")
    dep_order = models.IntegerField(help_text=u"依赖顺序")

class ServiceDomain(BaseModel):
    class Meta:
        db_table = 'service_domain'

    service_id = models.CharField(max_length=32, help_text=u"服务id")
    service_name = models.CharField(max_length=32, help_text=u"服务名")
    domain_name = models.CharField(max_length=32, help_text=u"域名")
    create_time = models.DateTimeField(auto_now=True, help_text=u"创建时间")

    def __unicode__(self):
        return self.domain_name


class PermRelService(BaseModel):
    class Meta:
        db_table = 'service_perms'

    user_id = models.IntegerField(help_text=u"用户id")
    service_id = models.IntegerField(help_text=u"服务id")
    identity = models.CharField(max_length=15, choices=service_identity, help_text=u"服务身份")


class PermRelTenant(BaseModel):
    class Meta:
        db_table = 'tenant_perms'

    user_id = models.IntegerField(help_text=u"关联用户")
    tenant_id = models.IntegerField(help_text=u"关联租户")
    identity = models.CharField(max_length=15, choices=tenant_identity, help_text=u"租户身份")
    
    
class TenantAccount(BaseModel):
    class Meta:
        db_table = 'tenant_account'
    tenant_id = models.CharField(max_length=32, help_text=u"租户id")
    tenant_name = models.CharField(max_length=40, unique=True, help_text=u"租户名称")
    balance_money = models.DecimalField(max_digits=9, decimal_places=2, help_text=u"余额")

class TenantRecharge(BaseModel):
    class Meta:
        db_table = 'tenant_recharge'
    tenant_id = models.CharField(max_length=32, help_text=u"租户id")
    user_id = models.IntegerField(help_text=u"充值用户")
    user_name = models.CharField(max_length=40, help_text=u"用户名")
    order_no = models.CharField(max_length=60, help_text=u"订单号")
    recharge_type = models.CharField(max_length=40, help_text=u"充值类型")
    money = models.DecimalField(max_digits=9, decimal_places=2, help_text=u"充值金额")
    subject = models.CharField(max_length=40, help_text=u"主题")
    body = models.CharField(max_length=80, help_text=u"详情")
    show_url = models.CharField(max_length=100, help_text=u"详情url")
    status = models.CharField(max_length=30, help_text=u"充值状态")
    trade_no = models.CharField(max_length=64, help_text=u"支付宝交易号")
    time = models.DateTimeField(auto_now=True, help_text=u"创建时间")
    
class TenantServiceStatics(BaseModel):
    class Meta:
        db_table = 'tenant_service_statics'
        unique_together = ('service_id', 'time_stamp')  
        get_latest_by = 'ID'  
    tenant_id = models.CharField(max_length=32, help_text=u"租户id")
    service_id = models.CharField(max_length=32, help_text=u"服务id")
    pod_id = models.CharField(max_length=32, help_text=u"服务id")
    node_num = models.IntegerField(help_text=u"节点个数", default=0)
    container_cpu = models.IntegerField(help_text=u"cpu使用", default=0)
    container_memory = models.IntegerField(help_text=u"内存使用K", default=0)
    container_memory_working = models.IntegerField(help_text=u"正在使用内存K", default=0)
    pod_cpu = models.IntegerField(help_text=u"cpu使用", default=0)
    pod_memory = models.IntegerField(help_text=u"内存使用K", default=0)
    pod_memory_working = models.IntegerField(help_text=u"正在使用内存K", default=0)
    container_disk = models.IntegerField(help_text=u"磁盘使用K", default=0)
    storage_disk = models.IntegerField(help_text=u"磁盘使用K", default=0)
    net_in = models.IntegerField(help_text=u"网络使用K", default=0)
    net_out = models.IntegerField(help_text=u"网络使用K", default=0)    
    time_stamp = models.IntegerField(help_text=u"时间戳", default=0)
    time = models.DateTimeField(auto_now=True, help_text=u"创建时间")
    
class TenantConsume(BaseModel):
    class Meta:
        db_table = 'tenant_consume'
    tenant_id = models.CharField(max_length=32, help_text=u"租户id")
    service_id = models.CharField(max_length=32, help_text=u"服务id")
    service_alias = models.CharField(max_length=100, help_text=u"服务别名")
    node_num = models.IntegerField(help_text=u"节点个数", default=0)
    cpu = models.IntegerField(help_text=u"cpu使用", default=0)
    memory = models.IntegerField(help_text=u"内存使用K", default=0)
    disk = models.IntegerField(help_text=u"磁盘使用K", default=0)
    net = models.IntegerField(help_text=u"网络使用K", default=0)
    money = models.DecimalField(max_digits=9, decimal_places=2, help_text=u"消费金额", default=0)
    total_memory = models.IntegerField(help_text=u"内存使用K", default=0)
    fee_rule = models.CharField(max_length=60, help_text=u"计费规则")
    pay_status = models.CharField(max_length=10, help_text=u"扣费状态；payed,unpayed")
    time = models.DateTimeField(auto_now=True, help_text=u"创建时间")

class TenantFeeBill(BaseModel):
    class Meta:
        db_table = 'tenant_fee_bill'  
    tenant_id = models.CharField(max_length=32, help_text=u"租户id")  
    bill_title = models.CharField(max_length=100, help_text=u"发票标题")
    bill_type = models.CharField(max_length=10, help_text=u"公司或个人")
    bill_address = models.CharField(max_length=100, help_text=u"邮寄地址")
    bill_phone = models.CharField(max_length=100, help_text=u"邮寄电话")
    money = models.DecimalField(max_digits=9, decimal_places=2, help_text=u"发票金额")
    status = models.CharField(max_length=10, help_text=u"审核状态:已审核(approved)，未审核(unapproved)")
    time = models.DateTimeField(auto_now=True, help_text=u"创建时间")

class TenantPaymentNotify(BaseModel):
    class Meta:
        db_table = 'tenant_payment_notify'
    tenant_id = models.CharField(max_length=32, help_text=u"租户id")
    notify_type = models.CharField(max_length=10, help_text=u"通知类型：余额不足，欠费") 
    notify_content = models.CharField(max_length=200, help_text=u"通知类容")
    send_person = models.CharField(max_length=20, help_text=u"通知人")
    time = models.DateTimeField(auto_now=True, help_text=u"创建时间")


    


    
    
    
