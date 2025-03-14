import random
from datetime import timedelta
from django.utils import timezone

from console.repositories.enterprise_repo import enterprise_repo
from console.repositories.sms_repo import sms_repo
from console.exception.main import ServiceHandleException
from console.services.config_service import EnterpriseConfigService

class SMSService(object):
    def generate_code(self):
        """生成6位随机验证码"""
        return ''.join([str(random.randint(0, 9)) for _ in range(6)])

    def send_verification_code(self, phone, purpose):
        """发送验证码"""
        # 检查发送频率
        recent_code = sms_repo.get_recent_code(phone)
        if recent_code:
            raise ServiceHandleException(
                msg="send too frequently",
                msg_show="请1分钟后再试",
                status_code=400
            )

        # 检查当天发送次数  
        today_count = sms_repo.count_today_codes(phone)
        if today_count >= 5:
            raise ServiceHandleException(
                msg="too many attempts today",
                msg_show="当天发送验证码次数已达上限",
                status_code=400
            )

        # 获取短信配置
        ent = enterprise_repo.get_enterprise_first()
        if not ent:
            raise ServiceHandleException(
                msg="no enterprise available on current platform",
                msg_show="当前平台无可用企业",
                status_code=400
            )
        config_service = EnterpriseConfigService(ent.enterprise_id, user_id=None)
        sms_config = config_service.get_config_by_key("SMS_CONFIG")
        if not sms_config or not sms_config.enable:
            raise ServiceHandleException(
                msg="sms service not configured",
                msg_show="请先配置短信服务",
                status_code=500
            )

        # 生成验证码
        code = self.generate_code()
        
        # 发送短信
        try:
            config = eval(sms_config.value)
            self._send_sms(phone, code, config)
        except Exception as e:
            raise ServiceHandleException(
                msg="send sms failed",
                msg_show=str(e),
                status_code=500
            )

        # 保存验证码
        expires_at = timezone.now() + timedelta(minutes=5)
        sms_repo.create_verification(phone, code, purpose, expires_at)
        
        return code

    def _send_sms(self, phone, code, config):
        """调用阿里云发送短信"""
        from alibabacloud_dysmsapi20170525.client import Client
        from alibabacloud_tea_openapi import models as open_api_models
        from alibabacloud_dysmsapi20170525 import models as dysmsapi_models

        client = Client(
            open_api_models.Config(
                access_key_id=config["access_key"],
                access_key_secret=config["access_secret"],
                endpoint='dysmsapi.aliyuncs.com'
            )
        )

        send_req = dysmsapi_models.SendSmsRequest(
            phone_numbers=phone,
            sign_name=config["sign_name"],
            template_code=config["template_code"],
            template_param='{"code":"%s"}' % code
        )

        response = client.send_sms(send_req)
        if response.body.code != "OK":
            raise Exception(response.body.message)

sms_service = SMSService() 