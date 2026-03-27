from unittest import TestCase
from unittest.mock import patch

from console.services.app import app_service


class CodeLongBuildVersionTests(TestCase):
    @patch("console.services.app.region_api")
    def test_get_code_long_build_version_forwards_build_strategy(self, region_api):
        region_api.get_lang_version.return_value = {
            "list": [{"lang": "openJDK", "version": "17", "build_strategy": "cnb"}]
        }

        result = app_service.get_code_long_build_version(
            "eid", "region-a", "openJDK", "component", "cnb")

        region_api.get_lang_version.assert_called_once_with(
            "eid", "region-a", "openJDK", "component", "cnb")
        self.assertEqual(result, [{"lang": "openJDK", "version": "17", "build_strategy": "cnb"}])
