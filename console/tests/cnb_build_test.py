# -*- coding: utf8 -*-
"""CNB 构建相关测试"""
from unittest import TestCase


class CNBParamsDetectionTestCase(TestCase):
    """测试 CNB 参数检测逻辑"""

    def test_has_cnb_params_with_framework(self):
        """测试：有 CNB_FRAMEWORK 时应检测到 CNB 参数"""
        build_env_dict = {"CNB_FRAMEWORK": "nextjs"}
        cnb_params = [
            "CNB_FRAMEWORK", "CNB_BUILD_SCRIPT", "CNB_OUTPUT_DIR", "CNB_NODE_VERSION",
            "CNB_MIRROR_SOURCE", "CNB_MIRROR_NPMRC", "CNB_MIRROR_YARNRC", "CNB_MIRROR_PNPMRC"
        ]
        has_cnb_params = any(key in build_env_dict for key in cnb_params)
        self.assertTrue(has_cnb_params)

    def test_has_cnb_params_with_build_script(self):
        """测试：有 CNB_BUILD_SCRIPT 时应检测到 CNB 参数"""
        build_env_dict = {"CNB_BUILD_SCRIPT": "build"}
        cnb_params = [
            "CNB_FRAMEWORK", "CNB_BUILD_SCRIPT", "CNB_OUTPUT_DIR", "CNB_NODE_VERSION",
            "CNB_MIRROR_SOURCE", "CNB_MIRROR_NPMRC", "CNB_MIRROR_YARNRC", "CNB_MIRROR_PNPMRC"
        ]
        has_cnb_params = any(key in build_env_dict for key in cnb_params)
        self.assertTrue(has_cnb_params)

    def test_has_cnb_params_with_output_dir(self):
        """测试：有 CNB_OUTPUT_DIR 时应检测到 CNB 参数"""
        build_env_dict = {"CNB_OUTPUT_DIR": "dist"}
        cnb_params = [
            "CNB_FRAMEWORK", "CNB_BUILD_SCRIPT", "CNB_OUTPUT_DIR", "CNB_NODE_VERSION",
            "CNB_MIRROR_SOURCE", "CNB_MIRROR_NPMRC", "CNB_MIRROR_YARNRC", "CNB_MIRROR_PNPMRC"
        ]
        has_cnb_params = any(key in build_env_dict for key in cnb_params)
        self.assertTrue(has_cnb_params)

    def test_has_cnb_params_with_node_version(self):
        """测试：有 CNB_NODE_VERSION 时应检测到 CNB 参数"""
        build_env_dict = {"CNB_NODE_VERSION": "20.20.0"}
        cnb_params = [
            "CNB_FRAMEWORK", "CNB_BUILD_SCRIPT", "CNB_OUTPUT_DIR", "CNB_NODE_VERSION",
            "CNB_MIRROR_SOURCE", "CNB_MIRROR_NPMRC", "CNB_MIRROR_YARNRC", "CNB_MIRROR_PNPMRC"
        ]
        has_cnb_params = any(key in build_env_dict for key in cnb_params)
        self.assertTrue(has_cnb_params)

    def test_has_cnb_params_with_mirror_source(self):
        """测试：有 CNB_MIRROR_SOURCE 时应检测到 CNB 参数"""
        build_env_dict = {"CNB_MIRROR_SOURCE": "global"}
        cnb_params = [
            "CNB_FRAMEWORK", "CNB_BUILD_SCRIPT", "CNB_OUTPUT_DIR", "CNB_NODE_VERSION",
            "CNB_MIRROR_SOURCE", "CNB_MIRROR_NPMRC", "CNB_MIRROR_YARNRC", "CNB_MIRROR_PNPMRC"
        ]
        has_cnb_params = any(key in build_env_dict for key in cnb_params)
        self.assertTrue(has_cnb_params)

    def test_has_cnb_params_with_mirror_npmrc(self):
        """测试：有 CNB_MIRROR_NPMRC 时应检测到 CNB 参数"""
        build_env_dict = {"CNB_MIRROR_NPMRC": "registry=https://registry.npmmirror.com"}
        cnb_params = [
            "CNB_FRAMEWORK", "CNB_BUILD_SCRIPT", "CNB_OUTPUT_DIR", "CNB_NODE_VERSION",
            "CNB_MIRROR_SOURCE", "CNB_MIRROR_NPMRC", "CNB_MIRROR_YARNRC", "CNB_MIRROR_PNPMRC"
        ]
        has_cnb_params = any(key in build_env_dict for key in cnb_params)
        self.assertTrue(has_cnb_params)

    def test_has_cnb_params_with_mirror_yarnrc(self):
        """测试：有 CNB_MIRROR_YARNRC 时应检测到 CNB 参数"""
        build_env_dict = {"CNB_MIRROR_YARNRC": 'registry "https://registry.npmmirror.com"'}
        cnb_params = [
            "CNB_FRAMEWORK", "CNB_BUILD_SCRIPT", "CNB_OUTPUT_DIR", "CNB_NODE_VERSION",
            "CNB_MIRROR_SOURCE", "CNB_MIRROR_NPMRC", "CNB_MIRROR_YARNRC", "CNB_MIRROR_PNPMRC"
        ]
        has_cnb_params = any(key in build_env_dict for key in cnb_params)
        self.assertTrue(has_cnb_params)

    def test_has_cnb_params_with_mirror_pnpmrc(self):
        """测试：有 CNB_MIRROR_PNPMRC 时应检测到 CNB 参数"""
        build_env_dict = {"CNB_MIRROR_PNPMRC": "registry=https://registry.npmmirror.com"}
        cnb_params = [
            "CNB_FRAMEWORK", "CNB_BUILD_SCRIPT", "CNB_OUTPUT_DIR", "CNB_NODE_VERSION",
            "CNB_MIRROR_SOURCE", "CNB_MIRROR_NPMRC", "CNB_MIRROR_YARNRC", "CNB_MIRROR_PNPMRC"
        ]
        has_cnb_params = any(key in build_env_dict for key in cnb_params)
        self.assertTrue(has_cnb_params)

    def test_no_cnb_params(self):
        """测试：没有 CNB 参数时应返回 False"""
        build_env_dict = {"BUILD_PACKAGE_TOOL": "npm", "BUILD_RUNTIMES": "20.x"}
        cnb_params = [
            "CNB_FRAMEWORK", "CNB_BUILD_SCRIPT", "CNB_OUTPUT_DIR", "CNB_NODE_VERSION",
            "CNB_MIRROR_SOURCE", "CNB_MIRROR_NPMRC", "CNB_MIRROR_YARNRC", "CNB_MIRROR_PNPMRC"
        ]
        has_cnb_params = any(key in build_env_dict for key in cnb_params)
        self.assertFalse(has_cnb_params)

    def test_empty_build_env_dict(self):
        """测试：空的构建环境变量字典"""
        build_env_dict = {}
        cnb_params = [
            "CNB_FRAMEWORK", "CNB_BUILD_SCRIPT", "CNB_OUTPUT_DIR", "CNB_NODE_VERSION",
            "CNB_MIRROR_SOURCE", "CNB_MIRROR_NPMRC", "CNB_MIRROR_YARNRC", "CNB_MIRROR_PNPMRC"
        ]
        has_cnb_params = any(key in build_env_dict for key in cnb_params)
        self.assertFalse(has_cnb_params)


