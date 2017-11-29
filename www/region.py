# -*- coding: utf8 -*-
from django.conf import settings
from www.utils import sn
from www.utils.conf_tool import regionConfig
import logging
logger = logging.getLogger("default")
class RegionInfo(object):

    # region_list = settings.REGIONS
    region_list = regionConfig.regions()

    region_ports = settings.WILD_PORTS
    region_domains = settings.WILD_DOMAINS
    is_private = sn.instance.is_private()
    if is_private:
        region_list = regionConfig.regions()[0:1]
        # region_list = settings.REGIONS[0:1]

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
    
    @classmethod
    def valid_regions(cls):
        choices = []
        for item in cls.region_list:
            if item['enable']:
                choices.append(item['name'])

        return choices

    @classmethod
    def region_port(cls, region_name):
        return cls.region_ports[region_name]

    @classmethod
    def region_domain(cls, region_name):
        return cls.region_domains[region_name]

    @classmethod
    def regions(cls):
        return regionConfig.regions()
