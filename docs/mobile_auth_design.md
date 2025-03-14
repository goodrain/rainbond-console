# 手机号验证与短信认证设计文档

## 概述

本文档概述了在Rainbond平台中实现手机号+短信验证码系统用于用户注册和登录的设计方案。该系统将利用阿里云的短信服务向用户手机发送验证码。

## 需求

1. **注册**：用户需要输入用户名、手机号和验证码
2. **登录**：用户可以使用手机号+短信验证码登录
3. **配置**：平台管理员可以配置短信模板

## 架构组件

### 1. 数据模型

```python
# 新模型用于存储短信验证码
class SMSVerificationCode(models.Model):
    """短信验证码模型"""
    phone = models.CharField(max_length=20)
    code = models.CharField(max_length=10)
    purpose = models.CharField(max_length=20)  # "login"或"register"
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)

# 注意：SMS配置将直接存储在现有的ConsoleSysConfig表中，无需创建新表
```

### 2. API端点

#### 短信配置
- `GET /console/enterprises/<enterprise_id>/sms-config` - 获取短信配置
- `PUT /console/enterprises/<enterprise_id>/sms-config` - 更新短信配置

#### 短信验证
- `POST /console/sms/send-code` - 发送登录/注册验证码

#### 用户注册/登录
- `POST /console/users/register-by-phone` - 使用手机号和验证码注册
- `POST /console/users/login-by-phone` - 使用手机号和验证码登录

### 3. 服务

#### 短信服务
此服务将处理与阿里云短信API的交互。

```python
# sms_service.py
class SMSService:
    def __init__(self, enterprise_id):
        self.enterprise_id = enterprise_id
        self.config = self._load_config()
    
    def _load_config(self):
        # 从ConsoleSysConfig表加载短信配置
        pass
    
    def send_verification_code(self, phone, purpose):
        # 生成随机验证码
        # 将验证码存储到SMSVerificationCode模型
        # 使用阿里云SDK发送验证码
        pass
    
    def verify_code(self, phone, code, purpose):
        # 检查验证码是否有效且未过期
        # 此方法将被登录/注册服务调用，不作为独立API
        pass
```

#### 用户认证服务（扩展）
扩展现有用户认证服务以支持基于手机的操作。

```python
# user_auth_service.py
class UserAuthService:
    def register_by_phone(self, username, phone, code, real_name=None):
        # 验证验证码
        # 创建新用户
        pass
    
    def login_by_phone(self, phone, code):
        # 验证验证码
        # 通过手机号查找用户
        # 生成JWT令牌
        pass
```

### 4. 配置管理

扩展`config_service.py`以包含短信配置：

```python
# 在config_service.py中
class EnterpriseConfigService:
    # 向cfg_keys添加SMS_CONFIG
    
    def init_base_config_value(self):
        self.cfg_keys.append("SMS_CONFIG")
        self.cfg_keys_value["SMS_CONFIG"] = {
            "value": {
                "access_key": None,
                "access_secret": None,
                "sign_name": None,
                "template_code": None,
            },
            "desc": "短信认证配置",
            "enable": True
        }
```

## 实施计划

### 1. 短信配置实现

1. 扩展`config_service.py`以支持SMS配置
2. 实现短信配置API端点
3. 测试配置保存和读取

### 2. 数据库模型实现

1. 创建SMSVerificationCode模型用于验证码存储
2. 创建并运行迁移

### 3. 短信服务实现

1. 集成阿里云短信SDK
2. 实现发送验证码的方法
3. 实现验证码验证逻辑

### 4. API端点实现

1. 实现验证码发送端点
2. 实现基于手机的注册端点
3. 实现基于手机的登录端点

### 5. 注册/登录流程

1. 更新注册流程以支持手机验证
2. 实现基于手机的登录流程

## 与阿里云短信的集成

### SDK安装

```bash
pip install alibabacloud_dysmsapi20170525
```

### 基本用法

```python
from alibabacloud_dysmsapi20170525.client import Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_dysmsapi20170525 import models as dysmsapi_models

def create_client(access_key_id, access_key_secret):
    """创建阿里云短信客户端"""
    config = open_api_models.Config(
        access_key_id=access_key_id,
        access_key_secret=access_key_secret
    )
    config.endpoint = 'dysmsapi.aliyuncs.com'
    return Client(config)

def send_sms(client, phone_numbers, sign_name, template_code, template_param):
    """使用阿里云发送短信"""
    request = dysmsapi_models.SendSmsRequest(
        phone_numbers=phone_numbers,
        sign_name=sign_name,
        template_code=template_code,
        template_param=template_param
    )
    return client.send_sms(request)
```

## 安全考虑

1. **速率限制：** 为短信发送实施速率限制以防止滥用（每个手机号每分钟最多1条，每天最多5条）
2. **验证码过期：** 确保验证码在短时间后过期（5分钟）
3. **安全存储：** 确保短信配置数据（特别是access_secret）安全存储

## 测试计划

1. **单元测试：** 独立测试短信服务功能
2. **API测试：** 使用模拟短信服务测试API端点
3. **集成测试：** 使用测试短信账户测试完整流程

## 兼容性考虑

1. 与现有用户账户保持兼容性（手机号需要在Users表中增加非空字段）
2. 确保系统与已有的JWT认证协同工作
3. 允许已有用户通过设置手机号后使用手机验证码登录

## 结论

本设计概述了实现手机号+短信验证用于用户注册和登录的方法。通过利用阿里云的短信服务并扩展现有认证基础设施，我们可以提供安全且用户友好的认证体验。
