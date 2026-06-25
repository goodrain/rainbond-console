# -*- coding: utf-8 -*-
"""Service-level tests for the wait_for_build_completion MCP tool.

Bounded blocking poll: returns immediately on terminal state; on failure
attaches a redacted error_summary + classified_reason; when the (clamped)
timeout elapses without a terminal state, returns status=running so the caller
can resume. time.sleep is patched to a no-op so tests never actually wait.
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
    return Obj(service_id="svc-1", service_alias="gr1234", service_region="rg", tenant_id="tid-1")


def _resp(status):
    return Obj(status=status)


def _events_body(items):
    return (_resp(200), {"list": items})


def _pods_payload(pod_names):
    return {"bean": {"new_pods": [{"pod_name": n, "pod_status": "ABNORMAL"} for n in pod_names], "old_pods": []}}


def _pod_detail_payload(events):
    return {"bean": {"status": {"type_str": "ABNORMAL"}, "events": events}}


class WaitBuildTerminalTests(SimpleTestCase):

    # capability_id: console.mcp.wait-for-build-completion
    def test_success_first_poll_no_sleep(self):
        args = {"team_name": "team1", "region_name": "rg", "app_id": "7",
                "service_id": "svc-1", "event_id": "ev-1"}
        items = [{"event_id": "ev-1", "status": "success", "final_status": "complete",
                  "opt_type": "build"}]
        with patch.object(mcp_query_service, "_get_team_app_service_context",
                          return_value=(_team(), _app(), _service())):
            with patch("console.services.mcp_query_service.region_api.get_target_events_list",
                       return_value=_events_body(items)):
                with patch("console.services.mcp_query_service.time.sleep") as slept:
                    result = mcp_query_service.wait_for_build_completion(Obj(nick_name="t"), args)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["event_id"], "ev-1")
        slept.assert_not_called()

    # capability_id: console.mcp.wait-for-build-completion
    def test_failure_attaches_error_summary_and_reason(self):
        # error_summary comes from the event log tail (build output); the
        # classified_reason comes from pod warnings (ImagePullBackOff is a K8s
        # pod event, not build-log text), matching get_operation_failure_context.
        args = {"team_name": "team1", "region_name": "rg", "app_id": "7",
                "service_id": "svc-1", "event_id": "ev-1"}
        items = [{"event_id": "ev-1", "status": "failure", "final_status": "complete",
                  "opt_type": "build", "message": "build failed"}]
        log = [{"message": "deploy step failed, see pod events"}]
        pod_events = [{"reason": "ImagePullBackOff", "message": "Back-off pulling image foo; ImagePullBackOff"}]
        with patch.object(mcp_query_service, "_get_team_app_service_context",
                          return_value=(_team(), _app(), _service())):
            with patch("console.services.mcp_query_service.region_api.get_target_events_list",
                       return_value=_events_body(items)):
                with patch("console.services.mcp_query_service.region_api.get_events_log",
                           return_value=(_resp(200), {"list": log})):
                    with patch("console.services.mcp_query_service.region_api.get_service_pods",
                               return_value=_pods_payload(["pod-a"])):
                        with patch("console.services.mcp_query_service.region_api.pod_detail",
                                   return_value=_pod_detail_payload(pod_events)):
                            with patch("console.services.mcp_query_service.time.sleep"):
                                result = mcp_query_service.wait_for_build_completion(Obj(nick_name="t"), args)
        self.assertEqual(result["status"], "failure")
        self.assertEqual(result["classified_reason"], "image_pull_failed")
        self.assertTrue(result["error_summary"])

    # capability_id: console.mcp.wait-for-build-completion
    def test_running_then_success_polls_again(self):
        args = {"team_name": "team1", "region_name": "rg", "app_id": "7",
                "service_id": "svc-1", "event_id": "ev-1"}
        running = [{"event_id": "ev-1", "status": "", "final_status": "", "opt_type": "build"}]
        done = [{"event_id": "ev-1", "status": "success", "final_status": "complete", "opt_type": "build"}]
        with patch.object(mcp_query_service, "_get_team_app_service_context",
                          return_value=(_team(), _app(), _service())):
            with patch("console.services.mcp_query_service.region_api.get_target_events_list",
                       side_effect=[_events_body(running), _events_body(done)]):
                with patch("console.services.mcp_query_service.time.sleep") as slept:
                    result = mcp_query_service.wait_for_build_completion(Obj(nick_name="t"), args)
        self.assertEqual(result["status"], "success")
        slept.assert_called_once()

    # capability_id: console.mcp.wait-for-build-completion
    def test_timeout_returns_running_with_event_id(self):
        args = {"team_name": "team1", "region_name": "rg", "app_id": "7",
                "service_id": "svc-1", "event_id": "ev-1", "timeout": 5}
        running = [{"event_id": "ev-1", "status": "", "final_status": "", "opt_type": "build"}]
        # monotonic: start=0, then >=deadline so the loop exits after first check
        with patch.object(mcp_query_service, "_get_team_app_service_context",
                          return_value=(_team(), _app(), _service())):
            with patch("console.services.mcp_query_service.region_api.get_target_events_list",
                       return_value=_events_body(running)):
                with patch("console.services.mcp_query_service.time.sleep"):
                    with patch("console.services.mcp_query_service.time.monotonic",
                               side_effect=[0.0, 100.0, 100.0]):
                        result = mcp_query_service.wait_for_build_completion(Obj(nick_name="t"), args)
        self.assertEqual(result["status"], "running")
        self.assertEqual(result["event_id"], "ev-1")

    # capability_id: console.mcp.wait-for-build-completion
    def test_event_not_found_treated_as_running(self):
        # If the awaited event is absent from the list (scrolled off / not yet
        # recorded), _query_operation_event returns None -> treated as running,
        # and the bounded wait eventually returns status='running' (not a crash).
        args = {"team_name": "team1", "region_name": "rg", "app_id": "7",
                "service_id": "svc-1", "event_id": "ev-missing", "timeout": 5}
        others = [{"event_id": "ev-other", "status": "success", "final_status": "complete"}]
        with patch.object(mcp_query_service, "_get_team_app_service_context",
                          return_value=(_team(), _app(), _service())):
            with patch("console.services.mcp_query_service.region_api.get_target_events_list",
                       return_value=_events_body(others)):
                with patch("console.services.mcp_query_service.time.sleep"):
                    with patch("console.services.mcp_query_service.time.monotonic",
                               side_effect=[0.0, 100.0, 100.0]):
                        result = mcp_query_service.wait_for_build_completion(Obj(nick_name="t"), args)
        self.assertEqual(result["status"], "running")
        self.assertEqual(result["event_id"], "ev-missing")
        self.assertEqual(result["event_status"], "")

    # capability_id: console.mcp.wait-for-build-completion
    def test_timeout_clamped_to_max(self):
        args = {"team_name": "team1", "region_name": "rg", "app_id": "7",
                "service_id": "svc-1", "event_id": "ev-1", "timeout": 99999}
        done = [{"event_id": "ev-1", "status": "success", "final_status": "complete", "opt_type": "build"}]
        with patch.object(mcp_query_service, "_get_team_app_service_context",
                          return_value=(_team(), _app(), _service())):
            with patch("console.services.mcp_query_service.region_api.get_target_events_list",
                       return_value=_events_body(done)):
                with patch("console.services.mcp_query_service.time.sleep"):
                    result = mcp_query_service.wait_for_build_completion(Obj(nick_name="t"), args)
        # success regardless; the assertion here is that an absurd timeout does
        # not blow up (clamp applied internally).
        self.assertEqual(result["status"], "success")
        self.assertLessEqual(result["timeout"], mcp_query_service.WAIT_BUILD_MAX_TIMEOUT)


class WaitBuildRegistrationTests(SimpleTestCase):
    # capability_id: console.mcp.wait-for-build-completion
    def test_tool_is_listed_and_dispatchable(self):
        user = Obj(user_id=1, enterprise_id="eid-1", nick_name="u", is_enterprise_admin=False)
        names = [t["name"] for t in mcp_query_service.list_tools(user)]
        self.assertIn("rainbond_wait_for_build_completion", names)
