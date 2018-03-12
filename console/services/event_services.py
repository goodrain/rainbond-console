# -*- coding: utf-8 -*-

import logging

from www.db import BaseConnection

logger = logging.getLogger("default")


class ServiceEventDynamic(object):
    def get_event_service_dynamic(self, team_id, region_name):
        dsn = BaseConnection()
        query_sql = '''
            SELECT e.type,e.start_time,e.status,e.final_status,s.service_alias,s.service_cname,u.nick_name,u.user_id FROM `service_event` e,tenant_service s, user_info u WHERE e.service_id=s.service_id and e.user_name=u.nick_name and e.tenant_id="{team_id}" and s.service_region="{region_name}" ORDER BY start_time DESC LIMIT 0,60;
        '''.format(team_id=team_id, region_name=region_name)
        event_service_dynamic = dsn.query(query_sql)
        return event_service_dynamic


service_event_dynamic = ServiceEventDynamic()
