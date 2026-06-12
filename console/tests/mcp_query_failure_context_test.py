# -*- coding: utf-8 -*-
"""Service-level tests for the get_operation_failure_context MCP tool.

The tool aggregates three independent data sources (failure event, event-log
tail, pod warnings), classifies the failure, and degrades gracefully when any
sub-query fails. These tests mock region_api so no live region is needed.
"""
import os
import sys
from types import ModuleType
from unittest.mock import patch

import django
from django.test import SimpleTestCase

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")
django.setup()

from console.services.mcp_query_service import mcp_query_service


class Obj(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def _team():
    return Obj(tenant_name="team1", tenant_id="tid-1", enterprise_id="eid-1")


def _app():
    return Obj(ID=7, region_name="rg")


def _service():
    return Obj(service_id="svc-1", service_alias="gr1234", service_region="rg",
               tenant_id="tid-1", extend_method="stateless_multiple")


def _resp(status):
    return Obj(status=status)


def _pods_payload(pod_names):
    return {"bean": {"new_pods": [{"pod_name": n, "pod_status": "ABNORMAL"} for n in pod_names], "old_pods": []}}


def _pod_detail_payload(events):
    return {"bean": {"status": {"type_str": "ABNORMAL"}, "events": events}}


class FailureContextHappyPathTests(SimpleTestCase):

    # capability_id: console.mcp.operation-failure-context
    def test_configmap_missing_pod_evidence(self):
        args = {"team_name": "team1", "region_name": "rg", "app_id": "7", "service_id": "svc-1"}
        events_list = [
            {"event_id": "ev-fail", "opt_type": "upgrade", "status": "failure",
             "message": "升级服务失败", "start_time": "s", "end_time": "e"},
        ]
        pod_events = [{"reason": "FailedMount", "count": 12,
                       "message": 'MountVolume.SetUp failed: configmap "app-conf" not found'}]
        with patch.object(mcp_query_service, "_get_team_app_service_context",
                          return_value=(_team(), _app(), _service())):
            with patch("console.services.mcp_query_service.region_api.get_target_events_list",
                       return_value=(_resp(200), {"list": events_list, "number": 1})):
                with patch("console.services.mcp_query_service.region_api.get_events_log",
                           return_value=(_resp(200), {"list": [{"message": "configmap app-conf not found"}]})):
                    with patch("console.services.mcp_query_service.region_api.get_service_pods",
                               return_value=_pods_payload(["pod-a"])):
                        with patch("console.services.mcp_query_service.region_api.pod_detail",
                                   return_value=_pod_detail_payload(pod_events)):
                            result = mcp_query_service.get_operation_failure_context(Obj(nick_name="t"), args)

        self.assertEqual(result["classified_reason"], "config_file_configmap_missing")
        self.assertEqual(result["verification_level"], "pod_evidence")
        self.assertEqual(result["event"]["event_id"], "ev-fail")
        self.assertTrue(result["pod_warnings"])
        self.assertEqual(result["pod_warnings"][0]["reason"], "FailedMount")
        self.assertTrue(result["event_log_tail"])

    # capability_id: console.mcp.operation-failure-context
    def test_explicit_event_id_skips_event_lookup(self):
        args = {"team_name": "team1", "region_name": "rg", "app_id": "7",
                "service_id": "svc-1", "event_id": "given-ev"}
        with patch.object(mcp_query_service, "_get_team_app_service_context",
                          return_value=(_team(), _app(), _service())):
            with patch("console.services.mcp_query_service.region_api.get_target_events_list") as mock_list:
                with patch("console.services.mcp_query_service.region_api.get_events_log",
                           return_value=(_resp(200), {"list": []})):
                    with patch("console.services.mcp_query_service.region_api.get_service_pods",
                               return_value=_pods_payload([])):
                        result = mcp_query_service.get_operation_failure_context(Obj(nick_name="t"), args)
        # event_id explicitly given: the tool short-circuits the events-list
        # query (the caller already knows which event to anchor on) and echoes it.
        mock_list.assert_not_called()
        self.assertEqual(result["event"]["event_id"], "given-ev")

    # capability_id: console.mcp.operation-failure-context
    def test_picks_most_recent_non_success_event(self):
        args = {"team_name": "team1", "region_name": "rg", "app_id": "7", "service_id": "svc-1"}
        events_list = [
            {"event_id": "ev-ok", "opt_type": "start", "status": "success"},
            {"event_id": "ev-bad", "opt_type": "upgrade", "status": "failure", "message": "x"},
            {"event_id": "ev-ok2", "opt_type": "stop", "status": "success"},
        ]
        with patch.object(mcp_query_service, "_get_team_app_service_context",
                          return_value=(_team(), _app(), _service())):
            with patch("console.services.mcp_query_service.region_api.get_target_events_list",
                       return_value=(_resp(200), {"list": events_list, "number": 3})):
                with patch("console.services.mcp_query_service.region_api.get_events_log",
                           return_value=(_resp(200), {"list": []})):
                    with patch("console.services.mcp_query_service.region_api.get_service_pods",
                               return_value=_pods_payload([])):
                        result = mcp_query_service.get_operation_failure_context(Obj(nick_name="t"), args)
        self.assertEqual(result["event"]["event_id"], "ev-bad")


class FailureContextDegradationTests(SimpleTestCase):

    # capability_id: console.mcp.operation-failure-context
    def test_event_only_when_no_pods(self):
        args = {"team_name": "team1", "region_name": "rg", "app_id": "7", "service_id": "svc-1"}
        events_list = [{"event_id": "ev", "opt_type": "upgrade", "status": "failure", "message": "m"}]
        with patch.object(mcp_query_service, "_get_team_app_service_context",
                          return_value=(_team(), _app(), _service())):
            with patch("console.services.mcp_query_service.region_api.get_target_events_list",
                       return_value=(_resp(200), {"list": events_list, "number": 1})):
                with patch("console.services.mcp_query_service.region_api.get_events_log",
                           return_value=(_resp(200), {"list": [{"message": "apply configmap failure"}]})):
                    with patch("console.services.mcp_query_service.region_api.get_service_pods",
                               return_value=_pods_payload([])):
                        result = mcp_query_service.get_operation_failure_context(Obj(nick_name="t"), args)
        self.assertEqual(result["verification_level"], "event_only")
        self.assertEqual(result["pod_warnings"], [])
        # event-log fallback still classifies
        self.assertEqual(result["classified_reason"], "k8s_api_rejected")

    # capability_id: console.mcp.operation-failure-context
    def test_no_evidence_when_all_empty(self):
        args = {"team_name": "team1", "region_name": "rg", "app_id": "7", "service_id": "svc-1"}
        with patch.object(mcp_query_service, "_get_team_app_service_context",
                          return_value=(_team(), _app(), _service())):
            with patch("console.services.mcp_query_service.region_api.get_target_events_list",
                       return_value=(_resp(200), {"list": [], "number": 0})):
                with patch("console.services.mcp_query_service.region_api.get_events_log",
                           return_value=(_resp(200), {"list": []})):
                    with patch("console.services.mcp_query_service.region_api.get_service_pods",
                               return_value=_pods_payload([])):
                        result = mcp_query_service.get_operation_failure_context(Obj(nick_name="t"), args)
        self.assertEqual(result["verification_level"], "no_evidence")
        self.assertEqual(result["classified_reason"], "unknown")

    # capability_id: console.mcp.operation-failure-context
    def test_pod_query_failure_does_not_break_aggregation(self):
        args = {"team_name": "team1", "region_name": "rg", "app_id": "7", "service_id": "svc-1"}
        events_list = [{"event_id": "ev", "opt_type": "upgrade", "status": "failure", "message": "m"}]
        with patch.object(mcp_query_service, "_get_team_app_service_context",
                          return_value=(_team(), _app(), _service())):
            with patch("console.services.mcp_query_service.region_api.get_target_events_list",
                       return_value=(_resp(200), {"list": events_list, "number": 1})):
                with patch("console.services.mcp_query_service.region_api.get_events_log",
                           return_value=(_resp(200), {"list": [{"message": "ImagePullBackOff"}]})):
                    with patch("console.services.mcp_query_service.region_api.get_service_pods",
                               side_effect=Exception("region down")):
                        result = mcp_query_service.get_operation_failure_context(Obj(nick_name="t"), args)
        self.assertEqual(result["pod_warnings"], [])
        self.assertEqual(result["verification_level"], "event_only")
        self.assertEqual(result["event"]["event_id"], "ev")

    # capability_id: console.mcp.operation-failure-context
    def test_event_log_failure_does_not_break_aggregation(self):
        args = {"team_name": "team1", "region_name": "rg", "app_id": "7", "service_id": "svc-1"}
        events_list = [{"event_id": "ev", "opt_type": "upgrade", "status": "failure", "message": "m"}]
        pod_events = [{"reason": "ImagePullBackOff", "message": "Back-off pulling image; ImagePullBackOff"}]
        with patch.object(mcp_query_service, "_get_team_app_service_context",
                          return_value=(_team(), _app(), _service())):
            with patch("console.services.mcp_query_service.region_api.get_target_events_list",
                       return_value=(_resp(200), {"list": events_list, "number": 1})):
                with patch("console.services.mcp_query_service.region_api.get_events_log",
                           side_effect=Exception("log unavailable")):
                    with patch("console.services.mcp_query_service.region_api.get_service_pods",
                               return_value=_pods_payload(["pod-a"])):
                        with patch("console.services.mcp_query_service.region_api.pod_detail",
                                   return_value=_pod_detail_payload(pod_events)):
                            result = mcp_query_service.get_operation_failure_context(Obj(nick_name="t"), args)
        self.assertEqual(result["event_log_tail"], [])
        self.assertEqual(result["classified_reason"], "image_pull_failed")
        self.assertEqual(result["verification_level"], "pod_evidence")


class FailureContextRedactionTests(SimpleTestCase):

    # capability_id: console.mcp.operation-failure-context
    def test_event_log_tail_is_redacted(self):
        args = {"team_name": "team1", "region_name": "rg", "app_id": "7", "service_id": "svc-1"}
        events_list = [{"event_id": "ev", "opt_type": "deploy", "status": "failure", "message": "m"}]
        secret_log = [{"message": "starting with password=hunter2 and token=abc123 ok"}]
        with patch.object(mcp_query_service, "_get_team_app_service_context",
                          return_value=(_team(), _app(), _service())):
            with patch("console.services.mcp_query_service.region_api.get_target_events_list",
                       return_value=(_resp(200), {"list": events_list, "number": 1})):
                with patch("console.services.mcp_query_service.region_api.get_events_log",
                           return_value=(_resp(200), {"list": secret_log})):
                    with patch("console.services.mcp_query_service.region_api.get_service_pods",
                               return_value=_pods_payload([])):
                        result = mcp_query_service.get_operation_failure_context(Obj(nick_name="t"), args)
        joined = " ".join(result["event_log_tail"])
        self.assertNotIn("hunter2", joined)
        self.assertNotIn("abc123", joined)
        self.assertIn("***", joined)

    # capability_id: console.mcp.operation-failure-context
    def test_redaction_handles_quoted_values_and_bearer_tokens(self):
        line = ('cfg secret="multi word value" Authorization: Bearer '
                'eyJhbGciOiJIUzI1NiJ9.payload.sig done')
        redacted = mcp_query_service._redact_failure_line(line)
        self.assertNotIn("multi word value", redacted)
        self.assertNotIn("eyJhbGciOiJIUzI1NiJ9", redacted)
        self.assertIn("***", redacted)
        self.assertIn("done", redacted)

    # capability_id: console.mcp.operation-failure-context
    def test_log_tail_lines_limit_respected(self):
        args = {"team_name": "team1", "region_name": "rg", "app_id": "7",
                "service_id": "svc-1", "log_tail_lines": 3}
        events_list = [{"event_id": "ev", "opt_type": "deploy", "status": "failure", "message": "m"}]
        log = [{"message": "line-%d" % i} for i in range(20)]
        with patch.object(mcp_query_service, "_get_team_app_service_context",
                          return_value=(_team(), _app(), _service())):
            with patch("console.services.mcp_query_service.region_api.get_target_events_list",
                       return_value=(_resp(200), {"list": events_list, "number": 1})):
                with patch("console.services.mcp_query_service.region_api.get_events_log",
                           return_value=(_resp(200), {"list": log})):
                    with patch("console.services.mcp_query_service.region_api.get_service_pods",
                               return_value=_pods_payload([])):
                        result = mcp_query_service.get_operation_failure_context(Obj(nick_name="t"), args)
        self.assertEqual(len(result["event_log_tail"]), 3)
        self.assertEqual(result["event_log_tail"][-1], "line-19")


class FailureContextToolRegistrationTests(SimpleTestCase):

    # capability_id: console.mcp.operation-failure-context
    def test_tool_is_listed_and_dispatchable(self):
        user = Obj(user_id=1, enterprise_id="eid-1", nick_name="u", is_enterprise_admin=False)
        names = [t["name"] for t in mcp_query_service.list_tools(user)]
        self.assertIn("rainbond_get_operation_failure_context", names)
