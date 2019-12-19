# -*- coding: utf8 -*-
from abc import ABCMeta, abstractmethod


class OAuth2User(object):
    def __init__(self, name, user_id, user_email):
        self.user_name = name
        self.user_id = user_id
        self.email = user_email


class OAuth2Interface(object):
    __metaclass__ = ABCMeta

    def set_oauth_user(self, oauth_user):
        '''
        set oauth user model
        :return:
        '''
        self.oauth_user = oauth_user

    def update_access_token(self, access_token, refresh_token):
        '''
        set oauth user model
        :return:
        '''
        if self.oauth_user:
            self.oauth_user.refresh_token = access_token
            self.oauth_user.access_token = refresh_token
            self.oauth_user.save()

    def is_git_oauth(self):
        '''
        :return:
        '''
        return False

    def set_oauth_service(self, oauth_service):
        '''
        set oauth server config model
        :return:
        '''
        self.oauth_service = oauth_service

    @abstractmethod
    def get_user_info(self):
        '''
        get oauth common user
        :return: OAuth2User
        '''

    @abstractmethod
    def get_redirect_url(self):
        '''
        get redirect url for this oauth server
        :return: url string, The 'service_id' GET parameter must be included
        '''