# -*- coding: utf-8 -*-
import json

from www.models.main import TenantServiceInfo


def populate_event_dependencies(events, tenant_id, include_empty=False):
    """Resolve dependency names once per response, keeping each event's alias order."""
    initiating = [(event, (event.get("message") or "").split(","))
                  for event in events if event.get("opt_type") == "INITIATING"]
    aliases = {alias for _, event_aliases in initiating for alias in event_aliases if alias}
    services = {}
    if aliases:
        for service in TenantServiceInfo.objects.filter(tenant_id=tenant_id, service_alias__in=aliases).order_by("pk"):
            # Match the previous unordered QuerySet.first() selection if legacy
            # data contains duplicate aliases despite the model's unique constraint.
            services.setdefault(service.service_alias, service)

    for event, event_aliases in initiating:
        dependencies = [{"service_cname": services[alias].service_cname, "serivce_alias": alias}
                        for alias in event_aliases if alias in services]
        if dependencies or include_empty:
            event["Message"] = "依赖的其他组件暂未运行 {0}".format(json.dumps(dependencies, ensure_ascii=False))
