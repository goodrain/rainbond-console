# coding: utf-8
from unittest import TestCase

import os
import sys
from types import ModuleType

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django

django.setup()

from console.utils.oauth.oauth_types import NoSupportOAuthType
from console.utils.oauth.oauth_types import get_oauth_instance
from console.utils.oauth.oauth_types import get_support_oauth_servers


class DummyOAuthService(object):
    pass


class DummyOAuthUser(object):
    pass


class OAuthTypeTests(TestCase):
    # capability_id: console.oauth.supported-types
    def test_get_support_oauth_servers(self):
        servers = get_support_oauth_servers()
        self.assertIn("github", servers)
        self.assertIn("gitlab", servers)
        self.assertIn("gitee", servers)

    # capability_id: console.oauth.instance-create
    def test_get_oauth_instance(self):
        oauth_service = DummyOAuthService()
        oauth_user = DummyOAuthUser()
        instance = get_oauth_instance("github", oauth_service=oauth_service, oauth_user=oauth_user)
        self.assertIs(instance.oauth_service, oauth_service)
        self.assertIs(instance.oauth_user, oauth_user)

    # capability_id: console.oauth.unsupported-type
    def test_get_oauth_instance_unsupported_type(self):
        with self.assertRaises(NoSupportOAuthType):
            get_oauth_instance("unsupported-oauth")
