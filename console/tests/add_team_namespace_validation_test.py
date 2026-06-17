# -*- coding: utf-8 -*-
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

from console.exception.bcode import ErrQualifiedName  # noqa: E402
from console.views.team import AddTeamView  # noqa: E402


# capability_id: console.team.create-invalid-namespace
class AddTeamInvalidNamespaceTest(TestCase):
    def test_invalid_namespace_raises_qualified_name_error_not_typeerror(self):
        view = AddTeamView()
        request = mock.Mock()
        request.user = mock.Mock(enterprise_id="ent-1", user_id="u-1")
        request.data = {
            "team_alias": "demo",
            "useable_regions": "",
            "namespace": "Invalid_NS",
            "bind_existing_namespace": False,
            "logo": "",
        }

        with mock.patch("console.views.team.is_qualified_name", return_value=False):
            with self.assertRaises(ErrQualifiedName) as ctx:
                view.post(request)

        # msg_show must be a single well-formed string (the original used ASCII
        # quotes around the hyphen, tokenizing it as "str" - "str" -> TypeError).
        self.assertIn("命名空间", ctx.exception.msg_show)
        self.assertIn("-", ctx.exception.msg_show)
