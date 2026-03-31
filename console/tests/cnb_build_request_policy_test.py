from unittest import TestCase

from console.utils.cnb_build import compose_source_code_info, policy_summary_to_snapshot


class DummyService(object):
    language = "Python"
    server_type = "git"
    cmd = "start web"
    dockerfile = ""


class CNBBuildRequestPolicyTests(TestCase):
    def test_compose_source_code_info_prefers_build_strategy_and_clears_slug_cmd(self):
        policy_snapshot = policy_summary_to_snapshot("Python", {
            "python": {
                "cpython": {
                    "visible_versions": ["3.11"],
                    "allowed_versions": ["3.11"],
                    "default_version": "3.11"
                }
            }
        })

        code_info = compose_source_code_info(
            DummyService(),
            {"BUILD_TYPE": "slug"},
            "cnb",
            policy_snapshot,
            "https://example.com/demo.git",
            "main",
        )

        self.assertEqual(code_info["build_type"], "cnb")
        self.assertEqual(code_info["build_strategy"], "cnb")
        self.assertEqual(code_info["cmd"], "")
        self.assertEqual(code_info["cnb_version_policy"]["languages"]["python"]["lang_key"], "python")

    def test_policy_summary_snapshot_uses_versioned_request_shape(self):
        snapshot = policy_summary_to_snapshot("java-maven", {
            "java": {
                "jdk": {
                    "visible_versions": ["17"],
                    "allowed_versions": ["11", "17"],
                    "default_version": "17"
                }
            }
        })

        self.assertEqual(snapshot, {
            "version": 1,
            "languages": {
                "java": {
                    "lang_key": "openJDK",
                    "visible_versions": ["17"],
                    "allowed_versions": ["11", "17"],
                    "default_version": "17"
                }
            }
        })
