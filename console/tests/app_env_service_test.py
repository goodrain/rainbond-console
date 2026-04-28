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
from console.services.app_config.env_service import AppEnvVarService  # noqa: E402


class AppEnvVarServiceUpdateTestCase(TestCase):
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

        with mock.patch.object(env_service_module, "env_var_repo", repo), mock.patch.object(env_service_module,
                                                                                             "region_api") as region_api:
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
