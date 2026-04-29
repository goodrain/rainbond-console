from unittest import TestCase

from console.utils.cnb_build import (normalize_source_build_config, resolve_build_strategy,
                                     resolve_requested_build_strategy, resolve_lang_update_build_strategy)


class SourceBuildConfigViewTests(TestCase):
    def test_generalized_cnb_payload_defaults_target_language_to_cnb(self):
        strategy, envs = normalize_source_build_config(
            "Python",
            build_env_dict={
                "BUILD_RUNTIMES": "3.11",
                "BUILD_PIP_INDEX_URL": "https://pypi.tuna.tsinghua.edu.cn/simple",
            },
        )

        self.assertEqual(strategy, "cnb")
        self.assertNotIn("BUILD_TYPE", envs)
        self.assertEqual(envs["BUILD_RUNTIMES"], "3.11")
        self.assertEqual(envs["BUILD_PIP_INDEX_URL"], "https://pypi.tuna.tsinghua.edu.cn/simple")

    def test_disable_default_to_cnb_keeps_existing_slug_strategy(self):
        strategy, envs = normalize_source_build_config(
            "Python",
            build_env_dict={
                "BUILD_RUNTIMES": "3.11",
            },
            default_to_cnb=False,
        )

        self.assertEqual(strategy, "")
        self.assertNotIn("BUILD_TYPE", envs)

    def test_node_compatibility_aliases_expand_into_build_env_dict(self):
        strategy, envs = normalize_source_build_config(
            "Node.js",
            package_tool="pnpm",
            compat_payload={
                "cnb_framework": "nextjs",
                "cnb_build_script": "build",
                "cnb_output_dir": ".next",
                "cnb_node_version": "24.13.0",
                "cnb_start_script": "start",
            },
        )

        self.assertEqual(strategy, "cnb")
        self.assertNotIn("BUILD_TYPE", envs)
        self.assertEqual(envs["CNB_FRAMEWORK"], "nextjs")
        self.assertEqual(envs["CNB_BUILD_SCRIPT"], "build")
        self.assertEqual(envs["CNB_OUTPUT_DIR"], ".next")
        self.assertEqual(envs["CNB_NODE_VERSION"], "24.13.0")
        self.assertEqual(envs["CNB_START_SCRIPT"], "start")
        self.assertEqual(envs["CNB_PACKAGE_TOOL"], "pnpm")

    def test_java_payload_preserves_extended_cnb_build_env_keys(self):
        strategy, envs = normalize_source_build_config(
            "java-maven",
            build_strategy="cnb",
            build_env_dict={
                "BUILD_RUNTIMES": "17",
                "BUILD_RUNTIMES_MAVEN": "3.9.14",
                "BUILD_MAVEN_SETTING_NAME": "team-maven",
                "BUILD_GRADLE_BUILD_ARGUMENTS": "build --info",
            },
        )

        self.assertEqual(strategy, "cnb")
        self.assertNotIn("BUILD_TYPE", envs)
        self.assertEqual(envs["BUILD_RUNTIMES_MAVEN"], "3.9.14")
        self.assertEqual(envs["BUILD_MAVEN_SETTING_NAME"], "team-maven")
        self.assertEqual(envs["BUILD_GRADLE_BUILD_ARGUMENTS"], "build --info")

    def test_dotnet_payload_defaults_target_language_to_cnb(self):
        strategy, envs = normalize_source_build_config(
            ".NetCore",
            build_env_dict={
                "BUILD_NO_CACHE": "true",
            },
        )

        self.assertEqual(strategy, "cnb")
        self.assertNotIn("BUILD_TYPE", envs)
        self.assertEqual(envs["BUILD_NO_CACHE"], "true")

    def test_legacy_build_type_can_be_resolved_into_cnb_strategy(self):
        strategy = resolve_build_strategy("", {"BUILD_TYPE": "cnb"})

        self.assertEqual(strategy, "cnb")

    def test_resolve_requested_build_strategy_prefers_current_legacy_cnb_over_payload_shape(self):
        strategy = resolve_requested_build_strategy(
            "",
            {"BUILD_TYPE": "cnb"},
            "",
            {"CNB_FRAMEWORK": "nextjs"}
        )

        self.assertEqual(strategy, "cnb")

    def test_resolve_requested_build_strategy_does_not_infer_cnb_from_payload_without_explicit_marker(self):
        strategy = resolve_requested_build_strategy(
            "",
            {},
            "",
            {"CNB_FRAMEWORK": "nextjs"}
        )

        self.assertEqual(strategy, "")

    def test_lang_update_defaults_supported_languages_to_cnb_when_strategy_is_empty(self):
        strategy = resolve_lang_update_build_strategy("Python", "")

        self.assertEqual(strategy, "cnb")

    def test_lang_update_keeps_explicit_slug_strategy_for_supported_language(self):
        strategy = resolve_lang_update_build_strategy("java-maven", "slug")

        self.assertEqual(strategy, "slug")

    def test_lang_update_defaults_gradle_to_cnb_when_strategy_is_empty(self):
        strategy = resolve_lang_update_build_strategy("gradle", "")

        self.assertEqual(strategy, "cnb")
