# -*- coding: utf8 -*-
import logging

from django.views.decorators.cache import never_cache
from rest_framework.response import Response

from console.exception.main import AbortRequest
from console.models.main import AutoscalerRules, AutoscalerRuleMetrics
from console.services.autoscaler_service import autoscaler_service
from console.services.autoscaler_service import scaling_records_service
from console.services.operation_log import operation_log_service, Operation
from console.utils.reqparse import parse_item
from console.views.app_config.base import AppBaseView
from www.utils.return_message import general_message

logger = logging.getLogger("default")


def validate_parameter(data):
    xpa_type = parse_item(data, key="xpa_type", required=True)
    if xpa_type not in ["hpa"]:
        raise AbortRequest(msg="unsupported xpa_type: " + xpa_type)

    parse_item(data, key="enable", required=True)

    min_replicas = parse_item(data, key="min_replicas", required=True)
    if min_replicas <= 0 or min_replicas > 65535:
        raise AbortRequest(msg="the range of min_replicas is (0, 65535]")

    max_replicas = parse_item(data, key="max_replicas", required=True)
    if max_replicas <= 0 or max_replicas > 65535:
        raise AbortRequest(msg="the range of max_replicas is (0, 65535]")
    if max_replicas < min_replicas:
        raise AbortRequest(msg="max_replicas must be greater than min_replicas")

    metrics = parse_item(data, key="metrics", required=True)
    if len(metrics) < 1:
        raise AbortRequest(msg="need at least one metric")
    for metric in metrics:
        metric_type = parse_item(metric, key="metric_type", required=True)
        if metric_type not in ["resource_metrics"]:
            raise AbortRequest(msg="unsupported metric type: {}".format(metric_type))
        metric_name = parse_item(metric, key="metric_name", required=True)
        # The metric_name of resource_metrics can only be cpu or memory
        if metric_name not in ["cpu", "memory"]:
            raise AbortRequest(msg="resource_metrics does not support metric name: {}".format(metric_name))
        metric_target_type = parse_item(metric, key="metric_target_type", required=True)
        if metric_target_type not in ["utilization", "average_value"]:
            raise AbortRequest(msg="unsupported metric target type: {}".format(metric_target_type))
        metric_target_value = parse_item(metric, key="metric_target_value", required=True)
        if metric_target_value < 0 or metric_target_value > 65535:
            raise AbortRequest(msg="the range of metric_target_value is [0, 65535]")


class ListAppAutoscalerView(AppBaseView):
    @never_cache
    def get(self, req, *args, **kwargs):
        rules = autoscaler_service.list_autoscaler_rules(self.service.service_id)
        result = general_message(200, "success", "查询成功", list=rules)
        return Response(data=result, status=200)

    @never_cache
    def post(self, req, *args, **kwargs):
        validate_parameter(req.data)

        data = req.data
        data["service_id"] = self.service.service_id
        res = autoscaler_service.create_autoscaler_rule(self.region_name, self.tenant.tenant_name, self.service.service_alias,
                                                        data)
        new_information = autoscaler_service.json_autoscaler_rules(
            max_replicas=req.data["max_replicas"], min_replicas=req.data["min_replicas"], metrics=req.data["metrics"])
        result = general_message(200, "success", "创建成功", bean=res)
        comment = operation_log_service.generate_component_comment(
            operation=Operation.CREATE,
            module_name=self.service.service_cname,
            region=self.service.service_region,
            team_name=self.tenant.tenant_name,
            service_alias=self.service.service_alias,
            suffix=" 的自动伸缩规则")
        operation_log_service.create_component_log(
            user=self.user,
            comment=comment,
            enterprise_id=self.user.enterprise_id,
            team_name=self.tenant.tenant_name,
            app_id=self.app.ID,
            service_alias=self.service.service_alias,
            new_information=new_information)
        return Response(data=result, status=200)


class AppAutoscalerView(AppBaseView):
    @never_cache
    def get(self, req, rule_id, *args, **kwargs):
        res = autoscaler_service.get_by_rule_id(rule_id)

        result = general_message(200, "success", "创建成功", bean=res)
        return Response(data=result, status=200)

    @never_cache
    def put(self, req, rule_id, *args, **kwargs):
        validate_parameter(req.data)
        old = AutoscalerRules.objects.get(rule_id=rule_id)
        old_metrics = AutoscalerRuleMetrics.objects.filter(rule_id=rule_id).values()
        old_information = autoscaler_service.json_autoscaler_rules(
            max_replicas=old.max_replicas, min_replicas=old.min_replicas, metrics=old_metrics)
        res = autoscaler_service.update_autoscaler_rule(self.region_name, self.tenant.tenant_name, self.service.service_alias,
                                                        rule_id, req.data, self.user.nick_name)

        new_information = autoscaler_service.json_autoscaler_rules(
            max_replicas=req.data["max_replicas"], min_replicas=req.data["min_replicas"], metrics=req.data["metrics"])
        if req.data["enable"] and not old.enable:
            old_information = None
        elif not req.data["enable"] and old.enable:
            new_information = None
        result = general_message(200, "success", "创建成功", bean=res)
        comment = operation_log_service.generate_component_comment(
            operation=Operation.UPDATE,
            module_name=self.service.service_cname,
            region=self.service.service_region,
            team_name=self.tenant.tenant_name,
            service_alias=self.service.service_alias,
            suffix=" 的自动伸缩规则")
        operation_log_service.create_component_log(
            user=self.user,
            comment=comment,
            enterprise_id=self.user.enterprise_id,
            team_name=self.tenant.tenant_name,
            app_id=self.app.ID,
            service_alias=self.service.service_alias,
            old_information=old_information,
            new_information=new_information)
        return Response(data=result, status=200)


class AppScalingRecords(AppBaseView):
    @never_cache
    def get(self, req, *args, **kwargs):
        page = req.GET.get("page", 1)
        page_size = req.GET.get("page_size", 10)

        data = scaling_records_service.list_scaling_records(self.region_name, self.tenant.tenant_name,
                                                            self.service.service_alias, page, page_size)
        result = general_message(200, "success", "查询成功", bean=data)
        return Response(data=result, status=200)
