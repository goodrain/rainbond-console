# -*- coding: utf8 -*-

from abc import ABCMeta, abstractmethod
from oauth import OAuth2Interface


class GitOAuth2Interface(OAuth2Interface):
    __metaclass__ = ABCMeta

    def is_git_oauth(self):
        '''
        Identifies whether the code repository class is serviced
        :return:
        '''
        return True

    @abstractmethod
    def get_repos(self, page, page_size):
        '''
        get repostory list by login user
        :return:
        '''

    @abstractmethod
    def search_repos(self, search_key):
        '''
        search repostory list by login user
        :return:
        '''

    @abstractmethod
    def create_webhook(self, repo_name, hook_url):
        '''
        create webhook
        :return:
        '''

    @abstractmethod
    def get_repo_detail(self, repo_name):
        '''
        get repostory detail info
        :return:
        '''

    @abstractmethod
    def get_branches(self, repo_name):
        '''
        get repostory branch list
        :return:
        '''
    @abstractmethod
    def get_tags(self, repo_name):
        '''
        get repostory tag list
        :return:
        '''

    @abstractmethod
    def get_clone_url(self, repo_name, base_url):
        '''
        get clone code url, Mainly dealing with authorization information
        base_url: Local storage url without authentication token
        :return: url string
        '''

    @abstractmethod
    def get_clone_user_password(self, repo_name):
        '''
        get clone code user and password
        :return: user(string), password(string)
        '''
