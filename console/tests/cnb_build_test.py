# -*- coding: utf8 -*-
"""CNB 构建相关测试"""
from unittest import TestCase

from console.utils.cnb_build import (
    extract_cnb_envs_from_runtime_info,
    has_cnb_build_params,
    is_cnb_language,
    sanitize_build_env_dict_for_language,
)


class CNBLanguageDetectionTestCase(TestCase):
    def test_nodejs_language_is_cnb(self):
        self.assertTrue(is_cnb_language("Node.js"))

    def test_static_language_is_cnb(self):
        self.assertTrue(is_cnb_language("static"))

    def test_java_language_is_not_cnb(self):
        self.assertFalse(is_cnb_language("java-maven"))

    def test_dockerfile_node_language_is_not_cnb(self):
        self.assertFalse(is_cnb_language("dockerfile,Node.js"))


class CNBParamsDetectionTestCase(TestCase):
    def test_node_language_detects_cnb_params(self):
        self.assertTrue(has_cnb_build_params({"CNB_FRAMEWORK": "nextjs"}, "Node.js"))

    def test_non_cnb_language_ignores_stale_cnb_params(self):
        self.assertFalse(has_cnb_build_params({"CNB_FRAMEWORK": "nextjs"}, "java-maven"))

    def test_empty_build_env_dict_has_no_cnb_params(self):
        self.assertFalse(has_cnb_build_params({}, "Node.js"))

    def test_each_supported_cnb_param_is_detected_for_node_language(self):
        cnb_params = [
            "CNB_FRAMEWORK",
            "CNB_BUILD_SCRIPT",
            "CNB_OUTPUT_DIR",
            "CNB_NODE_VERSION",
            "CNB_NODE_ENV",
            "CNB_MIRROR_SOURCE",
            "CNB_MIRROR_NPMRC",
            "CNB_MIRROR_YARNRC",
            "CNB_MIRROR_PNPMRC",
            "CNB_START_SCRIPT",
        ]
        for key in cnb_params:
            with self.subTest(key=key):
                self.assertTrue(has_cnb_build_params({key: "demo-value"}, "Node.js"))


class BuildTypeAutoSetTestCase(TestCase):
    def test_auto_set_build_type_cnb_for_node_language(self):
        build_env_dict = {"CNB_FRAMEWORK": "nextjs"}
        if has_cnb_build_params(build_env_dict, "Node.js") and "BUILD_TYPE" not in build_env_dict:
            build_env_dict["BUILD_TYPE"] = "cnb"
        self.assertEqual(build_env_dict.get("BUILD_TYPE"), "cnb")

    def test_do_not_auto_set_build_type_for_java_language(self):
        build_env_dict = {"CNB_FRAMEWORK": "nextjs"}
        if has_cnb_build_params(build_env_dict, "java-maven") and "BUILD_TYPE" not in build_env_dict:
            build_env_dict["BUILD_TYPE"] = "cnb"
        self.assertNotIn("BUILD_TYPE", build_env_dict)


class BuildEnvSanitizeTestCase(TestCase):
    def test_java_build_envs_strip_stale_cnb_markers(self):
        build_env_dict = sanitize_build_env_dict_for_language({
            "CNB_FRAMEWORK": "nextjs",
            "CNB_NODE_VERSION": "20.20.0",
            "BUILD_TYPE": "cnb",
            "BUILD_RUNTIMES": "17"
        }, "java-maven")
        self.assertNotIn("CNB_FRAMEWORK", build_env_dict)
        self.assertNotIn("CNB_NODE_VERSION", build_env_dict)
        self.assertNotIn("BUILD_TYPE", build_env_dict)
        self.assertEqual(build_env_dict["BUILD_RUNTIMES"], "17")

    def test_java_build_envs_strip_runtime_aliases_used_by_builder(self):
        build_env_dict = sanitize_build_env_dict_for_language({
            "TYPE": "cnb",
            "HAS_NPMRC": "true",
            "HAS_YARNRC": "true",
            "RUNTIMES": "17"
        }, "java-maven")
        self.assertNotIn("TYPE", build_env_dict)
        self.assertNotIn("HAS_NPMRC", build_env_dict)
        self.assertNotIn("HAS_YARNRC", build_env_dict)
        self.assertEqual(build_env_dict["RUNTIMES"], "17")

    def test_non_cnb_languages_strip_stale_cnb_markers(self):
        stale_envs = {
            "CNB_FRAMEWORK": "nextjs",
            "CNB_NODE_VERSION": "20.20.0",
            "CNB_MIRROR_SOURCE": "project",
            "BUILD_TYPE": "cnb",
            "TYPE": "cnb",
            "HAS_NPMRC": "true",
            "HAS_YARNRC": "true",
            "RUNTIMES": "demo"
        }
        languages = [
            "dockerfile",
            "java-maven",
            "java-war",
            "java-jar",
            "Python",
            "PHP",
            "Go",
            ".NetCore"
        ]
        for language in languages:
            with self.subTest(language=language):
                build_env_dict = sanitize_build_env_dict_for_language(stale_envs, language)
                self.assertNotIn("CNB_FRAMEWORK", build_env_dict)
                self.assertNotIn("CNB_NODE_VERSION", build_env_dict)
                self.assertNotIn("CNB_MIRROR_SOURCE", build_env_dict)
                self.assertNotIn("BUILD_TYPE", build_env_dict)
                self.assertNotIn("TYPE", build_env_dict)
                self.assertNotIn("HAS_NPMRC", build_env_dict)
                self.assertNotIn("HAS_YARNRC", build_env_dict)
                self.assertEqual(build_env_dict["RUNTIMES"], "demo")

    def test_node_build_envs_preserve_cnb_markers(self):
        build_env_dict = sanitize_build_env_dict_for_language({
            "CNB_FRAMEWORK": "nextjs",
            "BUILD_TYPE": "cnb"
        }, "Node.js")
        self.assertEqual(build_env_dict["CNB_FRAMEWORK"], "nextjs")
        self.assertEqual(build_env_dict["BUILD_TYPE"], "cnb")

    def test_static_build_envs_preserve_cnb_markers(self):
        build_env_dict = sanitize_build_env_dict_for_language({
            "CNB_FRAMEWORK": "react",
            "CNB_OUTPUT_DIR": "build",
            "BUILD_TYPE": "cnb"
        }, "static")
        self.assertEqual(build_env_dict["CNB_FRAMEWORK"], "react")
        self.assertEqual(build_env_dict["CNB_OUTPUT_DIR"], "build")
        self.assertEqual(build_env_dict["BUILD_TYPE"], "cnb")

    def test_node_build_envs_preserve_common_mirror_fields(self):
        build_env_dict = sanitize_build_env_dict_for_language({
            "CNB_MIRROR_SOURCE": "global",
            "CNB_MIRROR_NPMRC": "registry=https://registry.npmmirror.com",
            "CNB_MIRROR_YARNRC": 'registry "https://registry.npmmirror.com"',
            "CNB_MIRROR_PNPMRC": "registry=https://registry.npmmirror.com",
        }, "Node.js")
        self.assertEqual(build_env_dict["CNB_MIRROR_SOURCE"], "global")
        self.assertIn("CNB_MIRROR_NPMRC", build_env_dict)
        self.assertIn("CNB_MIRROR_YARNRC", build_env_dict)
        self.assertIn("CNB_MIRROR_PNPMRC", build_env_dict)

    def test_node_build_envs_preserve_known_node_versions(self):
        versions = ["18.20.7", "18.20.8", "20.19.6", "20.20.0", "22.21.1", "22.22.0", "24.12.0", "24.13.0"]
        for version in versions:
            with self.subTest(version=version):
                build_env_dict = sanitize_build_env_dict_for_language({
                    "CNB_NODE_VERSION": version
                }, "Node.js")
                self.assertEqual(build_env_dict["CNB_NODE_VERSION"], version)


