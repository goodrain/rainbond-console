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

    def load_payload(self, _record):
        return deepcopy(self.payload)


class EnterpriseFirstDeployServiceTests(TestCase):
    def setUp(self):
        self.service = EnterpriseFirstDeployService()

    def test_sync_record_reports_build_failure_with_raw_logs(self):
        payload = {
            "enterprise_id": "eid-1",
            "enterprise_name": "demo-enterprise",
            "deploy_type": self.service.DEPLOY_TYPE_SOURCE_CODE,
            "source_language": "Java",
            "status": self.service.STATUS_PENDING,
            "reported": False,
            "tenant_name": "demo-team",
            "region_name": "demo-region",
            "event_ids": ["event-build-1"],
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
        self.assertEqual(report_payload["failure_logs"][0]["lines"][0]["message"], "PASSWORD=plain-text")
        self.assertTrue(repo.payload["reported"])

    def test_sync_record_reports_runtime_failure_without_build_logs(self):
        payload = {
            "enterprise_id": "eid-1",
            "enterprise_name": "demo-enterprise",
            "deploy_type": self.service.DEPLOY_TYPE_IMAGE,
            "source_language": "",
            "status": self.service.STATUS_PENDING,
            "reported": False,
            "tenant_name": "demo-team",
            "region_name": "demo-region",
            "event_ids": ["event-runtime-1"],
        }
        repo = FirstDeployRepoStub(payload)
        report_response = Obj(status_code=200)

        with mock.patch("console.services.enterprise_first_deploy_service.enterprise_first_deploy_repo", repo), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.get_tenant_events",
                           return_value={"list": [{
                               "event_id": "event-runtime-1",
                               "service_id": "service-1",
                               "opt_type": "start-service",
                               "status": "failure",
                               "final_status": "complete",
                               "message": "start service failed",
                               "reason": "pod schedule failed",
                               "start_time": "2026-05-06 10:00:00",
                               "end_time": "2026-05-06 10:03:00",
                           }]}), \
                mock.patch("console.services.enterprise_first_deploy_service.region_api.get_events_log") as mock_get_logs, \
                mock.patch("console.services.enterprise_first_deploy_service.requests.post",
                           return_value=report_response) as mock_post:
            status = self.service._sync_record(repo.record, payload, "demo-team", "demo-region")

        self.assertEqual(status, self.service.STATUS_FAILURE)
        report_payload = mock_post.call_args[1]["json"]
        self.assertEqual(report_payload["failure_stage"], self.service.FAILURE_STAGE_RUNTIME)
        self.assertEqual(report_payload["failure_reason"], "start service failed")
        self.assertEqual(report_payload["failure_events"][0]["opt_type"], "start-service")
        self.assertEqual(report_payload["failure_logs"], [])
        self.assertFalse(mock_get_logs.called)

    def test_mark_failure_reports_explicit_reason_without_events(self):
        payload = {
            "enterprise_id": "eid-1",
            "enterprise_name": "demo-enterprise",
            "deploy_type": self.service.DEPLOY_TYPE_APP_MARKET,
            "source_language": "",
            "status": self.service.STATUS_PENDING,
            "reported": False,
            "tenant_name": "demo-team",
            "region_name": "demo-region",
            "event_ids": [],
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
        self.assertEqual(report_payload["failure_stage"], self.service.FAILURE_STAGE_UNKNOWN)
        self.assertEqual(report_payload["failure_reason"], "install request failed")
        self.assertEqual(report_payload["failure_events"], [])
        self.assertEqual(report_payload["failure_logs"], [])

