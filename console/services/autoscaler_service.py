# -*- coding: utf-8 -*-
import json

from django.db import IntegrityError
from django.db import transaction

from console.models.main import AutoscalerRules
from console.repositories.autoscaler_repo import autoscaler_rule_metrics_repo
from console.repositories.autoscaler_repo import autoscaler_rules_repo
from console.services.exception import ErrAutoscalerRuleNotFound
from console.services.exception import ErrDuplicateMetrics
from www.apiclient.regionapi import RegionInvokeApi
from www.utils.crypt import make_uuid

region_api = RegionInvokeApi()


class AutoscalerService(object):
    def json_autoscaler_rules(self, min_replicas, max_replicas, metrics):
        metric_type_dict = {
            "average_value": "使用量",
            "utilization": "使用率",
            "cpu": "CPU",
            "memory": "内存",
        }
        autoscaler_rules_dict = dict()
        autoscaler_rules_dict["最小实例数"] = min_replicas
        autoscaler_rules_dict["最大实例数"] = max_replicas
        for metric in metrics:
            metric_name = metric_type_dict.get(metric["metric_name"]) + metric_type_dict.get(metric["metric_target_type"])
            autoscaler_rules_dict[metric_name] = metric["metric_target_value"]
        return json.dumps(autoscaler_rules_dict, ensure_ascii=False)


    def get_by_rule_id(self, rule_id):
        try:
            rule = autoscaler_rules_repo.get_by_rule_id(rule_id)
            metrics = autoscaler_rule_metrics_repo.list_by_rule_ids([rule.rule_id])

            res = rule.to_dict()
            res["metrics"] = [m.to_dict() for m in metrics]
            return res
        except AutoscalerRules.DoesNotExist:
            raise ErrAutoscalerRuleNotFound

    def list_autoscaler_rules(self, service_id):
        rules = autoscaler_rules_repo.list_by_service_id(service_id)
        rule_ids = [rule.rule_id for rule in rules]

        metrics = autoscaler_rule_metrics_repo.list_by_rule_ids(rule_ids)
        # rule to metrics
        r2m = {}
        for metric in metrics:
            metric = metric.to_dict()
            if r2m.get(metric["rule_id"], None) is None:
                r2m[metric["rule_id"]] = [metric]
            else:
                r2m[metric["rule_id"]].append(metric)

        res = []
        for rule in rules:
            r = rule.to_dict()
            r["metrics"] = []
            if r2m.get(rule.rule_id, None) is not None:
                m = r2m[rule.rule_id]
                r["metrics"] = m
            res.append(r)

        return res

    @transaction.atomic
    def create_autoscaler_rule(self, region_name, tenant_name, service_alias, data):
        # create autoscaler rule
        autoscaler_rule = {
            "rule_id": make_uuid(),
            "service_id": data["service_id"],
            "xpa_type": data["xpa_type"],
            "enable": data["enable"],
            "min_replicas": data["min_replicas"],
            "max_replicas": data["max_replicas"],
        }
        autoscaler_rules_repo.create(**autoscaler_rule)

        # create autoscaler rule metrics
        metrics = []
        for metric in data["metrics"]:
            metrics.append({
                "rule_id": autoscaler_rule["rule_id"],
                "metric_type": metric["metric_type"],
                "metric_name": metric["metric_name"],
                "metric_target_type": metric["metric_target_type"],
                "metric_target_value": metric["metric_target_value"],
            })

        try:
            autoscaler_rule_metrics_repo.bulk_create(metrics)
        except IntegrityError:
            raise ErrDuplicateMetrics

        autoscaler_rule["metrics"] = metrics

        region_api.create_xpa_rule(region_name, tenant_name, service_alias, data=autoscaler_rule)

        return autoscaler_rule

    @transaction.atomic
    def update_autoscaler_rule(self, region_name, tenant_name, service_alias, rule_id, data, user_name=''):
        # create autoscaler rule
        autoscaler_rule = {
            "xpa_type": data["xpa_type"],
            "enable": data["enable"],
            "min_replicas": data["min_replicas"],
            "max_replicas": data["max_replicas"],
        }
        try:
            autoscaler_rule = autoscaler_rules_repo.update(rule_id, **autoscaler_rule)
        except AutoscalerRules.DoesNotExist:
            raise ErrAutoscalerRuleNotFound
        autoscaler_rule = autoscaler_rule.to_dict()

        # delete old autoscaler rule metrics
        autoscaler_rule_metrics_repo.delete_by_rule_id(rule_id)
        # create new ones
        metrics = []
        for metric in data["metrics"]:
            metrics.append({
                "rule_id": autoscaler_rule["rule_id"],
                "metric_type": metric["metric_type"],
                "metric_name": metric["metric_name"],
                "metric_target_type": metric["metric_target_type"],
                "metric_target_value": metric["metric_target_value"],
            })

        try:
            autoscaler_rule_metrics_repo.bulk_create(metrics)
        except IntegrityError:
            raise ErrDuplicateMetrics

        autoscaler_rule["metrics"] = metrics
        autoscaler_rule["operator"] = user_name

        region_api.update_xpa_rule(region_name, tenant_name, service_alias, data=autoscaler_rule)

        return autoscaler_rule

    @transaction.atomic
    def delete_autoscaler_rule(self, region_name, tenant_name, service_alias, rule_id):
        try:
            autoscaler_rule = autoscaler_rules_repo.delete(rule_id)
        except AutoscalerRules.DoesNotExist:
            raise ErrAutoscalerRuleNotFound
        autoscaler_rule = autoscaler_rule.to_dict()


class ScalingRecordsService(object):
    def list_scaling_records(self, region_name, tenant_name, service_alias, page=None, page_size=None):
        body = region_api.list_scaling_records(region_name, tenant_name, service_alias, page, page_size)
        return body["bean"]


autoscaler_service = AutoscalerService()
scaling_records_service = ScalingRecordsService()
