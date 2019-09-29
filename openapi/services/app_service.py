# -*- coding: utf-8 -*-
# creater by: barnett
import logging
from console.services.service_services import base_service
from console.services.group_service import group_service
from console.services.team_services import team_services
logger = logging.getLogger("default")


class AppService(object):
    def get_app_status(self, app):
        services = group_service.get_group_services(app.ID)
        service_ids = [service.service_id for service in services]
        team = team_services.get_team_by_team_id(app.tenant_id)
        status_list = base_service.status_multi_service(
                region=app.region_name, tenant_name=team.tenant_name, service_ids=service_ids, enterprise_id=team.enterprise_id)
        # As long as there is a service running, the application thinks it is running
        app_status = "closed"
        for status in status_list:
            if status["status"] == "running":
                app_status = "running"
        return app_status, services


app_service = AppService()
