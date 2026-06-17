# -*- coding: utf-8 -*-
import base64
import collections
import collections.abc
import os
import sys
from types import ModuleType
from unittest import TestCase, mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.test_settings")

import django  # noqa: E402

django.setup()

from console.views.enterprise_active import BindMarketEnterpriseOptimizAccessTokenView  # noqa: E402


# capability_id: console.enterprise.bind-market-token-decode
class BindMarketTokenDecodeTest(TestCase):
    def test_market_info_is_base64_decoded(self):
        # base64.decodestring was removed in Python 3.9 -> AttributeError before fix.
        encoded = base64.b64encode(b"{'eid': 'e1', 'token': 't1'}").decode("utf-8")
        view = BindMarketEnterpriseOptimizAccessTokenView()
        request = mock.Mock()
        request.data = {"market_info": encoded}

        # enterprise_id empty: decoding must succeed first, then the param check
        # short-circuits to a 400 (no enterprise lookup / region calls reached).
        response = view.post(request, enterprise_id="")

        self.assertEqual(response.status_code, 400)
