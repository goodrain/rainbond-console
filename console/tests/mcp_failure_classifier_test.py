# -*- coding: utf-8 -*-
"""Unit tests for the operation-failure classifier.

The classifier is a pure function that maps K8s pod warnings (and, as a
fallback, event-log tail lines) to a stable machine-readable
``classified_reason`` enum. rainagent routes by this enum into the matching
troubleshooter blocker branch instead of blindly retrying a failed operation.
"""
import os
import sys
from types import ModuleType

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

from console.services.mcp_failure_classifier import classify_failure


def _warn(reason, message="", count=1):
    return {"reason": reason, "message": message, "count": count}


def _line(message):
    return {"message": message}


class ClassifyFailureEnumTests(object):
    """One assertion per ``classified_reason`` enum value."""

    # capability_id: console.mcp.operation-failure-classifier
    def test_config_file_configmap_missing(self):
        warnings = [_warn(
            "FailedMount",
            'MountVolume.SetUp failed for volume "config" : configmap "app-conf" not found')]
        assert classify_failure(warnings, []) == "config_file_configmap_missing"

    # capability_id: console.mcp.operation-failure-classifier
    def test_volume_mount_failed_non_configmap(self):
        warnings = [_warn(
            "FailedMount",
            "Unable to attach or mount volumes: timed out waiting for the condition")]
        assert classify_failure(warnings, []) == "volume_mount_failed"

    # capability_id: console.mcp.operation-failure-classifier
    def test_image_pull_failed_backoff(self):
        warnings = [_warn("Failed", "Back-off pulling image; ImagePullBackOff")]
        assert classify_failure(warnings, []) == "image_pull_failed"

    # capability_id: console.mcp.operation-failure-classifier
    def test_image_pull_failed_err_image_pull(self):
        warnings = [_warn("Failed", "rpc error: ErrImagePull: not found")]
        assert classify_failure(warnings, []) == "image_pull_failed"

    # capability_id: console.mcp.operation-failure-classifier
    def test_image_pull_failed_pull_timeout(self):
        warnings = [_warn("Failed", "failed to pull image: pull access timeout")]
        assert classify_failure(warnings, []) == "image_pull_failed"

    # capability_id: console.mcp.operation-failure-classifier
    def test_image_pull_failed_standalone_backoff_pulling(self):
        # K8s emits a standalone reason=Failed / "Back-off pulling image ..."
        # event. The bare "back-off" token must NOT be misread as crash_loop;
        # image_pull outranks crash_loop and the regex now matches it directly.
        warnings = [_warn("Failed", "Back-off pulling image registry/app:latest")]
        assert classify_failure(warnings, []) == "image_pull_failed"

    # capability_id: console.mcp.operation-failure-classifier
    def test_crash_loop(self):
        warnings = [_warn("BackOff", "Back-off restarting failed container; CrashLoopBackOff")]
        assert classify_failure(warnings, []) == "crash_loop"

    # capability_id: console.mcp.operation-failure-classifier
    def test_probe_failed(self):
        warnings = [_warn("Unhealthy", "Readiness probe failed: HTTP probe failed with statuscode: 500")]
        assert classify_failure(warnings, []) == "probe_failed"

    # capability_id: console.mcp.operation-failure-classifier
    def test_unschedulable(self):
        warnings = [_warn("FailedScheduling", "0/3 nodes are available: 3 Insufficient memory")]
        assert classify_failure(warnings, []) == "unschedulable"

    # capability_id: console.mcp.operation-failure-classifier
    def test_k8s_api_rejected_from_event_log(self):
        log_tail = [_line("apply resource configmap failure: admission webhook denied")]
        assert classify_failure([], log_tail) == "k8s_api_rejected"

    # capability_id: console.mcp.operation-failure-classifier
    def test_unknown_when_nothing_matches(self):
        warnings = [_warn("SomethingElse", "a generic message with no signal")]
        assert classify_failure(warnings, [_line("just a log line")]) == "unknown"


class ClassifyFailureBoundaryTests(object):
    """Edge cases: empty / None inputs, casing, priority ordering."""

    # capability_id: console.mcp.operation-failure-classifier
    def test_empty_inputs_return_unknown(self):
        assert classify_failure([], []) == "unknown"

    # capability_id: console.mcp.operation-failure-classifier
    def test_none_inputs_return_unknown(self):
        assert classify_failure(None, None) == "unknown"

    # capability_id: console.mcp.operation-failure-classifier
    def test_case_insensitive_matching(self):
        warnings = [_warn("failedmount", 'CONFIGMAP "x" NOT FOUND')]
        assert classify_failure(warnings, []) == "config_file_configmap_missing"

    # capability_id: console.mcp.operation-failure-classifier
    def test_configmap_missing_wins_over_generic_mount(self):
        # Two warnings; configmap-missing must outrank a plain volume mount failure
        # regardless of list order.
        warnings = [
            _warn("FailedMount", "Unable to attach or mount volumes"),
            _warn("FailedMount", 'configmap "app-conf" not found'),
        ]
        assert classify_failure(warnings, []) == "config_file_configmap_missing"

    # capability_id: console.mcp.operation-failure-classifier
    def test_image_pull_wins_over_crash_loop_when_both_present(self):
        warnings = [
            _warn("BackOff", "CrashLoopBackOff"),
            _warn("Failed", "ImagePullBackOff"),
        ]
        assert classify_failure(warnings, []) == "image_pull_failed"

    # capability_id: console.mcp.operation-failure-classifier
    def test_pod_warning_outranks_event_log(self):
        # pod warning evidence is authoritative; event-log k8s_api_rejected is only
        # a fallback and must not override a concrete pod warning.
        warnings = [_warn("ImagePullBackOff", "ImagePullBackOff")]
        log_tail = [_line("apply configmap failure")]
        assert classify_failure(warnings, log_tail) == "image_pull_failed"

    # capability_id: console.mcp.operation-failure-classifier
    def test_string_log_lines_accepted(self):
        # log_tail may contain bare strings rather than {"message": ...} dicts.
        assert classify_failure([], ["patch deployment failure: forbidden"]) == "k8s_api_rejected"

    # capability_id: console.mcp.operation-failure-classifier
    def test_malformed_warning_entries_are_skipped(self):
        warnings = [None, "garbage", {"no_reason": True}, _warn("ImagePullBackOff", "ImagePullBackOff")]
        assert classify_failure(warnings, []) == "image_pull_failed"
