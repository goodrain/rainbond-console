# -*- coding: utf8 -*-
"""
  Created on 18/1/24.
"""
from www.models.main import ServiceEvent


class ServiceEventRepository(object):
    def get_last_event(self, tenant_id, service_id):
        events = ServiceEvent.objects.filter(tenant_id=tenant_id, service_id=service_id).order_by("-start_time")
        if events:
            return events[0]
        return None

    def get_last_deploy_event(self, tenant_id, service_id):
        events = ServiceEvent.objects.filter(tenant_id=tenant_id, service_id=service_id).order_by("-start_time")
        if events:
            return events[0]
        return None

    def get_event_by_event_id(self, event_id):
        try:
            return ServiceEvent.objects.get(event_id=event_id)
        except ServiceEvent.DoesNotExist:
            return None

    def get_events_before_specify_time(self, tenant_id, service_id, start_time):
        return ServiceEvent.objects.filter(tenant_id=tenant_id, service_id=service_id,
                                           start_time__lte=start_time).order_by("-start_time")

    def create_event(self, **event_info):
        return ServiceEvent.objects.create(**event_info)

    def delete_events(self, service_id):
        ServiceEvent.objects.filter(service_id=service_id).delete()

event_repo = ServiceEventRepository()
