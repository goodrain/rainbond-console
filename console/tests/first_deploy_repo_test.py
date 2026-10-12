# -*- coding: utf-8 -*-
import json
import os
import sys
from types import ModuleType

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from django.test import TestCase  # noqa: E402

from console.models.main import ConsoleSysConfig  # noqa: E402
from console.repositories.first_deploy_repo import enterprise_first_deploy_repo  # noqa: E402


# capability_id: console.first-deploy.concurrent-record-cleanup
class EnterpriseFirstDeployRepositoryConcurrencyTests(TestCase):
    def _record(self):
        return ConsoleSysConfig.objects.create(
            key="DEPLOY_DIAG_test",
            type="json",
            value="{}",
            desc=enterprise_first_deploy_repo.DESC,
            enable=True,
            enterprise_id="eid-1",
        )

    def test_update_payload_updates_existing_tracking_record(self):
        record = self._record()

        updated = enterprise_first_deploy_repo.update_payload(record, {"status": "success"})

        self.assertIs(updated, record)
        record.refresh_from_db()
        self.assertEqual(json.loads(record.value), {"status": "success"})
        self.assertTrue(record.enable)

    def test_update_payload_returns_none_when_record_was_deleted_concurrently(self):
        record = self._record()
        stale_record = ConsoleSysConfig.objects.get(pk=record.pk)
        ConsoleSysConfig.objects.filter(pk=record.pk).delete()

        updated = enterprise_first_deploy_repo.update_payload(stale_record, {"status": "success"})

        self.assertIsNone(updated)
        self.assertFalse(ConsoleSysConfig.objects.filter(key="DEPLOY_DIAG_test").exists())
