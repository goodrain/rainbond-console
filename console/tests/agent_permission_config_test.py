# -*- coding: utf-8 -*-
import json
import os
import sys
from types import ModuleType, SimpleNamespace
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django
from django.test import SimpleTestCase

django.setup()

from console.exception.main import ServiceHandleException
from console.services.agent_permission_config_service import (
    DEFAULT_PERMISSION_CONFIG,
    AgentPermissionConfigService,
)
from console.views.agent_permission_config import AgentPermissionConfigView
from rest_framework.test import APIRequestFactory, force_authenticate


class AgentPermissionConfigServiceTests(SimpleTestCase):

    def setUp(self):
        self.service = AgentPermissionConfigService()

    def test_default_config_is_returned_when_missing(self):
        with mock.patch("console.services.agent_permission_config_service.ConsoleSysConfig.objects.get",
                        side_effect=__import__("django").core.exceptions.ObjectDoesNotExist):
            result = self.service.get_runtime_config()

        self.assertEqual(result["config"], DEFAULT_PERMISSION_CONFIG)
        self.assertEqual(result["updated_by"], "")

    def test_update_validates_and_normalizes(self):
        with mock.patch.object(self.service, "_save_config") as save:
            result = self.service.update_config(DEFAULT_PERMISSION_CONFIG, updated_by="admin")

        self.assertEqual(result["config"]["version"], 1)
        self.assertEqual(result["updated_by"], "admin")
        save.assert_called_once()

    def test_rejects_duplicate_tools(self):
        config = json.loads(json.dumps(DEFAULT_PERMISSION_CONFIG))
        config["tools"] = [
            {"tool": "x", "class": "read", "scope": "team",
             "roles": {role: "allow" for role in ("enterprise_admin", "team_admin", "member", "viewer")}},
            {"tool": "x", "class": "read", "scope": "team",
             "roles": {role: "allow" for role in ("enterprise_admin", "team_admin", "member", "viewer")}},
        ]
        with self.assertRaises(ServiceHandleException) as context:
            self.service.update_config(config)
        self.assertIn("重复的工具策略", context.exception.msg_show)

    def test_rejects_invalid_decision(self):
        config = json.loads(json.dumps(DEFAULT_PERMISSION_CONFIG))
        config["defaultByRole"]["member"]["write"] = "maybe"
        with self.assertRaises(ServiceHandleException) as context:
            self.service.update_config(config)
        self.assertIn("allow/deny/ask", context.exception.msg_show)


class AgentPermissionConfigViewTests(SimpleTestCase):

    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = AgentPermissionConfigView.as_view()

    def _user(self, is_admin):
        return SimpleNamespace(
            user_id=1,
            nick_name="admin",
            enterprise_id="eid",
            is_authenticated=True,
            sys_admin=False,
        )

    def _auth_patches(self, is_admin):
        return (
            mock.patch("console.views.base.TenantEnterprise.objects.filter"),
            mock.patch("console.views.base.enterprise_user_perm_repo.is_admin", return_value=is_admin),
            mock.patch("console.views.base.user_services.list_roles", return_value=[]),
            mock.patch("console.views.base.perms.list_enterprise_perm_codes_by_roles", return_value=[]),
        )

    def test_get_requires_enterprise_admin(self):
        request = self.factory.get("/console/enterprise/eid/agent-permission-config")
        force_authenticate(request, user=self._user(False))
        p1, p2, p3, p4 = self._auth_patches(False)
        with p1 as enterprise_filter, p2, p3, p4:
            enterprise_filter.return_value.first.return_value = SimpleNamespace(enterprise_id="eid")
            response = self.view(request, eid="eid")
        self.assertEqual(response.status_code, 403)

    def test_get_returns_config_for_enterprise_admin(self):
        request = self.factory.get("/console/enterprise/eid/agent-permission-config")
        force_authenticate(request, user=self._user(True))
        p1, p2, p3, p4 = self._auth_patches(True)
        with p1 as enterprise_filter, p2, p3, p4, \
                mock.patch("console.views.agent_permission_config.agent_permission_config_service.get_config",
                           return_value={"config": DEFAULT_PERMISSION_CONFIG, "updated_by": "", "updated_at": ""}):
            enterprise_filter.return_value.first.return_value = SimpleNamespace(enterprise_id="eid")
            response = self.view(request, eid="eid")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["bean"]["config"]["version"], 1)
