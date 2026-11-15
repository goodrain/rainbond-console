# -*- coding: utf-8 -*-
from types import SimpleNamespace
from unittest import TestCase, mock

from console.tests import vm_manage_view_test  # noqa: F401
from console.views.app_manage import UpgradeAppView


# capability_id: console.component.upgrade-returns-task-id
class ComponentUpgradeEventViewTests(TestCase):
    def _view(self):
        view = UpgradeAppView()
        view.tenant = SimpleNamespace(tenant_name="demo", tenant_id="tenant")
        view.service = mock.Mock(service_alias="vm", service_region="region", service_cname="VM")
        view.user = SimpleNamespace(nick_name="tester", enterprise_id="enterprise")
        view.app = SimpleNamespace(ID=1)
        view.oauth_instance = None
        return view

    def test_upgrade_preserves_event_id_for_actual_task_result(self):
        view = self._view()
        with mock.patch("console.views.app_manage.app_manage_service.upgrade", return_value=(200, "accepted", "event-1")), \
                mock.patch("console.views.app_manage.operation_log_service"):
            response = view.post(mock.Mock())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["bean"]["event_id"], "event-1")

    def test_upgrade_rejection_does_not_return_a_successful_task(self):
        view = self._view()
        with mock.patch("console.views.app_manage.app_manage_service.upgrade", return_value=(409, "busy", "")):
            response = view.post(mock.Mock())
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["data"]["bean"], {})
        self.assertEqual(response.data["msg_show"], "busy")
