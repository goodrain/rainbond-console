
# -*- coding: utf8 -*-
import unittest
from oauth_types import get_support_oauth_servers, get_oauth_instance


class TestOAuth(unittest.TestCase):

    def test_get_support_oauth_servers(self):
        print(get_support_oauth_servers())

    def test_get_oauth_instance(self):
        oauth = get_oauth_instance("test", None, None)
        print(oauth.get_redirect_url())
        print(oauth.get_user_info())


if __name__ == '__main__':
    unittest.main()
