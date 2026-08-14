# -*- coding: utf-8 -*-
import copy
import contextlib
import datetime
import os
from types import SimpleNamespace
from unittest import TestCase, mock

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")
os.environ["DISABLE_RAINSKILLS_DEPLOY_SWEEPER"] = "1"

import django  # noqa: E402

django.setup()

from console.repositories.rainskills_deployment_repo import (  # noqa: E402
    RainSkillsDeploymentRepository, )
from console.repositories import rainskills_deployment_repo as repo_module  # noqa: E402
from console.services.rainskills_deployment_service import (  # noqa: E402
    RainSkillsDeploymentService, )
import console.services.rainskills_deployment_service as deployment_service_module  # noqa: E402

UTC = datetime.timezone.utc
NOW = datetime.datetime(2026, 7, 24, 9, 30, tzinfo=UTC)


class FakeRecord(object):

    def __init__(self,
                 key,
                 payload=None,
                 desc="rainskills deployment tracking"):
        self.key = key
        self.value = copy.deepcopy(payload or {})
        self.desc = desc


class FakeRepo(object):

    def __init__(self):
        self.records = {}
        self.deleted = []

    @staticmethod
    def build_attempt_key(attempt_id):
        return "RAINSKILLS_DEPLOY_{}".format(attempt_id[:13])

    def create_attempt(self, enterprise_id, attempt_id, payload):
        key = self.build_attempt_key(attempt_id)
        if key in self.records:
            return self.records[key], False
        record = FakeRecord(key, payload)
        self.records[key] = record
        return record, True

    def get_by_key(self, key):
        return self.records.get(key)

    def list_tracking_records(self):
        return list(self.records.values())

    @staticmethod
    def load_payload(record):
        return copy.deepcopy(record.value) if record else {}

    @staticmethod
    def update_payload(record, payload):
        record.value = copy.deepcopy(payload)
        return record

    def delete_payload(self, record):
        self.deleted.append(record.key)
        self.records.pop(record.key, None)


class FakeTransport(object):

    def __init__(self, statuses=None, error=None):
        self.statuses = list(statuses or [200])
        self.error = error
        self.requests = []

    def post(self, url, json=None, timeout=None):
        self.requests.append({
            "url": url,
            "json": copy.deepcopy(json),
            "timeout": timeout
        })
        if self.error:
            raise self.error
        status = self.statuses.pop(0) if self.statuses else 503
        return SimpleNamespace(status_code=status, text="central response")


class RaisingTransport(object):

    def __init__(self):
        self.requests = []

    def post(self, url, json=None, timeout=None):
        self.requests.append({
            "url": url,
            "json": copy.deepcopy(json),
            "timeout": timeout
        })
        raise RuntimeError("central unavailable")


class FakeRegion(object):

    def __init__(self, responses=None):
        self.responses = list(responses or [])
        self.requests = []

    def get_tenant_events(self, region, tenant, event_ids):
        self.requests.append((region, tenant, list(event_ids)))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return copy.deepcopy(response)


class DeferredThread(object):

    def __init__(self, target, args=(), **_kwargs):
        self.target = target
        self.args = args
        self.daemon = False
        self.started = False

    def start(self):
        self.started = True


def make_service(repo=None,
                 region=None,
                 transport=None,
                 clock=None,
                 sleep=None,
                 thread_factory=None):
    return RainSkillsDeploymentService(
        repo=repo or FakeRepo(),
        region_api_client=region or FakeRegion(),
        transport=transport or FakeTransport(),
        clock=clock or (lambda: NOW),
        sleep=sleep or (lambda _seconds: None),
        thread_factory=thread_factory or DeferredThread,
        start_sweeper=False,
    )


def begin(service,
          enterprise_id="enterprise-1",
          tenant_name="tenant-secret",
          region_name="region-a"):
    return service.begin_tracking(
        client="codex",
        tool="deploy-source-code",
        deploy_type="source_code",
        deploy_stage="initial",
        trigger="chat",
        enterprise_id=enterprise_id,
        tenant_name=tenant_name,
        region_name=region_name,
        app_id=7,
        resource_created=True,
        source_language="Go",
    )


