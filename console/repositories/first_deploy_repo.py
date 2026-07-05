# -*- coding: utf-8 -*-
import hashlib
import json
from typing import Any, Optional, Tuple

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.db.models import QuerySet

from console.models.main import ConsoleSysConfig


class EnterpriseFirstDeployRepository(object):
    KEY_PREFIX = "FIRST_DEPLOY_"
    ATTEMPT_KEY_PREFIX = "DEPLOY_DIAG_"
    DESC = "enterprise first deploy tracking"

    @classmethod
    def build_key(cls, enterprise_id: str) -> str:
        digest = hashlib.md5(str(enterprise_id).encode("utf-8")).hexdigest()[:16]
        return "{}{}".format(cls.KEY_PREFIX, digest)

    @classmethod
    def build_attempt_key(cls, enterprise_id: str, deploy_attempt_id: Optional[str]) -> str:
        raw = "{}:{}".format(enterprise_id or "", deploy_attempt_id or "")
        digest = hashlib.md5(raw.encode("utf-8")).hexdigest()[:20]
        return "{}{}".format(cls.ATTEMPT_KEY_PREFIX, digest)

    def get_by_enterprise_id(self, enterprise_id: str) -> Optional[ConsoleSysConfig]:
        key = self.build_key(enterprise_id)
        return ConsoleSysConfig.objects.filter(key=key).first()

    @staticmethod
    def get_by_key(key: Optional[str]) -> Optional[ConsoleSysConfig]:
        if not key:
            return None
        return ConsoleSysConfig.objects.filter(key=key).first()

    def list_tracking_records(self) -> "QuerySet[ConsoleSysConfig]":
        return ConsoleSysConfig.objects.filter(
            desc=self.DESC,
            enable=True,
        ).filter(Q(key__startswith=self.KEY_PREFIX) | Q(key__startswith=self.ATTEMPT_KEY_PREFIX)).all()

    def create_if_absent(self, enterprise_id: str, payload: dict) -> Tuple[Any, bool]:
        key = self.build_key(enterprise_id)
        return self._create_by_key(key, enterprise_id, payload)

    def create_attempt(self, enterprise_id: str, payload: dict) -> Tuple[Any, bool]:
        deploy_attempt_id = (payload.get("deployment_context") or {}).get("deploy_attempt_id")
        key = self.build_attempt_key(enterprise_id, deploy_attempt_id)
        return self._create_by_key(key, enterprise_id, payload)

    def _create_by_key(self, key: str, enterprise_id: str, payload: dict) -> Tuple[Any, bool]:
        value = json.dumps(payload, ensure_ascii=False)
        defaults = {
            "type": "json",
            "value": value,
            "desc": self.DESC,
            "enable": True,
            "enterprise_id": enterprise_id,
        }
        try:
            with transaction.atomic():
                return ConsoleSysConfig.objects.get_or_create(key=key, defaults=defaults)
        except IntegrityError:
            return self.get_by_key(key), False

    def update_payload(self, record: ConsoleSysConfig, payload: dict) -> ConsoleSysConfig:
        record.type = "json"
        record.value = json.dumps(payload, ensure_ascii=False)
        record.desc = self.DESC
        record.enable = True
        record.save(update_fields=["type", "value", "desc", "enable"])
        return record

    @staticmethod
    def delete_payload(record: ConsoleSysConfig) -> None:
        record.delete()

    @staticmethod
    def load_payload(record: Optional[ConsoleSysConfig]) -> dict:
        if not record or not record.value:
            return {}
        if isinstance(record.value, dict):
            return record.value
        try:
            return json.loads(record.value)
        except (TypeError, ValueError):
            return {}


enterprise_first_deploy_repo = EnterpriseFirstDeployRepository()
