# -*- coding: utf8 -*-
from oauth import OAuth2User, OAuth2Interface


class OAuth2Test(OAuth2Interface):

    def get_access_token(self):
        '''
        get oauth access token
        :return:
        '''
        return ""

    def refresh_access_token(self):
        '''
        refresh oauth access token
        :return:
        '''
        return True

    def get_user_info(self):
        '''
        get oauth common user
        :return: OAuth2User
        '''
        return OAuth2User("test", "12345", "test@test.com")

    def check_and_refresh_access_token(self):
        '''
        check access token ,if token expired, refresh it
        :return: true or false
        '''
        return True

    def get_redirect_url(self):
        return "https://test.com/oauth?service_id=12345&client_id=12345432&scope=test"
