# -*- coding: utf-8 -*-
import collections
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from types import ModuleType, SimpleNamespace
from unittest import TestCase, mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
if "openapi_client" not in sys.modules:
    client_module = ModuleType("openapi_client")
    client_module.ApiClient = object
    client_module.MarketOpenapiApi = object
    config_module = ModuleType("openapi_client.configuration")
    config_module.Configuration = type("Configuration", (), {})
    rest_module = ModuleType("openapi_client.rest")
    rest_module.ApiException = type("ApiException", (Exception,), {})
    sys.modules["openapi_client"] = client_module
    sys.modules["openapi_client.configuration"] = config_module
    sys.modules["openapi_client.rest"] = rest_module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.test_settings")

import django  # noqa: E402

django.setup()

from console.services import platform_plugin_service as plugin_module  # noqa: E402
from console.services.platform_plugin_service import PlatformPluginService  # noqa: E402
from console.utils import coalesced_read_cache as cache_module  # noqa: E402
from django.db import connection  # noqa: E402
from django.test.utils import CaptureQueriesContext  # noqa: E402
from www.models.main import TenantServiceGroup  # noqa: E402

# capability_id: console.platform-plugin.coalesced-catalog-reads
# capability_id: console.platform-plugin.batch-install-metadata


class PlatformPluginReadCacheTests(TestCase):
    def setUp(self):
        self.service = PlatformPluginService()
        self.market = SimpleNamespace(url="https://market.invalid", domain="enterprise", access_key="")
        self.plugins = [{"plugin_id": "sample", "plugin_views": [{"title": "original"}]}]

    def _cached_call(self, kind, key):
        if kind == "market":
            return self.service._get_market_platform_plugins_cached(key)
        return self.service._get_region_arches(key)

    def _patch_loader(self, kind, loader):
        if kind == "market":
            return mock.patch.object(self.service, "_get_market_platform_plugins", side_effect=loader)
        return mock.patch.object(plugin_module.region_api, "get_cluster_nodes_arch", side_effect=loader)

    def _result(self, kind):
        return (self.market, self.plugins) if kind == "market" else ({"status": 200}, {"list": ["arm64"]})

    def test_eight_same_key_cold_readers_use_one_downstream_call(self):
        for kind in ("market", "arch"):
            with self.subTest(kind=kind):
                start = threading.Barrier(8)
                entered = threading.Event()
                all_loaders_entered = threading.Event()
                release = threading.Event()
                calls = []
                lock = threading.Lock()

                def load(key):
                    with lock:
                        calls.append(key)
                        if len(calls) == 8:
                            all_loaders_entered.set()
                    entered.set()
                    if not release.wait(3):
                        raise AssertionError("test loader was not released")
                    return self._result(kind)

                def read(_):
                    start.wait(timeout=3)
                    return self._cached_call(kind, "same-key")

                with self._patch_loader(kind, load), ThreadPoolExecutor(max_workers=8) as pool:
                    futures = [pool.submit(read, i) for i in range(8)]
                    try:
                        self.assertTrue(entered.wait(3))
                        all_loaders_entered.wait(0.15)
                    finally:
                        release.set()
                    results = [future.result(timeout=3) for future in futures]
                self.assertEqual(1, len(calls))
                self.assertEqual(8, len(results))

    def test_different_keys_do_not_wait_for_each_others_network(self):
        for kind in ("market", "arch"):
            with self.subTest(kind=kind):
                both_loading = threading.Barrier(2)

                def load(key):
                    both_loading.wait(timeout=3)
                    return self._result(kind)

                with self._patch_loader(kind, load) as loader, ThreadPoolExecutor(max_workers=2) as pool:
                    futures = [pool.submit(self._cached_call, kind, key) for key in ("first-key", "other-key")]
                    for future in futures:
                        future.result(timeout=4)
                self.assertEqual(2, loader.call_count)

    def test_clear_detaches_inflight_reader_and_prevents_old_cache_repopulation(self):
        for kind in ("market", "arch"):
            with self.subTest(kind=kind):
                old_started, release_old = threading.Event(), threading.Event()
                call_count = []

                def load(key):
                    call_count.append(key)
                    if len(call_count) == 1:
                        old_started.set()
                        if not release_old.wait(3):
                            raise AssertionError("old loader not released")
                        return (self.market, [{"plugin_id": "old"}]) if kind == "market" else (None, {"list": ["amd64"]})
                    return (self.market, [{"plugin_id": "new"}]) if kind == "market" else (None, {"list": ["arm64"]})

                with self._patch_loader(kind, load), ThreadPoolExecutor(max_workers=2) as pool:
                    old = pool.submit(self._cached_call, kind, "clear-key")
                    self.assertTrue(old_started.wait(3))
                    if kind == "market":
                        self.service.clear_market_plugin_cache()
                    else:
                        self.service.clear_region_arches_cache()
                    try:
                        fresh = pool.submit(self._cached_call, kind, "clear-key").result(timeout=2)
                    finally:
                        release_old.set()
                    old.result(timeout=3)
                    current = self._cached_call(kind, "clear-key")
                self.assertEqual(fresh, current)
                self.assertEqual(2, len(call_count))

    def test_failed_market_read_wakes_waiters_and_next_read_retries(self):
        start, entered, release = threading.Barrier(8), threading.Event(), threading.Event()
        calls = []

        def load(key):
            calls.append(key)
            entered.set()
            if not release.wait(3):
                raise AssertionError("failed loader not released")
            raise ValueError("fixture unavailable")

        def read(_):
            start.wait(timeout=3)
            return self._cached_call("market", "error-key")

        with self._patch_loader("market", load), ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(read, i) for i in range(8)]
            self.assertTrue(entered.wait(3))
            # Waiters must have a chance to join the in-flight read before it fails.
            threading.Event().wait(0.15)
            release.set()
            for future in futures:
                with self.assertRaisesRegex(ValueError, "fixture unavailable"):
                    future.result(timeout=3)
        self.assertEqual(1, len(calls))
        with self._patch_loader("market", lambda key: self._result("market")) as retry:
            self._cached_call("market", "error-key")
            self.assertEqual(1, retry.call_count)

    def test_ttl_begins_when_successful_read_finishes(self):
        for kind in ("market", "arch"):
            with self.subTest(kind=kind):
                clock = SimpleNamespace(now=100.0)

                def load(key):
                    clock.now = 140.0
                    return self._result(kind)

                with mock.patch.object(cache_module.time, "monotonic", side_effect=lambda: clock.now), \
                        self._patch_loader(kind, load) as loader:
                    self._cached_call(kind, "completion-key")
                    clock.now = 170.0
                    self._cached_call(kind, "completion-key")
                    self.assertEqual(1, loader.call_count)
                    clock.now = 201.0
                    self._cached_call(kind, "completion-key")
                    self.assertEqual(2, loader.call_count)

    def test_disabled_ttl_does_not_cache_or_coalesce(self):
        for kind, env_name in (("market", "MARKET_PLUGIN_CACHE_TTL_SECONDS"), ("arch", "REGION_ARCH_CACHE_TTL_SECONDS")):
            for ttl in ("0", "-1"):
                with self.subTest(kind=kind, ttl=ttl), mock.patch.dict(os.environ, {env_name: ttl}):
                    barrier = threading.Barrier(4)

                    def load(key):
                        barrier.wait(timeout=3)
                        return self._result(kind)

                    with self._patch_loader(kind, load) as loader, ThreadPoolExecutor(max_workers=4) as pool:
                        futures = [pool.submit(self._cached_call, kind, "disabled-key") for _ in range(4)]
                        for future in futures:
                            future.result(timeout=4)
                    self.assertEqual(4, loader.call_count)

    def test_market_nested_returns_are_isolated_from_each_other_and_loader(self):
        with self._patch_loader("market", lambda key: self._result("market")) as loader:
            first = self._cached_call("market", "copy-key")
            first[1][0]["plugin_views"][0]["title"] = "caller-mutated"
            self.assertEqual("original", self._cached_call("market", "copy-key")[1][0]["plugin_views"][0]["title"])
            self.plugins[0]["plugin_views"][0]["title"] = "loader-mutated"
            self.assertEqual("original", self._cached_call("market", "copy-key")[1][0]["plugin_views"][0]["title"])
            self.assertEqual(1, loader.call_count)

    def test_arch_returns_do_not_expose_cached_set(self):
        with self._patch_loader("arch", lambda key: self._result("arch")) as loader:
            first = self._cached_call("arch", "copy-region")
            first.add("amd64")
            self.assertEqual({"arm64"}, self._cached_call("arch", "copy-region"))
            self.assertEqual(1, loader.call_count)

    def test_arch_failure_keeps_existing_fallback_and_cache_contract(self):
        with self._patch_loader("arch", lambda key: (_ for _ in ()).throw(ValueError("fixture unavailable"))) as loader:
            first = self._cached_call("arch", "fallback-region")
            first.clear()
            self.assertEqual({"amd64", "arm64"}, self._cached_call("arch", "fallback-region"))
            self.assertEqual(1, loader.call_count)

    def test_market_cached_model_cannot_be_mutated_by_a_caller(self):
        with self._patch_loader("market", lambda key: self._result("market")):
            market, _ = self._cached_call("market", "model-copy-key")
            market.url = "https://changed.invalid"
            self.assertEqual("https://market.invalid", self._cached_call("market", "model-copy-key")[0].url)

    def test_clear_without_a_new_reader_does_not_republish_old_value(self):
        entered, release = threading.Event(), threading.Event()

        def load(key):
            entered.set()
            if not release.wait(3):
                raise AssertionError("old read was not released")
            return self._result("market")

        with self._patch_loader("market", load) as loader, ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(self._cached_call, "market", "old-only-key")
            self.assertTrue(entered.wait(3))
            self.service.clear_market_plugin_cache()
            release.set()
            pending.result(timeout=3)
            self._cached_call("market", "old-only-key")
            self.assertEqual(2, loader.call_count)

    def test_invalid_ttl_uses_existing_sixty_second_default(self):
        for kind, env_name in (("market", "MARKET_PLUGIN_CACHE_TTL_SECONDS"), ("arch", "REGION_ARCH_CACHE_TTL_SECONDS")):
            with self.subTest(kind=kind), mock.patch.dict(os.environ, {env_name: "invalid"}), \
                    self._patch_loader(kind, lambda key: self._result(kind)) as loader:
                self._cached_call(kind, "invalid-ttl-key")
                self._cached_call(kind, "invalid-ttl-key")
                self.assertEqual(1, loader.call_count)