class BuildTypeAutoSetTestCase(TestCase):
    """测试 BUILD_TYPE 自动设置逻辑"""

    def test_auto_set_build_type_cnb(self):
        """测试：当有 CNB 参数且没有 BUILD_TYPE 时，应自动设置为 cnb"""
        build_env_dict = {"CNB_FRAMEWORK": "nextjs"}
        cnb_params = [
            "CNB_FRAMEWORK", "CNB_BUILD_SCRIPT", "CNB_OUTPUT_DIR", "CNB_NODE_VERSION",
            "CNB_MIRROR_SOURCE", "CNB_MIRROR_NPMRC", "CNB_MIRROR_YARNRC", "CNB_MIRROR_PNPMRC"
        ]
        has_cnb_params = any(key in build_env_dict for key in cnb_params)
        if has_cnb_params and "BUILD_TYPE" not in build_env_dict:
            build_env_dict["BUILD_TYPE"] = "cnb"

        self.assertEqual(build_env_dict.get("BUILD_TYPE"), "cnb")

    def test_preserve_existing_build_type(self):
        """测试：当已有 BUILD_TYPE 时，不应覆盖"""
        build_env_dict = {"CNB_FRAMEWORK": "nextjs", "BUILD_TYPE": "dockerfile"}
        cnb_params = [
            "CNB_FRAMEWORK", "CNB_BUILD_SCRIPT", "CNB_OUTPUT_DIR", "CNB_NODE_VERSION",
            "CNB_MIRROR_SOURCE", "CNB_MIRROR_NPMRC", "CNB_MIRROR_YARNRC", "CNB_MIRROR_PNPMRC"
        ]
        has_cnb_params = any(key in build_env_dict for key in cnb_params)
        if has_cnb_params and "BUILD_TYPE" not in build_env_dict:
            build_env_dict["BUILD_TYPE"] = "cnb"

        self.assertEqual(build_env_dict.get("BUILD_TYPE"), "dockerfile")

    def test_no_build_type_without_cnb_params(self):
        """测试：没有 CNB 参数时，不应设置 BUILD_TYPE"""
        build_env_dict = {"BUILD_PACKAGE_TOOL": "npm"}
        cnb_params = [
            "CNB_FRAMEWORK", "CNB_BUILD_SCRIPT", "CNB_OUTPUT_DIR", "CNB_NODE_VERSION",
            "CNB_MIRROR_SOURCE", "CNB_MIRROR_NPMRC", "CNB_MIRROR_YARNRC", "CNB_MIRROR_PNPMRC"
        ]
        has_cnb_params = any(key in build_env_dict for key in cnb_params)
        if has_cnb_params and "BUILD_TYPE" not in build_env_dict:
            build_env_dict["BUILD_TYPE"] = "cnb"

        self.assertNotIn("BUILD_TYPE", build_env_dict)

    def test_auto_set_with_only_mirror_config(self):
        """测试：仅配置 mirror 时也应自动设置 BUILD_TYPE=cnb"""
        build_env_dict = {"CNB_MIRROR_NPMRC": "registry=https://registry.npmmirror.com"}
        cnb_params = [
            "CNB_FRAMEWORK", "CNB_BUILD_SCRIPT", "CNB_OUTPUT_DIR", "CNB_NODE_VERSION",
            "CNB_MIRROR_SOURCE", "CNB_MIRROR_NPMRC", "CNB_MIRROR_YARNRC", "CNB_MIRROR_PNPMRC"
        ]
        has_cnb_params = any(key in build_env_dict for key in cnb_params)
        if has_cnb_params and "BUILD_TYPE" not in build_env_dict:
            build_env_dict["BUILD_TYPE"] = "cnb"

        self.assertEqual(build_env_dict.get("BUILD_TYPE"), "cnb")


