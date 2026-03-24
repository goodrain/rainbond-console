# -*- coding: utf-8 -*-
import collections
import json
import os
import sys
from types import ModuleType
from unittest import TestCase, mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from console.services.app_import_and_export_service import export_service  # noqa: E402


class AppExportServiceMetadataTestCase(TestCase):
    def test_get_app_metadata_allows_missing_picture(self):
        app = mock.Mock(pic=None, describe="demo app")
        app_version = mock.Mock(
            app_template=json.dumps({"group_key": "demo-app", "group_version": "1.0.0"}),
            app_version_info="bugfix",
            version_alias="stable",
        )

        metadata = export_service._AppExportService__get_app_metata(app, app_version, {"image_handle": ""})
        result = json.loads(metadata)

        self.assertEqual(result["annotations"]["suffix"], "")
        self.assertEqual(result["annotations"]["image_base64_string"], "")
        self.assertEqual(result["annotations"]["describe"], "demo app")
        self.assertEqual(result["helm_chart"]["image_handle"], "")
