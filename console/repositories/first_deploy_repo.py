# -*- coding: utf-8 -*-
import hashlib
import json

from django.db import IntegrityError, transaction

from console.models.main import ConsoleSysConfig


class EnterpriseFirstDeployRepository(object):
    KEY_PREFIX = "FIRST_DEPLOY_"
    DESC = "enterprise first deploy tracking"

    @classmethod
    def build_key(cls, enterprise_id):
        digest = hashlib.md5(str(enterprise_id).encode("utf-8")).hexdigest()[:16]
        return "{}{}".format(cls.KEY_PREFIX, digest)

    def get_by_enterprise_id(self, enterprise_id):
        key = self.build_key(enterprise_id)
        return ConsoleSysConfig.objects.filter(key=key).first()

    @staticmethod
    def get_by_key(key):
        return ConsoleSysConfig.objects.filter(key=key).first()

    def create_if_absent(self, enterprise_id, payload):
        key = self.build_key(enterprise_id)
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
            return self.get_by_enterprise_id(enterprise_id), False

    def update_payload(self, record, payload):
        record.type = "json"
        record.value = json.dumps(payload, ensure_ascii=False)
        record.desc = self.DESC
        record.enable = True
        record.save(update_fields=["type", "value", "desc", "enable"])
        return record

    @staticmethod
    def load_payload(record):
        if not record or not record.value:
            return {}
        if isinstance(record.value, dict):
            return record.value
        try:
            return json.loads(record.value)
        except (TypeError, ValueError):
            return {}


enterprise_first_deploy_repo = EnterpriseFirstDeployRepository()
