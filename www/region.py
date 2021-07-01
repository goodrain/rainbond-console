# -*- coding: utf8 -*-
from www.utils.conf_tool import regionConfig
import logging

logger = logging.getLogger("default")


class RegionInfo(object):
    @classmethod
    def region_names(cls, region_list):
        return tuple([e['name'] for e in region_list])

    @classmethod
    def region_labels(cls, region_list):
        return tuple([e['label'] for e in region_list])

    @classmethod
    def register_choices(cls, region_list):
        choices = []
        for item in region_list:
            if item['enable']:
                choices.append((item['name'], item['label']))

        return choices

    @classmethod
    def regions(cls):
        return regionConfig.regions()
