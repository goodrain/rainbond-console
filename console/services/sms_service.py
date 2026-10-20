import json
import logging
import random
import threading
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional
from django.utils import timezone

from console.models.main import SMSVerificationCode
from console.repositories.enterprise_repo import enterprise_repo
from console.repositories.sms_repo import sms_repo
from console.exception.main import ServiceHandleException
from console.services.config_service import EnterpriseConfigService
from console.services.sms_config import normalize_sms_config, parse_sms_config
from console.services.sms_credentials import (VolcanoCredentialProvider,
                                              create_aliyun_client)

logger = logging.getLogger("default")


class SMSProvider(object):
    """短信服务商基类"""
    def send_sms(self, phone: str, code: str, config: Dict) -> None:
        raise NotImplementedError


class AliyunSMSProvider(SMSProvider):
    """阿里云短信"""
    def __init__(self, client_factory: Callable[[Dict], Any] = create_aliyun_client) -> None:
        self.client_factory = client_factory

    def send_sms(self, phone: str, code: str, config: Dict) -> None:
        from alibabacloud_dysmsapi20170525 import models as dysmsapi_models

        client = self.client_factory(config)
        send_req = dysmsapi_models.SendSmsRequest(
            phone_numbers=phone,
            sign_name=config["sign_name"],
            template_code=config["template_code"],
            template_param='{"code":"%s"}' % code
        )

        response = client.send_sms(send_req)
        if response.body.code != "OK":
            raise Exception(response.body.message)


class VolcanoSMSProvider(SMSProvider):
    """火山云短信"""
    def __init__(self, credential_provider: Optional[VolcanoCredentialProvider] = None,
                 sms_service_factory: Optional[Callable[[], Any]] = None) -> None:
        self.credential_provider = credential_provider or VolcanoCredentialProvider()
        self.sms_service_factory = sms_service_factory or self._create_sms_service
        self.send_lock = threading.Lock()

    @staticmethod
    def _create_sms_service() -> Any:
        from volcengine.sms.SmsService import SmsService
        return SmsService()

    def send_sms(self, phone: str, code: str, config: Dict) -> None:
        body = {
            "SmsAccount": config["sms_account"],
            "Sign": config["sign_name"],
            "TemplateID": config["template_code"],
            "TemplateParam": '{"code":"%s"}' % code,
            "PhoneNumbers": phone,
        }
        credentials = self.credential_provider.get_credentials(config)
        with self.send_lock:
            sms_service = self.sms_service_factory()
            sms_service.set_ak(credentials.access_key)
            sms_service.set_sk(credentials.access_secret)
            sms_service.set_session_token(credentials.session_token)
            response = sms_service.send_sms(json.dumps(body))
        # 火山云返回码为 0 表示成功
        if response.get("ResponseMetadata", {}).get("Error") is not None:
            error = response["ResponseMetadata"]["Error"]
            raise Exception(f"Code: {error.get('Code')}, Message: {error.get('Message')}")


class SMSService(object):
    def __init__(self) -> None:
        self.providers: Dict[str, SMSProvider] = {
            "aliyun": AliyunSMSProvider(),
            "volcano": VolcanoSMSProvider()
        }

    def generate_code(self) -> str:
        """生成6位随机验证码"""
        return ''.join([str(random.randint(0, 9)) for _ in range(6)])

    def send_verification_code(self, phone: str, purpose: str) -> str:
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

        provider = "unknown"
        auth_type = "unknown"
        try:
            config = normalize_sms_config(parse_sms_config(sms_config.value))
            provider = config["provider"]
            auth_type = config["auth_type"]
            self.providers[provider].send_sms(phone, code, config)
        except ServiceHandleException:
            raise
        except Exception as e:
            logger.exception(
                "send verification SMS failed provider=%s auth_type=%s error_type=%s",
                provider,
                auth_type,
                type(e).__name__,
            )
            raise ServiceHandleException(
                msg="send sms failed",
                msg_show="短信发送失败，请检查短信服务认证、签名和模板配置",
                status_code=500
            )

        # 保存验证码
        expires_at: datetime = timezone.now() + timedelta(minutes=5)
        sms_repo.create_verification(phone, code, purpose, expires_at)

        return code

    def verify_code(self, phone: str, code: str, purpose: str) -> bool:
        """校验验证码"""
        if not phone or not code or not purpose:
            raise ServiceHandleException(
                msg="invalid parameters",
                msg_show="参数不能为空",
                status_code=400
            )

        # 获取有效的验证码
        verification: Optional[SMSVerificationCode] = sms_repo.get_valid_code(phone, purpose)
        if not verification:
            raise ServiceHandleException(
                msg="verification code not found or expired",
                msg_show="验证码不存在或已过期",
                status_code=400
            )

        # 校验验证码
        if verification.code != code:
            raise ServiceHandleException(
                msg="verification code error",
                msg_show="验证码错误",
                status_code=400
            )

        return True


sms_service = SMSService()
