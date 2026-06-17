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

from console.exception.exceptions import UserFavoriteNotExistError  # noqa: E402
from console.views import user_operation as user_operation_module  # noqa: E402
from console.views.user_operation import UserFavoriteUDView  # noqa: E402


# capability_id: console.user.favorite-delete-log
class UserFavoriteDeleteLogTest(TestCase):
    def test_delete_logs_favorite_name_without_nameerror(self):
        view = UserFavoriteUDView()
        view.user = mock.Mock(enterprise_id="ent-1")
        request = mock.Mock()
        request.user = mock.Mock(user_id="u-1")

        favorite = mock.Mock()
        favorite.name = "my-fav"

        with mock.patch.object(user_operation_module, "user_repo") as repo, \
                mock.patch.object(user_operation_module, "operation_log_service") as ops:
            repo.get_user_favorite_by_ID.return_value = favorite
            response = view.delete(request, "ent-1", "fav-1")

        self.assertEqual(response.status_code, 200)
        repo.delete_user_favorite_by_id.assert_called_once_with("u-1", "fav-1")
        comment_kwargs = ops.generate_generic_comment.call_args.kwargs
        self.assertEqual(comment_kwargs["module_name"], " my-fav")

    def test_delete_missing_favorite_returns_404(self):
        view = UserFavoriteUDView()
        view.user = mock.Mock(enterprise_id="ent-1")
        request = mock.Mock()
        request.user = mock.Mock(user_id="u-1")

        with mock.patch.object(user_operation_module, "user_repo") as repo, \
                mock.patch.object(user_operation_module, "operation_log_service"):
            repo.get_user_favorite_by_ID.side_effect = UserFavoriteNotExistError("missing")
            response = view.delete(request, "ent-1", "fav-1")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["code"], 404)
