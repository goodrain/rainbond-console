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

    def get_events_by_event_ids(self, event_ids):
        return ServiceEvent.objects.filter(event_id__in=event_ids)

    def get_events_before_specify_time(self, tenant_id, service_id, start_time):
        if start_time:
            return ServiceEvent.objects.filter(tenant_id=tenant_id, service_id=service_id,
                                               start_time__lte=start_time).order_by("-start_time")
        else:
            return ServiceEvent.objects.filter(tenant_id=tenant_id, service_id=service_id).order_by("-start_time")

    def create_event(self, **event_info):
        return ServiceEvent.objects.create(**event_info)

    def delete_events(self, service_id):
        ServiceEvent.objects.filter(service_id=service_id).delete()

    def delete_event_by_build_version(self, service_id, deploy_version):
        ServiceEvent.objects.filter(deploy_version=deploy_version, service_id=service_id).delete()

    def get_specified_num_events(self, tenant_id, service_id, num=6):
        """查询指定条数的日志"""
        return ServiceEvent.objects.filter(tenant_id=tenant_id, service_id=service_id).order_by("-ID")[:num]

    def get_specified_region_events(self, tenant_id, region):
        return ServiceEvent.objects.filter(tenant_id=tenant_id, region=region).order_by("-ID")

    def get_evevt_by_tenant_id_region(self, tenant_id):
        event_list = ServiceEvent.objects.filter(tenant_id=tenant_id)
        if not event_list:
            return []
        else:
            return event_list


event_repo = ServiceEventRepository()
