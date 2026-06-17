import importlib
import sys
import types
from unittest import TestCase
from unittest.mock import MagicMock


class TenantServiceVolumeStub(object):
    SHARE = "share-file"
    LOCAL = "local"
    TMPFS = "memoryfs"
    CONFIGFILE = "config-file"
    objects = MagicMock()


class DummyModel(object):
    objects = MagicMock()


class DummyQ(object):
    def __init__(self, *args, **kwargs):
        pass

    def __or__(self, other):
        return self


class DummyQuerySet(object):
    def __class_getitem__(cls, item):
        return cls


def install_stub(module_name, **attrs):
    module = types.ModuleType(module_name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[module_name] = module


class TenantServiceVolumnRepositoryTests(TestCase):
    def tearDown(self):
        for module_name in (
            "console.repositories.app_config",
            "console.exception.main",
            "console.utils.shortcuts",
            "www.db.base",
            "www.models.main",
            "www.models.service_publish",
        ):
            sys.modules.pop(module_name, None)

    def import_repository_module(self):
        sys.modules.pop("console.repositories.app_config", None)
        install_stub("console.exception.main", AbortRequest=Exception)
        install_stub("console.utils.shortcuts", get_object_or_404=lambda *args, **kwargs: None)
        install_stub("django", db=types.SimpleNamespace(models=types.SimpleNamespace(Q=DummyQ)))
        install_stub("django.db", models=types.SimpleNamespace(Q=DummyQ))
        install_stub("django.db.models", Q=DummyQ, QuerySet=DummyQuerySet)
        install_stub("www.db.base", BaseConnection=object)
        install_stub(
            "www.models.service_publish",
            ServiceExtendMethod=DummyModel,
        )
        install_stub(
            "www.models.main",
            GatewayCustomConfiguration=DummyModel,
            ServiceDomain=DummyModel,
            ServiceDomainCertificate=DummyModel,
            ServiceTcpDomain=DummyModel,
            TenantServiceAuth=DummyModel,
            TenantServiceConfigurationFile=DummyModel,
            TenantServiceEnv=DummyModel,
            TenantServiceEnvVar=DummyModel,
            TenantServiceMountRelation=DummyModel,
            TenantServiceRelation=DummyModel,
            TenantServiceInfo=DummyModel,
            Tenants=DummyModel,
            TenantServicesPort=DummyModel,
            TenantServiceVolume=TenantServiceVolumeStub,
            ThirdPartyServiceEndpoints=DummyModel,
        )
        return importlib.import_module("console.repositories.app_config")

    # capability_id: console.component.storage-custom-volume-filter
    def test_list_custom_volumes_treats_local_path_as_builtin_volume_type(self):
        repository_module = self.import_repository_module()
        filtered_queryset = MagicMock()
        repository_module.TenantServiceVolume.objects.filter.return_value = filtered_queryset

        repository_module.TenantServiceVolumnRepository().list_custom_volumes(["service-id"])

        filtered_queryset.exclude.assert_called_once_with(volume_type__in=[
            TenantServiceVolumeStub.CONFIGFILE,
            TenantServiceVolumeStub.SHARE,
            TenantServiceVolumeStub.LOCAL,
            TenantServiceVolumeStub.TMPFS,
            "local-path",
        ])


class TenantServiceEnvVarRepositoryTests(TestCase):
    def tearDown(self):
        for module_name in (
            "console.repositories.app_config",
            "console.exception.main",
            "console.utils.shortcuts",
            "www.db.base",
            "www.models.main",
            "www.models.service_publish",
        ):
            sys.modules.pop(module_name, None)

    def import_repository_module(self):
        sys.modules.pop("console.repositories.app_config", None)
        install_stub("console.exception.main", AbortRequest=Exception)
        install_stub("console.utils.shortcuts", get_object_or_404=lambda *args, **kwargs: None)
        install_stub("django", db=types.SimpleNamespace(models=types.SimpleNamespace(Q=DummyQ)))
        install_stub("django.db", models=types.SimpleNamespace(Q=DummyQ))
        install_stub("django.db.models", Q=DummyQ, QuerySet=DummyQuerySet)
        install_stub("www.db.base", BaseConnection=object)
        install_stub(
            "www.models.service_publish",
            ServiceExtendMethod=DummyModel,
        )
        install_stub(
            "www.models.main",
            GatewayCustomConfiguration=DummyModel,
            ServiceDomain=DummyModel,
            ServiceDomainCertificate=DummyModel,
            ServiceTcpDomain=DummyModel,
            TenantServiceAuth=DummyModel,
            TenantServiceConfigurationFile=DummyModel,
            TenantServiceEnv=DummyModel,
            TenantServiceEnvVar=DummyModel,
            TenantServiceMountRelation=DummyModel,
            TenantServiceRelation=DummyModel,
            TenantServiceInfo=DummyModel,
            Tenants=DummyModel,
            TenantServicesPort=DummyModel,
            TenantServiceVolume=TenantServiceVolumeStub,
            ThirdPartyServiceEndpoints=DummyModel,
        )
        return importlib.import_module("console.repositories.app_config")

    def test_get_build_envs_preserves_build_prefixes(self):
        repository_module = self.import_repository_module()
        repository_module.compile_env_repo = MagicMock()
        repository_module.compile_env_repo.get_service_compile_env.return_value = None

        build_env_rows = [
            types.SimpleNamespace(attr_name="BUILD_PROCFILE", attr_value="web: flask --app demo.app run --host 0.0.0.0 --port $PORT"),
            types.SimpleNamespace(attr_name="BUILD_PYTHON_PACKAGE_MANAGER", attr_value="pip"),
            types.SimpleNamespace(attr_name="BP_CPYTHON_VERSION", attr_value="3.14"),
        ]
        queryset = MagicMock()
        queryset.filter.return_value = build_env_rows

        repo = repository_module.TenantServiceEnvVarRepository()
        repo.get_service_env = MagicMock(return_value=queryset)

        envs = repo.get_build_envs("team-1", "svc-1")

        self.assertEqual(envs["BUILD_PROCFILE"], "web: flask --app demo.app run --host 0.0.0.0 --port $PORT")
        self.assertEqual(envs["BUILD_PYTHON_PACKAGE_MANAGER"], "pip")
        self.assertEqual(envs["BP_CPYTHON_VERSION"], "3.14")
        self.assertNotIn("PROCFILE", envs)
        self.assertNotIn("PYTHON_PACKAGE_MANAGER", envs)


class ServiceExtendRepositoryTests(TestCase):
    def tearDown(self):
        for module_name in (
            "console.repositories.app_config",
            "console.exception.main",
            "console.utils.shortcuts",
            "www.db.base",
            "www.models.main",
            "www.models.service_publish",
        ):
            sys.modules.pop(module_name, None)

    def import_repository_module(self, service_extend_method):
        sys.modules.pop("console.repositories.app_config", None)
        install_stub("console.exception.main", AbortRequest=Exception)
        install_stub("console.utils.shortcuts", get_object_or_404=lambda *args, **kwargs: None)
        install_stub("django", db=types.SimpleNamespace(models=types.SimpleNamespace(Q=DummyQ)))
        install_stub("django.db", models=types.SimpleNamespace(Q=DummyQ))
        install_stub("django.db.models", Q=DummyQ, QuerySet=DummyQuerySet)
        install_stub("www.db.base", BaseConnection=object)
        install_stub(
            "www.models.service_publish",
            ServiceExtendMethod=service_extend_method,
        )
        install_stub(
            "www.models.main",
            GatewayCustomConfiguration=DummyModel,
            ServiceDomain=DummyModel,
            ServiceDomainCertificate=DummyModel,
            ServiceTcpDomain=DummyModel,
            TenantServiceAuth=DummyModel,
            TenantServiceConfigurationFile=DummyModel,
            TenantServiceEnv=DummyModel,
            TenantServiceEnvVar=DummyModel,
            TenantServiceMountRelation=DummyModel,
            TenantServiceRelation=DummyModel,
            TenantServiceInfo=DummyModel,
            Tenants=DummyModel,
            TenantServicesPort=DummyModel,
            TenantServiceVolume=TenantServiceVolumeStub,
            ThirdPartyServiceEndpoints=DummyModel,
        )
        return importlib.import_module("console.repositories.app_config")

    # capability_id: console.component.extend-method-upsert
    def test_create_extend_method_replaces_existing_version_record(self):
        service_extend_method = MagicMock()
        existing_records = MagicMock()
        service_extend_method.objects.filter.return_value = existing_records
        service_extend_method.objects.create.return_value = "created"
        repository_module = self.import_repository_module(service_extend_method)

        result = repository_module.ServiceExtendRepository().create_extend_method(
            service_key="service-key",
            app_version="1.0.0",
            min_node=2,
            max_node=9,
            step_node=3,
        )

        service_extend_method.objects.filter.assert_called_once_with(
            service_key="service-key",
            app_version="1.0.0",
        )
        existing_records.delete.assert_called_once_with()
        service_extend_method.objects.create.assert_called_once_with(
            service_key="service-key",
            app_version="1.0.0",
            min_node=2,
            max_node=9,
            step_node=3,
        )
        self.assertEqual(result, "created")

    # capability_id: console.component.extend-method-upsert
    def test_get_extend_method_by_service_uses_latest_record(self):
        service_extend_method = MagicMock()
        query = MagicMock()
        ordered_query = MagicMock()
        ordered_query.first.return_value = "latest"
        query.order_by.return_value = ordered_query
        service_extend_method.objects.filter.return_value = query
        repository_module = self.import_repository_module(service_extend_method)
        service = types.SimpleNamespace(service_source="market", service_key="service-key", version="1.0.0")

        result = repository_module.ServiceExtendRepository().get_extend_method_by_service(service)

        service_extend_method.objects.filter.assert_called_once_with(
            service_key="service-key",
            app_version="1.0.0",
        )
        query.order_by.assert_called_once_with("-ID")
        ordered_query.first.assert_called_once_with()
        self.assertEqual(result, "latest")

    # capability_id: console.component.extend-method-upsert
    def test_bulk_create_or_update_replaces_existing_version_records_by_business_key(self):
        service_extend_method = MagicMock()
        existing_records = MagicMock()
        service_extend_method.objects.filter.return_value = existing_records
        extend_info = types.SimpleNamespace(ID=None, service_key="service-key", app_version="1.0.0")
        repository_module = self.import_repository_module(service_extend_method)

        repository_module.ServiceExtendRepository().bulk_create_or_update([extend_info])

        filter_args, filter_kwargs = service_extend_method.objects.filter.call_args
        self.assertTrue(filter_args)
        self.assertEqual(filter_kwargs, {})
        existing_records.delete.assert_called_once_with()
        service_extend_method.objects.bulk_create.assert_called_once_with([extend_info])
