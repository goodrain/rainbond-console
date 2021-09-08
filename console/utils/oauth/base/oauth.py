# -*- coding: utf8 -*-
from abc import ABCMeta, abstractmethod

import requests
from requests.adapters import HTTPAdapter


class OAuth2User(object):
    def __init__(self, name, user_id, user_email):
        self.name = name
        self.id = user_id
        self.email = user_email


class OAuth2Interface(object, metaclass=ABCMeta):
    def set_session(self):
        self._session = requests.Session()
        self._session.mount('http://', HTTPAdapter(max_retries=3))
        self._session.mount('https://', HTTPAdapter(max_retries=3))

    def set_oauth_user(self, oauth_user):
        '''
        set oauth user model
        :return:
        '''
        self.oauth_user = oauth_user

    def update_access_token(self, access_token, refresh_token=None):
        '''
        set oauth user model
        :return:
        '''
        if self.oauth_user:
            self.oauth_user.access_token = access_token
            self.oauth_user.refresh_token = refresh_token
            self.oauth_user.save()

    def is_git_oauth(self):
        '''
        :return:
        '''
        return False

    def is_communication_oauth(self):
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
    def get_user_info(self, code=None):
        '''
        get oauth common user
        :return: OAuth2User
        '''

    @abstractmethod
    def get_authorize_url(self):
        '''
        get redirect url for this oauth server
        :return: url string, The 'service_id' GET parameter must be included
        '''

    @abstractmethod
    def get_auth_url(self, home_url=None):
        '''
        get authorize url for creating oauth server
        :return: url string
        '''

    @abstractmethod
    def get_access_token_url(self, home_url=None):
        '''
        get access_token url for creating oauth server
        :return: url string
        '''

    @abstractmethod
    def get_user_url(self, home_url=None):
        '''
        get user url for creating oauth server
        :return: url string
        '''
