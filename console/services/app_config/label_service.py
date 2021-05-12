# -*- coding: utf8 -*-
"""
  Created on 18/1/30.
"""
import logging

from console.repositories.label_repo import label_repo
from console.repositories.label_repo import node_label_repo
from console.repositories.label_repo import service_label_repo
from console.repositories.region_repo import region_repo
from www.apiclient.regionapi import RegionInvokeApi
from www.models.label import ServiceLabels

logger = logging.getLogger("default")
region_api = RegionInvokeApi()


class LabelService(object):
    def get_service_labels(self, service):
        service_label_ids = service_label_repo.get_service_labels(service.service_id).values_list("label_id", flat=True)
        logger.debug('----------------->{0}'.format(service_label_ids))
        region_config = region_repo.get_region_by_region_name(service.service_region)
        node_label_ids = []
        # 判断标签是否被节点使用
        if region_config:
            node_label_ids = node_label_repo.get_node_label_by_region(
                region_config.region_id).exclude(label_id__in=service_label_ids).values_list("label_id", flat=True)
        used_labels = label_repo.get_labels_by_label_ids(service_label_ids)
        logger.debug('-----------used_labels------->{0}'.format(used_labels))
        unused_labels = []
        if node_label_ids:
            unused_labels = label_repo.get_labels_by_label_ids(node_label_ids)

        result = {
            "used_labels": [label.to_dict() for label in used_labels],
            "unused_labels": [label.to_dict() for label in unused_labels],
        }
        return result

    def add_service_labels(self, tenant, service, label_ids, user_name=''):
        labels = label_repo.get_labels_by_label_ids(label_ids)
        labels_list = list()
        body = dict()
        label_map = [label.label_name for label in labels]
        service_labels = list()
        for label_id in label_ids:
            service_label = ServiceLabels(tenant_id=tenant.tenant_id,
                                          service_id=service.service_id,
                                          label_id=label_id,
                                          region=service.service_region)
            service_labels.append(service_label)

        if service.create_status == "complete":
            for label_name in label_map:
                label_dict = dict()
                label_dict["label_key"] = "node-selector"
                label_dict["label_value"] = label_name
                labels_list.append(label_dict)
            body["labels"] = labels_list
            body["operator"] = user_name
            try:
                region_api.addServiceNodeLabel(service.service_region, tenant.tenant_name, service.service_alias, body)
            except region_api.CallApiError as e:
                if "is exist" not in e.body.get("msg"):
                    logger.exception(e)
                    return 507, "组件异常", None
        ServiceLabels.objects.bulk_create(service_labels)
        return 200, "操作成功", None

    def get_region_labels(self, tenant, service):
        try:
            data = region_api.get_region_labels(service.service_region, tenant.tenant_name)
        except region_api.CallApiError as e:
            logger.exception(e)
            return 507, "组件异常", None

        return 200, "操作成功", data["list"]

    def delete_service_label(self, tenant, service, label_id, user_name=''):

        label = label_repo.get_label_by_label_id(label_id)
        if not label:
            return 404, "指定标签不存在", None
        body = dict()
        # 组件标签删除
        label_dict = dict()
        label_list = list()
        label_dict["label_key"] = "node-selector"
        label_dict["label_value"] = label.label_name
        label_list.append(label_dict)
        body["labels"] = label_list
        body["operator"] = user_name
        logger.debug('-------------------->{0}'.format(body))
        try:
            region_api.deleteServiceNodeLabel(service.service_region, tenant.tenant_name, service.service_alias, body)
            service_label_repo.delete_service_labels(service.service_id, label_id)
        except region_api.CallApiError as e:
            logger.exception(e)
            return 507, "组件异常", None

        return 200, "success", None

    def update_service_state_label(self, tenant, service):
        service_status = service.extend_method
        label_dict = dict()
        body = dict()
        # made ...
        body["label_key"] = "service-type"
        body["label_value"] = "StatelessServiceType" if service_status == "stateless" else "StatefulServiceType"
        label_list = list()
        label_list.append(body)
        label_dict["labels"] = label_list
        region_api.update_service_state_label(service.service_region, tenant.tenant_name, service.service_alias, label_dict)
        return 200, "success"

    def set_service_os_label(self, tenant, service, os):
        os_label = label_repo.get_labels_by_label_name(os)
        if not os_label:
            os_label = label_repo.create_label(os, os)
        return self.add_service_labels(tenant, service, [os_label.label_id])

    def get_service_os_name(self, service):
        os_label = label_repo.get_labels_by_label_name("windows")
        if os_label:
            if service_label_repo.get_service_label(service.service_id, os_label.label_id):
                return "windows"
        return "linux"
