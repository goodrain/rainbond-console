from unittest import TestCase

from console.utils.cnb_build import normalize_source_build_config


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
        self.assertEqual(envs["BUILD_TYPE"], "cnb")
        self.assertEqual(envs["BUILD_RUNTIMES"], "3.11")
        self.assertEqual(envs["BUILD_PIP_INDEX_URL"], "https://pypi.tuna.tsinghua.edu.cn/simple")

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
        self.assertEqual(envs["BUILD_TYPE"], "cnb")
        self.assertEqual(envs["CNB_FRAMEWORK"], "nextjs")
        self.assertEqual(envs["CNB_BUILD_SCRIPT"], "build")
        self.assertEqual(envs["CNB_OUTPUT_DIR"], ".next")
        self.assertEqual(envs["CNB_NODE_VERSION"], "24.13.0")
        self.assertEqual(envs["CNB_START_SCRIPT"], "start")
        self.assertEqual(envs["CNB_PACKAGE_TOOL"], "pnpm")

