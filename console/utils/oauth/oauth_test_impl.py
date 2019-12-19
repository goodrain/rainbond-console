# -*- coding: utf8 -*-
from oauth import OAuth2User, OAuth2Interface


class OAuth2Test(OAuth2Interface):

    def _get_access_token(self):
        '''
        private function, get access_token
        :return: OAuth2User
        '''
        access_token = "12345"
        refresh_token = "65432"

        self.update_access_token(access_token, refresh_token)
        return access_token

    def get_user_info(self):
        '''
        get oauth common user
        :return: OAuth2User
        '''
        access_token = self._get_access_token()
        return OAuth2User("test", "12345", "test@test.com")

    def get_redirect_url(self):
        return "https://test.com/oauth?service_id=12345&client_id=12345432&scope=test"
