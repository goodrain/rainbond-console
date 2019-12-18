# -*- coding: utf8 -*-
from oauth_test_impl import OAuth2Test

support_oauth_type = {
    "test": OAuth2Test,
}


class NoSupportOAuthType(Exception):
    """
    type not support
    """


def get_support_oauth_servers():
    '''
    get the supported oauth server type
    '''
    all_types = []
    for key in support_oauth_type:
        all_types.append(key)
    return all_types


def get_oauth_instance(type_str, oauth_service, oauth_user):
    if type_str in support_oauth_type:
        instance = support_oauth_type[type_str]()
        instance.set_oauth_service(oauth_service)
        instance.set_oauth_service(oauth_user)
        return instance
    raise NoSupportOAuthType()
