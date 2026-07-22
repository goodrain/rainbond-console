import collections
import collections.abc
import os
import sys
from types import ModuleType, SimpleNamespace
from unittest import TestCase
from unittest import mock

import yaml

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

import django  # noqa: E402

django.setup()

from console.services.app_check_service import AppCheckService  # noqa: E402


class AppCheckK8sAttributeTests(TestCase):

    def setUp(self):
        self.tenant = SimpleNamespace(tenant_id="tenant-a")
        self.service = SimpleNamespace(service_id="service-a")

    # capability_id: console.app-check.cmd-args-yaml
    def test_save_k8s_command_persists_cmd_as_yaml_sequence(self):
        service = AppCheckService()
        existing = mock.Mock()
        existing.exists.return_value = False

        with mock.patch("console.services.app_check_service.k8s_attribute_repo.get_by_component_id_name",
                        return_value=existing), \
                mock.patch("console.services.app_check_service.k8s_attribute_repo.create") as repo_create:
            service._AppCheckService__save_k8s_command(self.tenant, self.service, ["/entrypoint.sh"])

        repo_create.assert_called_once_with(
            tenant_id="tenant-a",
            component_id="service-a",
            name="cmd",
            save_type="yaml",
            attribute_value=yaml.safe_dump(["/entrypoint.sh"], default_flow_style=False, allow_unicode=True),
        )

    def test_save_k8s_attribute_persists_args_as_yaml_sequence(self):
        service = AppCheckService()
        existing = mock.Mock()
        existing.exists.return_value = False
        args = ["/bin/sh", "-c", "echo hello world"]

        with mock.patch("console.services.app_check_service.k8s_attribute_repo.get_by_component_id_name",
                        return_value=existing), \
                mock.patch("console.services.app_check_service.k8s_attribute_repo.create") as repo_create:
            service._AppCheckService__save_k8s_attribute(self.tenant, self.service, "args", args, save_type="yaml")

        repo_create.assert_called_once_with(
            tenant_id="tenant-a",
            component_id="service-a",
            name="args",
            save_type="yaml",
            attribute_value=yaml.safe_dump(args, default_flow_style=False, allow_unicode=True),
        )
