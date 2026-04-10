# -*- coding: utf-8 -*-
import collections
import os
import sys
from types import ModuleType, SimpleNamespace
from unittest import TestCase, mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402
from rest_framework.test import APIRequestFactory  # noqa: E402
from rest_framework.views import APIView  # noqa: E402

base_module = ModuleType("console.views.base")
app_base_module = ModuleType("console.views.app_config.base")
app_service_module = ModuleType("console.services.app")


class _RegionTenantHeaderView(APIView):
    pass


class _AppBaseView(APIView):
    pass


base_module.RegionTenantHeaderView = _RegionTenantHeaderView
app_base_module.AppBaseView = _AppBaseView
app_service_module.app_service = SimpleNamespace(get_service_status=lambda *args, **kwargs: {"status": "closed"})
sys.modules.setdefault("console.views.base", base_module)
sys.modules.setdefault("console.views.app_config.base", app_base_module)
sys.modules.setdefault("console.services.app", app_service_module)

django.setup()

from console.views.vm_template import VirtualMachineTemplateListView, VirtualMachineTemplateManageView  # noqa: E402


class VirtualMachineTemplateViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.list_view = VirtualMachineTemplateListView()
        self.manage_view = VirtualMachineTemplateManageView()
        tenant = SimpleNamespace(tenant_id="tenant-a", tenant_name="demo-team")
        self.list_view.tenant = tenant
        self.manage_view.tenant = tenant

    def test_list_returns_team_templates(self):
        request = self.list_view.initialize_request(
            self.factory.get("/console/teams/demo-team/vm/templates")
        )

        with mock.patch(
            "console.views.vm_template.vms.list_vm_templates",
            return_value=[{"id": 12, "name": "win10-devtools", "status": "ready"}]
        ) as list_mock:
            response = self.list_view.get(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(1, len(response.data["data"]["list"]))
        self.assertEqual("win10-devtools", response.data["data"]["list"][0]["name"])
        list_mock.assert_called_once_with("tenant-a")

    def test_detail_returns_template_versions_and_disks(self):
        request = self.manage_view.initialize_request(
            self.factory.get("/console/teams/demo-team/vm/templates/12")
        )

        with mock.patch(
            "console.views.vm_template.vms.get_vm_template_detail",
            return_value={
                "id": 12,
                "name": "ubuntu-dev",
                "versions": [{"id": 38, "version": "v2", "disks": [{"disk_key": "rootdisk"}]}]
            }
        ) as detail_mock:
            response = self.manage_view.get(request, template_id="12")

        self.assertEqual(response.status_code, 200)
        self.assertEqual("ubuntu-dev", response.data["data"]["bean"]["name"])
        self.assertEqual("v2", response.data["data"]["bean"]["versions"][0]["version"])
        detail_mock.assert_called_once_with("tenant-a", "12")

    def test_detail_returns_404_when_template_missing(self):
        request = self.manage_view.initialize_request(
            self.factory.get("/console/teams/demo-team/vm/templates/404")
        )

        with mock.patch("console.views.vm_template.vms.get_vm_template_detail", return_value=None):
            response = self.manage_view.get(request, template_id="404")

        self.assertEqual(response.status_code, 404)

    def test_put_disables_template(self):
        request = self.manage_view.initialize_request(
            self.factory.put("/console/teams/demo-team/vm/templates/12", {"disabled": True}, format="json")
        )

        with mock.patch(
            "console.views.vm_template.vms.set_vm_template_disabled",
            return_value={"id": 12, "disabled": True, "status": "disabled"}
        ) as disable_mock:
            response = self.manage_view.put(request, template_id="12")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["data"]["bean"]["disabled"])
        disable_mock.assert_called_once_with("tenant-a", "12", True)
