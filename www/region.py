# -*- coding: utf8 -*-
from django.conf import settings

class RegionInfo(object):
    region_list = settings.REGIONS

    @classmethod
    def region_names(cls):
        return tuple([e['name'] for e in cls.region_list])

    @classmethod
    def region_labels(cls):
        return tuple([e['label'] for e in cls.region_list])

    @classmethod
    def register_choices(cls):
        choices = []
        for item in cls.region_list:
            if item['enable']:
                choices.append((item['name'], item['label']))

        return choices
