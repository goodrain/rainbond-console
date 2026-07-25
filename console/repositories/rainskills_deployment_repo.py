# -*- coding: utf-8 -*-
import hashlib
import json
from typing import Any, Optional, Tuple

from django.db import IntegrityError, transaction
from django.db.models import QuerySet

from console.models.main import ConsoleSysConfig


class RainSkillsDeploymentRepository(object):
    KEY_PREFIX = "RAINSKILLS_DEPLOY_"
    DESC = "rainskills deployment tracking"

    @classmethod
    def build_attempt_key(cls, deploy_attempt_id: str) -> str:
        raw_attempt_id = str(deploy_attempt_id or "")
        digest = hashlib.sha256(
            raw_attempt_id.encode("utf-8")).hexdigest()[:14]
        return "{}{}".format(cls.KEY_PREFIX, digest)

    @staticmethod
    def get_by_key(key: Optional[str]) -> Optional[ConsoleSysConfig]:
        if not key:
            return None
        return ConsoleSysConfig.objects.filter(key=key).first()

    def list_tracking_records(self) -> "QuerySet[ConsoleSysConfig]":
        return ConsoleSysConfig.objects.filter(
            key__startswith=self.KEY_PREFIX,
            desc=self.DESC,
            enable=True,
        ).all()

    def create_attempt(self, enterprise_id: str, deploy_attempt_id: str,
                       payload: dict) -> Tuple[Any, bool]:
        key = self.build_attempt_key(deploy_attempt_id)
        defaults = {
            "type": "json",
            "value": json.dumps(payload, ensure_ascii=False),
            "desc": self.DESC,
            "enable": True,
            "enterprise_id": enterprise_id,
        }
        try:
            with transaction.atomic():
                return ConsoleSysConfig.objects.get_or_create(
                    key=key, defaults=defaults)
        except IntegrityError:
            return self.get_by_key(key), False

    def update_payload(self, record: ConsoleSysConfig,
                       payload: dict) -> ConsoleSysConfig:
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
            return dict(record.value)
        try:
            value = json.loads(record.value)
        except (TypeError, ValueError):
            return {}
        return value if isinstance(value, dict) else {}


rainskills_deployment_repo = RainSkillsDeploymentRepository()
