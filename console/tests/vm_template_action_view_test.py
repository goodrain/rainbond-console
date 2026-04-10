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

from console.views.vm_template import AppVMTemplateView, VirtualMachineTemplateVersionRetryView  # noqa: E402


class AppVMTemplateViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = AppVMTemplateView()
        self.view.tenant = SimpleNamespace(tenant_id="tenant-a", tenant_name="demo-team")
        self.view.service = SimpleNamespace(
            tenant_id="tenant-a",
            service_id="service-a",
            service_alias="demo-vm",
            extend_method="vm",
            image="demo/image"
        )
        self.view.response_region = "demo-region"
        self.view.app = SimpleNamespace(ID=1)

    def test_post_starts_template_generation(self):
        request = self.view.initialize_request(
            self.factory.post(
                "/console/teams/demo-team/apps/demo-vm/vm-templates",
                {"name": "win10-devtools", "description": "template", "include_data_disks": True},
                format="json"
            )
        )

        with mock.patch("console.views.vm_template.app_service.get_service_status", return_value={"status": "running"}), \
                mock.patch(
                    "console.views.vm_template.vms.save_vm_template",
                    return_value={"id": 12, "status": "generating", "name": "win10-devtools"}
                ) as save_mock:
            response = self.view.post(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual("win10-devtools", response.data["data"]["bean"]["name"])
        save_mock.assert_called_once()

    def test_post_requires_template_name(self):
        request = self.view.initialize_request(
            self.factory.post("/console/teams/demo-team/apps/demo-vm/vm-templates", {}, format="json")
        )

        response = self.view.post(request)

        self.assertEqual(response.status_code, 400)


class VirtualMachineTemplateVersionRetryViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = VirtualMachineTemplateVersionRetryView()
        self.view.tenant = SimpleNamespace(tenant_id="tenant-a", tenant_name="demo-team")
        self.view.response_region = "demo-region"

    def test_post_retries_failed_template_version(self):
        request = self.view.initialize_request(
            self.factory.post("/console/teams/demo-team/vm/templates/12/versions/38/retry", {}, format="json")
        )

        with mock.patch(
            "console.views.vm_template.vms.retry_vm_template_version",
            return_value={"id": 38, "status": "generating"}
        ) as retry_mock:
            response = self.view.post(request, template_id="12", version_id="38")

        self.assertEqual(response.status_code, 200)
        self.assertEqual("generating", response.data["data"]["bean"]["status"])
        retry_mock.assert_called_once_with(
            tenant_id="tenant-a",
            template_id="12",
            version_id="38",
            region_name="demo-region",
            tenant_name="demo-team"
        )
