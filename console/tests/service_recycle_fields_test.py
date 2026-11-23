# -*- coding: utf-8 -*-
import copy
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.test_settings")

import django  # noqa: E402

django.setup()

from django.db import IntegrityError, transaction  # noqa: E402
from django.test import TestCase  # noqa: E402

from console.models.main import ServiceRecycleBin  # noqa: E402
from console.repositories.app import recycle_bin_repo  # noqa: E402
from console.services.app_actions.app_manage import AppManageService  # noqa: E402
from www.models.main import TenantServiceInfo  # noqa: E402


# capability_id: console.component.recycle-model-fields
class RecycleModelFieldsTests(TestCase):
    def setUp(self):
        self.service = TenantServiceInfo.objects.create(
            service_id="recycle-component", tenant_id="recycle-tenant", service_key="component-key",
            service_alias="web", service_cname="Web", service_region="region", category="application",
            version="1.0", image="example.invalid/web:1.0", cmd="run", create_status="complete",
            min_memory=512, k8s_component_name="web", arch="amd64", build_strategy="normal")

    @staticmethod
    def shared_fields():
        source_fields = {field.attname for field in TenantServiceInfo._meta.concrete_fields}
        return {field.attname for field in ServiceRecycleBin._meta.concrete_fields
                if not field.primary_key and field.attname in source_fields
                and field.attname not in ("create_time", "update_time")}

    def test_move_to_recycle_accepts_real_source_model_and_preserves_shared_fields(self):
        source = self.service.toJSON()
        service_id = self.service.service_id
        record = AppManageService().move_service_into_recycle_bin(self.service)
        self.assertFalse(TenantServiceInfo.objects.filter(service_id=service_id).exists())
        record.refresh_from_db()
        for field in self.shared_fields():
            self.assertEqual(getattr(record, field), source[field], field)

    def test_repository_filters_source_primary_key_and_does_not_mutate_input(self):
        source = self.service.toJSON()
        source["ID"] = 100000
        before = copy.deepcopy(source)
        record = recycle_bin_repo.create_trash_service(**source)
        self.assertNotEqual(record.ID, source["ID"])
        self.assertEqual(source, before)

    def test_repository_keeps_target_recovery_metadata_outside_shared_source_fields(self):
        source = self.service.toJSON()
        source["recovery_metadata"] = {"fixture": "target-recovery-context"}
        record = recycle_bin_repo.create_trash_service(**source)
        record.refresh_from_db()
        self.assertEqual(record.recovery_metadata, source["recovery_metadata"])
        self.assertNotIn("recovery_metadata", self.shared_fields())

    def test_shared_recycle_fields_can_be_reconstructed_with_source_model_defaults(self):
        source = self.service.toJSON()
        record = AppManageService().move_service_into_recycle_bin(self.service)
        values = {field: getattr(record, field) for field in self.shared_fields()}
        restored = TenantServiceInfo.objects.create(**values)
        for field in self.shared_fields():
            self.assertEqual(getattr(restored, field), source[field], field)
        self.assertEqual(restored.arch, "amd64")
        self.assertFalse(restored.open_webhooks)

    def test_recycle_fields_accept_source_model_string_capacities_without_truncation(self):
        values = {
            name: "x" * TenantServiceInfo._meta.get_field(name).max_length
            for name in ("version", "setting", "extend_method", "git_url")
        }
        record = ServiceRecycleBin(**values)
        for name, value in values.items():
            with self.subTest(field=name):
                field = ServiceRecycleBin._meta.get_field(name)
                self.assertEqual(field.clean(value, record), value)

    def test_database_recycle_failure_preserves_original_component(self):
        existing = self.service.toJSON()
        existing = {key: value for key, value in existing.items() if key in self.shared_fields()}
        ServiceRecycleBin.objects.create(**existing)
        with self.assertRaises(IntegrityError), transaction.atomic():
            AppManageService().move_service_into_recycle_bin(self.service)
        self.assertTrue(TenantServiceInfo.objects.filter(service_id=self.service.service_id).exists())
