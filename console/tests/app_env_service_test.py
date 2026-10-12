# -*- coding: utf-8 -*-
import collections
import os
import sys
from types import ModuleType
from unittest import TestCase, mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

import console.services.app_config.env_service as env_service_module  # noqa: E402
import console.repositories.app_config as app_config_repo_module  # noqa: E402
import console.views.app_config.app_env as app_env_view_module  # noqa: E402
from console.exception.main import AbortRequest  # noqa: E402
from console.repositories.app_config import TenantServiceEnvVarRepository  # noqa: E402
from console.services.app_config.env_service import AppEnvVarService  # noqa: E402
from console.views.app_config.app_env import AppEnvManageView  # noqa: E402
from django.test import RequestFactory  # noqa: E402


class TenantServiceEnvVarRepositoryUpdateTestCase(TestCase):
    # capability_id: console.component-env.delete-missing-404
    def test_404_lookup_rejects_non_numeric_environment_id_before_querying(self):
        with self.assertRaises(AbortRequest) as raised:
            TenantServiceEnvVarRepository().get_service_env_or_404_by_env_id(
                "tenant-id", "service-id", "CORS_ORIGINS")

        self.assertEqual(raised.exception.status_code, 404)
        self.assertEqual(raised.exception.msg_show, "环境变量`CORS_ORIGINS`不存在")

    def test_update_env_var_can_update_attr_name_while_filtering_by_old_key(self):
        queryset = mock.Mock()
        manager = mock.Mock()
        manager.filter.return_value = queryset

        with mock.patch.object(app_config_repo_module.TenantServiceEnvVar, "objects", manager):
            TenantServiceEnvVarRepository().update_env_var(
                "tenant-id", "service-id", "OLD_KEY", attr_name="NEW_KEY", attr_value="new-value")

        manager.filter.assert_called_once_with(tenant_id="tenant-id", service_id="service-id", attr_name="OLD_KEY")
        queryset.update.assert_called_once_with(attr_name="NEW_KEY", attr_value="new-value")


