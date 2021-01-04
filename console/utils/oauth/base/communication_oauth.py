# -*- coding: utf8 -*-

from abc import ABCMeta, abstractmethod

from .oauth import OAuth2Interface


class CommunicationOAuth2User(object):
    def __init__(self, name, user_id, user_email, phone, enterprise_name, domain):
        self.name = name
        self.id = user_id
        self.email = user_email
        self.phone = phone
        self.enterprise_name = enterprise_name
        self.domain = domain


class CommunicationOAuth2Interface(OAuth2Interface, metaclass=ABCMeta):
    def is_git_oauth(self):
        '''
        Identifies whether the code repository class is serviced
        :return:
        '''
        return False

    def is_communication_oauth(self):
        return True

    @abstractmethod
    def list_user(self, *args, **kwargs):
        '''
        get user list by login user
        :return:
        '''

    @abstractmethod
    def create_user(self, *args, **kwargs):
        '''
        create user by login user
        :return:
        '''

    @abstractmethod
    def update_user(self, *args, **kwargs):
        '''
        create user by login user
        :return:
        '''

    @abstractmethod
    def delete_user(self, *args, **kwargs):
        '''
        create user by login user
        :return:
        '''
