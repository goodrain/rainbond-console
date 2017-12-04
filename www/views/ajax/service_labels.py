# -*- coding: utf8 -*-

import json
import logging

from django.forms.models import model_to_dict
from django.http import JsonResponse
from django.views.decorators.cache import never_cache

from backends.models.main import RegionConfig
from www.apiclient.regionapi import RegionInvokeApi
from www.decorator import perm_required
from www.models import ServiceEvent
from www.models.label import *
from www.utils.crypt import make_uuid
from www.views import AuthedView
from www.views.mixin import LeftSideBarMixin

logger = logging.getLogger('default')
region_api = RegionInvokeApi()


def create_label_event(tenant, user, service, action):
    try:
        import datetime
        event = ServiceEvent(event_id=make_uuid(), service_id=service.service_id,
                             tenant_id=tenant.tenant_id, type="{0}".format(action),
                             deploy_version=service.deploy_version,
                             old_deploy_version=service.deploy_version,
                             user_name=user.nick_name, start_time=datetime.datetime.now())
        event.save()
        return event.event_id
    except Exception as e:
        raise e


class ServiceLabelsView(LeftSideBarMixin, AuthedView):
    @never_cache
    @perm_required("view_service")
    def get(self, request, *args, **kwargs):
        result = {}
        service_id = self.service.service_id
        try:
            service_label_ids = ServiceLabels.objects.filter(service_id=service_id).values_list("label_id", flat=True)
            region = self.response_region
            region_confs = RegionConfig.objects.filter(region_name=region)

            node_label_ids = []
            # 判断标签是否被节点使用
            if region_confs:
                region_conf = region_confs[0]
                node_label_ids = NodeLabels.objects.filter(region_id=region_conf.region_id).exclude(
                    label_id__in=service_label_ids).values_list("label_id",
                                                                flat=True)
            used_labels = Labels.objects.filter(label_id__in=service_label_ids)
            unused_labels = []
            if node_label_ids:
                unused_labels = Labels.objects.filter(label_id__in=node_label_ids)
            result["used_labels"] = [model_to_dict(label) for label in used_labels]
            result["unused_labels"] = [model_to_dict(label) for label in unused_labels]
            result["ok"] = True
            result["msg"] = "查询成功"
        except Exception as e:
            logger.exception(e)
            result["ok"] = False

        return JsonResponse(result, status=200)

    @never_cache
    @perm_required("manage_service")
    def post(self, request, *args, **kwargs):
        label_ids = request.POST.get("labels", None)
        result = {}
        try:
            label_ids = json.loads(label_ids)
            labels = Labels.objects.filter(label_id__in=label_ids)
            # 标签ID和标签英文名称字符串
            label_map = {l.label_id: l.label_name for l in labels}
            service_labels = []
            for label_id in label_ids:
                service_label = ServiceLabels(
                    tenant_id=self.tenant.tenant_id,
                    service_id=self.service.service_id,
                    label_id=label_id,
                    region=self.response_region
                )
                service_labels.append(service_label)
            ServiceLabels.objects.bulk_create(service_labels)
            event_id = create_label_event(self.tenant, self.user, self.service, "add_label")
            body = {}
            body["event_id"] = event_id
            label_name_list = []
            for label_id in label_ids:
                label_name = label_map.get(label_id, None)
                if label_name:
                    label_name_list.append(label_name)

            body["label_values"] = label_name_list
            body["enterprise_id"] = self.tenant.enterprise_id
            region_api.addServiceNodeLabel(self.response_region, self.tenantName, self.serviceAlias, body)
            result["ok"] = True
            result["msg"] = "添加标签成功"
        except Exception as e:
            logger.exception(e)
            result["ok"] = False
            result["msg"] = "系统异常"
        return JsonResponse(result, status=200)


class ServiceLabelsManageView(LeftSideBarMixin, AuthedView):
    @never_cache
    @perm_required("manage_service")
    def post(self, request, *args, **kwargs):
        label_id = request.POST.get("label_id", None)
        result = {}
        try:
            event_id = create_label_event(self.tenant, self.user, self.service, "delete_label")
            label = Labels.objects.get(label_id=label_id)
            body = {}
            body["event_id"] = event_id
            # 服务标签删除
            body["label_values"] = [label.label_name]
            body["enterprise_id"] = self.tenant.enterprise_id
            region_api.deleteServiceNodeLabel(self.response_region, self.tenantName, self.serviceAlias,
                                              body)
            ServiceLabels.objects.filter(service_id=self.service.service_id, label_id=label_id).delete()
            result["ok"] = True
            result["msg"] = "删除成功"
        except Exception as e:
            logger.exception(e)
            result["ok"] = False
            result["msg"] = "系统异常"
        return JsonResponse(result, status=200)
