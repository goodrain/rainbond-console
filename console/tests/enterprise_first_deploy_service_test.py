# -*- coding: utf-8 -*-
import collections
import os
import sys
from copy import deepcopy
from types import ModuleType
from unittest import TestCase, mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")
os.environ.setdefault("DISABLE_FIRST_DEPLOY_SWEEPER", "1")

import django  # noqa: E402

django.setup()

from console.services.enterprise_first_deploy_service import EnterpriseFirstDeployService  # noqa: E402


class Obj(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class FirstDeployRepoStub(object):
    def __init__(self, payload):
        self.record = Obj(key="record-key")
        self.payload = deepcopy(payload)
        self.saved_payloads = []

    def get_by_enterprise_id(self, _enterprise_id):
        return self.record

    def update_payload(self, _record, payload):
        self.payload = deepcopy(payload)
        self.saved_payloads.append(deepcopy(payload))
        return self.record

    def get_by_key(self, _key):
        return self.record

    def list_tracking_records(self):
        return [self.record]

    def load_payload(self, _record):
        return deepcopy(self.payload)


class EnterpriseFirstDeployServiceTests(TestCase):
    def setUp(self):
        self.service = EnterpriseFirstDeployService()
        self.service.RUNTIME_OBSERVE_WINDOW = 30
        self.service.READINESS_FINAL_OBSERVE_WINDOW = 90
        self.service.BUILD_FAILURE_LOG_WAIT_WINDOW = 10
        self.service.COMPILE_FAILURE_LOG_WAIT_WINDOW = 10
        self.service.BUILD_FAILURE_LOG_RETRY_INTERVAL = 1
        self.service.report_async = False

    def test_build_payload_seeds_service_ids_for_runtime_watch(self):
        enterprise = Obj(enterprise_alias="demo-enterprise", enterprise_name="demo-enterprise")
        with mock.patch("console.services.enterprise_first_deploy_service.TenantEnterprise.objects.filter") as mock_filter:
            mock_filter.return_value.first.return_value = enterprise
            payload = self.service._build_payload(
                enterprise_id="eid-1",
                tenant_name="demo-team",
                region_name="demo-region",
                deploy_type=self.service.DEPLOY_TYPE_SOURCE_CODE,
                operator="admin",
                source_language="Java",
                service_id="service-1")

        self.assertEqual(payload["service_ids"], ["service-1"])

    def test_begin_tracking_does_not_block_on_pending_report(self):
        self.service.report_async = True
        payload = {
            "enterprise_id": "eid-1",
            "enterprise_name": "demo-enterprise",
            "deploy_type": self.service.DEPLOY_TYPE_SOURCE_CODE,
            "source_language": "Java",
            "status": self.service.STATUS_FAILURE,
            "reported": False,
            "tenant_name": "demo-team",
            "region_name": "demo-region",
            "event_ids": ["event-build-1"],
            "service_ids": ["service-1"],
        }
        repo = FirstDeployRepoStub(payload)

        with mock.patch("console.services.enterprise_first_deploy_service.enterprise_first_deploy_repo", repo), \
                mock.patch.object(self.service, "_start_report_thread", create=True) as mock_start_report, \
                mock.patch("console.services.enterprise_first_deploy_service.requests.post") as mock_post:
            tracker = self.service.begin_tracking(
                enterprise_id="eid-1",
                tenant_name="demo-team",
                region_name="demo-region",
                deploy_type=self.service.DEPLOY_TYPE_SOURCE_CODE,
                operator="admin",
                source_language="Java",
                service_id="service-1")

        self.assertIsNone(tracker)
        mock_start_report.assert_called_once_with("record-key")
        self.assertFalse(mock_post.called)

    def test_sync_record_reports_build_failure_with_redacted_logs(self):
        payload = {
            "enterprise_id": "eid-1",
            "enterprise_name": "demo-enterprise",
            "deploy_type": self.service.DEPLOY_TYPE_SOURCE_CODE,
            "source_language": "Java",
            "status": self.service.STATUS_PENDING,
            "build_status": self.service.STAGE_STATUS_PENDING,
            "runtime_status": self.service.STAGE_STATUS_PENDING,
            "reported": False,
            "tenant_name": "demo-team",
            "region_name": "demo-region",
            "event_ids": ["event-build-1"],
            "service_ids": ["service-1"],
        }
        repo = FirstDeployRepoStub(payload)
        report_response = Obj(status_code=200)

        with mock.patch("console.services.enterprise_first_deploy_service.enterprise_first_deploy_repo", repo), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.get_tenant_events",
                           return_value={"list": [{
                               "event_id": "event-build-1",
                               "service_id": "service-1",
                               "opt_type": "build-service",
                               "status": "failure",
                               "final_status": "complete",
                               "message": "build failed",
                               "reason": "compile error",
                               "start_time": "2026-05-06 10:00:00",
                               "end_time": "2026-05-06 10:03:00",
                           }]}), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.get_events_log",
                           return_value=(Obj(status=200), {"list": [{
                               "time": "2026-05-06 10:02:59",
                               "message": "PASSWORD=plain-text",
                           }]})), \
                mock.patch("console.services.enterprise_first_deploy_service.requests.post",
                           return_value=report_response) as mock_post:
            status = self.service._sync_record(repo.record, payload, "demo-team", "demo-region")

        self.assertEqual(status, self.service.STATUS_FAILURE)
        report_payload = mock_post.call_args[1]["json"]
        self.assertEqual(report_payload["failure_stage"], self.service.FAILURE_STAGE_BUILD)
        self.assertEqual(report_payload["payload_version"], self.service.PAYLOAD_VERSION)
        self.assertEqual(report_payload["failure_reason"], "build failed")
        self.assertEqual(report_payload["failure_events"][0]["event_id"], "event-build-1")
        self.assertEqual(report_payload["failure_logs"][0]["stage"], self.service.FAILURE_STAGE_BUILD)
        self.assertEqual(report_payload["failure_logs"][0]["lines"][0]["message"], "PASSWORD=<redacted>")
        self.assertTrue(repo.payload["reported"])

    def test_sync_record_retries_build_failure_logs_before_reporting(self):
        payload = {
            "enterprise_id": "eid-1",
            "enterprise_name": "demo-enterprise",
            "deploy_type": self.service.DEPLOY_TYPE_SOURCE_CODE,
            "source_language": "Node.js",
            "status": self.service.STATUS_PENDING,
            "build_status": self.service.STAGE_STATUS_PENDING,
            "runtime_status": self.service.STAGE_STATUS_PENDING,
            "reported": False,
            "tenant_name": "demo-team",
            "region_name": "demo-region",
            "event_ids": ["event-build-1"],
            "service_ids": ["service-1"],
        }
        repo = FirstDeployRepoStub(payload)
        report_response = Obj(status_code=200)
        empty_log_response = (Obj(status=200), {"list": []})
        ready_log_response = (Obj(status=200), {"list": [{"time": "2026-05-06 10:02:59", "message": "npm ERR! build failed"}]})

        with mock.patch("console.services.enterprise_first_deploy_service.enterprise_first_deploy_repo", repo), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.get_tenant_events",
                           return_value={"list": [{
                               "event_id": "event-build-1",
                               "service_id": "service-1",
                               "opt_type": "build-service",
                               "status": "failure",
                               "final_status": "complete",
                               "message": "build failed",
                               "reason": "compile error",
                               "start_time": "2026-05-06 10:00:00",
                               "end_time": "2026-05-06 10:03:00",
                           }]}), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.get_events_log",
                           side_effect=[empty_log_response, ready_log_response]) as mock_get_logs, \
                mock.patch("console.services.enterprise_first_deploy_service.time.sleep") as mock_sleep, \
                mock.patch("console.services.enterprise_first_deploy_service.requests.post",
                           return_value=report_response) as mock_post:
            status = self.service._sync_record(repo.record, payload, "demo-team", "demo-region")

        self.assertEqual(status, self.service.STATUS_FAILURE)
        self.assertEqual(mock_get_logs.call_count, 2)
        mock_sleep.assert_called_once_with(self.service.BUILD_FAILURE_LOG_RETRY_INTERVAL)
        report_payload = mock_post.call_args[1]["json"]
        self.assertEqual(report_payload["failure_logs"][0]["lines"][0]["message"], "npm ERR! build failed")

    def test_compile_failure_uses_compile_log_wait_window(self):
        self.service.BUILD_FAILURE_LOG_WAIT_WINDOW = 10
        self.service.COMPILE_FAILURE_LOG_WAIT_WINDOW = 30
        self.service.BUILD_FAILURE_LOG_RETRY_INTERVAL = 5

        compile_attempts = self.service._failure_log_collect_attempts(
            self.service.FAILURE_STAGE_BUILD,
            self.service.FAILURE_CATEGORY_COMPILE_FAILED)
        image_push_attempts = self.service._failure_log_collect_attempts(
            self.service.FAILURE_STAGE_BUILD,
            self.service.FAILURE_CATEGORY_IMAGE_PUSH_FAILED)

        self.assertEqual(compile_attempts, 7)
        self.assertEqual(image_push_attempts, 3)

    def test_sync_record_reports_build_diagnostic_when_event_log_stays_empty(self):
        payload = {
            "enterprise_id": "eid-1",
            "enterprise_name": "demo-enterprise",
            "deploy_type": self.service.DEPLOY_TYPE_SOURCE_CODE,
            "source_language": "Node.js",
            "status": self.service.STATUS_PENDING,
            "build_status": self.service.STAGE_STATUS_PENDING,
            "runtime_status": self.service.STAGE_STATUS_PENDING,
            "reported": False,
            "tenant_name": "demo-team",
            "region_name": "demo-region",
            "event_ids": ["event-build-1"],
            "service_ids": ["service-1"],
        }
        repo = FirstDeployRepoStub(payload)
        report_response = Obj(status_code=200)

        with mock.patch("console.services.enterprise_first_deploy_service.enterprise_first_deploy_repo", repo), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.get_tenant_events",
                           return_value={"list": [{
                               "event_id": "event-build-1",
                               "service_id": "service-1",
                               "opt_type": "build-service",
                               "status": "failure",
                               "final_status": "complete",
                               "message": "编译失败，请查看构建日志",
                               "reason": "",
                               "start_time": "2026-05-06 10:00:00",
                               "end_time": "2026-05-06 10:03:00",
                           }]}), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.get_events_log",
                           return_value=(Obj(status=200), {"list": []})), \
                mock.patch("console.services.enterprise_first_deploy_service.time.sleep"), \
                mock.patch("console.services.enterprise_first_deploy_service.requests.post",
                           return_value=report_response) as mock_post:
            status = self.service._sync_record(repo.record, payload, "demo-team", "demo-region")

        self.assertEqual(status, self.service.STATUS_FAILURE)
        report_payload = mock_post.call_args[1]["json"]
        self.assertEqual(report_payload["failure_category"], "compile_failed")
        self.assertEqual(report_payload["log_collect_status"], "event_log_empty_after_retry")
        self.assertEqual(report_payload["failure_events"][0]["failure_category"], "compile_failed")
        self.assertEqual(report_payload["failure_logs"][0]["source"], "diagnostic_summary")
        self.assertIn("event_log_empty_after_retry", report_payload["failure_logs"][0]["lines"][0]["message"])

    def test_sync_record_reports_build_image_pull_event_details(self):
        payload = {
            "enterprise_id": "eid-1",
            "enterprise_name": "demo-enterprise",
            "deploy_type": self.service.DEPLOY_TYPE_SOURCE_CODE,
            "source_language": "Dockerfile",
            "status": self.service.STATUS_PENDING,
            "build_status": self.service.STAGE_STATUS_PENDING,
            "runtime_status": self.service.STAGE_STATUS_PENDING,
            "reported": False,
            "tenant_name": "demo-team",
            "region_name": "demo-region",
            "event_ids": ["event-build-1"],
            "service_ids": ["service-1"],
        }
        repo = FirstDeployRepoStub(payload)
        report_response = Obj(status_code=200)

        with mock.patch("console.services.enterprise_first_deploy_service.enterprise_first_deploy_repo", repo), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.get_tenant_events",
                           return_value={"list": [{
                               "event_id": "event-build-1",
                               "service_id": "service-1",
                               "opt_type": "build-service",
                               "status": "failure",
                               "final_status": "complete",
                               "message": "拉取镜像失败，请排查镜像是否可以访问: goodrain.me/demo:v1",
                               "reason": "x509: certificate signed by unknown authority",
                           }]}), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.get_events_log",
                           return_value=(Obj(status=200), {"list": []})), \
                mock.patch("console.services.enterprise_first_deploy_service.time.sleep"), \
                mock.patch("console.services.enterprise_first_deploy_service.requests.post",
                           return_value=report_response) as mock_post:
            status = self.service._sync_record(repo.record, payload, "demo-team", "demo-region")

        self.assertEqual(status, self.service.STATUS_FAILURE)
        report_payload = mock_post.call_args[1]["json"]
        self.assertEqual(report_payload["failure_stage"], self.service.FAILURE_STAGE_BUILD)
        self.assertEqual(report_payload["failure_category"], "image_pull_failed")
        self.assertIn("goodrain.me/demo:v1", report_payload["failure_events"][0]["message"])
        self.assertIn("x509", report_payload["failure_events"][0]["reason"])
        self.assertIn("x509", report_payload["failure_logs"][0]["lines"][0]["message"])

    def test_sync_record_reports_build_image_push_failure(self):
        payload = {
            "enterprise_id": "eid-1",
            "enterprise_name": "demo-enterprise",
            "deploy_type": self.service.DEPLOY_TYPE_APP_MARKET,
            "source_language": "",
            "status": self.service.STATUS_PENDING,
            "build_status": self.service.STAGE_STATUS_PENDING,
            "runtime_status": self.service.STAGE_STATUS_PENDING,
            "reported": False,
            "tenant_name": "demo-team",
            "region_name": "demo-region",
            "event_ids": ["event-build-1"],
            "service_ids": ["service-1"],
        }
        repo = FirstDeployRepoStub(payload)
        report_response = Obj(status_code=200)

        with mock.patch("console.services.enterprise_first_deploy_service.enterprise_first_deploy_repo", repo), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.get_tenant_events",
                           return_value={"list": [{
                               "event_id": "event-build-1",
                               "service_id": "service-1",
                               "opt_type": "build-service",
                               "status": "failure",
                               "final_status": "complete",
                               "message": "推送镜像至镜像仓库失败",
                               "reason": "denied: requested access to the resource is denied",
                           }]}), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.get_events_log",
                           return_value=(Obj(status=200), {"list": []})), \
                mock.patch("console.services.enterprise_first_deploy_service.time.sleep"), \
                mock.patch("console.services.enterprise_first_deploy_service.requests.post",
                           return_value=report_response) as mock_post:
            status = self.service._sync_record(repo.record, payload, "demo-team", "demo-region")

        self.assertEqual(status, self.service.STATUS_FAILURE)
        report_payload = mock_post.call_args[1]["json"]
        self.assertEqual(report_payload["failure_stage"], self.service.FAILURE_STAGE_BUILD)
        self.assertEqual(report_payload["failure_category"], "image_push_failed")
        self.assertIn("denied", report_payload["failure_logs"][0]["lines"][0]["message"])

    def test_sync_record_reports_version_info_failure_reason(self):
        payload = {
            "enterprise_id": "eid-1",
            "enterprise_name": "demo-enterprise",
            "deploy_type": self.service.DEPLOY_TYPE_APP_MARKET,
            "source_language": "",
            "status": self.service.STATUS_PENDING,
            "build_status": self.service.STAGE_STATUS_PENDING,
            "runtime_status": self.service.STAGE_STATUS_PENDING,
            "reported": False,
            "tenant_name": "demo-team",
            "region_name": "demo-region",
            "event_ids": ["event-build-1"],
            "service_ids": ["service-1"],
        }
        repo = FirstDeployRepoStub(payload)
        report_response = Obj(status_code=200)

        with mock.patch("console.services.enterprise_first_deploy_service.enterprise_first_deploy_repo", repo), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.get_tenant_events",
                           return_value={"list": [{
                               "event_id": "event-build-1",
                               "service_id": "service-1",
                               "opt_type": "create-app-version",
                               "status": "failure",
                               "final_status": "complete",
                               "message": "应用版本信息异常: helm render failed",
                               "reason": "missing values.yaml",
                           }]}), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.get_events_log",
                           return_value=(Obj(status=200), {"list": []})), \
                mock.patch("console.services.enterprise_first_deploy_service.time.sleep"), \
                mock.patch("console.services.enterprise_first_deploy_service.requests.post",
                           return_value=report_response) as mock_post:
            status = self.service._sync_record(repo.record, payload, "demo-team", "demo-region")

        self.assertEqual(status, self.service.STATUS_FAILURE)
        report_payload = mock_post.call_args[1]["json"]
        self.assertEqual(report_payload["failure_category"], "version_info_failed")
        self.assertEqual(report_payload["failure_reason"], "应用版本信息异常: helm render failed")
        self.assertIn("missing values.yaml", report_payload["failure_events"][0]["reason"])

    def test_sync_record_reports_no_event_id_diagnostic_for_build_failure(self):
        payload = {
            "enterprise_id": "eid-1",
            "enterprise_name": "demo-enterprise",
            "deploy_type": self.service.DEPLOY_TYPE_APP_MARKET,
            "source_language": "",
            "status": self.service.STATUS_PENDING,
            "build_status": self.service.STAGE_STATUS_PENDING,
            "runtime_status": self.service.STAGE_STATUS_PENDING,
            "reported": False,
            "tenant_name": "demo-team",
            "region_name": "demo-region",
            "event_ids": ["event-build-1"],
            "service_ids": ["service-1"],
        }
        repo = FirstDeployRepoStub(payload)
        report_response = Obj(status_code=200)

        with mock.patch("console.services.enterprise_first_deploy_service.enterprise_first_deploy_repo", repo), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.get_tenant_events",
                           return_value={"list": [{
                               "event_id": "",
                               "service_id": "service-1",
                               "opt_type": "",
                               "status": "failure",
                               "final_status": "complete",
                               "message": "",
                               "reason": "",
                               "start_time": "2026-05-06 10:00:00",
                               "end_time": "2026-05-06 10:03:00",
                           }]}), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.get_events_log") as mock_get_logs, \
                mock.patch("console.services.enterprise_first_deploy_service.requests.post",
                           return_value=report_response) as mock_post:
            status = self.service._sync_record(repo.record, payload, "demo-team", "demo-region")

        self.assertEqual(status, self.service.STATUS_FAILURE)
        self.assertFalse(mock_get_logs.called)
        report_payload = mock_post.call_args[1]["json"]
        self.assertEqual(report_payload["failure_category"], "unknown")
        self.assertEqual(report_payload["log_collect_status"], "no_event_id")
        self.assertEqual(report_payload["failure_reason"], "build failure: no failure reason reported")
        self.assertEqual(report_payload["failure_logs"][0]["source"], "diagnostic_summary")
        self.assertIn("build failure: no failure reason reported", report_payload["failure_logs"][0]["lines"][0]["message"])
        self.assertIn("no_event_id", report_payload["failure_logs"][0]["lines"][0]["message"])

    def test_redact_log_message_masks_quoted_and_bare_secrets(self):
        message = 'PASSWORD="plain text" token=abc123 https://user:pass@example.com'

        redacted = self.service._redact_log_message(message)

        self.assertEqual(redacted, 'PASSWORD="<redacted>" token=<redacted> https://<redacted>@example.com')

    def test_sync_record_reports_runtime_failure_without_build_logs(self):
        payload = {
            "enterprise_id": "eid-1",
            "enterprise_name": "demo-enterprise",
            "deploy_type": self.service.DEPLOY_TYPE_IMAGE,
            "source_language": "",
            "status": self.service.STATUS_PENDING,
            "build_status": self.service.STATUS_SUCCESS,
            "build_started_at": "2026-05-06 10:00:00",
            "build_finished_at": "2026-05-06 10:03:00",
            "build_event_id": "deploy-event-1",
            "runtime_status": self.service.STAGE_STATUS_PENDING,
            "reported": False,
            "tenant_name": "demo-team",
            "region_name": "demo-region",
            "event_ids": ["deploy-event-1"],
            "service_ids": ["service-1"],
            "runtime_started_at": "2026-05-06 10:03:00",
            "runtime_watch_started_at": "2026-05-06 10:03:00",
        }
        repo = FirstDeployRepoStub(payload)
        report_response = Obj(status_code=200)

        with mock.patch("console.services.enterprise_first_deploy_service.enterprise_first_deploy_repo", repo), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.get_tenant_events",
                           return_value={"list": [{
                               "event_id": "deploy-event-1",
                               "service_id": "service-1",
                               "opt_type": "start-service",
                               "status": "success",
                               "final_status": "complete",
                               "message": "deploy success",
                               "reason": "",
                               "start_time": "2026-05-06 10:00:00",
                               "end_time": "2026-05-06 10:03:00",
                           }]}), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.get_target_events_list",
                           return_value=(Obj(status=200), {"list": [{
                               "event_id": "event-runtime-1",
                               "service_id": "service-1",
                               "target": "pod",
                               "target_id": "pod-1",
                               "opt_type": "ContainerExitError",
                               "status": "failure",
                               "final_status": "complete",
                               "message": "start service failed",
                               "reason": "pod schedule failed",
                               "start_time": "2026-05-06T10:03:05+08:00",
                               "end_time": "2026-05-06T10:03:06+08:00",
                               "create_time": "2026-05-06T10:03:05+08:00",
                           }]})), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.get_events_log",
                           return_value=(Obj(status=200), {"list": []})) as mock_get_logs, \
                mock.patch("console.services.enterprise_first_deploy_service.requests.post",
                           return_value=report_response) as mock_post:
            status = self.service._sync_record(repo.record, payload, "demo-team", "demo-region")

        self.assertEqual(status, self.service.STATUS_FAILURE)
        report_payload = mock_post.call_args[1]["json"]
        self.assertEqual(report_payload["failure_stage"], self.service.FAILURE_STAGE_RUNTIME)
        self.assertEqual(report_payload["failure_reason"], "start service failed")
        self.assertEqual(report_payload["failure_events"][0]["opt_type"], "ContainerExitError")
        self.assertEqual(report_payload["log_collect_status"], "event_log_empty_after_retry")
        self.assertEqual(report_payload["failure_logs"][0]["source"], "diagnostic_summary")
        self.assertIn("event-runtime-1", report_payload["failure_logs"][0]["lines"][0]["message"])
        self.assertTrue(mock_get_logs.called)

    def test_mark_failure_reports_explicit_reason_without_events(self):
        payload = {
            "enterprise_id": "eid-1",
            "enterprise_name": "demo-enterprise",
            "deploy_type": self.service.DEPLOY_TYPE_APP_MARKET,
            "source_language": "",
            "status": self.service.STATUS_PENDING,
            "build_status": self.service.STAGE_STATUS_PENDING,
            "runtime_status": self.service.STAGE_STATUS_PENDING,
            "reported": False,
            "tenant_name": "demo-team",
            "region_name": "demo-region",
            "event_ids": [],
            "service_ids": ["service-1"],
        }
        repo = FirstDeployRepoStub(payload)
        report_response = Obj(status_code=200)
        tracker = {"enterprise_id": "eid-1"}

        with mock.patch("console.services.enterprise_first_deploy_service.enterprise_first_deploy_repo", repo), \
                mock.patch("console.services.enterprise_first_deploy_service.requests.post",
                           return_value=report_response) as mock_post:
            self.service.mark_failure(
                tracker,
                reason="install request failed",
                failure_stage=self.service.FAILURE_STAGE_UNKNOWN)

        report_payload = mock_post.call_args[1]["json"]
        self.assertEqual(report_payload["failure_stage"], self.service.FAILURE_STAGE_BUILD)
        self.assertEqual(report_payload["failure_reason"], "install request failed")
        self.assertEqual(report_payload["failure_events"], [])
        self.assertEqual(report_payload["failure_category"], "unknown")
        self.assertEqual(report_payload["log_collect_status"], "no_event_id")
        self.assertEqual(report_payload["failure_logs"][0]["source"], "diagnostic_summary")

    def test_sync_record_enters_runtime_observe_window_after_deploy_success(self):
        payload = {
            "enterprise_id": "eid-1",
            "enterprise_name": "demo-enterprise",
            "deploy_type": self.service.DEPLOY_TYPE_IMAGE,
            "source_language": "",
            "status": self.service.STATUS_PENDING,
            "build_status": self.service.STAGE_STATUS_PENDING,
            "runtime_status": self.service.STAGE_STATUS_PENDING,
            "reported": False,
            "tenant_name": "demo-team",
            "region_name": "demo-region",
            "event_ids": ["deploy-event-1"],
        }
        repo = FirstDeployRepoStub(payload)

        with mock.patch("console.services.enterprise_first_deploy_service.enterprise_first_deploy_repo", repo), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.get_tenant_events",
                           return_value={"list": [{
                               "event_id": "deploy-event-1",
                               "service_id": "service-1",
                               "opt_type": "start-service",
                               "status": "success",
                               "final_status": "complete",
                               "message": "deploy success",
                               "reason": "",
                               "start_time": "2026-05-06 10:00:00",
                               "end_time": "2026-05-06 10:03:00",
                           }]}), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.get_target_events_list",
                           return_value=(Obj(status=200), {"list": []})), \
                mock.patch.object(self.service, "_now", return_value="2026-05-06 10:03:00"), \
                mock.patch("console.services.enterprise_first_deploy_service.requests.post") as mock_post:
            status = self.service._sync_record(repo.record, payload, "demo-team", "demo-region")

        self.assertIsNone(status)
        self.assertEqual(repo.payload["runtime_watch_started_at"], "2026-05-06 10:03:00")
        self.assertEqual(repo.payload["service_ids"], ["service-1"])
        self.assertEqual(repo.payload["build_status"], self.service.STATUS_SUCCESS)
        self.assertFalse(mock_post.called)

    def test_sync_record_reports_runtime_failure_after_deploy_event_success(self):
        payload = {
            "enterprise_id": "eid-1",
            "enterprise_name": "demo-enterprise",
            "deploy_type": self.service.DEPLOY_TYPE_IMAGE,
            "source_language": "",
            "status": self.service.STATUS_PENDING,
            "build_status": self.service.STATUS_SUCCESS,
            "build_started_at": "2026-05-06 10:00:00",
            "build_finished_at": "2026-05-06 10:03:00",
            "build_event_id": "deploy-event-1",
            "runtime_status": self.service.STAGE_STATUS_PENDING,
            "reported": False,
            "tenant_name": "demo-team",
            "region_name": "demo-region",
            "event_ids": ["deploy-event-1"],
            "service_ids": ["service-1"],
            "runtime_started_at": "2026-05-06 10:03:00",
            "runtime_watch_started_at": "2026-05-06 10:03:00",
        }
        repo = FirstDeployRepoStub(payload)
        report_response = Obj(status_code=200)

        with mock.patch("console.services.enterprise_first_deploy_service.enterprise_first_deploy_repo", repo), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.get_tenant_events",
                           return_value={"list": [{
                               "event_id": "deploy-event-1",
                               "service_id": "service-1",
                               "opt_type": "start-service",
                               "status": "success",
                               "final_status": "complete",
                               "message": "deploy success",
                               "reason": "",
                               "start_time": "2026-05-06 10:00:00",
                               "end_time": "2026-05-06 10:03:00",
                           }]}), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.get_target_events_list",
                           return_value=(Obj(status=200), {"list": [{
                               "event_id": "runtime-event-1",
                               "service_id": "service-1",
                               "target": "pod",
                               "target_id": "pod-1",
                               "opt_type": "ContainerExitError",
                               "status": "failure",
                               "final_status": "complete",
                               "message": "container startup failed",
                               "reason": "exit code 1",
                               "start_time": "2026-05-06T10:03:05+08:00",
                               "end_time": "2026-05-06T10:03:06+08:00",
                               "create_time": "2026-05-06T10:03:05+08:00",
                           }]})), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.get_events_log",
                           return_value=(Obj(status=200), {"list": [{
                               "time": "2026-05-06 10:03:05",
                               "message": "runtime stack trace line",
                           }]})), \
                mock.patch.object(self.service, "_now", return_value="2026-05-06 10:03:10"), \
                mock.patch("console.services.enterprise_first_deploy_service.requests.post",
                           return_value=report_response) as mock_post:
            status = self.service._sync_record(repo.record, payload, "demo-team", "demo-region")

        self.assertEqual(status, self.service.STATUS_FAILURE)
        report_payload = mock_post.call_args[1]["json"]
        self.assertEqual(report_payload["failure_stage"], self.service.FAILURE_STAGE_RUNTIME)
        self.assertEqual(report_payload["failure_events"][0]["event_id"], "runtime-event-1")
        self.assertEqual(report_payload["failure_logs"][0]["event_id"], "runtime-event-1")
        self.assertEqual(report_payload["failure_logs"][0]["lines"][0]["message"], "runtime stack trace line")

    def test_sync_record_reports_runtime_failure_from_pod_events(self):
        payload = {
            "enterprise_id": "eid-1",
            "enterprise_name": "demo-enterprise",
            "deploy_type": self.service.DEPLOY_TYPE_IMAGE,
            "source_language": "",
            "status": self.service.STATUS_PENDING,
            "build_status": self.service.STATUS_SUCCESS,
            "build_started_at": "2026-05-06 10:00:00",
            "build_finished_at": "2026-05-06 10:03:00",
            "build_event_id": "deploy-event-1",
            "runtime_status": self.service.STAGE_STATUS_PENDING,
            "reported": False,
            "tenant_name": "demo-team",
            "region_name": "demo-region",
            "event_ids": ["deploy-event-1"],
            "service_ids": ["service-1"],
            "service_alias": "demo-service",
            "runtime_started_at": "2026-05-06 10:03:00",
            "runtime_watch_started_at": "2026-05-06 10:03:00",
        }
        repo = FirstDeployRepoStub(payload)
        report_response = Obj(status_code=200)

        with mock.patch("console.services.enterprise_first_deploy_service.enterprise_first_deploy_repo", repo), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.get_tenant_events",
                           return_value={"list": [{
                               "event_id": "deploy-event-1",
                               "service_id": "service-1",
                               "opt_type": "start-service",
                               "status": "success",
                               "final_status": "complete",
                               "message": "deploy success",
                               "reason": "",
                               "start_time": "2026-05-06 10:00:00",
                               "end_time": "2026-05-06 10:03:00",
                           }]}), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.get_service_pods",
                           return_value={"bean": {"new_pods": [{
                               "pod_name": "pod-1",
                               "pod_status": "INITIATING",
                               "container": [{"container_name": "main"}],
                           }], "old_pods": []}}), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.pod_detail",
                           return_value={"bean": {
                               "name": "pod-1",
                               "status": {
                                   "type_str": "ABNORMAL",
                                   "reason": "ContainersNotReady",
                                   "message": "Failed to pull image",
                               },
                               "init_containers": [{
                                   "image": "goodrain.me/default-demo:v1",
                                   "state": "Waiting",
                                   "reason": "ImagePullBackOff",
                               }],
                               "containers": [{
                                   "image": "goodrain.me/default-demo:v1",
                                   "state": "Waiting",
                                   "reason": "ErrImagePull",
                               }],
                               "events": [{
                                   "type": "Warning",
                                   "reason": "Failed",
                                   "message": "lookup goodrain.me on 100.96.0.3:53: no such host",
                               }],
                           }}), \
                mock.patch("console.services.enterprise_first_deploy_service.requests.post",
                           return_value=report_response) as mock_post:
            status = self.service._sync_record(repo.record, payload, "demo-team", "demo-region")

        self.assertEqual(status, self.service.STATUS_FAILURE)
        report_payload = mock_post.call_args[1]["json"]
        self.assertEqual(report_payload["failure_stage"], self.service.FAILURE_STAGE_RUNTIME)
        self.assertEqual(report_payload["failure_events"][0]["opt_type"], "ImagePullBackOff")
        self.assertIn("goodrain.me", report_payload["failure_logs"][0]["lines"][0]["message"])

    def test_sync_record_reports_runtime_pod_failed_event_lines_when_status_is_generic(self):
        payload = {
            "enterprise_id": "eid-1",
            "enterprise_name": "demo-enterprise",
            "deploy_type": self.service.DEPLOY_TYPE_APP_MARKET,
            "source_language": "",
            "status": self.service.STATUS_PENDING,
            "build_status": self.service.STATUS_SUCCESS,
            "build_started_at": "2026-05-06 10:00:00",
            "build_finished_at": "2026-05-06 10:03:00",
            "build_event_id": "deploy-event-1",
            "runtime_status": self.service.STAGE_STATUS_PENDING,
            "reported": False,
            "tenant_name": "demo-team",
            "region_name": "demo-region",
            "event_ids": ["deploy-event-1"],
            "service_ids": ["service-1"],
            "service_alias": "demo-service",
            "runtime_started_at": "2026-05-06 10:03:00",
            "runtime_watch_started_at": "2026-05-06 10:03:00",
        }
        repo = FirstDeployRepoStub(payload)
        report_response = Obj(status_code=200)

        with mock.patch("console.services.enterprise_first_deploy_service.enterprise_first_deploy_repo", repo), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.get_tenant_events",
                           return_value={"list": [{
                               "event_id": "deploy-event-1",
                               "service_id": "service-1",
                               "opt_type": "start-service",
                               "status": "success",
                               "final_status": "complete",
                               "message": "deploy success",
                               "reason": "",
                           }]}), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.get_service_pods",
                           return_value={"bean": {"new_pods": [{
                               "pod_name": "pod-1",
                               "pod_status": "FAILED",
                           }], "old_pods": []}}), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.pod_detail",
                           return_value={"bean": {
                               "name": "pod-1",
                               "status": {"type_str": "FAILED", "reason": "PodFailed", "message": "容器启动失败，请查看日志"},
                               "events": [
                                   {"reason": "Started", "message": "Started container app", "age": "2s ago"},
                                   {"reason": "Killing", "message": "Stopping container app", "age": "1s ago"},
                               ],
                               "containers": [{
                                   "container_name": "app",
                                   "image": "goodrain.me/default-demo:v1",
                                   "state": "Terminated",
                                   "reason": "Error",
                                   "exit_code": 1,
                                   "message": "process exited with status 1",
                               }],
                               "init_containers": [],
                           }}), \
                mock.patch("console.services.enterprise_first_deploy_service.requests.post",
                           return_value=report_response) as mock_post:
            status = self.service._sync_record(repo.record, payload, "demo-team", "demo-region")

        self.assertEqual(status, self.service.STATUS_FAILURE)
        lines = mock_post.call_args[1]["json"]["failure_logs"][0]["lines"]
        messages = [line["message"] for line in lines]
        self.assertTrue(any("Started container app" in message for message in messages))
        self.assertTrue(any("Stopping container app" in message for message in messages))
        self.assertTrue(any("image=goodrain.me/default-demo:v1" in message for message in messages))
        self.assertTrue(any("exit_code=1" in message for message in messages))

    def test_sync_record_marks_runtime_timeout_when_pod_never_reaches_running(self):
        payload = {
            "enterprise_id": "eid-1",
            "enterprise_name": "demo-enterprise",
            "deploy_type": self.service.DEPLOY_TYPE_IMAGE,
            "source_language": "",
            "status": self.service.STATUS_PENDING,
            "build_status": self.service.STATUS_SUCCESS,
            "build_started_at": "2026-05-06 10:00:00",
            "build_finished_at": "2026-05-06 10:03:00",
            "build_event_id": "deploy-event-1",
            "runtime_status": self.service.STAGE_STATUS_PENDING,
            "reported": False,
            "tenant_name": "demo-team",
            "region_name": "demo-region",
            "event_ids": ["deploy-event-1"],
            "service_ids": ["service-1"],
            "service_alias": "demo-service",
            "runtime_started_at": "2026-05-06 10:03:00",
            "runtime_watch_started_at": "2026-05-06 10:03:00",
        }
        repo = FirstDeployRepoStub(payload)
        report_response = Obj(status_code=200)

        with mock.patch("console.services.enterprise_first_deploy_service.enterprise_first_deploy_repo", repo), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.get_tenant_events",
                           return_value={"list": [{
                               "event_id": "deploy-event-1",
                               "service_id": "service-1",
                               "opt_type": "start-service",
                               "status": "success",
                               "final_status": "complete",
                               "message": "deploy success",
                               "reason": "",
                               "start_time": "2026-05-06 10:00:00",
                               "end_time": "2026-05-06 10:03:00",
                           }]}), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.get_service_pods",
                           return_value={"bean": {"new_pods": [{
                               "pod_name": "pod-1",
                               "pod_status": "INITIATING",
                               "container": [{"container_name": "main"}],
                           }], "old_pods": []}}), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.pod_detail",
                           return_value={"bean": {
                               "name": "pod-1",
                               "status": {
                                   "type_str": "INITIATING",
                                   "reason": "PodInitializing",
                                   "message": "pod still initializing",
                               },
                               "events": [],
                           }}), \
                mock.patch.object(self.service, "_now", return_value="2026-05-06 10:03:40"), \
                mock.patch("console.services.enterprise_first_deploy_service.requests.post",
                           return_value=report_response) as mock_post:
            status = self.service._sync_record(repo.record, payload, "demo-team", "demo-region")

        self.assertEqual(status, self.service.STATUS_FAILURE)
        report_payload = mock_post.call_args[1]["json"]
        self.assertEqual(report_payload["failure_stage"], self.service.FAILURE_STAGE_RUNTIME)
        self.assertEqual(report_payload["failure_reason"], "pod still initializing")

    def test_sync_record_includes_pod_events_in_runtime_timeout_failure(self):
        """Non-readiness pod timeout with events includes pod events in failure logs."""
        payload = {
            "enterprise_id": "eid-1",
            "enterprise_name": "demo-enterprise",
            "deploy_type": self.service.DEPLOY_TYPE_SOURCE_CODE,
            "source_language": "Java-maven",
            "status": self.service.STATUS_PENDING,
            "build_status": self.service.STATUS_SUCCESS,
            "build_started_at": "2026-05-06 10:00:00",
            "build_finished_at": "2026-05-06 10:03:00",
            "build_event_id": "deploy-event-1",
            "runtime_status": self.service.STAGE_STATUS_PENDING,
            "reported": False,
            "tenant_name": "demo-team",
            "region_name": "demo-region",
            "event_ids": ["deploy-event-1"],
            "service_ids": ["service-1"],
            "service_alias": "demo-service",
            "runtime_started_at": "2026-05-06 10:03:00",
            "runtime_watch_started_at": "2026-05-06 10:03:00",
        }
        repo = FirstDeployRepoStub(payload)
        report_response = Obj(status_code=200)

        with mock.patch("console.services.enterprise_first_deploy_service.enterprise_first_deploy_repo", repo), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.get_tenant_events",
                           return_value={"list": [{
                               "event_id": "deploy-event-1",
                               "service_id": "service-1",
                               "opt_type": "start-service",
                               "status": "success",
                               "final_status": "complete",
                               "message": "deploy success",
                               "reason": "",
                               "start_time": "2026-05-06 10:00:00",
                               "end_time": "2026-05-06 10:03:00",
                           }]}), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.get_service_pods",
                           return_value={"bean": {"new_pods": [{
                               "pod_name": "pod-1",
                               "pod_status": "INITIATING",
                           }], "old_pods": []}}), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.pod_detail",
                           return_value={"bean": {
                               "name": "pod-1",
                               "status": {
                                   "type_str": "INITIATING",
                                   "reason": "PodInitializing",
                                   "message": "pod still initializing",
                               },
                               "events": [{
                                   "type": "Warning",
                                   "reason": "BackOff",
                                   "message": "Back-off restarting failed container app",
                                   "age": "5s",
                               }],
                           }}), \
                mock.patch.object(self.service, "_now", return_value="2026-05-06 10:03:40"), \
                mock.patch("console.services.enterprise_first_deploy_service.requests.post",
                           return_value=report_response) as mock_post:
            status = self.service._sync_record(repo.record, payload, "demo-team", "demo-region")

        self.assertEqual(status, self.service.STATUS_FAILURE)
        report_payload = mock_post.call_args[1]["json"]
        self.assertEqual(report_payload["failure_stage"], self.service.FAILURE_STAGE_RUNTIME)
        self.assertNotEqual(report_payload["failure_logs"], [])
        self.assertIn("Back-off", report_payload["failure_logs"][0]["lines"][0]["message"])

    def test_sync_record_checks_runtime_even_when_build_event_query_returns_empty(self):
        payload = {
            "enterprise_id": "eid-1",
            "enterprise_name": "demo-enterprise",
            "deploy_type": self.service.DEPLOY_TYPE_IMAGE,
            "source_language": "",
            "status": self.service.STATUS_PENDING,
            "build_status": self.service.STATUS_SUCCESS,
            "build_started_at": "2026-05-06 10:00:00",
            "build_finished_at": "2026-05-06 10:03:00",
            "build_event_id": "deploy-event-1",
            "runtime_status": self.service.STAGE_STATUS_PENDING,
            "reported": False,
            "tenant_name": "demo-team",
            "region_name": "demo-region",
            "event_ids": ["deploy-event-1"],
            "service_ids": ["service-1"],
            "service_alias": "demo-service",
            "runtime_started_at": "2026-05-06 10:03:00",
            "runtime_watch_started_at": "2026-05-06 10:03:00",
        }
        repo = FirstDeployRepoStub(payload)
        report_response = Obj(status_code=200)

        with mock.patch("console.services.enterprise_first_deploy_service.enterprise_first_deploy_repo", repo), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.get_tenant_events",
                           return_value={"list": []}), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.get_service_pods",
                           return_value={"bean": {"new_pods": [{
                               "pod_name": "pod-1",
                               "pod_status": "INITIATING",
                               "container": [{"container_name": "main"}],
                           }], "old_pods": []}}), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.pod_detail",
                           return_value={"bean": {
                               "name": "pod-1",
                               "status": {
                                   "type_str": "ABNORMAL",
                                   "reason": "ContainersNotReady",
                                   "message": "Failed to pull image",
                               },
                               "events": [{
                                   "type": "Warning",
                                   "reason": "Failed",
                                   "message": "lookup goodrain.me on 100.96.0.3:53: no such host",
                               }],
                           }}), \
                mock.patch("console.services.enterprise_first_deploy_service.requests.post",
                           return_value=report_response) as mock_post:
            status = self.service._sync_record(repo.record, payload, "demo-team", "demo-region")

        self.assertEqual(status, self.service.STATUS_FAILURE)
        self.assertIn("goodrain.me", mock_post.call_args[1]["json"]["failure_logs"][0]["lines"][0]["message"])

    def test_poll_until_finished_continues_after_single_runtime_exception(self):
        payload = {
            "enterprise_id": "eid-1",
            "enterprise_name": "demo-enterprise",
            "deploy_type": self.service.DEPLOY_TYPE_IMAGE,
            "source_language": "",
            "status": self.service.STATUS_PENDING,
            "reported": False,
            "event_ids": ["deploy-event-1"],
        }
        repo = FirstDeployRepoStub(payload)

        with mock.patch("console.services.enterprise_first_deploy_service.enterprise_first_deploy_repo", repo), \
                mock.patch.object(self.service, "_sync_record",
                                  side_effect=[RuntimeError("boom"), self.service.STATUS_SUCCESS]) as mock_sync:
            self.service.POLL_INTERVAL = 0
            self.service.POLL_TIMEOUT = 1
            self.service._poll_until_finished("record-key", "demo-team", "demo-region")

        self.assertEqual(mock_sync.call_count, 2)

    def test_resume_pending_trackers_restarts_runtime_polling(self):
        payload = {
            "enterprise_id": "eid-1",
            "tenant_name": "demo-team",
            "region_name": "demo-region",
            "status": self.service.STATUS_PENDING,
            "event_ids": ["deploy-event-1"],
            "runtime_watch_started_at": "2026-05-06 10:03:00",
        }
        repo = FirstDeployRepoStub(payload)

        with mock.patch("console.services.enterprise_first_deploy_service.enterprise_first_deploy_repo", repo), \
                mock.patch.object(self.service, "_start_sync_thread") as mock_start_sync_thread:
            self.service._resume_pending_trackers_once()

        mock_start_sync_thread.assert_called_once_with("record-key", "demo-team", "demo-region")

    def test_readiness_probe_failure_within_observe_window_does_not_immediately_fail(self):
        """ContainersNotReady during observe window should not trigger immediate FAILURE."""
        payload = {
            "enterprise_id": "eid-1",
            "enterprise_name": "demo-enterprise",
            "deploy_type": self.service.DEPLOY_TYPE_APP_MARKET,
            "source_language": "",
            "status": self.service.STATUS_PENDING,
            "build_status": self.service.STATUS_SUCCESS,
            "build_started_at": "2026-05-07 18:18:07",
            "build_finished_at": "2026-05-07 18:18:10",
            "build_event_id": "event-1",
            "runtime_status": self.service.STAGE_STATUS_PENDING,
            "reported": False,
            "tenant_name": "demo-team",
            "region_name": "demo-region",
            "event_ids": ["event-1"],
            "service_ids": ["service-1"],
            "service_alias": "demo-service",
            "service_aliases": [],
            "runtime_started_at": "2026-05-07 18:18:10",
            "runtime_watch_started_at": "2026-05-07 18:18:10",
        }
        repo = FirstDeployRepoStub(payload)

        # _now returns a time still within the 30s observe window
        with mock.patch("console.services.enterprise_first_deploy_service.enterprise_first_deploy_repo", repo), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.get_tenant_events",
                           return_value={"list": [{"event_id": "event-1", "status": "success",
                                                   "opt_type": "start-service", "service_id": "service-1",
                                                   "final_status": "complete", "message": "", "reason": "",
                                                   "start_time": "2026-05-07 18:18:07",
                                                   "end_time": "2026-05-07 18:18:10"}]}), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.get_service_pods",
                           return_value={
                               "bean": {
                                   "new_pods": [{"pod_name": "pod-1", "pod_status": "UNHEALTHY"}],
                                   "old_pods": [],
                               }
                           }), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.pod_detail",
                           return_value={"bean": {
                               "name": "pod-1",
                               "status": {"type_str": "UNHEALTHY", "reason": "ContainersNotReady",
                                          "message": "就绪检查失败，请查看日志或调整健康检查配置"},
                               "events": [{"message": "Readiness probe failed: connection refused", "age": "3s ago"}],
                               "containers": [],
                               "init_containers": [],
                           }}), \
                mock.patch.object(self.service, "_now", return_value="2026-05-07 18:18:17"):
            # Only 7 seconds elapsed — within the 30s observe window
            status = self.service._sync_record(repo.record, payload, "demo-team", "demo-region")

        # Should NOT immediately fail; container is still initializing
        self.assertIsNone(status)

    def test_readiness_probe_failure_after_first_window_waits_for_final_window(self):
        """ContainersNotReady after first observe window should keep polling until final window."""
        payload = {
            "enterprise_id": "eid-1",
            "enterprise_name": "demo-enterprise",
            "deploy_type": self.service.DEPLOY_TYPE_APP_MARKET,
            "source_language": "",
            "status": self.service.STATUS_PENDING,
            "build_status": self.service.STATUS_SUCCESS,
            "build_started_at": "2026-05-07 18:18:07",
            "build_finished_at": "2026-05-07 18:18:10",
            "build_event_id": "event-1",
            "runtime_status": self.service.STAGE_STATUS_PENDING,
            "reported": False,
            "tenant_name": "demo-team",
            "region_name": "demo-region",
            "event_ids": ["event-1"],
            "service_ids": ["service-1"],
            "service_alias": "demo-service",
            "service_aliases": [],
            "runtime_started_at": "2026-05-07 18:18:10",
            "runtime_watch_started_at": "2026-05-07 18:18:10",
            "runtime_failure_reason": "就绪检查失败，请查看日志或调整健康检查配置",
            "runtime_failure_logs": [{"stage": "runtime", "event_id": "pod-1", "source": "pod_event",
                                      "truncated": False, "lines": [{"time": "3s ago", "message": "Readiness probe failed"}]}],
        }
        repo = FirstDeployRepoStub(payload)
        report_response = mock.Mock(status_code=200)

        with mock.patch("console.services.enterprise_first_deploy_service.enterprise_first_deploy_repo", repo), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.get_tenant_events",
                           return_value={"list": [{"event_id": "event-1", "status": "success",
                                                   "opt_type": "start-service", "service_id": "service-1",
                                                   "final_status": "complete", "message": "", "reason": "",
                                                   "start_time": "2026-05-07 18:18:07",
                                                   "end_time": "2026-05-07 18:18:10"}]}), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.get_service_pods",
                           return_value={
                               "bean": {
                                   "new_pods": [{"pod_name": "pod-1", "pod_status": "UNHEALTHY"}],
                                   "old_pods": [],
                               }
                           }), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.pod_detail",
                           return_value={"bean": {
                               "name": "pod-1",
                               "status": {"type_str": "UNHEALTHY", "reason": "ContainersNotReady",
                                          "message": "就绪检查失败，请查看日志或调整健康检查配置"},
                               "events": [{"message": "Readiness probe failed: connection refused", "age": "35s ago"}],
                               "containers": [],
                               "init_containers": [],
                           }}), \
                mock.patch.object(self.service, "_now", return_value="2026-05-07 18:18:45"), \
                mock.patch("console.services.enterprise_first_deploy_service.requests.post",
                           return_value=report_response) as mock_post:
            # 35 seconds elapsed — past the first observe window but before final failure window
            status = self.service._sync_record(repo.record, payload, "demo-team", "demo-region")

        self.assertIsNone(status)
        self.assertFalse(mock_post.called)

    def test_readiness_probe_failure_after_final_window_reports_failure(self):
        """ContainersNotReady after final readiness window should report FAILURE."""
        payload = {
            "enterprise_id": "eid-1",
            "enterprise_name": "demo-enterprise",
            "deploy_type": self.service.DEPLOY_TYPE_APP_MARKET,
            "source_language": "",
            "status": self.service.STATUS_PENDING,
            "build_status": self.service.STATUS_SUCCESS,
            "build_started_at": "2026-05-07 18:18:07",
            "build_finished_at": "2026-05-07 18:18:10",
            "build_event_id": "event-1",
            "runtime_status": self.service.STAGE_STATUS_PENDING,
            "reported": False,
            "tenant_name": "demo-team",
            "region_name": "demo-region",
            "event_ids": ["event-1"],
            "service_ids": ["service-1"],
            "service_alias": "demo-service",
            "service_aliases": [],
            "runtime_started_at": "2026-05-07 18:18:10",
            "runtime_watch_started_at": "2026-05-07 18:18:10",
            "runtime_failure_reason": "就绪检查失败，请查看日志或调整健康检查配置",
            "runtime_failure_logs": [{"stage": "runtime", "event_id": "pod-1", "source": "pod_event",
                                      "truncated": False, "lines": [{"time": "60s ago", "message": "Readiness probe failed"}]}],
        }
        repo = FirstDeployRepoStub(payload)
        report_response = mock.Mock(status_code=200)

        with mock.patch("console.services.enterprise_first_deploy_service.enterprise_first_deploy_repo", repo), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.get_tenant_events",
                           return_value={"list": [{"event_id": "event-1", "status": "success",
                                                   "opt_type": "start-service", "service_id": "service-1",
                                                   "final_status": "complete", "message": "", "reason": "",
                                                   "start_time": "2026-05-07 18:18:07",
                                                   "end_time": "2026-05-07 18:18:10"}]}), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.get_service_pods",
                           return_value={
                               "bean": {
                                   "new_pods": [{"pod_name": "pod-1", "pod_status": "UNHEALTHY"}],
                                   "old_pods": [],
                               }
                           }), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.pod_detail",
                           return_value={"bean": {
                               "name": "pod-1",
                               "status": {"type_str": "UNHEALTHY", "reason": "ContainersNotReady",
                                          "message": "就绪检查失败，请查看日志或调整健康检查配置"},
                               "events": [{"message": "Readiness probe failed: connection refused", "age": "95s ago"}],
                               "containers": [],
                               "init_containers": [],
                           }}), \
                mock.patch.object(self.service, "_now", return_value="2026-05-07 18:19:45"), \
                mock.patch("console.services.enterprise_first_deploy_service.requests.post",
                           return_value=report_response) as mock_post:
            # 95 seconds elapsed — past final failure window
            status = self.service._sync_record(repo.record, payload, "demo-team", "demo-region")

        self.assertEqual(status, self.service.STATUS_FAILURE)
        report_payload = mock_post.call_args[1]["json"]
        self.assertEqual(report_payload["failure_stage"], self.service.FAILURE_STAGE_RUNTIME)
        self.assertIn("就绪检查", report_payload["failure_reason"])

    def test_runtime_timeout_reports_diagnostic_snapshot_when_no_pods_observed(self):
        payload = {
            "enterprise_id": "eid-1",
            "enterprise_name": "demo-enterprise",
            "deploy_type": self.service.DEPLOY_TYPE_APP_MARKET,
            "source_language": "",
            "status": self.service.STATUS_PENDING,
            "build_status": self.service.STATUS_SUCCESS,
            "build_started_at": "2026-05-07 18:18:07",
            "build_finished_at": "2026-05-07 18:18:10",
            "build_event_id": "event-1",
            "runtime_status": self.service.STAGE_STATUS_PENDING,
            "reported": False,
            "tenant_name": "demo-team",
            "region_name": "demo-region",
            "event_ids": ["event-1"],
            "service_ids": ["service-1"],
            "service_alias": "demo-service",
            "service_aliases": [],
            "runtime_started_at": "2026-05-07 18:18:10",
            "runtime_watch_started_at": "2026-05-07 18:18:10",
        }
        repo = FirstDeployRepoStub(payload)
        report_response = Obj(status_code=200)

        with mock.patch("console.services.enterprise_first_deploy_service.enterprise_first_deploy_repo", repo), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.get_tenant_events",
                           return_value={"list": [{"event_id": "event-1", "status": "success",
                                                   "opt_type": "start-service", "service_id": "service-1",
                                                   "final_status": "complete", "message": "", "reason": "",
                                                   "start_time": "2026-05-07 18:18:07",
                                                   "end_time": "2026-05-07 18:18:10"}]}), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.get_service_pods",
                           return_value={"bean": {"new_pods": [], "old_pods": []}}), \
                mock.patch.object(self.service, "_now", return_value="2026-05-07 18:19:45"), \
                mock.patch("console.services.enterprise_first_deploy_service.requests.post",
                           return_value=report_response) as mock_post:
            status = self.service._sync_record(repo.record, payload, "demo-team", "demo-region")

        self.assertEqual(status, self.service.STATUS_FAILURE)
        report_payload = mock_post.call_args[1]["json"]
        self.assertEqual(report_payload["failure_reason"], "runtime timeout: no pods observed")
        self.assertEqual(report_payload["failure_events"][0]["opt_type"], "RuntimeVerificationTimeout")
        self.assertEqual(report_payload["failure_logs"][0]["source"], "runtime_snapshot")
        self.assertIn("no pods observed", report_payload["failure_logs"][0]["lines"][0]["message"])

    def test_runtime_timeout_reports_partial_no_pods_for_multi_component_app(self):
        payload = {
            "enterprise_id": "eid-1",
            "enterprise_name": "demo-enterprise",
            "deploy_type": self.service.DEPLOY_TYPE_APP_MARKET,
            "source_language": "",
            "status": self.service.STATUS_PENDING,
            "build_status": self.service.STATUS_SUCCESS,
            "build_started_at": "2026-05-07 18:18:07",
            "build_finished_at": "2026-05-07 18:18:10",
            "build_event_id": "event-1",
            "runtime_status": self.service.STAGE_STATUS_PENDING,
            "reported": False,
            "tenant_name": "demo-team",
            "region_name": "demo-region",
            "event_ids": ["event-1"],
            "service_ids": ["service-a", "service-b"],
            "service_alias": "",
            "service_aliases": ["svc-a", "svc-b"],
            "runtime_started_at": "2026-05-07 18:18:10",
            "runtime_watch_started_at": "2026-05-07 18:18:10",
        }
        repo = FirstDeployRepoStub(payload)
        report_response = Obj(status_code=200)

        def fake_get_service_pods(region_name, tenant_name, service_alias, enterprise_id):
            if service_alias == "svc-a":
                return {"bean": {"new_pods": [{"pod_name": "pod-a-1", "pod_status": "RUNNING"}], "old_pods": []}}
            return {"bean": {"new_pods": [], "old_pods": []}}

        def fake_pod_detail(region_name, tenant_name, service_alias, pod_name):
            return {"bean": {
                "name": pod_name,
                "status": {"type_str": "RUNNING"},
                "events": [],
                "containers": [],
                "init_containers": [],
            }}

        with mock.patch("console.services.enterprise_first_deploy_service.enterprise_first_deploy_repo", repo), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.get_tenant_events",
                           return_value={"list": [{"event_id": "event-1", "status": "success",
                                                   "opt_type": "start-service", "service_id": "service-a",
                                                   "final_status": "complete", "message": "", "reason": "",
                                                   "start_time": "2026-05-07 18:18:07",
                                                   "end_time": "2026-05-07 18:18:10"}]}), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.get_service_pods",
                           side_effect=fake_get_service_pods), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.pod_detail",
                           side_effect=fake_pod_detail), \
                mock.patch.object(self.service, "_now", return_value="2026-05-07 18:19:45"), \
                mock.patch("console.services.enterprise_first_deploy_service.requests.post",
                           return_value=report_response) as mock_post:
            status = self.service._sync_record(repo.record, payload, "demo-team", "demo-region")

        self.assertEqual(status, self.service.STATUS_FAILURE)
        report_payload = mock_post.call_args[1]["json"]
        self.assertEqual(report_payload["failure_reason"], "runtime timeout: some components have no pods observed")
        self.assertIn("svc-b", report_payload["failure_logs"][0]["lines"][1]["message"])

    def test_sync_record_multi_component_app_market_pod_failure(self):
        """Multi-component app_market: service_aliases used, failure in one component triggers FAILURE."""
        payload = {
            "enterprise_id": "eid-1",
            "enterprise_name": "demo-enterprise",
            "deploy_type": self.service.DEPLOY_TYPE_APP_MARKET,
            "source_language": "",
            "status": self.service.STATUS_PENDING,
            "build_status": self.service.STATUS_SUCCESS,
            "build_started_at": "2026-05-06 10:00:00",
            "build_finished_at": "2026-05-06 10:03:00",
            "build_event_id": "deploy-event-1",
            "runtime_status": self.service.STAGE_STATUS_PENDING,
            "reported": False,
            "tenant_name": "demo-team",
            "region_name": "demo-region",
            "event_ids": ["deploy-event-1"],
            "service_ids": ["service-a", "service-b"],
            "service_alias": "",
            "service_aliases": ["svc-a", "svc-b"],
            "runtime_started_at": "2026-05-06 10:03:00",
            "runtime_watch_started_at": "2026-05-06 10:03:00",
        }
        repo = FirstDeployRepoStub(payload)
        report_response = Obj(status_code=200)

        def fake_get_service_pods(region_name, tenant_name, service_alias, enterprise_id):
            # svc-a is running, svc-b has a failing pod
            if service_alias == "svc-a":
                return {"bean": {"new_pods": [{"pod_name": "pod-a-1", "pod_status": "RUNNING"}], "old_pods": []}}
            return {"bean": {"new_pods": [{"pod_name": "pod-b-1", "pod_status": "RUNNING"}], "old_pods": []}}

        def fake_pod_detail(region_name, tenant_name, service_alias, pod_name):
            if service_alias == "svc-a":
                return {"bean": {
                    "name": "pod-a-1",
                    "status": {"type_str": "RUNNING"},
                    "events": [],
                    "containers": [],
                    "init_containers": [],
                }}
            return {"bean": {
                "name": "pod-b-1",
                "status": {"type_str": "RUNNING"},
                "events": [],
                "containers": [{"container_name": "app", "reason": "ImagePullBackOff"}],
                "init_containers": [],
            }}

        with mock.patch("console.services.enterprise_first_deploy_service.enterprise_first_deploy_repo", repo), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.get_tenant_events",
                           return_value={"list": [{
                               "event_id": "deploy-event-1",
                               "service_id": "service-a",
                               "opt_type": "start-service",
                               "status": "success",
                               "final_status": "complete",
                               "message": "",
                               "reason": "",
                               "start_time": "2026-05-06 10:00:00",
                               "end_time": "2026-05-06 10:03:00",
                           }]}), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.get_service_pods",
                           side_effect=fake_get_service_pods), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.pod_detail",
                           side_effect=fake_pod_detail), \
                mock.patch("console.services.enterprise_first_deploy_service.requests.post",
                           return_value=report_response) as mock_post:
            status = self.service._sync_record(repo.record, payload, "demo-team", "demo-region")

        self.assertEqual(status, self.service.STATUS_FAILURE)
        report_payload = mock_post.call_args[1]["json"]
        self.assertEqual(report_payload["failure_stage"], self.service.FAILURE_STAGE_RUNTIME)
        self.assertIn("ImagePullBackOff", report_payload["failure_reason"])
