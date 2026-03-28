# -*- coding: utf8 -*-
"""CNB 构建相关测试"""
from unittest import TestCase

from console.utils.cnb_build import (
    compose_build_env_response,
    extract_cnb_envs_from_runtime_info,
    has_cnb_build_params,
    is_cnb_language,
    normalize_java_cnb_env_dict_for_response,
    normalize_java_cnb_env_dict_for_save,
    sanitize_build_env_dict_for_language,
    summarize_build_env,
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
    def test_java_build_envs_strip_stale_node_markers_but_keep_build_type(self):
        build_env_dict = sanitize_build_env_dict_for_language({
            "CNB_FRAMEWORK": "nextjs",
            "CNB_NODE_VERSION": "20.20.0",
            "BUILD_TYPE": "cnb",
            "BUILD_RUNTIMES_MAVEN": "3.9.14",
            "BUILD_RUNTIMES": "17"
        }, "java-maven")
        self.assertNotIn("CNB_FRAMEWORK", build_env_dict)
        self.assertNotIn("CNB_NODE_VERSION", build_env_dict)
        self.assertNotIn("BUILD_RUNTIMES_MAVEN", build_env_dict)
        self.assertEqual(build_env_dict["BUILD_TYPE"], "cnb")
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

    def test_legacy_non_cnb_languages_strip_stale_cnb_markers(self):
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
            "Ruby"
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

    def test_generalized_cnb_languages_keep_build_type_while_stripping_node_specific_markers(self):
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
                self.assertEqual(build_env_dict["BUILD_TYPE"], "cnb")
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


class BuildSummaryTestCase(TestCase):
    def test_summarize_java_cnb_env_prefers_bp_contract(self):
        summary = summarize_build_env("java-maven", "cnb", {
            "BP_JVM_VERSION": "21",
            "BP_MAVEN_BUILD_ARGUMENTS": "clean package",
            "BP_MAVEN_ADDITIONAL_BUILD_ARGUMENTS": "-DskipTests",
            "BP_MAVEN_BUILT_MODULE": "service-a",
            "BP_MAVEN_BUILT_ARTIFACT": "service-a/target/app.jar",
            "BP_GRADLE_BUILD_ARGUMENTS": "build",
            "BP_GRADLE_ADDITIONAL_BUILD_ARGUMENTS": "--info",
            "BP_GRADLE_BUILT_MODULE": "service-a",
            "BP_GRADLE_BUILT_ARTIFACT": "service-a/build/libs/app.jar",
            "BP_JAVA_APP_SERVER": "tomcat",
        })

        annotations = summary["yaml_observable"]["annotations"]
        self.assertEqual(annotations["cnb-bp-jvm-version"], "21")
        self.assertEqual(annotations["cnb-bp-maven-build-arguments"], "clean package")
        self.assertEqual(annotations["cnb-bp-maven-additional-build-arguments"], "-DskipTests")
        self.assertEqual(annotations["cnb-bp-maven-built-module"], "service-a")
        self.assertEqual(annotations["cnb-bp-maven-built-artifact"], "service-a/target/app.jar")
        self.assertEqual(annotations["cnb-bp-gradle-build-arguments"], "build")
        self.assertEqual(annotations["cnb-bp-gradle-additional-build-arguments"], "--info")
        self.assertEqual(annotations["cnb-bp-gradle-built-module"], "service-a")
        self.assertEqual(annotations["cnb-bp-gradle-built-artifact"], "service-a/build/libs/app.jar")
        self.assertEqual(annotations["cnb-bp-java-app-server"], "tomcat")

    def test_summarize_java_cnb_env_exposes_extended_annotations(self):
        summary = summarize_build_env("java-maven", "cnb", {
            "BUILD_RUNTIMES": "17",
            "BUILD_MAVEN_CUSTOM_GOALS": "clean package",
            "BUILD_MAVEN_CUSTOM_OPTS": "-DskipTests",
            "BUILD_MAVEN_BUILT_MODULE": "service-a",
            "BUILD_MAVEN_BUILT_ARTIFACT": "service-a/target/app.jar",
            "BUILD_GRADLE_BUILD_ARGUMENTS": "build",
            "BUILD_GRADLE_ADDITIONAL_BUILD_ARGUMENTS": "--info",
        })

        annotations = summary["yaml_observable"]["annotations"]
        self.assertEqual(annotations["cnb-bp-jvm-version"], "17")
        self.assertNotIn("cnb-bp-maven-version", annotations)
        self.assertEqual(annotations["cnb-bp-maven-build-arguments"], "clean package")
        self.assertEqual(annotations["cnb-bp-maven-additional-build-arguments"], "-DskipTests")
        self.assertEqual(annotations["cnb-bp-maven-built-module"], "service-a")
        self.assertEqual(annotations["cnb-bp-maven-built-artifact"], "service-a/target/app.jar")
        self.assertEqual(annotations["cnb-bp-gradle-build-arguments"], "build")
        self.assertEqual(annotations["cnb-bp-gradle-additional-build-arguments"], "--info")

    def test_summarize_python_golang_php_extended_annotations(self):
        python_summary = summarize_build_env("Python", "cnb", {
            "BUILD_RUNTIMES": "3.11",
            "BUILD_CONDA_SOLVER": "libmamba",
            "BUILD_LIVE_RELOAD_ENABLED": "true",
        })
        self.assertEqual(
            python_summary["yaml_observable"]["annotations"]["cnb-bp-conda-solver"], "libmamba")
        self.assertEqual(
            python_summary["yaml_observable"]["annotations"]["cnb-bp-live-reload-enabled"], "true")

        golang_summary = summarize_build_env("Golang", "cnb", {
            "BUILD_GOVERSION": "1.23",
            "BUILD_GO_BUILD_FLAGS": "-trimpath",
            "BUILD_GO_BUILD_LDFLAGS": "-s -w",
            "BUILD_GO_BUILD_IMPORT_PATH": "example.com/app",
            "BUILD_GO_KEEP_FILES": "static/**",
            "BUILD_GO_WORK_USE": "./cmd/api",
        })
        go_annotations = golang_summary["yaml_observable"]["annotations"]
        self.assertEqual(go_annotations["cnb-bp-go-build-flags"], "-trimpath")
        self.assertEqual(go_annotations["cnb-bp-go-build-ldflags"], "-s -w")
        self.assertEqual(go_annotations["cnb-bp-go-build-import-path"], "example.com/app")
        self.assertEqual(go_annotations["cnb-bp-keep-files"], "static/**")
        self.assertEqual(go_annotations["cnb-bp-go-work-use"], "./cmd/api")

        php_summary = summarize_build_env("PHP", "cnb", {
            "BUILD_RUNTIMES": "8.2",
            "BUILD_RUNTIMES_SERVER": "nginx",
            "BUILD_COMPOSER_VERSION": "2.8.1",
            "BUILD_COMPOSER_INSTALL_OPTIONS": "--no-dev",
            "BUILD_COMPOSER_INSTALL_GLOBAL": "true",
            "BUILD_PHP_WEB_DIR": "public",
            "BUILD_PHP_NGINX_ENABLE_HTTPS": "true",
            "BUILD_PHP_ENABLE_HTTPS_REDIRECT": "true",
        })
        php_annotations = php_summary["yaml_observable"]["annotations"]
        self.assertEqual(php_annotations["cnb-bp-composer-version"], "2.8.1")
        self.assertEqual(php_annotations["cnb-bp-composer-install-options"], "--no-dev")
        self.assertEqual(php_annotations["cnb-bp-composer-install-global"], "true")
        self.assertEqual(php_annotations["cnb-bp-php-web-dir"], "public")
        self.assertEqual(php_annotations["cnb-bp-php-nginx-enable-https"], "true")
        self.assertEqual(php_annotations["cnb-bp-php-enable-https-redirect"], "true")


class BuildEnvResponseTestCase(TestCase):
    def test_compose_build_env_response_attaches_cnb_policy_metadata(self):
        bean = compose_build_env_response(
            {"BUILD_RUNTIMES": "17"},
            "cnb",
            {
                "java": {
                    "jdk": {
                        "visible_versions": ["8", "17", "21"],
                        "allowed_versions": ["8", "17", "21"],
                        "default_version": "17"
                    }
                }
            }
        )

        self.assertEqual(bean["BUILD_RUNTIMES"], "17")
        self.assertEqual(bean["build_strategy"], "cnb")
        self.assertEqual(bean["cnb_version_policy"]["java"]["jdk"]["default_version"], "17")

    def test_compose_build_env_response_skips_policy_for_non_cnb(self):
        bean = compose_build_env_response({"BUILD_RUNTIMES": "17"}, "slug", {
            "java": {"jdk": {"default_version": "17"}}
        })

        self.assertEqual(bean["build_strategy"], "slug")
        self.assertNotIn("cnb_version_policy", bean)

    def test_compose_build_env_response_omits_empty_env_values(self):
        bean = compose_build_env_response(
            {
                "BP_JVM_VERSION": "25",
                "BP_JVM_TYPE": "JRE",
                "BP_MAVEN_BUILD_ARGUMENTS": "clean package",
                "BP_MAVEN_ADDITIONAL_BUILD_ARGUMENTS": "",
                "BUILD_MAVEN_JAVA_OPTS": "",
                "BP_MAVEN_BUILT_MODULE": "",
                "BP_MAVEN_BUILT_ARTIFACT": "",
            },
            "cnb",
            {
                "java": {
                    "jdk": {
                        "visible_versions": ["17", "25"],
                        "allowed_versions": ["17", "25"],
                        "default_version": "17"
                    }
                }
            }
        )

        self.assertEqual(bean["BP_JVM_VERSION"], "25")
        self.assertEqual(bean["BP_JVM_TYPE"], "JRE")
        self.assertEqual(bean["BP_MAVEN_BUILD_ARGUMENTS"], "clean package")
        self.assertNotIn("BP_MAVEN_ADDITIONAL_BUILD_ARGUMENTS", bean)
        self.assertNotIn("BUILD_MAVEN_JAVA_OPTS", bean)
        self.assertNotIn("BP_MAVEN_BUILT_MODULE", bean)
        self.assertNotIn("BP_MAVEN_BUILT_ARTIFACT", bean)
        self.assertEqual(bean["build_strategy"], "cnb")
        self.assertIn("cnb_version_policy", bean)


class JavaCNBContractNormalizeTestCase(TestCase):
    def test_response_normalizes_legacy_java_cnb_keys_to_bp_contract(self):
        normalized = normalize_java_cnb_env_dict_for_response(
            {
                "BUILD_RUNTIMES": "17",
                "BUILD_MAVEN_CUSTOM_GOALS": "clean package",
                "BUILD_MAVEN_CUSTOM_OPTS": "-DskipTests",
                "BUILD_GRADLE_BUILD_ARGUMENTS": "build",
                "BUILD_RUNTIMES_SERVER": "tomcat",
                "BUILD_TYPE": "cnb",
                "BUILD_PROCFILE": "web: java -jar app.jar",
            },
            "java-maven",
            "cnb",
        )

        self.assertEqual(normalized["BP_JVM_VERSION"], "17")
        self.assertEqual(normalized["BP_MAVEN_BUILD_ARGUMENTS"], "clean package")
        self.assertEqual(normalized["BP_MAVEN_ADDITIONAL_BUILD_ARGUMENTS"], "-DskipTests")
        self.assertEqual(normalized["BP_GRADLE_BUILD_ARGUMENTS"], "build")
        self.assertEqual(normalized["BP_JAVA_APP_SERVER"], "tomcat")
        self.assertNotIn("BUILD_RUNTIMES", normalized)
        self.assertNotIn("BUILD_MAVEN_CUSTOM_GOALS", normalized)
        self.assertNotIn("BUILD_TYPE", normalized)
        self.assertEqual(normalized["BUILD_PROCFILE"], "web: java -jar app.jar")

    def test_save_normalizes_java_cnb_payload_to_bp_contract(self):
        normalized = normalize_java_cnb_env_dict_for_save(
            {
                "BUILD_RUNTIMES": "17",
                "BUILD_MAVEN_CUSTOM_GOALS": "clean package",
                "BUILD_MAVEN_CUSTOM_OPTS": "-DskipTests",
                "BUILD_MAVEN_BUILT_MODULE": "service-a",
                "BUILD_MAVEN_BUILT_ARTIFACT": "service-a/target/app.jar",
                "BUILD_GRADLE_BUILD_ARGUMENTS": "build",
                "BUILD_GRADLE_ADDITIONAL_BUILD_ARGUMENTS": "--info",
                "BUILD_RUNTIMES_SERVER": "tomcat",
                "BUILD_NO_CACHE": "true",
                "BUILD_TYPE": "cnb",
            },
            "java-maven",
            "cnb",
        )

        self.assertEqual(normalized["BP_JVM_VERSION"], "17")
        self.assertEqual(normalized["BP_MAVEN_BUILD_ARGUMENTS"], "clean package")
        self.assertEqual(normalized["BP_MAVEN_ADDITIONAL_BUILD_ARGUMENTS"], "-DskipTests")
        self.assertEqual(normalized["BP_MAVEN_BUILT_MODULE"], "service-a")
        self.assertEqual(normalized["BP_MAVEN_BUILT_ARTIFACT"], "service-a/target/app.jar")
        self.assertEqual(normalized["BP_GRADLE_BUILD_ARGUMENTS"], "build")
        self.assertEqual(normalized["BP_GRADLE_ADDITIONAL_BUILD_ARGUMENTS"], "--info")
        self.assertEqual(normalized["BP_JAVA_APP_SERVER"], "tomcat")
        self.assertNotIn("BUILD_RUNTIMES", normalized)
        self.assertNotIn("BUILD_MAVEN_CUSTOM_GOALS", normalized)
        self.assertNotIn("BUILD_TYPE", normalized)
        self.assertEqual(normalized["BUILD_NO_CACHE"], "true")

    def test_save_ignores_java_cnb_bp_keys_for_slug_strategy(self):
        normalized = normalize_java_cnb_env_dict_for_save(
            {
                "BP_JVM_VERSION": "21",
                "BP_MAVEN_BUILD_ARGUMENTS": "clean package",
                "BP_JAVA_APP_SERVER": "tomcat",
                "BUILD_RUNTIMES": "17",
                "BUILD_MAVEN_CUSTOM_GOALS": "clean package",
                "BUILD_TYPE": "cnb",
            },
            "java-maven",
            "slug",
        )

        self.assertNotIn("BP_JVM_VERSION", normalized)
        self.assertNotIn("BP_MAVEN_BUILD_ARGUMENTS", normalized)
        self.assertNotIn("BP_JAVA_APP_SERVER", normalized)
        self.assertNotIn("BUILD_TYPE", normalized)
        self.assertEqual(normalized["BUILD_RUNTIMES"], "17")
        self.assertEqual(normalized["BUILD_MAVEN_CUSTOM_GOALS"], "clean package")
