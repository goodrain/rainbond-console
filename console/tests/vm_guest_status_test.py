from unittest import TestCase

from console.services.vm_guest_status import normalize_vm_guest_status


# capability_id: console.vm-guest.profile-observation
class VMGuestStatusNormalizationTests(TestCase):
    def test_connected_guest_preserves_boolean_and_whitelisted_os(self):
        result = normalize_vm_guest_status({
            "status": "responding", "reason": "agent_connected", "agent_connected": True,
            "os": {"name": "Ubuntu", "version": "24.04", "kernel_release": "6.8", "users": ["omit"]}
        })
        self.assertIs(result["agent_connected"], True)
        self.assertEqual(result["os"], {"name": "Ubuntu", "version": "24.04", "kernel_release": "6.8"})

    def test_false_is_not_missing_and_stale_os_is_removed(self):
        result = normalize_vm_guest_status({
            "status": "unconfirmed", "reason": "agent_disconnected", "agent_connected": False,
            "os": {"name": "stale"}
        })
        self.assertIs(result["agent_connected"], False)
        self.assertNotIn("os", result)

    def test_missing_backend_and_read_failure_are_distinct(self):
        self.assertEqual(normalize_vm_guest_status(None)["reason"], "backend_unsupported")
        self.assertEqual(normalize_vm_guest_status(None, fallback_reason="read_failed")["reason"], "read_failed")
        self.assertIsNone(normalize_vm_guest_status(None)["agent_connected"])

    def test_missing_agent_condition_does_not_mean_uninstalled(self):
        result = normalize_vm_guest_status({
            "status": "unconfirmed", "reason": "agent_not_reported", "agent_connected": None
        })
        self.assertIsNone(result["agent_connected"])
        self.assertEqual(result["status"], "unconfirmed")

    def test_nonrunning_states_preserve_unknown_agent(self):
        for status, reason in [("powered_off", "vm_stopped"), ("paused", "vm_paused"), ("starting", "vm_starting"),
                               ("unavailable", "instance_not_created"), ("unavailable", "read_failed")]:
            with self.subTest(status=status, reason=reason):
                result = normalize_vm_guest_status({"status": status, "reason": reason, "agent_connected": None})
                self.assertEqual(result["status"], status)
                self.assertIsNone(result["agent_connected"])

    def test_invalid_or_inconsistent_response_never_claims_connected(self):
        invalid = [
            [], "running", {}, {"status": "ready", "agent_connected": True},
            {"status": "responding", "reason": "agent_connected", "agent_connected": "true"},
            {"status": "responding", "reason": "agent_connected", "agent_connected": 1},
            {"status": "responding", "reason": "agent_connected", "agent_connected": False},
            {"status": "paused", "reason": "vm_paused", "agent_connected": True},
            {"status": "unconfirmed", "reason": "agent_connected", "agent_connected": False},
        ]
        for payload in invalid:
            with self.subTest(payload=payload):
                result = normalize_vm_guest_status(payload)
                self.assertEqual(result["reason"], "invalid_response")
                self.assertEqual(result["status"], "unavailable")
                self.assertIsNone(result["agent_connected"])
