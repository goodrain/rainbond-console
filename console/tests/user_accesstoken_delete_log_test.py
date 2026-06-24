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

from console.views import user_accesstoken as accesstoken_module  # noqa: E402
from console.views.user_accesstoken import UserAccessTokenRUDView  # noqa: E402


# capability_id: console.user.access-token-delete-log
class UserAccessTokenDeleteLogTest(TestCase):
    def test_delete_logs_token_note_without_nameerror(self):
        view = UserAccessTokenRUDView()
        view.user = mock.Mock(enterprise_id="ent-1")
        request = mock.Mock()
        request.user = mock.Mock(user_id="u-1")

        with mock.patch.object(accesstoken_module, "user_access_services") as svc, \
                mock.patch.object(accesstoken_module, "operation_log_service") as ops:
            svc.get_user_access_key_by_id.return_value.first.return_value = mock.Mock(note="my-token")
            response = view.delete(request, "key-1")

        self.assertEqual(response.status_code, 200)
        svc.delete_user_access_key_by_id.assert_called_once_with("u-1", "key-1")
        comment_kwargs = ops.generate_generic_comment.call_args.kwargs
        self.assertEqual(comment_kwargs["module_name"], "my-token")
