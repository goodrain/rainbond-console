# -*- coding: utf8 -*-
from django.conf import settings

class ServiceType(object):
    
    type_list = (
        {"name": "mysql", "label": 'mysql', "enable": True},
        {"name": "redis", "label": 'redis', "enable": True},
        {"name": "memcached", "label": 'memcached', "enable": True},
        {"name": "postgresql", "label": 'postgresql', "enable": True},
        {"name": "mongodb", "label": 'mongodb', "enable": True},
        {"name": "application", "label": 'application', "enable": True},
    )

    @classmethod
    def type_names(cls):
        return tuple([e['name'] for e in cls.type_list])

    @classmethod
    def type_labels(cls):
        return tuple([e['label'] for e in cls.type_list])

    @classmethod
    def type_choices(cls):
        choices = []
        for item in cls.type_list:
            if item['enable']:
                choices.append((item['name'], item['label']))

        return choices
    
    @classmethod
    def type_maps(cls):
        choices = {}
        for item in cls.type_list:
            if item['enable']:
                choices[item['name']] = item['label']
        return choices
    
    @classmethod
    def type_lists(cls):
        choices = []
        for item in cls.type_list:
            if item['enable']:
                if item['name'] != "application":
                    choices.append(item['name'])
        return choices
