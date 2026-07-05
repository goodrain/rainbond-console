# -*- coding: utf-8 -*-
from typing import Any, List

from django.db.models import QuerySet

from console.models.main import AutoscalerRuleMetrics
from console.models.main import AutoscalerRules


class AutoscalerRulesRepository(object):
    def create(self, **data: Any) -> AutoscalerRules:
        return AutoscalerRules.objects.create(**data)

    def update(self, rule_id: str, **data: Any) -> AutoscalerRules:
        AutoscalerRules.objects.filter(rule_id=rule_id).update(**data)
        res = AutoscalerRules.objects.get(rule_id=rule_id)
        return res

    def list_by_service_id(self, service_id: str) -> QuerySet:
        return AutoscalerRules.objects.filter(service_id=service_id)

    def get_by_rule_id(self, rule_id: str) -> AutoscalerRules:
        return AutoscalerRules.objects.get(rule_id=rule_id)


class AutoscalerRuleMetricsRepository(object):
    def bulk_create(self, data: Any) -> List[AutoscalerRuleMetrics]:
        metrics = []
        for item in data:
            metrics.append(
                AutoscalerRuleMetrics(
                    rule_id=item["rule_id"],
                    metric_type=item["metric_type"],
                    metric_name=item["metric_name"],
                    metric_target_type=item["metric_target_type"],
                    metric_target_value=item["metric_target_value"],
                ))
        return AutoscalerRuleMetrics.objects.bulk_create(metrics)

    def list_by_rule_ids(self, rule_ids: Any) -> QuerySet:
        return AutoscalerRuleMetrics.objects.filter(rule_id__in=rule_ids)

    def update_or_create(self, rule_id: str, metric: dict) -> AutoscalerRuleMetrics:
        try:
            m = AutoscalerRuleMetrics.objects.get(
                rule_id=rule_id, metric_type=metric["metric_type"], metric_name=metric["metric_name"])
            m.metric_target_type = metric["metric_target_type"]
            m.metric_target_value = metric["metric_target_value"]
            m.save()
            return m
        except AutoscalerRuleMetrics.DoesNotExist:
            return AutoscalerRuleMetrics.objects.create(
                rule_id=rule_id,
                metric_type=metric["metric_type"],
                metric_name=metric["metric_name"],
                metric_target_type=metric["metric_target_type"],
                metric_target_value=metric["metric_target_value"])

    def delete_by_rule_id(self, rule_id: str) -> None:
        AutoscalerRuleMetrics.objects.filter(rule_id=rule_id).delete()


autoscaler_rules_repo = AutoscalerRulesRepository()
autoscaler_rule_metrics_repo = AutoscalerRuleMetricsRepository()