class RainSkillsDeploymentRepositoryTests(TestCase):

    def test_repository_uses_only_the_independent_prefix_and_description(self):
        self.assertEqual(RainSkillsDeploymentRepository.KEY_PREFIX,
                         "RAINSKILLS_DEPLOY_")
        self.assertEqual(RainSkillsDeploymentRepository.DESC,
                         "rainskills deployment tracking")

    def test_attempt_key_is_stable_unique_and_fits_model_limit(self):
        first = RainSkillsDeploymentRepository.build_attempt_key("attempt-a")
        second = RainSkillsDeploymentRepository.build_attempt_key("attempt-a")
        other = RainSkillsDeploymentRepository.build_attempt_key("attempt-b")

        self.assertEqual(first, second)
        self.assertNotEqual(first, other)
        self.assertTrue(first.startswith("RAINSKILLS_DEPLOY_"))
        self.assertLessEqual(len(first), 32)

    def test_repository_creates_loads_lists_updates_and_deletes_json(self):

        class QuerySet(object):

            def __init__(self, records):
                self.records = records

            def first(self):
                return self.records[0] if self.records else None

            def all(self):
                return self.records

        class Record(object):

            def __init__(self, manager, key, **fields):
                self.manager = manager
                self.key = key
                self.__dict__.update(fields)

            def save(self, update_fields=None):
                self.update_fields = update_fields

            def delete(self):
                self.manager.records.pop(self.key, None)

        class Manager(object):

            def __init__(self):
                self.records = {}
                self.filters = []

            def get_or_create(self, key, defaults):
                if key in self.records:
                    return self.records[key], False
                record = Record(self, key, **defaults)
                self.records[key] = record
                return record, True

            def filter(self, **kwargs):
                self.filters.append(kwargs)
                records = list(self.records.values())
                for name, value in kwargs.items():
                    if name == "key__startswith":
                        records = [
                            record for record in records
                            if record.key.startswith(value)
                        ]
                    else:
                        records = [
                            record for record in records
                            if getattr(record, name) == value
                        ]
                return QuerySet(records)

        manager = Manager()
        model = SimpleNamespace(objects=manager)
        repository = RainSkillsDeploymentRepository()
        with mock.patch.object(repo_module, "ConsoleSysConfig", model), \
                mock.patch.object(repo_module.transaction, "atomic", return_value=contextlib.nullcontext()):
            record, created = repository.create_attempt(
                "eid-1", "attempt-1", {"status": "accepted"})
            self.assertTrue(created)
            self.assertEqual(
                repository.load_payload(repository.get_by_key(record.key)),
                {"status": "accepted"})

            repository.update_payload(record, {"status": "success"})
            self.assertEqual(repository.load_payload(record),
                             {"status": "success"})
            self.assertEqual(repository.list_tracking_records(), [record])
            self.assertEqual(
                manager.filters[-1], {
                    "key__startswith": "RAINSKILLS_DEPLOY_",
                    "desc": "rainskills deployment tracking",
                    "enable": True,
                })

            repository.delete_payload(record)
            self.assertIsNone(repository.get_by_key(record.key))

    def test_concurrent_create_returns_the_winning_record(self):
        from django.db import IntegrityError

        winning = FakeRecord("RAINSKILLS_DEPLOY_winner",
                             {"status": "accepted"})

        class QuerySet(object):

            @staticmethod
            def first():
                return winning

        class Manager(object):

            @staticmethod
            def get_or_create(**_kwargs):
                raise IntegrityError("duplicate key")

            @staticmethod
            def filter(**_kwargs):
                return QuerySet()

        repository = RainSkillsDeploymentRepository()
        model = SimpleNamespace(objects=Manager())
        with mock.patch.object(repo_module, "ConsoleSysConfig", model), \
                mock.patch.object(repo_module.transaction, "atomic", return_value=contextlib.nullcontext()):
            record, created = repository.create_attempt(
                "eid-1", "attempt-1", {})

        self.assertIs(record, winning)
        self.assertFalse(created)


