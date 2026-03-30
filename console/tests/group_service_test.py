# -*- coding: utf-8 -*-
import os
import sys
from types import ModuleType
from unittest import TestCase, mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from console.services import group_service as group_service_module  # noqa: E402
from console.services.group_service import group_service  # noqa: E402


# capability_id: console.app.delete
class GroupServiceDeleteAppTestCase(TestCase):
    def test_delete_app_cleans_hidden_template_records(self):
        relation = mock.Mock(app_model_id="hidden-template-id")

        with mock.patch.object(group_service_module.group_repo, "delete_group_by_pk") as delete_group_mock, \
                mock.patch.object(group_service_module.upgrade_repo,
                                  "delete_app_record_by_group_id") as delete_upgrade_mock, \
                mock.patch.object(group_service_module.region_app_repo,
                                  "get_region_app_id",
                                  return_value="region-app-id") as get_region_app_id_mock, \
                mock.patch.object(group_service_module.migrate_repo,
                                  "get_by_original_group_id",
                                  return_value=None) as get_migrate_mock, \
                mock.patch.object(group_service_module.region_api, "delete_app") as delete_region_app_mock, \
                mock.patch("console.services.app_version_service.app_version_service.get_hidden_template",
                           return_value=(relation, None)) as get_hidden_template_mock, \
                mock.patch("console.services.app_version_service.rainbond_app_repo.delete_app_version_by_id"
                           ) as delete_app_version_mock, \
                mock.patch("console.services.app_version_service.rainbond_app_repo.delete_app_by_id"
                           ) as delete_hidden_app_mock, \
                mock.patch("console.services.app_version_service.app_version_template_relation_repo.delete_by_group_id",
                           create=True) as delete_relation_mock:
            group_service._delete_app("demo-team", "demo-region", 42)

        delete_group_mock.assert_called_once_with(42)
        delete_upgrade_mock.assert_called_once_with(42)
        get_hidden_template_mock.assert_called_once_with(42)
        delete_app_version_mock.assert_called_once_with("hidden-template-id")
        delete_hidden_app_mock.assert_called_once_with("hidden-template-id")
        delete_relation_mock.assert_called_once_with(42)
        get_region_app_id_mock.assert_called_once_with("demo-region", 42)
        get_migrate_mock.assert_called_once_with(42)
        delete_region_app_mock.assert_called_once_with(
            "demo-region", "demo-team", "region-app-id", {"etcd_keys": []}
        )
