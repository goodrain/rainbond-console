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

from console.services import auth as auth_module  # noqa: E402


class FakeRequest(object):
    def __init__(self, session):
        self.session = session


class FakeUser(object):
    def __init__(self, pk):
        self.pk = pk


# capability_id: console.auth.get-user-no-legacy-middleware
class GetUserNoLegacyMiddlewareTests(TestCase):
    BACKEND_PATH = "django.contrib.auth.backends.ModelBackend"

    def _session(self):
        return {
            auth_module.SESSION_KEY: 42,
            auth_module.BACKEND_SESSION_KEY: self.BACKEND_PATH,
        }

    def test_returns_user_without_touching_middleware_classes(self):
        # Arrange
        request = FakeRequest(self._session())
        expected_user = FakeUser(pk=42)
        fake_backend = mock.Mock()
        fake_backend.get_user.return_value = expected_user

        with mock.patch.object(auth_module.settings, "AUTHENTICATION_BACKENDS", [self.BACKEND_PATH]), \
                mock.patch.object(auth_module, "load_backend", return_value=fake_backend) as load_backend_mock:
            # Act — must not raise AttributeError on settings.MIDDLEWARE_CLASSES
            result = auth_module.get_user(request)

        # Assert
        load_backend_mock.assert_called_once_with(self.BACKEND_PATH)
        fake_backend.get_user.assert_called_once_with(42)
        self.assertIs(result, expected_user)

    def test_returns_anonymous_user_when_no_session(self):
        # Arrange
        request = FakeRequest({})

        # Act
        result = auth_module.get_user(request)

        # Assert
        from www.models.main import AnonymousUser
        self.assertIsInstance(result, AnonymousUser)