class AppEnvVarServiceUpdateTestCase(TestCase):
    # capability_id: console.component-env.field-length-validation
    def test_add_env_rejects_overlong_description_before_region_or_database_write(self):
        tenant = mock.Mock(tenant_id="tenant-id", tenant_name="tenant-name", enterprise_id="enterprise-id")
        service = mock.Mock(
            tenant_id="tenant-id",
            service_id="service-id",
            service_region="region-name",
            service_alias="service-alias",
            create_status="complete")
        repo = mock.Mock()
        repo.get_service_env_by_attr_name.return_value = None

        cases = (
            ("x" * 1025, "VALID_NAME", "环境变量说明长度不能超过1024个字符"),
            ("description", "A" * 1025, "环境变量名称长度不能超过1024个字符"),
        )
        for name, attr_name, expected_message in cases:
            with self.subTest(expected_message=expected_message), \
                    mock.patch.object(env_service_module, "env_var_repo", repo), \
                    mock.patch.object(env_service_module, "region_api") as region_api:
                code, msg, env = AppEnvVarService().add_service_env_var(
                    tenant, service, 0, name, attr_name, "value", True, "inner", "operator")

            self.assertEqual(code, 400)
            self.assertEqual(msg, expected_message)
            self.assertIsNone(env)
            region_api.add_service_env.assert_not_called()
            repo.add_service_env.assert_not_called()

    # capability_id: console.component-env.delete-missing-404
    def test_delete_env_by_env_id_uses_404_aware_lookup_and_returns_deleted_env(self):
        tenant = mock.Mock(tenant_id="tenant-id", tenant_name="tenant-name", enterprise_id="enterprise-id")
        service = mock.Mock(
            service_id="service-id",
            service_region="region-name",
            service_alias="service-alias",
            create_status="complete")
        env = mock.Mock(ID=7, attr_name="OLD_KEY")
        repo = mock.Mock()
        repo.get_service_env_or_404_by_env_id.return_value = env

        with mock.patch.object(env_service_module, "env_var_repo", repo), \
                mock.patch.object(env_service_module, "region_api") as region_api:
            deleted = AppEnvVarService().delete_env_by_env_id(
                tenant, service, "7", "operator")

        self.assertIs(deleted, env)
        repo.get_service_env_or_404_by_env_id.assert_called_once_with("tenant-id", "service-id", "7")
        repo.get_env_by_ids_and_env_id.assert_not_called()
        repo.delete_service_env_by_attr_name.assert_called_once_with("tenant-id", "service-id", "OLD_KEY")
        region_api.delete_service_env.assert_called_once_with(
            "region-name",
            "tenant-name",
            "service-alias",
            {
                "env_name": "OLD_KEY",
                "enterprise_id": "enterprise-id",
                "operator": "operator",
            },
        )

    def test_delete_view_reuses_the_environment_returned_by_the_service(self):
        env = mock.Mock(attr_name="OLD_KEY", attr_value="old-value", name="old note")
        env_service = mock.Mock()
        env_service.delete_env_by_env_id.return_value = env
        env_service.json_service_env_var.return_value = {"attr_name": "OLD_KEY"}
        operation_log_service = mock.Mock()
        operation_log_service.generate_component_comment.return_value = "deleted OLD_KEY"
        view = AppEnvManageView()
        view.tenant = mock.Mock(tenant_name="tenant-name")
        view.service = mock.Mock(service_cname="component", service_region="region-name", service_alias="service-alias")
        view.user = mock.Mock(nick_name="operator", enterprise_id="enterprise-id")
        view.app = mock.Mock(ID=12)

        with mock.patch.object(app_env_view_module, "env_var_service", env_service), \
                mock.patch.object(app_env_view_module, "operation_log_service", operation_log_service), \
                mock.patch.object(app_env_view_module, "env_var_repo") as env_var_repo:
            response = view.delete(
                RequestFactory().delete("/console/teams/tenant-name/apps/service-alias/envs/7"),
                env_id="7",
            )

        self.assertEqual(response.status_code, 200)
        env_service.delete_env_by_env_id.assert_called_once_with(
            view.tenant, view.service, "7", "operator")
        env_var_repo.get_env_by_ids_and_env_id.assert_not_called()
        operation_log_service.create_component_log.assert_called_once()

    def test_update_env_by_env_id_renames_env_key_in_console_and_region(self):
        tenant = mock.Mock(tenant_id="tenant-id", tenant_name="tenant-name", enterprise_id="enterprise-id")
        service = mock.Mock(
            service_id="service-id",
            service_region="region-name",
            service_alias="service-alias",
            create_status="complete")
        env = mock.Mock(ID=7, attr_name="OLD_KEY", attr_value="old-value", name="old note", scope="inner")
        repo = mock.Mock()
        repo.get_env_by_ids_and_env_id.return_value = env
        repo.get_service_env_by_attr_name.return_value = None

        with mock.patch.object(env_service_module, "env_var_repo", repo), \
             mock.patch.object(env_service_module, "region_api") as region_api:
            code, msg, updated = AppEnvVarService().update_env_by_env_id(
                tenant, service, "7", "new note", "new-value", "operator", attr_name="NEW_KEY")

        self.assertEqual(code, 200)
        self.assertEqual(msg, "success")
        self.assertIs(updated, env)
        repo.update_env_var.assert_called_once_with(
            "tenant-id", "service-id", "OLD_KEY", name="new note", attr_value="new-value", attr_name="NEW_KEY")
        region_api.update_service_env.assert_called_once_with(
            "region-name",
            "tenant-name",
            "service-alias",
            {
                "old_env_name": "OLD_KEY",
                "env_name": "NEW_KEY",
                "env_value": "new-value",
                "scope": "inner",
                "operator": "operator",
            },
        )
        self.assertEqual(env.attr_name, "NEW_KEY")
        self.assertEqual(env.attr_value, "new-value")
        self.assertEqual(env.name, "new note")
