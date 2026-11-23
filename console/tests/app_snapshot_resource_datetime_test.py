# -*- coding: utf-8 -*-
import json
import os
from contextlib import nullcontext
from unittest import mock

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.test_settings")

import django  # noqa: E402

django.setup()

from django.core.serializers.json import DjangoJSONEncoder  # noqa: E402
from django.test import TestCase  # noqa: E402
from django.utils import timezone  # noqa: E402

from console.models.main import K8sResource, RainbondCenterAppVersion, RegionConfig  # noqa: E402
from console.exception.main import ServiceHandleException  # noqa: E402
from console.services.app_version_service import app_version_service  # noqa: E402
from console.services.share_services import share_service  # noqa: E402
from www.models.main import ServiceGroup, Tenants, Users  # noqa: E402


# capability_id: console.app-version.snapshot-resource-datetime
class SnapshotResourceDatetimeTests(TestCase):
    def setUp(self):
        self.tenant = Tenants.objects.create(
            tenant_id="snapshot-tenant", tenant_name="snapshot-team", namespace="snapshot-team", enterprise_id="enterprise")
        self.region = RegionConfig(region_name="region")
        self.user = Users(user_id=7)
        self.app = ServiceGroup.objects.create(
            tenant_id=self.tenant.tenant_id, group_name="snapshot-app", region_name="region",
            create_time=timezone.now(), update_time=timezone.now())
        self.resource = K8sResource.objects.create(
            app_id=str(self.app.ID), name="settings", kind="ConfigMap", state=1,
            content="apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: settings\n", error_overview="")
        patcher = mock.patch(
            "console.services.cleanup_coordination.protect_region_references", return_value=nullcontext())
        patcher.start()
        self.addCleanup(patcher.stop)

    def create_snapshot(self, **kwargs):
        return app_version_service.create_snapshot(self.tenant, self.region, self.user, self.app, **kwargs)

    def test_database_resource_dates_survive_real_template_build_and_snapshot_write(self):
        raw = list(share_service.get_k8s_resources(self.app.ID))
        self.assertTrue(hasattr(raw[0]["create_time"], "isoformat"))
        result = self.create_snapshot()
        self.assertTrue(result["created"])
        saved = RainbondCenterAppVersion.objects.get(ID=result["version_id"])
        template = json.loads(saved.app_template)
        self.assertEqual(template["k8s_resources"], json.loads(json.dumps(raw, cls=DjangoJSONEncoder)))
        self.assertEqual(template["arch"], "amd64")
        self.assertEqual(template["apps"], [])
        self.resource.refresh_from_db()
        self.assertTrue(hasattr(self.resource.create_time, "isoformat"))

    def test_share_info_resource_dates_use_the_same_safe_snapshot_boundary(self):
        raw = list(share_service.get_k8s_resources(self.app.ID))
        result = self.create_snapshot(share_info={"share_k8s_resources": raw})
        saved = RainbondCenterAppVersion.objects.get(ID=result["version_id"])
        self.assertEqual(json.loads(saved.app_template)["k8s_resources"],
                         json.loads(json.dumps(raw, cls=DjangoJSONEncoder)))

    def test_unavailable_and_other_application_resources_remain_excluded(self):
        K8sResource.objects.create(app_id=str(self.app.ID), name="failed", kind="ConfigMap", state=0,
                                   content="", error_overview="failed")
        K8sResource.objects.create(app_id="other-app", name="unrelated", kind="ConfigMap", state=1,
                                   content="", error_overview="")
        result = self.create_snapshot()
        saved = RainbondCenterAppVersion.objects.get(ID=result["version_id"])
        self.assertEqual([item["name"] for item in json.loads(saved.app_template)["k8s_resources"]], ["settings"])

    def test_unknown_non_json_object_still_fails_without_creating_a_version(self):
        with self.assertRaises(TypeError):
            self.create_snapshot(share_info={"share_k8s_resources": [{"content": object()}]})
        self.assertFalse(RainbondCenterAppVersion.objects.exists())

    def test_resource_snapshot_reuses_unchanged_version_without_duplicate_write(self):
        first = self.create_snapshot()
        second = self.create_snapshot()
        self.assertTrue(first["created"])
        self.assertFalse(second["created"])
        self.assertEqual(first["version_id"], second["version_id"])
        self.assertEqual(RainbondCenterAppVersion.objects.count(), 1)

    def test_automatic_completeness_guard_is_preserved_with_resource_dates(self):
        with self.assertRaises(ServiceHandleException) as context:
            self.create_snapshot(require_complete=True)
        self.assertEqual(context.exception.status_code, 409)
        self.assertFalse(RainbondCenterAppVersion.objects.exists())
