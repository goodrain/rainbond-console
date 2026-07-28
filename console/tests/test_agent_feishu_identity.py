# -*- coding: utf-8 -*-
import os
import sys
from types import ModuleType, SimpleNamespace
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django
from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory

django.setup()

from console.views.agent_feishu_identity import AgentFeishuEligibleUsersView


class AgentFeishuEligibleUsersViewTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    def test_returns_minimal_active_employee_fields_for_admin(self):
        view = AgentFeishuEligibleUsersView()
        view.is_enterprise_admin = True
        view.user = SimpleNamespace(enterprise_id="eid")
        request = self.factory.get("/console/enterprise/eid/agent/feishu/eligible-users?query=dev")
        users = [SimpleNamespace(
            user_id=7, nick_name="dev", real_name="Developer", is_active=True)]

        with mock.patch(
                "console.views.agent_feishu_identity.user_services.get_user_by_eid",
                return_value=(users, 1)):
            response = view.get(request, enterprise_id="eid")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["list"], [{
            "user_id": 7,
            "display_name": "Developer",
            "username": "dev",
            "is_active": True,
        }])
        self.assertNotIn("email", str(response.data))

    def test_rejects_non_admin(self):
        view = AgentFeishuEligibleUsersView()
        view.is_enterprise_admin = False
        view.user = SimpleNamespace(enterprise_id="eid")
        response = view.get(self.factory.get("/"), enterprise_id="eid")
        self.assertEqual(response.status_code, 403)
