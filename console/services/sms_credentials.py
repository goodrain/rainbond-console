import hashlib
import json
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, Optional, Tuple

from dateutil.parser import isoparse


ROLE_SESSION_NAME = "rainbond-console-sms"
VOLCANO_ROLE_DURATION_SECONDS = "3600"
VOLCANO_REFRESH_WINDOW = timedelta(minutes=5)


class SMSCredentials(object):
    def __init__(self, access_key: str, access_secret: str, session_token: str = "") -> None:
        self.access_key = access_key
        self.access_secret = access_secret
        self.session_token = session_token


def create_aliyun_client(config: Dict[str, Any], client_class: Any = None,
                         openapi_config_class: Any = None, credential_client_class: Any = None,
                         credential_config_class: Any = None) -> Any:
    if client_class is None:
        from alibabacloud_dysmsapi20170525.client import Client
        client_class = Client
    if openapi_config_class is None:
        from alibabacloud_tea_openapi.models import Config
        openapi_config_class = Config

    if config.get("auth_type", "access_key") == "role":
        if credential_client_class is None:
            from alibabacloud_credentials.client import Client as CredentialClient
            credential_client_class = CredentialClient
        if credential_config_class is None:
            from alibabacloud_credentials.models import Config as CredentialConfig
            credential_config_class = CredentialConfig

        credential = credential_client_class(
            credential_config_class(
                type="ram_role_arn",
                access_key_id=config["access_key"],
                access_key_secret=config["access_secret"],
                role_arn=config["role_arn"],
                role_session_name=ROLE_SESSION_NAME,
            ))
        openapi_config = openapi_config_class(
            credential=credential,
            endpoint="dysmsapi.aliyuncs.com",
        )
    else:
        openapi_config = openapi_config_class(
            access_key_id=config["access_key"],
            access_key_secret=config["access_secret"],
            endpoint="dysmsapi.aliyuncs.com",
        )
    return client_class(openapi_config)


class VolcanoCredentialProvider(object):
    def __init__(self, sts_service_factory: Optional[Callable[[], Any]] = None,
                 now: Optional[Callable[[], datetime]] = None) -> None:
        self._sts_service_factory = sts_service_factory or self._create_sts_service
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._lock = threading.Lock()
        self._cache_fingerprint = ""
        self._cached_credentials: Optional[SMSCredentials] = None
        self._expires_at: Optional[datetime] = None

    @staticmethod
    def _create_sts_service() -> Any:
        from volcengine.sts.StsService import StsService
        return StsService()

    @staticmethod
    def _fingerprint(config: Dict[str, Any]) -> str:
        source = json.dumps([
            config.get("access_key", ""),
            config.get("access_secret", ""),
            config.get("role_trn", ""),
        ], separators=(",", ":"))
        return hashlib.sha256(source.encode("utf-8")).hexdigest()

    def get_credentials(self, config: Dict[str, Any]) -> SMSCredentials:
        if config.get("auth_type", "access_key") != "role":
            return SMSCredentials(config["access_key"], config["access_secret"])

        fingerprint = self._fingerprint(config)
        with self._lock:
            now = self._normalize_time(self._now())
            if self._cache_is_valid(fingerprint, now):
                return self._cached_credentials  # type: ignore[return-value]

            credentials, expires_at = self._assume_role(config)
            self._cache_fingerprint = fingerprint
            self._cached_credentials = credentials
            self._expires_at = expires_at
            return credentials

    def _cache_is_valid(self, fingerprint: str, now: datetime) -> bool:
        return bool(
            self._cached_credentials and
            self._expires_at and
            self._cache_fingerprint == fingerprint and
            self._expires_at - now > VOLCANO_REFRESH_WINDOW
        )

    def _assume_role(self, config: Dict[str, Any]) -> Tuple[SMSCredentials, datetime]:
        service = self._sts_service_factory()
        service.set_ak(config["access_key"])
        service.set_sk(config["access_secret"])
        response = service.assume_role({
            "DurationSeconds": VOLCANO_ROLE_DURATION_SECONDS,
            "RoleSessionName": ROLE_SESSION_NAME,
            "RoleTrn": config["role_trn"],
        })
        try:
            payload = response["Result"]["Credentials"]
            credentials = SMSCredentials(
                payload["AccessKeyId"],
                payload["SecretAccessKey"],
                payload["SessionToken"],
            )
            expires_at = self._normalize_time(isoparse(payload["ExpiredTime"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("火山引擎 STS 返回的临时凭证无效") from exc
        return credentials, expires_at

    @staticmethod
    def _normalize_time(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