class RuntimeInfoExtractTestCase(TestCase):
    def test_extract_nodejs_cnb_envs_from_runtime_info(self):
        runtime_info = {
            "language": "nodejs",
            "language_version": "20.20.0",
            "framework": {"name": "nextjs"},
            "build_config": {"output_dir": ".next", "build_command": "build"},
            "package_manager": {"name": "pnpm"},
            "config_files": {"has_npmrc": True, "has_yarnrc": False}
        }
        cnb_envs = extract_cnb_envs_from_runtime_info(runtime_info)
        self.assertEqual(cnb_envs["CNB_FRAMEWORK"], "nextjs")
        self.assertEqual(cnb_envs["CNB_NODE_VERSION"], "20.20.0")
        self.assertEqual(cnb_envs["CNB_OUTPUT_DIR"], ".next")
        self.assertEqual(cnb_envs["CNB_BUILD_SCRIPT"], "build")
        self.assertEqual(cnb_envs["CNB_PACKAGE_TOOL"], "pnpm")
        self.assertEqual(cnb_envs["BUILD_HAS_NPMRC"], "true")
        self.assertEqual(cnb_envs["CNB_MIRROR_SOURCE"], "project")

    def test_java_runtime_info_does_not_generate_cnb_envs(self):
        runtime_info = {
            "language": "java-maven",
            "language_version": "17"
        }
        self.assertEqual(extract_cnb_envs_from_runtime_info(runtime_info), {})

    def test_static_runtime_info_without_framework_has_no_extra_cnb_envs(self):
        runtime_info = {
            "language": "static"
        }
        self.assertEqual(extract_cnb_envs_from_runtime_info(runtime_info), {})

    def test_extract_static_framework_contract(self):
        runtime_info = {
            "language": "static",
            "framework": {"name": "react"},
            "build_config": {"output_dir": "build", "build_command": "build"}
        }
        cnb_envs = extract_cnb_envs_from_runtime_info(runtime_info)
        self.assertEqual(cnb_envs["CNB_FRAMEWORK"], "react")
        self.assertEqual(cnb_envs["CNB_OUTPUT_DIR"], "build")
        self.assertEqual(cnb_envs["CNB_BUILD_SCRIPT"], "build")
        self.assertNotIn("CNB_NODE_VERSION", cnb_envs)

    def test_extract_known_framework_output_dir_examples(self):
        framework_output_dirs = {
            "vue": "dist",
            "react": "build",
            "vite": "dist",
            "nextjs": ".next",
            "nuxt": ".output",
            "gatsby": "public",
            "docusaurus": "build"
        }
        for framework, output_dir in framework_output_dirs.items():
            with self.subTest(framework=framework):
                runtime_info = {
                    "language": "nodejs",
                    "framework": {"name": framework},
                    "build_config": {"output_dir": output_dir}
                }
                cnb_envs = extract_cnb_envs_from_runtime_info(runtime_info)
                self.assertEqual(cnb_envs["CNB_FRAMEWORK"], framework)
                self.assertEqual(cnb_envs["CNB_OUTPUT_DIR"], output_dir)