class RainSkillsDeploymentServiceTests(TestCase):

    def test_polling_worker_releases_database_connections_between_polls(self):
        repo = FakeRepo()
        region = FakeRegion([
            {"list": [{"event_id": "event-1", "status": "pending"}]},
            {"list": [{"event_id": "event-1", "status": "success"}]},
        ])
        transport = FakeTransport([204, 204])
        service = make_service(repo=repo, region=region, transport=transport)
        tracker = begin(service)
        service.bind_events(tracker, ["event-1"], [])

        with mock.patch.object(deployment_service_module,
                               "close_old_connections") as close_old, \
                mock.patch.object(deployment_service_module.connections,
                                  "close_all") as close_all:
            service._worker_entry(tracker["key"])

        self.assertGreaterEqual(close_old.call_count, 2)
        self.assertGreaterEqual(close_all.call_count, 2)
        self.assertNotIn(tracker["key"], repo.records)

    def test_report_url_is_always_the_canonical_request_server(self):
        with mock.patch.dict(
                os.environ,
                {"RAINSKILLS_DEPLOY_REPORT_URL": "http://unused.example/api"}):
            service = make_service()

        self.assertEqual(
            service.report_url,
            "https://log.rainbond.com/api/rainskills/deployments")

    def test_classify_tool_call_covers_the_deployment_entry_matrix(self):
        service = make_service()
        cases = [
            ("rainbond_create_component", {"is_deploy": True}, None,
             ("initial", "image_create", "image", True, False)),
            ("rainbond_create_component_from_image", {"is_deploy": True}, None,
             ("initial", "image_create", "image", True, False)),
            ("rainbond_create_component_from_source", {"is_deploy": True}, None,
             ("initial", "source_create", "source_code", True, True)),
            ("rainbond_create_component_from_package", {"is_deploy": True}, None,
             ("initial", "package_create", "package", True, True)),
            ("rainbond_create_component_from_local_package", {"is_deploy": True}, None,
             ("initial", "package_create", "package", True, True)),
            ("rainbond_install_app_model", {"is_deploy": True}, None,
             ("initial", "market_install", "app_market", True, True)),
            ("rainbond_install_app_by_market", {"is_deploy": True}, None,
             ("initial", "market_install", "app_market", True, True)),
            ("rainbond_create_app_from_snapshot_version", {"is_deploy": True}, None,
             ("initial", "snapshot_create", "app_market", True, True)),
            ("rainbond_build_component", {"is_deploy": True}, ["source_code"],
             ("continuous", "build_component", "source_code", False, False)),
            ("rainbond_build_component", {"is_deploy": True}, ["docker_image"],
             ("continuous", "build_component", "image", False, False)),
            ("rainbond_build_component", {"is_deploy": True}, ["package_build"],
             ("continuous", "build_component", "package", False, False)),
            ("rainbond_operate_app", {"action": "deploy"}, ["source_code"],
             ("continuous", "operate_app_deploy", "source_code", False, False)),
            ("rainbond_operate_app", {"action": "upgrade"}, ["docker_run"],
             ("continuous", "operate_app_upgrade", "image", False, False)),
            ("rainbond_operate_app", {"action": "deploy"}, ["source_code", "docker_image"],
             ("continuous", "operate_app_deploy", "mixed", False, False)),
            ("rainbond_execute_app_upgrade_record", {}, None,
             ("continuous", "execute_upgrade_record", "app_market", False, False)),
            ("rainbond_deploy_app_upgrade_record", {}, None,
             ("continuous", "deploy_upgrade_record", "app_market", False, False)),
            ("rainbond_upgrade_app", {}, None,
             ("continuous", "upgrade_app", "app_market", False, False)),
            ("rainbond_rollback_app_upgrade_record", {}, None,
             ("rollback", "rollback_app_upgrade_record", "app_market", False, False)),
            ("rainbond_rollback_app_version_snapshot", {}, None,
             ("rollback", "rollback_app_version_snapshot", "app_market", False, False)),
        ]

        for tool_name, arguments, service_sources, expected in cases:
            with self.subTest(tool_name=tool_name, arguments=arguments, service_sources=service_sources):
                spec = service.classify_tool_call(tool_name, arguments, service_sources=service_sources)
                self.assertIsNotNone(spec)
                self.assertEqual(
                    (spec.deploy_stage, spec.trigger, spec.deploy_type,
                     spec.resource_created, spec.legacy_tracked), expected)

    def test_classify_tool_call_rejects_non_deployment_conditions(self):
        service = make_service()
        cases = [
            ("rainbond_create_component", {"is_deploy": False}),
            ("rainbond_create_component_from_source", {"is_deploy": "false"}),
            ("rainbond_install_app_model", {"is_deploy": 0}),
            ("rainbond_create_app_from_snapshot_version", {"is_deploy": "off"}),
            ("rainbond_build_component", {"is_deploy": False}),
            ("rainbond_operate_app", {"action": "start"}),
            ("rainbond_operate_app", {"action": "stop"}),
            ("rainbond_operate_app", {"action": "restart"}),
            ("rainbond_build_helm_app", {}),
            ("rainbond_create_app_from_yaml", {}),
            ("rainbond_check_yaml_app", {}),
            ("rainbond_get_yaml_app_check_result", {}),
            ("rainbond_check_component", {}),
            ("rainbond_get_component_check_result", {}),
            ("rainbond_unknown_tool", {"is_deploy": True}),
        ]

        for tool_name, arguments in cases:
            with self.subTest(tool_name=tool_name, arguments=arguments):
                self.assertIsNone(service.classify_tool_call(tool_name, arguments))

    def test_classifier_uses_only_trusted_service_sources(self):
        service = make_service()

        spec = service.classify_tool_call(
            "rainbond_operate_app",
            {
                "action": "deploy",
                "service_source": "source_code",
                "service_sources": ["source_code"],
            },
            service_sources=["docker_image"],
        )

        self.assertEqual(spec.deploy_type, "image")

    def test_classifier_accepts_trusted_service_models_and_serialized_models(self):
        service = make_service()
        model_spec = service.classify_tool_call(
            "rainbond_operate_app", {"action": "upgrade"},
            service_sources=[SimpleNamespace(service_source="source_code")])
        dict_spec = service.classify_tool_call(
            "rainbond_build_component", {"is_deploy": True},
            service_sources=[{"service_source": "package_build"}])

        self.assertEqual(model_spec.deploy_type, "source_code")
        self.assertEqual(dict_spec.deploy_type, "package")

    def test_normalize_tool_result_uses_bounded_top_level_whitelist_fields(self):
        service = make_service()
        event_ids = ["event-{:03d}".format(index) for index in range(55)]
        event_ids += ["event-001", ""]
        service_ids = ["service-{:03d}".format(index) for index in range(52)]
        result = {
            "app_id": "17",
            "event_id": "event-060",
            "event_ids": event_ids + [{"event_id": "event-059", "service_id": "service-059"}],
            "service_id": "service-060",
            "service_ids": service_ids,
            "record": {
                "event_id": "nested-event-must-not-leak",
                "service_id": "nested-service-must-not-leak",
            },
            "arguments": {"event_id": "argument-event-must-not-leak"},
        }

        normalized = service.normalize_tool_result(result)

        self.assertEqual(normalized["app_id"], 17)
        self.assertEqual(normalized["event_count"], 57)
        self.assertEqual(normalized["event_ids"], ["event-{:03d}".format(index) for index in range(50)])
        self.assertTrue(normalized["event_ids_truncated"])
        self.assertEqual(normalized["service_count"], 54)
        self.assertEqual(normalized["service_ids"], ["service-{:03d}".format(index) for index in range(50)])
        self.assertTrue(normalized["service_ids_truncated"])
        self.assertNotIn("nested-event-must-not-leak", normalized["event_ids"])
        self.assertNotIn("nested-service-must-not-leak", normalized["service_ids"])

    def test_normalize_tool_result_accepts_only_scalar_or_standard_id_items(self):
        service = make_service()
        result = {
            "event_ids": [
                "event-2",
                {"event_id": "event-1", "service_id": "service-1"},
                {"id": "generic-id-must-not-be-used"},
                ["nested-event-must-not-be-used"],
            ],
            "service_ids": ["service-2", {"service_id": "service-3"}, {"id": "generic-id-must-not-be-used"}],
        }

        normalized = service.normalize_tool_result(result)

        self.assertEqual(normalized["event_ids"], ["event-1", "event-2"])
        self.assertEqual(normalized["service_ids"], ["service-1", "service-2", "service-3"])
        self.assertEqual(normalized["event_count"], 2)
        self.assertEqual(normalized["service_count"], 3)
        self.assertFalse(normalized["event_ids_truncated"])
        self.assertFalse(normalized["service_ids_truncated"])

    def test_normalize_tool_result_accepts_only_boolean_is_deploy(self):
        service = make_service()

        self.assertIs(service.normalize_tool_result({"is_deploy": False})["is_deploy"], False)
        self.assertIs(service.normalize_tool_result({"is_deploy": True})["is_deploy"], True)
        self.assertIsNone(service.normalize_tool_result({"is_deploy": "false"})["is_deploy"])
        self.assertIsNone(service.normalize_tool_result({})["is_deploy"])

    def test_bind_tool_result_discards_awaiting_tracker_when_result_did_not_deploy(self):
        repo = FakeRepo()
        transport = FakeTransport([200])
        threads = []

        def factory(*args, **kwargs):
            thread = DeferredThread(*args, **kwargs)
            threads.append(thread)
            return thread

        service = make_service(repo=repo, transport=transport, thread_factory=factory)
        spec = service.classify_tool_call(
            "rainbond_build_component", {"is_deploy": True},
            service_sources=[SimpleNamespace(service_source="third_party")])
        tracker = service.begin_tracking(
            client="codex",
            tool="rainbond_build_component",
            deploy_type=spec.deploy_type,
            deploy_stage=spec.deploy_stage,
            trigger=spec.trigger,
            app_id=7,
        )

        service.bind_tool_result(
            tracker, {
                "app_id": 7,
                "service_id": "svc-third-party",
                "event_id": "event-must-not-report",
                "is_deploy": False,
            })

        self.assertEqual(repo.records, {})
        self.assertEqual(repo.deleted, [tracker["key"]])
        self.assertEqual(transport.requests, [])
        self.assertEqual(threads, [])

    def test_bind_tool_result_applies_trusted_result_app_and_bounded_ids(self):
        repo = FakeRepo()
        threads = []

        def factory(*args, **kwargs):
            thread = DeferredThread(*args, **kwargs)
            threads.append(thread)
            return thread

        service = make_service(repo=repo, thread_factory=factory)
        tracker = service.begin_tracking(
            client="codex",
            tool="rainbond_create_app_from_snapshot_version",
            deploy_type="app_market",
            deploy_stage="initial",
            trigger="snapshot_create",
            app_id=0,
        )
        result = {
            "app_id": 88,
            "event_ids": ["event-{:03d}".format(index) for index in range(55)],
            "service_ids": ["service-{:03d}".format(index) for index in range(52)],
            "is_deploy": True,
        }

        service.bind_tool_result(tracker, result)

        payload = repo.load_payload(repo.get_by_key(tracker["key"]))
        self.assertEqual(payload["app_id"], 88)
        self.assertEqual(payload["event_count"], 55)
        self.assertEqual(len(payload["event_ids"]), 50)
        self.assertTrue(payload["event_ids_truncated"])
        self.assertEqual(payload["service_count"], 52)
        self.assertEqual(len(payload["service_ids"]), 50)
        self.assertTrue(payload["service_ids_truncated"])
        self.assertEqual(len(threads), 1)

    def test_begin_tracking_uses_stable_anonymous_eid_without_persisting_tenant_in_report(
            self):
        repo = FakeRepo()
        service = make_service(repo=repo)

        first = begin(service, enterprise_id="")
        second_service = make_service(repo=FakeRepo())
        second = begin(second_service, enterprise_id="")

        first_payload = repo.load_payload(repo.get_by_key(first["key"]))
        self.assertEqual(first_payload["eid"], second["eid"])
        self.assertEqual(len(first_payload["eid"]), 32)
        self.assertNotIn("tenant-secret",
                         service._build_report_payload(first_payload).values())
        self.assertNotIn("tenant_name",
                         service._build_report_payload(first_payload))
        self.assertNotIn("region_name",
                         service._build_report_payload(first_payload))

    def test_sweeper_skips_awaiting_result_created_by_begin(self):
        repo = FakeRepo()
        transport = FakeTransport([200])
        service = make_service(repo=repo, transport=transport)
        tracker = begin(service)

        payload = repo.load_payload(repo.get_by_key(tracker["key"]))
        service.sweep_once()

        self.assertEqual(payload["local_state"], "awaiting_result")
        self.assertNotIn("local_state", service._build_report_payload(payload))
        self.assertIn(tracker["key"], repo.records)
        self.assertEqual(transport.requests, [])

    def test_sweeper_retries_dispatch_only_after_bind_marks_record_bound(self):
        repo = FakeRepo()
        transport = FakeTransport([503, 503, 503, 204])
        threads = []

        def factory(*args, **kwargs):
            thread = DeferredThread(*args, **kwargs)
            threads.append(thread)
            return thread

        service = make_service(repo=repo,
                               transport=transport,
                               thread_factory=factory)
        tracker = begin(service)

        service.bind_events(tracker, [], [])
        threads.pop(0).target(tracker["key"])
        payload = repo.load_payload(repo.get_by_key(tracker["key"]))
        service.sweep_once()
        threads.pop(0).target(tracker["key"])

        self.assertEqual(payload["local_state"], "bound")
        self.assertNotIn("local_state", transport.requests[-1]["json"])
        self.assertNotIn(tracker["key"], repo.records)
        self.assertEqual(len(transport.requests), 4)

    def test_bind_without_events_reports_dispatch_and_deletes_on_2xx(self):
        repo = FakeRepo()
        transport = FakeTransport([204])
        service = make_service(repo=repo, transport=transport)
        tracker = begin(service)

        service.bind_events(tracker, [], [])
        service._worker_entry(tracker["key"])

        self.assertEqual(repo.records, {})
        self.assertEqual(transport.requests[0]["json"]["report_phase"],
                         "dispatch")
        self.assertEqual(transport.requests[0]["json"]["status"], "accepted")

    def test_bind_without_events_keeps_record_after_three_failed_posts(self):
        repo = FakeRepo()
        transport = FakeTransport([503, 503, 503])
        service = make_service(repo=repo, transport=transport)
        tracker = begin(service)

        service.bind_events(tracker, [], [])
        service._worker_entry(tracker["key"])

        self.assertIn(tracker["key"], repo.records)
        self.assertEqual(len(transport.requests), 3)

    def test_safe_bind_defers_failing_transport_until_worker_runs(self):
        repo = FakeRepo()
        transport = RaisingTransport()
        threads = []

        def factory(*args, **kwargs):
            thread = DeferredThread(*args, **kwargs)
            threads.append(thread)
            return thread

        service = make_service(repo=repo,
                               transport=transport,
                               thread_factory=factory)
        tracker = begin(service)

        self.assertIsNone(service.safe_bind_events(tracker, [], []))

        self.assertEqual(transport.requests, [])
        self.assertEqual(len(threads), 1)
        threads[0].target(*threads[0].args)
        self.assertEqual(len(transport.requests), 3)
        self.assertIn(tracker["key"], repo.records)

    def test_safe_mark_failure_defers_failing_transport_until_worker_runs(
            self):
        repo = FakeRepo()
        transport = RaisingTransport()
        threads = []

        def factory(*args, **kwargs):
            thread = DeferredThread(*args, **kwargs)
            threads.append(thread)
            return thread

        service = make_service(repo=repo,
                               transport=transport,
                               thread_factory=factory)
        tracker = begin(service)

        self.assertIsNone(
            service.safe_mark_failure(
                tracker,
                reason="tool failed",
                failure_stage="tool",
                failure_category="invocation_failed",
            ))

        self.assertEqual(transport.requests, [])
        payload = repo.load_payload(repo.get_by_key(tracker["key"]))
        self.assertEqual((payload["report_phase"], payload["status"]),
                         ("final", "failure"))
        self.assertEqual(len(threads), 1)
        threads[0].target(*threads[0].args)
        self.assertEqual(len(transport.requests), 3)
        self.assertIn(tracker["key"], repo.records)

    def test_event_poll_reports_success_and_deletes_record(self):
        repo = FakeRepo()
        region = FakeRegion([{
            "list": [{
                "event_id": "event-1",
                "status": "success"
            }]
        }])
        transport = FakeTransport([200, 200])
        service = make_service(repo=repo, region=region, transport=transport)
        tracker = begin(service)
        service.bind_events(tracker, ["event-1"], ["service-1"])

        service._poll_by_key(tracker["key"])

        self.assertEqual(transport.requests[-1]["json"]["report_phase"],
                         "final")
        self.assertEqual(transport.requests[-1]["json"]["status"], "success")
        self.assertNotIn(tracker["key"], repo.records)

    def test_event_poll_reports_failure_with_redacted_bounded_diagnostics(
            self):
        reason = "password=secret token=abc " + ("x" * 1200)
        region = FakeRegion([{
            "list": [{
                "EventID": "event-1",
                "Status": "failure",
                "Message": reason,
                "Reason": reason,
                "Arguments": {
                    "password": "do-not-store"
                },
                "OptType": "BuildService",
            }]
        }])
        transport = FakeTransport([200, 200])
        service = make_service(region=region, transport=transport)
        tracker = begin(service)
        service.bind_events(tracker, ["event-1"], [])

        service._poll_by_key(tracker["key"])

        final = transport.requests[-1]["json"]
        self.assertEqual(final["status"], "failure")
        self.assertEqual(final["failure_stage"], "build")
        self.assertNotIn("secret", final["failure_reason"])
        self.assertNotIn("abc", final["failure_reason"])
        self.assertLessEqual(len(final["failure_reason"]), 1024)
        self.assertNotIn("Arguments", str(final))

    def test_event_poll_reports_region_timeout_status(self):
        region = FakeRegion([{
            "list": [{
                "event_id": "event-1",
                "status": "timeout",
                "message": "deadline"
            }]
        }])
        transport = FakeTransport([200, 200])
        service = make_service(region=region, transport=transport)
        tracker = begin(service)
        service.bind_events(tracker, ["event-1"], [])

        service._poll_by_key(tracker["key"])

        self.assertEqual(transport.requests[-1]["json"]["status"], "timeout")

    def test_failure_stage_and_category_are_redacted_and_bounded(self):
        region = FakeRegion([{
            "list": [{
                "event_id": "event-1",
                "status": "failure",
                "failure_stage": "token=stage-secret",
                "failure_category": "password=category-secret",
                "reason": "failed",
            }]
        }])
        transport = FakeTransport([200, 200])
        service = make_service(region=region, transport=transport)
        tracker = begin(service)
        service.bind_events(tracker, ["event-1"], [])

        service._poll_by_key(tracker["key"])

        final = transport.requests[-1]["json"]
        self.assertNotIn("stage-secret", final["failure_stage"])
        self.assertNotIn("category-secret", final["failure_category"])
        self.assertLessEqual(len(final["failure_stage"]), 32)
        self.assertLessEqual(len(final["failure_category"]), 64)

    def test_sanitize_text_redacts_quoted_json_url_and_auth_credentials(self):
        service = make_service()
        sensitive = ('password="secret value" '
                     '{"password": "json secret value"} '
                     "https://user:url-secret@example.com/path "
                     "mysql://dbuser:mysql-secret@db.example.com/app "
                     "redis://:redis-secret@cache.example.com/0 "
                     "Bearer bearer-secret Basic basic-secret "
                     "access token <eyJhbGciOiJIUzI1NiJ9.payload.signature>")

        sanitized = service._sanitize_text(sensitive, 2048)

        for secret in (
                "secret value",
                "json secret value",
                "user",
                "url-secret",
                "bearer-secret",
                "basic-secret",
                "dbuser",
                "mysql-secret",
                "redis-secret",
                "eyJhbGciOiJIUzI1NiJ9.payload.signature",
        ):
            self.assertNotIn(secret, sanitized)
        self.assertIn('password="[Filtered]"', sanitized)
        self.assertIn('"password": "[Filtered]"', sanitized)
        self.assertIn("https://[Filtered]@example.com/path", sanitized)
        self.assertIn("mysql://[Filtered]@db.example.com/app", sanitized)
        self.assertIn("redis://[Filtered]@cache.example.com/0", sanitized)
        self.assertIn("Bearer [Filtered]", sanitized)
        self.assertIn("Basic [Filtered]", sanitized)
        self.assertIn("access token [Filtered]", sanitized)

    def test_final_post_failure_keeps_record_for_retry(self):
        repo = FakeRepo()
        region = FakeRegion([{
            "list": [{
                "event_id": "event-1",
                "status": "success"
            }]
        }])
        transport = FakeTransport([200, 503, 503, 503])
        service = make_service(repo=repo, region=region, transport=transport)
        tracker = begin(service)
        service.bind_events(tracker, ["event-1"], [])

        service._poll_by_key(tracker["key"])

        payload = repo.load_payload(repo.get_by_key(tracker["key"]))
        self.assertEqual(payload["report_phase"], "final")
        self.assertEqual(payload["status"], "success")

    def test_bind_sorts_deduplicates_and_truncates_ids_deterministically(self):
        repo = FakeRepo()
        service = make_service(repo=repo,
                               transport=FakeTransport([503, 503, 503]))
        tracker = begin(service)
        event_ids = [
            "event-{:02d}".format(index) for index in reversed(range(60))
        ] + ["event-01"]
        service_ids = [
            "service-{:02d}".format(index) for index in reversed(range(55))
        ] + ["service-01"]

        service.bind_events(tracker, event_ids, service_ids)

        payload = repo.load_payload(repo.get_by_key(tracker["key"]))
        self.assertEqual(payload["event_ids"], sorted(set(event_ids))[:50])
        self.assertEqual(payload["service_ids"], sorted(set(service_ids))[:50])
        self.assertEqual(payload["event_count"], 60)
        self.assertEqual(payload["service_count"], 55)
        self.assertTrue(payload["event_ids_truncated"])
        self.assertTrue(payload["service_ids_truncated"])

    def test_start_worker_deduplicates_running_key_and_releases_it(self):
        threads = []

        def factory(*args, **kwargs):
            thread = DeferredThread(*args, **kwargs)
            threads.append(thread)
            return thread

        service = make_service(thread_factory=factory)
        tracker = begin(service)
        service.bind_events(tracker, ["event-1"], [])
        service._start_worker(tracker["key"])

        self.assertEqual(len(threads), 1)
        self.assertIn(tracker["key"], service._running_keys)
        with mock.patch.object(service, "_poll_by_key"):
            threads[0].target(*threads[0].args)
        self.assertNotIn(tracker["key"], service._running_keys)

    def test_worker_marks_timeout_after_twenty_minutes(self):
        repo = FakeRepo()
        times = iter([
            NOW, NOW, NOW + datetime.timedelta(minutes=20, seconds=1),
            NOW + datetime.timedelta(minutes=20, seconds=1)
        ])
        region = FakeRegion([{
            "list": [{
                "event_id": "event-1",
                "status": ""
            }]
        }])
        transport = FakeTransport([200, 200])
        service = make_service(repo=repo,
                               region=region,
                               transport=transport,
                               clock=lambda: next(times))
        tracker = begin(service)
        service.bind_events(tracker, ["event-1"], [])

        service._poll_by_key(tracker["key"])

        self.assertEqual(transport.requests[-1]["json"]["status"], "timeout")

    def test_sweeper_recovers_final_pending_event_pending_and_dispatch_pending(
            self):
        repo = FakeRepo()
        service = make_service(repo=repo)
        base = {
            "created_at": NOW.isoformat(),
            "report_phase": "dispatch",
            "status": "accepted",
            "event_ids": [],
            "local_state": "bound",
        }
        repo.records = {
            "final":
            FakeRecord("final",
                       dict(base, report_phase="final", status="success")),
            "events":
            FakeRecord("events", dict(base, event_ids=["event-1"])),
            "dispatch":
            FakeRecord("dispatch", base),
        }

        with mock.patch.object(service, "_start_worker") as start_worker:
            service.sweep_once()

        self.assertEqual(
            start_worker.call_args_list,
            [mock.call("final"),
             mock.call("events"),
             mock.call("dispatch")])

    def test_sweeper_deletes_records_older_than_seven_days(self):
        repo = FakeRepo()
        old = (NOW - datetime.timedelta(days=8)).isoformat()
        repo.records["old"] = FakeRecord("old", {
            "created_at": old,
            "report_phase": "dispatch",
            "event_ids": []
        })
        service = make_service(repo=repo)

        with self.assertLogs("console.services.rainskills_deployment_service",
                             level="WARNING"):
            service.sweep_once()

        self.assertNotIn("old", repo.records)

    def test_sweeper_loop_continues_after_top_level_sweep_failure(self):

        class StopSweeper(BaseException):
            pass

        service = make_service()
        with mock.patch.object(
                service,
                "sweep_once",
                side_effect=[
                    RuntimeError("database unavailable"),
                    StopSweeper()
                ],
        ) as sweep_once:
            with self.assertLogs(
                    "console.services.rainskills_deployment_service",
                    level="WARNING"):
                with self.assertRaises(StopSweeper):
                    service._sweeper_loop()

        self.assertEqual(sweep_once.call_count, 2)

    def test_http_post_retries_central_failure_and_sends_only_dto_fields(self):
        transport = FakeTransport([503, 500, 204])
        service = make_service(transport=transport)
        payload = {
            "deploy_attempt_id": "attempt-1",
            "eid": "enterprise-1",
            "deploy_client": "codex",
            "tool_name": "deploy-source-code",
            "deploy_type": "source_code",
            "deploy_stage": "initial",
            "trigger": "chat",
            "source_language": "Go",
            "resource_created": True,
            "app_id": 7,
            "service_ids": [],
            "event_ids": [],
            "service_count": 0,
            "event_count": 0,
            "service_ids_truncated": False,
            "event_ids_truncated": False,
            "report_phase": "final",
            "status": "success",
            "deploy_result_at": "0002-01-01T00:00:00+00:00",
            "failure_stage": "",
            "failure_category": "",
            "failure_reason": "",
            "tenant_name": "must-not-send",
            "arguments": {
                "token": "must-not-send"
            },
        }

        self.assertTrue(service._post_report_payload(payload))
        self.assertEqual(len(transport.requests), 3)
        sent = transport.requests[-1]["json"]
        self.assertNotIn("tenant_name", sent)
        self.assertNotIn("arguments", sent)
        self.assertGreaterEqual(
            datetime.datetime.fromisoformat(sent["deploy_result_at"]).year,
            1000)
        self.assertTrue(
            all(request["timeout"] == 5 for request in transport.requests))

    def test_safe_wrappers_swallow_all_errors(self):
        service = make_service()
        with mock.patch.object(service, "begin_tracking", side_effect=RuntimeError("db down")), \
                mock.patch.object(service, "bind_events", side_effect=RuntimeError("state down")), \
                mock.patch.object(service, "mark_failure", side_effect=RuntimeError("report down")):
            self.assertIsNone(service.safe_begin_tracking(client="codex"))
            self.assertIsNone(service.safe_bind_events({}, [], []))
            self.assertIsNone(service.safe_mark_failure({}, reason="failed"))
