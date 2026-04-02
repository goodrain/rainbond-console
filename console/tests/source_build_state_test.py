from unittest import TestCase

from console.utils.source_build_state import (build_compile_env_payload, normalize_detected_languages,
                                              pick_preferred_language, read_compile_env_state,
                                              restore_language_snapshot)


class SourceBuildStateTests(TestCase):
    def test_normalize_detected_languages_moves_dockerfile_after_non_dockerfile(self):
        self.assertEqual(normalize_detected_languages("dockerfile,Java-maven"), "Java-maven,dockerfile")
        self.assertEqual(normalize_detected_languages("dockerfile, Python"), "Python,dockerfile")

    def test_normalize_detected_languages_keeps_non_dockerfile_relative_order(self):
        self.assertEqual(normalize_detected_languages("dockerfile,Python,Go"), "Python,Go,dockerfile")

    def test_pick_preferred_language_prefers_non_dockerfile_candidate(self):
        self.assertEqual(pick_preferred_language("dockerfile,Java-maven"), "Java-maven")
        self.assertEqual(pick_preferred_language("dockerfile"), "dockerfile")

    def test_restore_language_snapshot_prefers_user_saved_and_backfills_detected_defaults(self):
        state = {
            "detected_defaults": {
                "Java-maven": {
                    "compile_env": {
                        "language": "Java-maven",
                        "runtimes": "1.8",
                        "procfile": "",
                        "dependencies": {}
                    },
                    "build_env_dict": {
                        "BUILD_RUNTIMES": "17",
                        "BUILD_MAVEN_BUILT_MODULE": "service-a",
                    },
                    "build_strategy": "cnb",
                    "cmd": "start web"
                }
            },
            "user_saved": {
                "Java-maven": {
                    "compile_env": {
                        "language": "Java-maven",
                        "runtimes": "21",
                        "procfile": "",
                        "dependencies": {}
                    },
                    "build_env_dict": {
                        "BUILD_RUNTIMES": "21",
                    },
                    "build_strategy": "cnb",
                }
            }
        }

        restored = restore_language_snapshot(
            state,
            "Java-maven",
            fallback_compile_env={
                "language": "Java-maven",
                "runtimes": "1.8",
                "procfile": "",
                "dependencies": {}
            })

        self.assertEqual(restored["compile_env"]["runtimes"], "21")
        self.assertEqual(restored["build_env_dict"]["BUILD_RUNTIMES"], "21")
        self.assertEqual(restored["build_env_dict"]["BUILD_MAVEN_BUILT_MODULE"], "service-a")
        self.assertEqual(restored["build_strategy"], "cnb")
        self.assertEqual(restored["cmd"], "start web")

    def test_build_compile_env_payload_preserves_legacy_fields_and_embeds_state(self):
        payload = build_compile_env_payload(
            {
                "language": "Java-maven",
                "runtimes": "17",
                "procfile": "",
                "dependencies": {}
            },
            {
                "detected_defaults": {
                    "Java-maven": {
                        "build_env_dict": {
                            "BUILD_RUNTIMES": "17"
                        }
                    }
                }
            })

        parsed_compile_env, parsed_state = read_compile_env_state(payload)
        self.assertEqual(parsed_compile_env["language"], "Java-maven")
        self.assertEqual(parsed_compile_env["runtimes"], "17")
        self.assertIn("Java-maven", parsed_state["detected_defaults"])