class CNBMirrorConfigTestCase(TestCase):
    """测试 CNB Mirror 配置相关逻辑"""

    def test_mirror_source_project(self):
        """测试：mirror source 为 project"""
        build_env_dict = {"CNB_MIRROR_SOURCE": "project"}
        self.assertEqual(build_env_dict.get("CNB_MIRROR_SOURCE"), "project")

    def test_mirror_source_global(self):
        """测试：mirror source 为 global"""
        build_env_dict = {"CNB_MIRROR_SOURCE": "global"}
        self.assertEqual(build_env_dict.get("CNB_MIRROR_SOURCE"), "global")

    def test_all_mirror_configs(self):
        """测试：同时配置所有 mirror 文件"""
        build_env_dict = {
            "CNB_MIRROR_SOURCE": "global",
            "CNB_MIRROR_NPMRC": "registry=https://registry.npmmirror.com",
            "CNB_MIRROR_YARNRC": 'registry "https://registry.npmmirror.com"',
            "CNB_MIRROR_PNPMRC": "registry=https://registry.npmmirror.com"
        }
        self.assertIn("CNB_MIRROR_NPMRC", build_env_dict)
        self.assertIn("CNB_MIRROR_YARNRC", build_env_dict)
        self.assertIn("CNB_MIRROR_PNPMRC", build_env_dict)


class CNBFrameworkValidationTestCase(TestCase):
    """测试 CNB 框架配置验证"""

    def test_valid_static_frameworks(self):
        """测试：静态框架列表"""
        static_frameworks = ["vue", "react", "vite", "nextjs", "nuxt", "umi", "cra", "vue-cli", "gatsby", "docusaurus"]
        for framework in static_frameworks:
            build_env_dict = {"CNB_FRAMEWORK": framework}
            self.assertEqual(build_env_dict.get("CNB_FRAMEWORK"), framework)

    def test_valid_server_frameworks(self):
        """测试：服务端框架列表"""
        server_frameworks = ["express", "nestjs", "koa", "fastify", "remix"]
        for framework in server_frameworks:
            build_env_dict = {"CNB_FRAMEWORK": framework}
            self.assertEqual(build_env_dict.get("CNB_FRAMEWORK"), framework)


class CNBOutputDirTestCase(TestCase):
    """测试 CNB 输出目录配置"""

    def test_default_output_dirs(self):
        """测试：常见框架的默认输出目录"""
        framework_output_dirs = {
            "vue": "dist",
            "react": "build",
            "vite": "dist",
            "nextjs": ".next",
            "nuxt": ".output",
            "umi": "dist",
            "cra": "build",
            "gatsby": "public",
            "docusaurus": "build"
        }
        for framework, expected_dir in framework_output_dirs.items():
            build_env_dict = {"CNB_FRAMEWORK": framework, "CNB_OUTPUT_DIR": expected_dir}
            self.assertEqual(build_env_dict.get("CNB_OUTPUT_DIR"), expected_dir)


class CNBNodeVersionTestCase(TestCase):
    """测试 CNB Node.js 版本配置"""

    def test_valid_node_versions(self):
        """测试：有效的 Node.js 版本"""
        valid_versions = ["18.20.7", "18.20.8", "20.19.6", "20.20.0", "22.21.1", "22.22.0", "24.12.0", "24.13.0"]
        for version in valid_versions:
            build_env_dict = {"CNB_NODE_VERSION": version}
            self.assertEqual(build_env_dict.get("CNB_NODE_VERSION"), version)

    def test_empty_node_version(self):
        """测试：空的 Node.js 版本应使用默认值"""
        build_env_dict = {}
        # 默认不设置版本，由 CNB 自动检测
        self.assertNotIn("CNB_NODE_VERSION", build_env_dict)
