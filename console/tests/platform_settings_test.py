# -*- coding: utf-8 -*-
import collections
import os
import sys
from types import ModuleType, SimpleNamespace
from unittest import TestCase, mock

from rest_framework.test import APIRequestFactory

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from console.views.platform_settings import PlatformSettingsUpdateView, PlatformSettingsView  # noqa: E402


class PlatformSettingsTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.enterprise = SimpleNamespace(enable_team_resource_view=False)

        def save(update_fields=None):
            self.enterprise.saved_update_fields = update_fields

        self.enterprise.save = save

    def test_get_returns_global_image_registry_enable_status(self):
        request = self.factory.get("/console/enterprise/eid-1/platform-settings")
        config = SimpleNamespace(enable=True)

        with mock.patch("console.views.platform_settings.TenantEnterprise.objects.get", return_value=self.enterprise), \
                mock.patch("console.views.platform_settings.EnterpriseConfigService") as config_service_cls:
            config_service_cls.return_value.get_config_by_key.return_value = config
            response = PlatformSettingsView().get(request, eid="eid-1")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["bean"]["enable_global_image_registry"], True)
        config_service_cls.assert_called_once_with("eid-1", None)

    def test_update_global_image_registry_status_without_requiring_team_resource_view(self):
        request = SimpleNamespace(data={"enable_global_image_registry": False})

        with mock.patch("console.views.platform_settings.TenantEnterprise.objects.get", return_value=self.enterprise), \
                mock.patch("console.views.platform_settings.EnterpriseConfigService") as config_service_cls:
            config_service_cls.return_value.get_config_by_key.return_value = SimpleNamespace(enable=True)
            response = PlatformSettingsUpdateView().put(request, eid="eid-1")

        self.assertEqual(response.status_code, 200)
        config_service_cls.return_value.update_config_enable_status.assert_called_once_with(
            key="GLOBAL_IMAGE_REGISTRY",
            enable=False,
        )
        self.assertFalse(hasattr(self.enterprise, "saved_update_fields"))

    def test_update_global_image_registry_status_parses_false_string(self):
        request = SimpleNamespace(data={"enable_global_image_registry": "false"})

        with mock.patch("console.views.platform_settings.TenantEnterprise.objects.get", return_value=self.enterprise), \
                mock.patch("console.views.platform_settings.EnterpriseConfigService") as config_service_cls:
            config_service_cls.return_value.get_config_by_key.return_value = SimpleNamespace(enable=True)
            response = PlatformSettingsUpdateView().put(request, eid="eid-1")

        self.assertEqual(response.status_code, 200)
        config_service_cls.return_value.update_config_enable_status.assert_called_once_with(
            key="GLOBAL_IMAGE_REGISTRY",
            enable=False,
        )
