from console.exception.main import ServiceHandleException
from console.repositories.group import group_service_relation_repo
from www.apiclient.regionapi import RegionInvokeApi
import logging

region_api = RegionInvokeApi()
logger = logging.getLogger('default')


class Service_overview(object):
    def get_service_overview(self, enterprise_id, region_name):
        service_count = group_service_relation_repo.get_service_number(region_name)
        running_component_ids = list()
        abnormal_component_ids = list()
        try:
            data = region_api.get_enterprise_running_services(enterprise_id, region_name, test=True)
        except (region_api.CallApiError, ServiceHandleException) as e:
            logger.exception("get region:'{0}' running failed: {1}".format(region_name, e))
        if data:
            if data.get("service_ids"):
                running_component_ids.extend(data.get("service_ids"))
            if data.get("abnormal_ids"):
                abnormal_component_ids.extend(data.get("abnormal_ids"))
        run_count = len(running_component_ids)
        abnormal_count = len(abnormal_component_ids)
        return run_count, abnormal_count, service_count - run_count - abnormal_count


service_overview = Service_overview()
