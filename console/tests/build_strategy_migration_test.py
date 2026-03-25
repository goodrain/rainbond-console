from unittest import TestCase

from console.utils.cnb_build import convert_slug_to_cnb


class DummyService(object):
    def __init__(self, language):
        self.language = language


class BuildStrategyMigrationTests(TestCase):
    def test_convert_python_slug_to_cnb_requires_procfile(self):
        envs, status, message, debug_meta = convert_slug_to_cnb(DummyService("Python"), {
            "BUILD_RUNTIMES": "3.11"
        })

        self.assertEqual(status, "failed")
        self.assertIn("BUILD_PROCFILE", message)
        self.assertEqual(debug_meta, {})

    def test_convert_golang_slug_to_cnb_success(self):
        envs, status, message, debug_meta = convert_slug_to_cnb(DummyService("Golang"), {
            "BUILD_GOVERSION": "1.23",
            "BUILD_GO_INSTALL_PACKAGE_SPEC": "./cmd/api"
        })

        self.assertEqual(status, "migrated")
        self.assertEqual(message, "")
        self.assertEqual(envs["BUILD_TYPE"], "cnb")
        self.assertEqual(debug_meta["builder_image"], "registry.cn-hangzhou.aliyuncs.com/goodrain/ubuntu-noble-builder:0.0.72")
        self.assertEqual(debug_meta["yaml_observable"]["annotations"]["cnb-bp-go-targets"], "./cmd/api")

    def test_convert_php_slug_to_cnb_rejects_unknown_server(self):
        envs, status, message, debug_meta = convert_slug_to_cnb(DummyService("PHP"), {
            "BUILD_RUNTIMES": "8.2",
            "BUILD_RUNTIMES_SERVER": "iis"
        })

        self.assertEqual(status, "failed")
        self.assertIn("nginx", message)
        self.assertEqual(debug_meta, {})
