# -*- coding: utf-8 -*-
import copy
import os
from unittest import TestCase, mock

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.test_settings")

import django  # noqa: E402

django.setup()

from console.services.enterprise_services import EnterpriseServices  # noqa: E402

# capability_id: console.enterprise.component-health-upgrade-compatibility


class EnterpriseComponentHealthTest(TestCase):
    def setUp(self):
        self.service = EnterpriseServices()
        self.client = mock.Mock()

    def pod(self, name, phase, owner_kind=None, controller=True):
        metadata = {"name": name, "creationTimestamp": "2026-11-24T00:00:00Z"}
        if owner_kind is not None:
            metadata["ownerReferences"] = [{"kind": owner_kind, "name": "owner", "controller": controller}]
        return {
            "metadata": metadata,
            "status": {
                "phase": phase,
                "podIP": "192.0.2.1",
                "containerStatuses": [{
                    "restartCount": 3,
                    "state": {"running": {}} if phase == "Running" else {"terminated": {}},
                }],
            },
        }

    def normalize(self, component):
        original = copy.deepcopy(component)
        self.client.get_rainbond_components.return_value = ({"status": 200}, {"list": [component]})
        result = self.service.get_rbdcomponents(
            "region-a", connect_timeout=2, timeout=3, retries=0, region_api_client=self.client)
        self.client.get_rainbond_components.assert_called_with("region-a", connect_timeout=2, timeout=3, retries=0)
        self.assertEqual(original, component)
        self.assertEqual(1, len(result))
        return result[0]

    def test_current_ready_replica_ignores_terminal_history_without_losing_pod_details(self):
        component = {
            "name": "rbd-gateway", "run_pods": 1, "all_pods": 2,
            "replica_status": {"ready": 1, "total": 1},
            "pods": [self.pod("old", "Succeeded", "ReplicaSet"), self.pod("current", "Running", "ReplicaSet")],
        }

        result = self.normalize(component)

        self.assertEqual({
            "name": "rbd-gateway", "run_pods": 1, "all_pods": 1, "status": "Running",
            "pods": [{
                "pod_name": "old", "create_time": "2026-11-24T00:00:00Z", "status": "Succeeded",
                "pod_ip": "192.0.2.1", "all_container": 1, "run_container": 0, "restart_count": 3,
            }, {
                "pod_name": "current", "create_time": "2026-11-24T00:00:00Z", "status": "Running",
                "pod_ip": "192.0.2.1", "all_container": 1, "run_container": 1, "restart_count": 3,
            }],
        }, result)

    def test_missing_desired_replica_remains_abnormal(self):
        result = self.normalize({
            "run_pods": 1, "all_pods": 2, "replica_status": {"ready": 1, "total": 2},
            "pods": [self.pod("old", "Succeeded", "ReplicaSet"), self.pod("current", "Running", "ReplicaSet")],
        })
        self.assertEqual((1, 2, "Abnormal"), (result["run_pods"], result["all_pods"], result["status"]))

    def test_optional_replica_status_rejects_malformed_values_and_keeps_raw_counts(self):
        malformed = [
            None, False, True, [], "1/1", 1, {}, {"ready": 1}, {"total": 1},
            {"ready": True, "total": 1}, {"ready": 1, "total": True},
            {"ready": False, "total": 1}, {"ready": 0, "total": False},
            {"ready": "1", "total": 1}, {"ready": 1, "total": "1"},
            {"ready": 1.0, "total": 1}, {"ready": 1, "total": 1.0},
            {"ready": None, "total": 1}, {"ready": 1, "total": None},
            {"ready": -1, "total": 1}, {"ready": 0, "total": -1},
            {"ready": 0, "total": 0}, {"ready": 2, "total": 1},
        ]
        for status in malformed:
            with self.subTest(replica_status=status):
                result = self.normalize({
                    "run_pods": 1, "all_pods": 2, "replica_status": status,
                    "pods": [self.pod("current", "Running", "ReplicaSet")],
                })
                self.assertEqual((1, 2, "Abnormal"), (result["run_pods"], result["all_pods"], result["status"]))

    def test_absent_optional_status_keeps_old_go_counts(self):
        for ready, total, expected in [(1, 2, "Abnormal"), (2, 2, "Running"), (0, 0, "Abnormal")]:
            with self.subTest(ready=ready, total=total):
                result = self.normalize({"run_pods": ready, "all_pods": total, "pods": []})
                self.assertEqual((ready, total, expected), (result["run_pods"], result["all_pods"], result["status"]))

    def test_legacy_caller_uses_default_client_without_timeout_overrides(self):
        component = {"run_pods": 1, "all_pods": 1, "pods": [self.pod("ready", "Running", "ReplicaSet")]}
        with mock.patch("console.services.enterprise_services.region_api.get_rainbond_components",
                        return_value=({"status": 200}, {"list": [component]})) as get:
            result = self.service.get_rbdcomponents("region-a")

        get.assert_called_once_with("region-a")
        self.assertEqual((1, 1, "Running"), (result[0]["run_pods"], result[0]["all_pods"], result[0]["status"]))

    def test_valid_zero_ready_status_remains_abnormal(self):
        result = self.normalize({"run_pods": 1, "all_pods": 2, "replica_status": {"ready": 0, "total": 1}})
        self.assertEqual((0, 1, "Abnormal"), (result["run_pods"], result["all_pods"], result["status"]))

    def test_failed_history_is_retained_with_corrected_replica_status(self):
        result = self.normalize({
            "run_pods": 1, "all_pods": 2, "replica_status": {"ready": 1, "total": 1},
            "pods": [self.pod("failed", "Failed", "ReplicaSet"), self.pod("current", "Running", "ReplicaSet")],
        })
        self.assertEqual("Running", result["status"])
        self.assertEqual(["Failed", "Running"], [pod["status"] for pod in result["pods"]])

    def test_succeeded_long_running_controller_pod_is_not_completed(self):
        for kind in ("ReplicaSet", "Deployment", "StatefulSet", "DaemonSet", "ReplicationController"):
            with self.subTest(kind=kind):
                result = self.normalize({"run_pods": 0, "all_pods": 1, "pods": [self.pod("old", "Succeeded", kind)]})
                self.assertEqual("Abnormal", result["status"])

    def test_succeeded_job_pods_remain_completed(self):
        result = self.normalize({
            "run_pods": 0, "all_pods": 2,
            "pods": [self.pod("job-1", "Succeeded", "Job"), self.pod("job-2", "Succeeded", "Job")],
        })
        self.assertEqual("Completed", result["status"])

    def test_legacy_succeeded_pods_without_controller_remain_completed(self):
        for references in (None, [], [{"kind": "ReplicaSet", "controller": False}], [{"kind": "Deployment"}]):
            with self.subTest(references=references):
                pod = self.pod("legacy-job", "Succeeded")
                pod["metadata"]["ownerReferences"] = references
                result = self.normalize({"run_pods": 0, "all_pods": 1, "pods": [pod]})
                self.assertEqual("Completed", result["status"])

    def test_completed_uses_actual_pods_rather_than_replica_count(self):
        result = self.normalize({"run_pods": 0, "all_pods": 2, "pods": [self.pod("job", "Succeeded", "Job")]})
        self.assertEqual("Completed", result["status"])

    def test_succeeded_job_and_ready_pod_do_not_complete_a_component(self):
        result = self.normalize({
            "run_pods": 1, "all_pods": 1,
            "pods": [self.pod("job", "Succeeded", "Job"), self.pod("ready", "Running", "ReplicaSet")],
        })
        self.assertEqual("Running", result["status"])

    def test_mixed_job_and_workload_succeeded_pods_do_not_complete_a_component(self):
        result = self.normalize({
            "run_pods": 0, "all_pods": 2,
            "pods": [self.pod("job", "Succeeded", "Job"), self.pod("old", "Succeeded", "ReplicaSet")],
        })
        self.assertEqual("Abnormal", result["status"])

    def test_succeeded_and_pending_pods_do_not_complete_a_component(self):
        result = self.normalize({
            "run_pods": 0, "all_pods": 1,
            "pods": [self.pod("job", "Succeeded", "Job"), self.pod("pending", "Pending")],
        })
        self.assertEqual("Abnormal", result["status"])

    def test_empty_or_pending_pods_remain_abnormal(self):
        for pods in (None, [], [{"metadata": {"name": "pending"}, "status": {"phase": "Pending"}}]):
            with self.subTest(pods=pods):
                result = self.normalize({"run_pods": 0, "all_pods": 1 if pods else 0, "pods": pods})
                self.assertEqual("Abnormal", result["status"])
