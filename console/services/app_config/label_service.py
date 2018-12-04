# -*- coding: utf8 -*-
"""
  Created on 18/1/30.
"""

from console.repositories.label_repo import service_label_repo, node_label_repo, label_repo
from console.repositories.region_repo import region_repo
from www.apiclient.regionapi import RegionInvokeApi
from www.models import ServiceLabels
from console.services.app_actions.app_log import AppEventService
import logging

logger = logging.getLogger("default")
event_service = AppEventService()
region_api = RegionInvokeApi()


class LabelService(object):
    def get_service_labels(self, service):
        service_label_ids = service_label_repo.get_service_labels(service.service_id).values_list("label_id", flat=True)
        region_config = region_repo.get_region_by_region_name(service.service_region)
        node_label_ids = []
        # 判断标签是否被节点使用
        if region_config:
            node_label_ids = node_label_repo.get_node_label_by_region(region_config.region_id).exclude(
                label_id__in=service_label_ids).values_list("label_id",
                                                            flat=True)
        used_labels = label_repo.get_labels_by_label_ids(service_label_ids)
        unused_labels = []
        if node_label_ids:
            unused_labels = label_repo.get_labels_by_label_ids(node_label_ids)

        result = {
            "used_labels": [label.to_dict() for label in used_labels],
            "unused_labels": [label.to_dict() for label in unused_labels],

        }
        return result

    def add_service_labels(self, tenant, service, label_ids):
        labels = label_repo.get_labels_by_label_ids(label_ids)
        labels_list = list()
        body = dict()
        label_map = [l.label_name for l in labels]
        service_labels = list()
        for label_id in label_ids:
            service_label = ServiceLabels(
                tenant_id=tenant.tenant_id,
                service_id=service.service_id,
                label_id=label_id,
                region=service.service_region
            )
            service_labels.append(service_label)

        if service.create_status == "complete":
            label_dict = dict()
            label_dict["label_key"] = "node-selector"
            label_dict["label_value"] = label_map
            labels_list.append(label_dict)
        body["labels"] = labels_list
        try:
            region_api.addServiceNodeLabel(service.service_region, tenant.tenant_name, service.service_alias, body)
            ServiceLabels.objects.bulk_create(service_labels)
        except region_api.CallApiError as e:
            logger.exception(e)
            return 507, u"服务异常", None

        return 200, u"操作成功", None

    def delete_service_label(self, tenant, service, label_id):

        label = label_repo.get_label_by_label_id(label_id)
        if not label:
            return 404, u"指定标签不存在", None
        body = dict()
        # 服务标签删除
        body["label_key"] = "node-selector"
        body["label_value"] = label.label_name
        try:
            region_api.deleteServiceNodeLabel(service.service_region, tenant.tenant_name, service.service_alias,
                                              body)
            service_label_repo.delete_service_labels(service.service_id, label_id)
        except region_api.CallApiError as e:
            logger.exception(e)
            return 507, u"服务异常", None

        return 200, u"success", None

    def update_service_state_label(self, tenant, service):
        service_status = service.extend_method
        body = {}
        # made ...
        body["label_key"] = "service-type"
        body["label_value"] = "无状态的应用" if service_status == "stateless" else "有状态的应用"
        region_api.update_service_state_label(service.service_region, tenant.tenant_name, service.service_alias, body)
        return 200, u"success"
