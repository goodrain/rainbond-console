import ast
import json
import re
from typing import Any, Dict


SUPPORTED_PROVIDERS = ("aliyun", "volcano")
SUPPORTED_AUTH_TYPES = ("access_key", "role")
ALIYUN_ROLE_ARN_PATTERN = re.compile(r"^acs:ram::[0-9]+:role/[A-Za-z0-9._-]+$")
VOLCANO_ROLE_TRN_PATTERN = re.compile(r"^trn:iam::[0-9]+:role/[A-Za-z0-9._-]+$")


class SMSConfigValidationError(ValueError):
    pass


def default_sms_config() -> Dict[str, str]:
    return {
        "provider": "aliyun",
        "auth_type": "access_key",
        "access_key": "",
        "access_secret": "",
        "role_arn": "",
        "role_trn": "",
        "sign_name": "",
        "template_code": "",
        "sms_account": "",
    }


def parse_sms_config(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if not isinstance(value, str) or not value.strip():
        raise SMSConfigValidationError("短信配置格式无效")

    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        try:
            parsed = ast.literal_eval(value)
        except (SyntaxError, ValueError) as exc:
            raise SMSConfigValidationError("短信配置格式无效") from exc

    if not isinstance(parsed, dict):
        raise SMSConfigValidationError("短信配置格式无效")
    return parsed


def apply_sms_config_defaults(config: Dict[str, Any]) -> Dict[str, Any]:
    result = default_sms_config()
    result.update(config)
    if not result.get("auth_type"):
        result["auth_type"] = "access_key"
    return result


def _require_nonblank(config: Dict[str, Any], field: str) -> str:
    value = config.get(field)
    if not isinstance(value, str) or not value.strip():
        raise SMSConfigValidationError("缺少必要的配置字段: {}".format(field))
    return value.strip()


def normalize_sms_config(config: Any) -> Dict[str, Any]:
    if not isinstance(config, dict):
        raise SMSConfigValidationError("短信配置格式无效")

    normalized = apply_sms_config_defaults(config)
    provider = _require_nonblank(normalized, "provider").lower()
    auth_type = _require_nonblank(normalized, "auth_type").lower()
    if provider not in SUPPORTED_PROVIDERS:
        raise SMSConfigValidationError("不支持的短信服务商")
    if auth_type not in SUPPORTED_AUTH_TYPES:
        raise SMSConfigValidationError("不支持的认证方式")

    normalized["provider"] = provider
    normalized["auth_type"] = auth_type
    for field in ("access_key", "access_secret", "sign_name", "template_code"):
        normalized[field] = _require_nonblank(normalized, field)

    if provider == "aliyun" and auth_type == "role":
        role_arn = _require_nonblank(normalized, "role_arn")
        if not ALIYUN_ROLE_ARN_PATTERN.match(role_arn):
            raise SMSConfigValidationError("阿里云 Role ARN 格式无效")
        normalized["role_arn"] = role_arn

    if provider == "volcano":
        normalized["sms_account"] = _require_nonblank(normalized, "sms_account")
        if auth_type == "role":
            role_trn = _require_nonblank(normalized, "role_trn")
            if not VOLCANO_ROLE_TRN_PATTERN.match(role_trn):
                raise SMSConfigValidationError("火山引擎 Role TRN 格式无效")
            normalized["role_trn"] = role_trn

    return normalized
