# -*- coding: utf8 -*-
import logging

from django.db.models import Q
from fuzzyfinder.main import fuzzyfinder

from backends.services.exceptions import *
from www.models.label import Labels, ServiceLabels, NodeLabels
from www.utils.crypt import make_uuid

logger = logging.getLogger("default")


class LabelService(object):
    def get_all_labels(self):
        """
        获取所有的标签
        """
        labels = Labels.objects.all()
        return labels

    def get_label_by_label_name(self, label_alias):
        labels = Labels.objects.filter(label_alias=label_alias)
        if not labels:
            raise LabelNotExistError("标签{0}不存在".format(label_alias))
        return labels[0]

    def get_service_num_by_label(self, label_id):
        service_labels = ServiceLabels.objects.filter(label_id=label_id)
        return service_labels

    def get_node_num_by_label(self, label_id):
        node_labels = NodeLabels.objects.filter(label_id=label_id)
        return node_labels

    def get_label_usage(self, label_alias):
        if not label_alias:
            labels = self.get_all_labels()
        else:
            labels = []
            l = self.get_label_by_label_name(label_alias)
            labels.append(l)
        label_list = []
        for label in labels:
            label_info = {}
            service_num = self.get_service_num_by_label(label.label_id)
            node_num = self.get_node_num_by_label(label.label_id)
            label_info.update(label.to_dict())
            label_info["service_num"] = len(service_num)
            label_info["node_num"] = len(node_num)
            label_list.append(label_info)
        return label_list

    def add_label(self, label_alias):
        if not label_alias:
            raise ParamsError("标签名不能为空")
        labels = Labels.objects.filter(label_alias=label_alias)
        if labels:
            raise LabelExistError("标签名{0}已存在".format(label_alias))
        label_name = self.chinese2pinyin(label_alias)

        while Labels.objects.filter(label_name=label_name).count() > 0:
            label_name = label_name + make_uuid(label_name)[-3:]

        label_id = make_uuid(label_name)
        label = Labels(label_id=label_id, label_name=label_name, label_alias=label_alias)
        label.save()
        return label

    def delete_label(self, label_id):
        label = Labels.objects.get(label_id=label_id)
        # TODO 删除region端对应的数据

        # 删除标签与应用的关系
        ServiceLabels.objects.filter(label_id=label_id).delete()
        # TODO 删除Node上的标签

        # 删除标签和节点的关系
        NodeLabels.objects.filter(label_id=label_id).delete()
        label.delete()
        return label

    def chinese2pinyin(self, character):
        """
        汉字转拼音
        """
        from pypinyin import lazy_pinyin
        if isinstance(character, unicode):
            res = lazy_pinyin(character)
        else:
            character = character.decode("utf-8")
            res = lazy_pinyin(character)
        pinyin = ""
        for py in res:
            pinyin += py
        return pinyin

    def get_fuzzy_labels(self, label_alias):
        label_alias_map = list(Labels.objects.values("label_alias"))
        label_alias_list = map(lambda x: x.get("label_alias", "").lower(), label_alias_map)
        find_label_alias = list(fuzzyfinder(label_alias.lower(), label_alias_list))
        label_query = Q(label_alias__in=find_label_alias)
        label_list = Labels.objects.filter(label_query)
        return label_list


label_service = LabelService()
