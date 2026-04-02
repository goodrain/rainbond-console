from unittest import TestCase

from console.utils.cnb_build import build_cnb_version_policy


class CNBVersionPolicyTests(TestCase):
    def test_build_policy_from_enterprise_versions(self):
        policy = build_cnb_version_policy("Python", [{
            "lang": "python",
            "version": "python-3.10.9",
            "build_strategy": "cnb",
            "show": False,
            "is_allowed": True,
            "first_choice": False
        }, {
            "lang": "python",
            "version": "python-3.11.9",
            "build_strategy": "cnb",
            "show": True,
            "is_allowed": True,
            "first_choice": True
        }, {
            "lang": "python",
            "version": "python-3.12.1",
            "build_strategy": "cnb",
            "show": False,
            "is_allowed": False,
            "first_choice": False
        }], [])

        self.assertEqual(policy, {
            "python": {
                "cpython": {
                    "visible_versions": ["3.11"],
                    "allowed_versions": ["3.10", "3.11"],
                    "default_version": "3.11"
                }
            }
        })

    def test_build_policy_uses_empty_nodejs_policy_without_enterprise_versions(self):
        policy = build_cnb_version_policy("Node.js", [], [{
            "version": "20.20.0",
            "default": False
        }, {
            "version": "24.13.0",
            "default": True
        }])

        self.assertEqual(policy, {
            "nodejs": {
                "nodejs": {
                    "visible_versions": [],
                    "allowed_versions": [],
                    "default_version": ""
                }
            }
        })

    def test_build_policy_uses_empty_java_policy_without_enterprise_versions(self):
        policy = build_cnb_version_policy("java-maven", [], [{
            "version": "8",
            "default": False
        }, {
            "version": "17",
            "default": True
        }, {
            "version": "21",
            "default": False
        }])

        self.assertEqual(policy, {
            "java": {
                "jdk": {
                    "visible_versions": [],
                    "allowed_versions": [],
                    "default_version": ""
                }
            }
        })

    def test_build_policy_uses_empty_python_policy_without_enterprise_versions(self):
        policy = build_cnb_version_policy("Python", [], [{
            "version": "3.10",
            "default": False
        }, {
            "version": "3.11",
            "default": False
        }, {
            "version": "3.12",
            "default": False
        }, {
            "version": "3.13",
            "default": False
        }, {
            "version": "3.14",
            "default": True
        }])

        self.assertEqual(policy, {
            "python": {
                "cpython": {
                    "visible_versions": [],
                    "allowed_versions": [],
                    "default_version": ""
                }
            }
        })

    def test_build_policy_normalizes_java_major_versions(self):
        policy = build_cnb_version_policy("java-maven", [{
            "lang": "openJDK",
            "version": "1.8",
            "build_strategy": "cnb",
            "show": True,
            "is_allowed": True,
            "first_choice": False
        }, {
            "lang": "openJDK",
            "version": "17.0.12",
            "build_strategy": "cnb",
            "show": True,
            "is_allowed": True,
            "first_choice": True
        }], [])

        self.assertEqual(policy["java"]["jdk"]["visible_versions"], ["8", "17"])
        self.assertEqual(policy["java"]["jdk"]["allowed_versions"], ["8", "17"])
        self.assertEqual(policy["java"]["jdk"]["default_version"], "17")

    def test_build_policy_sorts_java_versions_in_ascending_order(self):
        policy = build_cnb_version_policy("java-maven", [{
            "lang": "openJDK",
            "version": "17.0.12",
            "build_strategy": "cnb",
            "show": True,
            "is_allowed": True,
            "first_choice": True
        }, {
            "lang": "openJDK",
            "version": "1.8",
            "build_strategy": "cnb",
            "show": True,
            "is_allowed": True,
            "first_choice": False
        }, {
            "lang": "openJDK",
            "version": "11.0.25",
            "build_strategy": "cnb",
            "show": True,
            "is_allowed": True,
            "first_choice": False
        }, {
            "lang": "openJDK",
            "version": "21.0.4",
            "build_strategy": "cnb",
            "show": True,
            "is_allowed": True,
            "first_choice": False
        }, {
            "lang": "openJDK",
            "version": "25.0.0",
            "build_strategy": "cnb",
            "show": True,
            "is_allowed": True,
            "first_choice": False
        }], [])

        self.assertEqual(policy["java"]["jdk"]["visible_versions"], ["8", "11", "17", "21", "25"])
        self.assertEqual(policy["java"]["jdk"]["allowed_versions"], ["8", "11", "17", "21", "25"])
        self.assertEqual(policy["java"]["jdk"]["default_version"], "17")

    def test_non_cnb_language_has_no_policy(self):
        self.assertEqual(build_cnb_version_policy("dockerfile", [], []), {})
