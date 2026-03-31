# coding: utf-8
from unittest import TestCase, mock

import os
import sys
from types import ModuleType

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django

django.setup()

from console.utils.oauth.base.git_oauth import GitOAuth2Interface
from console.utils.oauth.base.oauth import OAuth2Interface


class DummyOAuth(OAuth2Interface):
    def get_user_info(self, code=None):
        return None

    def get_authorize_url(self):
        return ""

    def get_auth_url(self, home_url=None):
        return ""

    def get_access_token_url(self, home_url=None):
        return ""

    def get_user_url(self, home_url=None):
        return ""


class DummyGitOAuth(GitOAuth2Interface):
    def get_user_info(self, code=None):
        return None

    def get_authorize_url(self):
        return ""

    def get_auth_url(self, home_url=None):
        return ""

    def get_access_token_url(self, home_url=None):
        return ""

    def get_user_url(self, home_url=None):
        return ""

    def get_repos(self, *args, **kwargs):
        return [], 0

    def search_repos(self, search_key):
        return [], 0

    def create_hook(self, repo_name, hook_url):
        return None

    def get_repo_detail(self, repo_name):
        return {}

    def get_branches(self, repo_name):
        return []

    def get_tags(self, repo_name):
        return []

    def get_branches_or_tags(self, type, full_name):
        return []

    def get_clone_url(self, url):
        return url

    def get_clone_user_password(self):
        return "", ""


class DummyOAuthUser(object):
    def __init__(self):
        self.access_token = None
        self.refresh_token = None
        self.saved = False

    def save(self):
        self.saved = True


class OAuthBaseTests(TestCase):
    # capability_id: console.oauth.session-retry
    def test_set_session_builds_retrying_requests_session(self):
        oauth = DummyOAuth()
        oauth.set_session()
        self.assertIsNotNone(oauth._session)
        self.assertIn("http://", oauth._session.adapters)
        self.assertIn("https://", oauth._session.adapters)

    # capability_id: console.oauth.user-binding
    def test_set_oauth_user_and_service(self):
        oauth = DummyOAuth()
        user = object()
        service = object()
        oauth.set_oauth_user(user)
        oauth.set_oauth_service(service)
        self.assertIs(oauth.oauth_user, user)
        self.assertIs(oauth.oauth_service, service)

    # capability_id: console.oauth.token-update
    def test_update_access_token_updates_bound_user(self):
        oauth = DummyOAuth()
        user = DummyOAuthUser()
        oauth.set_oauth_user(user)
        oauth.update_access_token("token-1", "refresh-1")
        self.assertEqual(user.access_token, "token-1")
        self.assertEqual(user.refresh_token, "refresh-1")
        self.assertTrue(user.saved)

    # capability_id: console.oauth.kind-flags
    def test_oauth_kind_flags(self):
        oauth = DummyOAuth()
        self.assertFalse(oauth.is_git_oauth())
        self.assertFalse(oauth.is_communication_oauth())

        git_oauth = DummyGitOAuth()
        self.assertTrue(git_oauth.is_git_oauth())
        self.assertFalse(git_oauth.is_communication_oauth())
