# -*- coding: utf-8 -*-
import logging

from console.repositories.app_config import port_repo
from console.repositories.base import BaseConnection
from console.services.service_services import base_service
from www.models.main import ServiceEvent
from www.models.main import TenantServiceInfo
from www.models.main import ServiceGroupRelation
from www.utils.status_translate import get_status_info_map

logger = logging.getLogger("default")


class ServiceRepo(object):
    def check_sourcecode_svc_by_eid(self, eid):
        conn = BaseConnection()
        sql = """
            SELECT
                service_alias
            FROM
                tenant_service a,
                tenant_info b
            WHERE
                a.tenant_id = b.tenant_id
                AND b.enterprise_id = "{eid}"
                AND a.service_source = "source_code"
                AND a.create_status = "complete"
                LIMIT 1""".format(eid=eid)
        result = conn.query(sql)
        return True if len(result) > 0 else False

    def check_image_svc_by_eid(self, eid):
        conn = BaseConnection()
        sql = """
            SELECT
                service_alias
            FROM
                tenant_service a,
                tenant_info b
            WHERE
                a.tenant_id = b.tenant_id
                AND b.enterprise_id = "{eid}"
                AND a.create_status="complete"
                AND a.service_source IN ( "docker_image", "docker_compose", "docker_run" )
                LIMIT 1""".format(eid=eid)
        result = conn.query(sql)
        return True if len(result) > 0 else False

    def check_db_from_market_by_eid(self, eid):
        conn = BaseConnection()
        sql = """
            SELECT
                service_alias
            FROM
                tenant_service a,
                tenant_info b
            WHERE
                a.tenant_id = b.tenant_id
                AND b.enterprise_id = "{eid}"
                AND a.service_source = "market"
                AND ( a.image LIKE "%mysql%" OR a.image LIKE "%postgres%" OR a.image LIKE "%mariadb%" )
                LIMIT 1""".format(eid=eid)
        result = conn.query(sql)
        return True if len(result) > 0 else False

    def list_svc_by_tenant(self, tenant):
        return TenantServiceInfo.objects.filter(tenant_id=tenant.tenant_id)

    def get_team_service_num_by_team_id(self, team_id, region_name):
        return ServiceGroupRelation.objects.filter(tenant_id=team_id, region_name=region_name).count()

    def get_group_service_by_group_id(self, group_id, region_name, team_id, team_name, enterprise_id, query=""):
        group_services_list = base_service.get_group_services_list(team_id, region_name, group_id, query)
        if not group_services_list:
            return []
        service_ids = [service.service_id for service in group_services_list]
        status_list = base_service.status_multi_service(region_name, team_name, service_ids, enterprise_id)
        status_cache = {}
        statuscn_cache = {}
        for status in status_list:
            status_cache[status["service_id"]] = status["status"]
            statuscn_cache[status["service_id"]] = status["status_cn"]
        result = []
        component_ports = port_repo.list_by_service_ids(team_id, [component.get("service_id") for component in group_services_list])
        component_port_map = {component_port.service_id: component_port.k8s_service_name for component_port in component_ports}
        for service in group_services_list:
            service["k8s_service_name"] = component_port_map.get(service["service_id"])
            service_obj = TenantServiceInfo.objects.filter(service_id=service["service_id"]).first()
            if service_obj:
                service["service_source"] = service_obj.service_source
            service["status_cn"] = statuscn_cache.get(service["service_id"], "未知")
            status = status_cache.get(service["service_id"], "unknow")

            if status == "unknow" and service["create_status"] != "complete":
                service["status"] = "creating"
                service["status_cn"] = "创建中"
            else:
                service["status"] = status_cache.get(service["service_id"], "unknow")
            if service["status"] == "closed" or service["status"] == "undeploy":
                service["min_memory"] = 0
            status_map = get_status_info_map(service["status"])
            service.update(status_map)
            result.append(service)
        return result

    def get_no_group_service_status_by_group_id(self, team_name, team_id, region_name, enterprise_id):
        no_services = base_service.get_no_group_services_list(team_id=team_id, region_name=region_name)
        if no_services:
            service_ids = [service.service_id for service in no_services]
            status_list = base_service.status_multi_service(
                region=region_name, tenant_name=team_name, service_ids=service_ids, enterprise_id=enterprise_id)
            status_cache = {}
            statuscn_cache = {}
            for status in status_list:
                status_cache[status["service_id"]] = status["status"]
                statuscn_cache[status["service_id"]] = status["status_cn"]
            result = []
            for service in no_services:
                if service["group_name"] is None:
                    service["group_name"] = "未分组"
                service["status_cn"] = statuscn_cache.get(service["service_id"], "未知")
                status = status_cache.get(service["service_id"], "unknow")

                if status == "unknow" and service["create_status"] != "complete":
                    service["status"] = "creating"
                    service["status_cn"] = "创建中"
                else:
                    service["status"] = status_cache.get(service["service_id"], "unknow")
                if service["status"] == "closed" or service["status"] == "undeploy":
                    service["min_memory"] = 0
                status_map = get_status_info_map(service["status"])
                service.update(status_map)
                result.append(service)

            return result
        else:
            return []

    def create_service_event(self, create_info):
        service_event = ServiceEvent.objects.create(**create_info)
        return service_event

    def get_service_by_tenant_and_alias(self, tenant_id, service_alias="", service_id=""):
        services = []
        if service_alias:
            services = TenantServiceInfo.objects.filter(tenant_id=tenant_id, service_alias=service_alias)
        if service_id:
            services = TenantServiceInfo.objects.filter(tenant_id=tenant_id, service_id=service_id)
        if services:
            return services[0]
        return None

    @staticmethod
    def list_by_component_ids(service_ids: []):
        return TenantServiceInfo.objects.filter(service_id__in=service_ids)

    @staticmethod
    def bulk_create(components):
        TenantServiceInfo.objects.bulk_create(components)

    @staticmethod
    def bulk_update(components):
        TenantServiceInfo.objects.filter(pk__in=[cpt.ID for cpt in components]).delete()
        TenantServiceInfo.objects.bulk_create(components)


service_repo = ServiceRepo()
