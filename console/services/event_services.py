# -*- coding: utf-8 -*-

import logging
from django.db.models import Q
import datetime

from www.apiclient.regionapi import RegionInvokeApi
from www.db import BaseConnection
from www.models.main import ServiceEvent
from goodrain_web.tools import JuncheePaginator
from console.repositories.app import service_repo
from console.services.app_actions.app_log import AppEventService
from console.repositories.team_repo import team_repo

logger = logging.getLogger("default")
region_api = RegionInvokeApi()
e_s = AppEventService()


class ServiceEventDynamic(object):
    def get_team_current_region_service_events(self, region, team, page, page_size):
        dsn = BaseConnection()
        start = (int(page)-1) * int(page_size)
        end = page_size

        query_sql = ''' select e.start_time, e.event_id,s.service_alias,s.service_cname from service_event e JOIN tenant_service s on e.service_id=s.service_id  WHERE e.tenant_id="{team_id}" and s.service_region="{region_name}" ORDER BY start_time DESC LIMIT {start},{end} '''.format(
            team_id=team.tenant_id, region_name=region, start=start, end=end)
        events = dsn.query(query_sql)
        events_ids = []
        event_id_service_info_map = dict()
        for e in events:
            events_ids.append(e.event_id)
            event_id_service_info_map[e.event_id] = {"service_alias": e.service_alias, "service_cname": e.service_cname}

        events = ServiceEvent.objects.filter(event_id__in=events_ids).order_by("-ID")
        try:
            self.__sync_region_service_event_status(region, team.tenant_name, events, False)
        except Exception as e:
            logger.exception("synchorized services events error !")
        for event in events:
            bean = event_id_service_info_map.get(event.event_id, None)
            if bean:
                event.service_alias = bean["service_alias"]
                event.service_cname = bean["service_cname"]
        return events


    def get_services_events(self, page, page_size, create_time, status, team):

        query = Q()
        status = "success" if status == "complete" else status
        if team:
            query &= Q(tenant_id=team.tenant_id)
        if create_time:
            query &= Q(start_time__gte=create_time)
        if status:
            query &= Q(status=status)

        events = ServiceEvent.objects.filter(query).order_by("-ID")
        logger.debug(events.query)
        total = events.count()
        paginator = JuncheePaginator(events, int(page_size))
        show_events = paginator.page(int(page))
        service_ids = list(set([e.service_id for e in show_events]))
        team_ids = list(set([e.tenant_id for e in show_events]))
        teams = team_repo.get_team_by_team_ids(team_ids)
        services = service_repo.get_services_by_service_ids(*service_ids)
        id_service_map = {s.service_id: s for s in services}
        id_team_map = {t.tenant_id: t for t in teams}
        # 数据中心对应的event
        region_events_map = {}
        for event in show_events:
            service = id_service_map.get(event.service_id, None)
            t = id_team_map.get(event.tenant_id, None)
            if service:
                event.service_cname = service.service_cname
                event.service_alias = service.service_alias
                event.team_name = t.tenant_name if t else None
                event.service_region = service.service_region
                # 处理数据中心对应的event
                if event.final_status == "" and not status:
                    region_events = region_events_map.get(service.service_region, [])
                    if region_events:
                        region_events.append(event)
                    else:
                        region_events_map[service.service_region] = [event]
            else:
                event.service_cname = None
                event.service_alias = None
                event.team_name = None
                event.service_region = None
        if not status:
            # 从数据中心更新信息
            for region, events in region_events_map.iteritems():
                # 同步数据中心信息
                self.__sync_events(region, events)

        return show_events, total

    def __sync_events(self, region, events, timeout=False):
        local_events_not_complete = {event.event_id: event for event in events}
        try:
            body = region_api.get_events_by_event_ids(region, local_events_not_complete.keys())
        except Exception as e:
            logger.exception(e)
            return
        region_events = body.get('list')
        for region_event in region_events:
            local_event = local_events_not_complete.get(region_event.get('EventID'))
            if not local_event:
                continue
            if not region_event.get('Status'):
                if timeout:
                    e_s.checkEventTimeOut(local_event)
            else:
                local_event.status = region_event.get('Status')
                local_event.message = region_event.get('Message')
                local_event.code_version = region_event.get('CodeVersion')
                local_event.deploy_version = region_event.get('DeployVersion')
                local_event.final_status = 'complete'
                endtime = datetime.datetime.strptime(region_event.get('EndTime')[0:19], '%Y-%m-%d %H:%M:%S')
                if endtime:
                    local_event.end_time = endtime
                else:
                    local_event.end_time = datetime.datetime.now()
                local_event.save()


    def __sync_region_service_event_status(self, region, tenant_name, events, timeout=False):
        local_events_not_complete = dict()
        for event in events:
            if event.final_status == '':
                local_events_not_complete[event.event_id] = event

        if not local_events_not_complete:
            return

        try:
            body = region_api.get_tenant_events(region, tenant_name, local_events_not_complete.keys())
        except Exception as e:
            logger.exception(e)
            return

        region_events = body.get('list')
        for region_event in region_events:
            local_event = local_events_not_complete.get(region_event.get('EventID'))
            if not local_event:
                continue
            if not region_event.get('Status'):
                if timeout:
                    e_s.checkEventTimeOut(local_event)
            else:
                local_event.status = region_event.get('Status')
                local_event.message = region_event.get('Message')
                local_event.code_version = region_event.get('CodeVersion')
                local_event.deploy_version = region_event.get('DeployVersion')
                local_event.final_status = 'complete'
                endtime = datetime.datetime.strptime(region_event.get('EndTime')[0:19], '%Y-%m-%d %H:%M:%S')
                if endtime:
                    local_event.end_time = endtime
                else:
                    local_event.end_time = datetime.datetime.now()
                local_event.save()

service_event_dynamic = ServiceEventDynamic()
