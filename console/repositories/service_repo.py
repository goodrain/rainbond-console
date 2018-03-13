# -*- coding: utf-8 -*-
import logging

from console.repositories.team_repo import team_repo
from console.services.service_services import base_service
from openapi.controllers.openservicemanager import OpenTenantServiceManager
from www.models import TenantServiceInfo, ServiceGroupRelation, ServiceGroup, ServiceEvent
from www.utils.status_translate import get_status_info_map

logger = logging.getLogger("default")


class ServiceRepo(object):
    def get_team_service_num_by_team_id(self, team_id, region_name):
        return TenantServiceInfo.objects.filter(tenant_id=team_id, service_region=region_name).count()

    def get_no_grop_service_by_team_id(self, team_id, region_name):
        team_service = TenantServiceInfo.objects.filter(tenant_id=team_id, service_region=region_name)
        if team_service:
            every_service_ids = list()
            for team_every_service in team_service:
                every_service_id = team_every_service.service_id
                every_service_ids.append(every_service_id)
            group_service_ids = ServiceGroupRelation.objects.filter(tenant_id=team_id,
                                                                    region_name=region_name).values_list("service_id",
                                                                                                         flat=True)
            no_group_ids = list(set(every_service_ids).difference(set(group_service_ids)))
            no_group_info = list()
            for no_group_id in no_group_ids:
                try:
                    service = TenantServiceInfo.objects.filter(service_id=no_group_id)[0]
                    code, bool, result = OpenTenantServiceManager().status_service(service=service)
                    no_group_info.append(
                        {
                            "service_id": service.service_id,
                            "service_name": service.service_cname,
                            "group_id": -1,
                            "group_name": "未分组",
                            "service_version": service.version,
                            "update_time": service.update_time,
                            "service_alias": service.service_alias,
                            "service_status": result
                        }
                    )
                except Exception as e:
                    logger.exception(e)
                    pass
            return no_group_info
        else:
            return []

    def get_service_group_list(self, team_name, region_name):
        team = team_repo.get_tenant_by_tenant_name(tenant_name=team_name, exception=True)
        service_groups = ServiceGroup.objects.filter(tenant_id=team.tenant_id, region_name=region_name)
        group_list = list()
        if service_groups:
            for service_group in service_groups:
                group_info = dict()
                group_info["group_id"] = service_group.ID
                group_info["group_name"] = service_group.group_name
                g_s_l = ServiceGroupRelation.objects.filter(group_id=service_group.ID, region_name=region_name)
                gslist = list()
                for g_s in g_s_l:
                    g_n_l = TenantServiceInfo.objects.filter(service_id=g_s.service_id, service_region=region_name)
                    if g_n_l:
                        g_n = g_n_l[0]
                        service_info = dict()
                        service_info["service_id"] = g_s.service_id
                        service_info["service_cname"] = g_n.service_cname
                        service_info["service_alias"] = g_n.service_alias
                        gslist.append(service_info)
                    group_info["service_list"] = gslist
                group_list.append(group_info)
            no_services = self.get_no_grop_service_by_team_id(team_id=team.tenant_id, region_name=region_name)
            no_service_list = []
            for no_service in no_services:
                service = TenantServiceInfo.objects.filter(service_id=no_service.get("service_id"))[0]
                no_service_list.append(
                    {
                        "service_id": service.service_id,
                        "service_cname": service.service_cname,
                        "service_alias": service.service_alias
                    }
                )
            group_list.append({"group_id": -1, "group_name": "未分组", "service_list": no_service_list})
            return group_list
        else:
            return []

    def get_no_group_list(self, team_name, region_name):
        team = team_repo.get_tenant_by_tenant_name(tenant_name=team_name, exception=True)
        group_list = list()
        no_services = self.get_no_grop_service_by_team_id(team_id=team.tenant_id, region_name=region_name)
        if no_services:
            no_service_list = []
            for no_service in no_services:
                service = TenantServiceInfo.objects.filter(service_id=no_service.get("service_id"))[0]
                no_service_list.append(
                    {
                        "service_id": service.service_id,
                        "service_cname": service.service_cname,
                        "service_alias": service.service_alias
                    }
                )
            group_list.append({"group_id": -1, "group_name": "未分组", "service_list": no_service_list})
            return group_list
        else:
            return []

    def get_group_service_by_group_id(self, group_id, region_name, team_id, team_name, enterprise_id):
        group_services_list = base_service.get_group_services_list(team_id=team_id, region_name=region_name,
                                                                   group_id=group_id)
        if group_services_list:
            service_ids = [service.service_id for service in group_services_list]
            status_list = base_service.status_multi_service(region=region_name, tenant_name=team_name,
                                                            service_ids=service_ids,
                                                            enterprise_id=enterprise_id)
            status_cache = {}
            statuscn_cache = {}
            for status in status_list:
                status_cache[status["service_id"]] = status["status"]
                statuscn_cache[status["service_id"]] = status["status_cn"]
            result = []
            for service in group_services_list:
                service["status_cn"] = statuscn_cache.get(service["service_id"], "未知")
                status = status_cache.get(service["service_id"], "unknow")
                status_map = get_status_info_map(status)
                if status == "unknow" and service["create_status"] != "compelet":
                    service["status"] = "creating"
                    service["status_cn"] = "创建中"
                else:
                    service["status"] = status_cache.get(service["service_id"], "unknow")
                if service["status"] == "closed" or service["status"] == "undeploy":
                    service["min_memory"] = 0
                service.update(status_map)
                result.append(service)
            return result
        else:
            return []

    def get_no_group_service_status_by_group_id(self, team_name, team_id, region_name, enterprise_id):
        no_services = base_service.get_no_group_services_list(team_id=team_id, region_name=region_name)
        if no_services:
            service_ids = [service.service_id for service in no_services]
            status_list = base_service.status_multi_service(region=region_name, tenant_name=team_name,
                                                            service_ids=service_ids,
                                                            enterprise_id=enterprise_id)
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
                status_map = get_status_info_map(status)
                if status == "unknow" and service["create_status"] != "compelet":
                    service["status"] = "creating"
                    service["status_cn"] = "创建中"
                else:
                    service["status"] = status_cache.get(service["service_id"], "unknow")
                if service["status"] == "closed" or service["status"] == "undeploy":
                    service["min_memory"] = 0
                service.update(status_map)
                result.append(service)
            return result
        else:
            return []

    def create_service_event(self, create_info):
        service_event = ServiceEvent.objects.create(**create_info)
        return service_event


service_repo = ServiceRepo()
