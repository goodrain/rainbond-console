# -*- coding: utf8 -*-


class RegionInfo(object):
    region_list = (
        {"name": "ucloud-bj-1", "label": u"ucloud[北京]", "enable": True},
        {"name": "aws-jp-1", "label": u"亚马逊[日本]", "enable": True},
        {"name": "ali-sh", "label": u"阿里云[上海]", "enable": True},
        {"name": "aws-bj-1", "label": u"亚马逊[北京]", "enable": True},
    )

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
