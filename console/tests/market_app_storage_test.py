# -*- coding: utf-8 -*-
import collections
import os
import sys
from types import ModuleType, SimpleNamespace
from unittest import TestCase, mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
if "openapi_client" not in sys.modules:
    openapi_client_module = ModuleType("openapi_client")
    configuration_module = ModuleType("openapi_client.configuration")
    rest_module = ModuleType("openapi_client.rest")

    class _OpenAPIConfiguration(object):
        def __init__(self):
            self.host = ""
            self.ssl_ca_cert = None
            self.verify_ssl = False

    class _ApiException(Exception):
        pass

    openapi_client_module.ApiClient = object
    openapi_client_module.MarketOpenapiApi = object
    configuration_module.Configuration = _OpenAPIConfiguration
    rest_module.ApiException = _ApiException
    openapi_client_module.configuration = configuration_module
    openapi_client_module.rest = rest_module
    sys.modules["openapi_client"] = openapi_client_module
    sys.modules["openapi_client.configuration"] = configuration_module
    sys.modules["openapi_client.rest"] = rest_module

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from console.models.main import ConsoleSysConfig  # noqa: E402
from console.services.app_config.volume_service import AppVolumeService  # noqa: E402
from console.services.market_app import new_components as new_components_module  # noqa: E402


class MarketAppDefaultStorageClassTests(TestCase):
    def setUp(self):
        self.tenant = SimpleNamespace(tenant_id="tenant-1", enterprise_id="eid-1")
        self.component = SimpleNamespace(component_id="service-1", service_id="service-1", service_region="r1")

    # capability_id: console.market-app.install-default-storage-class
    def test_resolve_market_default_volume_type_prefers_configured_storage_class(self):
        service = AppVolumeService()
        config_queryset = mock.Mock()
        config_queryset.first.return_value = SimpleNamespace(value="nfs-storage")

        with mock.patch.object(
            ConsoleSysConfig.objects,
            "filter",
            return_value=config_queryset,
        ), mock.patch.object(
            service,
            "get_service_support_volume_options",
            return_value=[{"volume_type": "nfs-storage", "provisioner": "cluster.local/nfs"}],
        ):
            volume_type = service.get_market_default_volume_type(self.tenant, self.component, "local-path")

        self.assertEqual(volume_type, "nfs-storage")

    # capability_id: console.market-app.install-default-storage-class
    def test_template_to_volumes_uses_configured_default_storage_class(self):
        installer = new_components_module.NewComponents.__new__(new_components_module.NewComponents)
        installer.tenant = self.tenant
        config_queryset = mock.Mock()
        config_queryset.first.return_value = SimpleNamespace(value="nfs-storage")

        with mock.patch.object(
            ConsoleSysConfig.objects,
            "filter",
            return_value=config_queryset,
        ), mock.patch.object(
            new_components_module.volume_service,
            "get_service_support_volume_options",
            return_value=[{"volume_type": "nfs-storage", "provisioner": "cluster.local/nfs"}],
        ), mock.patch.object(
            new_components_module.volume_service,
            "create_service_volume",
            return_value="created-volume",
        ) as create_volume:
            volumes, config_files = installer._template_to_volumes(
                self.component,
                [
                    {
                        "volume_name": "data",
                        "volume_path": "/data",
                        "volume_type": "local-path",
                        "volume_capacity": 10,
                    }
                ],
            )

        self.assertEqual(config_files, [])
        self.assertEqual(volumes, ["created-volume"])
        self.assertEqual(create_volume.call_args[0][3], "nfs-storage")

    # capability_id: console.market-app.restore-volume-capacity-helper
    def test_resolve_market_restore_volume_settings_preserves_capacity_when_storage_type_changes(self):
        service = AppVolumeService()
        volume = {
            "volume_name": "disk",
            "volume_path": "/disk",
            "volume_type": "nfs-storage-nvme",
            "volume_capacity": 30,
            "access_mode": "RWX",
            "share_policy": "exclusive",
        }

        with mock.patch.object(
            service,
            "get_market_default_volume_type",
            return_value="nfs-storage-nvme",
        ), mock.patch.object(
            service,
            "get_best_suitable_volume_settings",
            return_value={"volume_type": "share-file", "changed": True},
        ):
            volume_type, settings = service.resolve_market_restore_volume_settings(
                self.tenant,
                self.component,
                volume,
            )

        self.assertEqual(volume_type, "share-file")
        self.assertEqual(settings["volume_capacity"], 30)

    # capability_id: console.market-app.restore-preserves-volume-capacity-on-storage-fallback
    def test_template_to_volumes_preserves_capacity_when_storage_type_changes(self):
        installer = new_components_module.NewComponents.__new__(new_components_module.NewComponents)
        installer.tenant = self.tenant

        with mock.patch.object(
            new_components_module.volume_service,
            "get_market_default_volume_type",
            return_value="nfs-storage-nvme",
        ), mock.patch.object(
            new_components_module.volume_service,
            "get_best_suitable_volume_settings",
            return_value={"volume_type": "share-file", "changed": True},
        ), mock.patch.object(
            new_components_module.volume_service,
            "create_service_volume",
            return_value="created-volume",
        ) as create_volume:
            installer._template_to_volumes(
                self.component,
                [
                    {
                        "volume_name": "disk",
                        "volume_path": "/disk",
                        "volume_type": "nfs-storage-nvme",
                        "volume_capacity": 30,
                        "access_mode": "RWX",
                        "share_policy": "exclusive",
                    }
                ],
            )

        self.assertEqual(create_volume.call_args[0][3], "share-file")
        self.assertEqual(create_volume.call_args[1]["settings"]["volume_capacity"], 30)
