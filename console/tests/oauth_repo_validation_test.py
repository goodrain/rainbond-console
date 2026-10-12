# -*- coding: utf-8 -*-
import collections
import os
import sys
from types import ModuleType
from unittest import TestCase, mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from console.exception.bcode import ErrOauthServiceNotFound  # noqa: E402
from console.repositories.oauth_repo import OAuthRepo  # noqa: E402


class OAuthRepoValidationTestCase(TestCase):
    # capability_id: console.oauth.service-validation
    def test_get_service_rejects_non_numeric_id_as_not_found(self):
        with self.assertRaises(ErrOauthServiceNotFound):
            OAuthRepo().get_oauth_services_by_service_id("<svc>")

    # capability_id: console.oauth.service-validation
    def test_update_rejects_deleted_oauth_service_before_reading_home_url(self):
        repo = OAuthRepo()
        values = [{
            "service_id": 7,
            "name": "git-service",
            "client_id": "client-id",
            "client_secret": "client-secret",
            "eid": "enterprise-id",
            "redirect_uri": "https://example.com/callback",
            "oauth_type": "gitea",
            "home_url": "https://example.com",
            "enable": True,
            "is_auto_login": False,
            "is_console": False,
        }]
        oauth_instance = mock.Mock()
        oauth_instance.get_auth_url.return_value = "https://example.com/login"
        oauth_instance.get_access_token_url.return_value = "https://example.com/token"
        oauth_instance.get_user_url.return_value = "https://example.com/user"
        oauth_instance.is_git_oauth.return_value = True

        with mock.patch("console.repositories.oauth_repo.get_oauth_instance", return_value=oauth_instance), \
                mock.patch.object(repo, "open_get_oauth_services_by_service_id", return_value=None):
            with self.assertRaises(ErrOauthServiceNotFound):
                repo.create_or_update_oauth_services(values, "enterprise-id", "user-id")
