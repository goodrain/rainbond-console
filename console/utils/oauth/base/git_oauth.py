# -*- coding: utf8 -*-

from abc import ABCMeta, abstractmethod

from .oauth import OAuth2Interface


class GitOAuth2Interface(OAuth2Interface, metaclass=ABCMeta):
    def is_git_oauth(self):
        '''
        Identifies whether the code repository class is serviced
        :return:
        '''
        return True

    def is_communication_oauth(self):
        '''
        :return:
        '''
        return False

    @abstractmethod
    def get_repos(self, *args, **kwargs):
        '''
        get repository list by login user
        :return: list, int
        '''

    @abstractmethod
    def search_repos(self, search_key):
        '''
        search repository list by login user
        :return: list, int
        '''

    @abstractmethod
    def create_hook(self, repo_name, hook_url):
        '''
        create webhook
        :return:
        '''

    @abstractmethod
    def get_repo_detail(self, repo_name):
        '''
        get repository detail info
        :return:
        '''

    @abstractmethod
    def get_branches(self, repo_name):
        '''
        get repository branch list
        :return:
        '''

    @abstractmethod
    def get_tags(self, repo_name):
        '''
        get repository tag list
        :return:
        '''

    @abstractmethod
    def get_branches_or_tags(self, type, full_name):
        '''
        get repository branches or tags list
        :return:
        '''

    @abstractmethod
    def get_clone_url(self, url):
        '''
        get clone code url, Mainly dealing with authorization information
        base_url: Local storage url without authentication token
        :return: url string
        '''

    @abstractmethod
    def get_clone_user_password(self):
        '''
        get clone code user and password
        :return: user(string), password(string)
        '''
