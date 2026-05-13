# -*- coding: utf-8 -*-
import os
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, patch

sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".venv", "src", "openapi-client")))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django
from django.test import SimpleTestCase

django.setup()

from console.exception.exceptions import AuthenticationInfoHasExpiredError
from console.views.base import JSONWebTokenAuthentication, custom_exception_handler


class FakeQuerySet(object):
    def __init__(self, user):
        self.user = user

    def first(self):
        return self.user


class JSONWebTokenAuthenticationTests(SimpleTestCase):

    def test_authenticate_credentials_prefers_matching_user_id(self):
        user = SimpleNamespace(user_id=33, nick_name="user-83847590", is_active=True)

        with patch("console.views.base.Users.objects.filter", return_value=FakeQuerySet(user)) as filter_users:
            auth_user = JSONWebTokenAuthentication().authenticate_credentials({
                "user_id": 33,
                "username": "user-83847590",
            })

        self.assertEqual(auth_user, user)
        filter_users.assert_called_once_with(user_id=33)

    def test_authenticate_credentials_rejects_user_id_username_mismatch(self):
        user = SimpleNamespace(user_id=33, nick_name="other-user", is_active=True)

        with patch("console.views.base.Users.objects.filter", return_value=FakeQuerySet(user)):
            with self.assertRaises(AuthenticationInfoHasExpiredError):
                JSONWebTokenAuthentication().authenticate_credentials({
                    "user_id": 33,
                    "username": "user-83847590",
                })

    def test_authenticate_credentials_falls_back_to_username_when_user_id_missing(self):
        user = SimpleNamespace(user_id=33, nick_name="user-83847590", is_active=True)

        with patch("console.views.base.Users.objects.filter", return_value=FakeQuerySet(None)), \
                patch("console.views.base.Users.objects.get", Mock(return_value=user)) as get_user:
            auth_user = JSONWebTokenAuthentication().authenticate_credentials({
                "user_id": 33,
                "username": "user-83847590",
            })

        self.assertEqual(auth_user, user)
        get_user.assert_called_once_with(nick_name="user-83847590")

    def test_authentication_expired_returns_401(self):
        response = custom_exception_handler(AuthenticationInfoHasExpiredError("签名不合法."), {})

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["code"], 10405)
