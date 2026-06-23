# -*- coding: utf-8 -*-
import os
import sys
from unittest import TestCase, mock

sys.modules.setdefault("MySQLdb", mock.Mock())

import default_region  # noqa: E402
import default_region_sqlite  # noqa: E402


class DefaultRegionScriptTest(TestCase):
    def test_mysql_default_region_uses_internal_websocket_service(self):
        with mock.patch.dict(os.environ, {"REGION_WS_URL": "ws://203.0.113.10:6060"}):
            self.assertEqual(default_region.get_wsurl(), "ws://rbd-api-websocket:6060")

    def test_sqlite_default_region_uses_internal_websocket_service(self):
        with mock.patch.dict(os.environ, {"REGION_WS_URL": "ws://203.0.113.10:6060"}):
            self.assertEqual(default_region_sqlite.get_wsurl(), "ws://rbd-api-websocket:6060")