class PlatformPluginInstallationBatchTests(TestCase):
    fixture_tenant_id = "perf-plugin-install-fixture"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.created_table = TenantServiceGroup._meta.db_table not in connection.introspection.table_names()
        if cls.created_table:
            with connection.schema_editor() as editor:
                editor.create_model(TenantServiceGroup)

    @classmethod
    def tearDownClass(cls):
        if cls.created_table:
            with connection.schema_editor() as editor:
                editor.delete_model(TenantServiceGroup)
        super().tearDownClass()

    def tearDown(self):
        TenantServiceGroup.objects.filter(tenant_id=self.fixture_tenant_id).delete()

    def _list(self, installed, catalog, mapped):
        service = PlatformPluginService()
        with mock.patch.object(plugin_module, "is_cloud_market_disabled", return_value=False), \
                mock.patch.object(service, "_get_license_bean", return_value={}), \
                mock.patch.object(service, "_get_installed_plugins", return_value=installed), \
                mock.patch.object(service, "_get_region_app_id_map", return_value=mapped), \
                mock.patch.object(service, "_get_region_arches", return_value={"amd64", "arm64"}), \
                mock.patch.object(service, "_get_market_platform_plugins_cached", return_value=(None, catalog)):
            with CaptureQueriesContext(connection) as queries:
                result = service.list_platform_plugins("fixture-enterprise", "fixture-region")
        return result, list(queries.captured_queries)

    def test_latest_sku_and_version_use_one_real_query_at_one_five_and_fifty_plugins(self):
        for count in (1, 5, 50):
            with self.subTest(plugins=count):
                TenantServiceGroup.objects.filter(tenant_id=self.fixture_tenant_id).delete()
                installed, catalog, mapped = {}, [], {}
                for i in range(count):
                    app_id = 700000 + i
                    plugin_id = "fixture-plugin-{}".format(i)
                    region_app_id = "region-app-{}".format(i)
                    for key, version in (("old-sku", "old-version"), ("arm-sku", "installed-v2")):
                        TenantServiceGroup.objects.create(
                            tenant_id=self.fixture_tenant_id, service_group_id=app_id,
                            group_key=key, group_version=version, region_name="fixture-region")
                    installed[plugin_id] = {"region_app_id": region_app_id, "status": "RUNNING"}
                    mapped[region_app_id] = app_id
                    catalog.extend([
                        {"plugin_id": plugin_id, "app_key": "amd-sku", "arch": "amd64", "app_level": "free",
                         "latest_version": "amd-v9"},
                        {"plugin_id": plugin_id, "app_key": "arm-sku", "arch": "arm64", "app_level": "free",
                         "latest_version": "arm-v3"},
                    ])
                result, queries = self._list(installed, catalog, mapped)
                self.assertEqual(count, len(result))
                self.assertTrue(all(item["installed_version"] == "installed-v2" for item in result))
                self.assertTrue(all(item["latest_version"] == "arm-v3" for item in result))
                self.assertTrue(all(item["installed_arch"] == "arm64" for item in result))
                self.assertTrue(all(item["selected_arch"] == "amd64" for item in result))
                self.assertTrue(all(item["upgradeable"] for item in result))
                self.assertEqual(1, len(queries), "installation metadata must be one batch, not per-plugin SQL")

    def test_empty_installed_plugins_do_not_query_installation_table(self):
        result, queries = self._list({}, [{"plugin_id": "free-plugin", "app_level": "free"}], {})
        self.assertEqual(1, len(result))
        self.assertEqual([], queries)

    def test_nonpositive_application_mapping_does_not_query_installation_table(self):
        installed = {"missing": {"region_app_id": "missing-app"}}
        for app_id in (0, -1):
            with self.subTest(app_id=app_id):
                result, queries = self._list(installed, [{"plugin_id": "missing", "app_level": "free"}],
                                             {"missing-app": app_id})
                self.assertEqual(app_id, result[0]["app_id"])
                self.assertEqual("", result[0]["installed_version"])
                self.assertEqual([], queries)

    def test_local_import_and_missing_metadata_keep_upgrade_disabled(self):
        TenantServiceGroup.objects.create(tenant_id=self.fixture_tenant_id, service_group_id=700001,
                                          group_key="imported-sku", group_version="local-v1", region_name="fixture-region")
        installed = {"local": {"region_app_id": "local-app"}, "missing": {"region_app_id": "missing-app"}}
        catalog = [{"plugin_id": plugin_id, "app_key": "market-sku", "app_level": "free", "latest_version": "market-v3"}
                   for plugin_id in installed]
        result, queries = self._list(installed, catalog, {"local-app": 700001, "missing-app": 700002})
        by_id = {item["plugin_id"]: item for item in result}
        self.assertEqual("local-v1", by_id["local"]["installed_version"])
        self.assertEqual("local-v1", by_id["local"]["latest_version"])
        self.assertEqual("", by_id["missing"]["installed_version"])
        self.assertEqual("", by_id["missing"]["latest_version"])
        self.assertFalse(any(item["can_upgrade"] for item in result))
        self.assertEqual(1, len(queries))

    def test_arch_or_license_filtered_plugins_do_not_read_installation_metadata(self):
        service = PlatformPluginService()
        installed = {"filtered": {"region_app_id": "installed-region-app"}}
        catalog = [{"plugin_id": "filtered", "app_key": "enterprise-sku", "app_level": "enterprise", "arch": "arm64"}]
        for region_arches, license_bean in (({"amd64"}, {}), ({"arm64"}, {"valid": True, "plugin_mapping": {}})):
            with self.subTest(arches=region_arches), \
                    mock.patch.object(plugin_module, "is_cloud_market_disabled", return_value=False), \
                    mock.patch.object(service, "_get_license_bean", return_value=license_bean), \
                    mock.patch.object(service, "_get_installed_plugins", return_value=installed), \
                    mock.patch.object(service, "_get_region_app_id_map", return_value={"installed-region-app": 700001}), \
                    mock.patch.object(service, "_get_region_arches", return_value=region_arches), \
                    mock.patch.object(service, "_get_market_platform_plugins_cached", return_value=(None, catalog)), \
                    CaptureQueriesContext(connection) as queries:
                self.assertEqual([], service.list_platform_plugins("fixture-enterprise", "fixture-region"))
                self.assertEqual([], list(queries.captured_queries))
