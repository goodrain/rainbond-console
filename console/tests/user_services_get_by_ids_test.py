# -*- coding: utf-8 -*-
import collections
import collections.abc
import os
import sys
from types import ModuleType
from unittest import TestCase, mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from console.services import user_services as user_services_module  # noqa: E402
from console.services.user_services import UserService  # noqa: E402


# capability_id: console.user.get-users-by-ids
class GetUsersByUserIdsTest(TestCase):
    def test_delegates_to_repo_get_by_user_ids(self):
        sentinel = object()
        with mock.patch.object(user_services_module, "user_repo") as mock_repo:
            mock_repo.get_by_user_ids.return_value = sentinel
            result = UserService().get_users_by_user_ids(["u1", "u2"])
        self.assertIs(result, sentinel)
        mock_repo.get_by_user_ids.assert_called_once_with(["u1", "u2"])
