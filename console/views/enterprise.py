# -*- coding: utf8 -*-
import logging

from rest_framework import status
from rest_framework.response import Response

from www.apiclient.regionapi import RegionInvokeApi
from www.utils.return_message import general_message

from console.services.user_services import user_services
from console.repositories.enterprise_repo import enterprise_repo
from console.repositories.service_repo import service_repo
from console.repositories.team_repo import team_repo
from console.models.main import RegionConfig
from console.views.base import JWTAuthApiView
from console.views.base import RegionTenantHeaderView

region_api = RegionInvokeApi()
logger = logging.getLogger("default")


class Enterprises(RegionTenantHeaderView):
    def get(self, request, *args, **kwargs):
        enterprises_list = []
        enterprises = enterprise_repo.get_team_enterprises(self.team.tenant_id)
        if enterprises:
            for enterprise in enterprises:
                enterprises_list.append({
                    "ID": enterprise.ID,
                    "enterprise_alias": enterprise.enterprise_alias,
                    "enterprise_name": enterprise.enterprise_name,
                    "is_active": enterprise.is_active,
                    "enterprise_id": enterprise.enterprise_id,
                    "enterprise_token": enterprise.enterprise_token,
                    "create_time": enterprise.create_time,
                })
            data = general_message(200, "success", "查询成功", list=enterprises_list)
            return Response(data, status=status.HTTP_200_OK)
        else:
            data = general_message(404, "no found", "未找到企业")
            return Response(data, status=status.HTTP_404_NOT_FOUND)


class EnterpriseInfo(RegionTenantHeaderView):
    def get(self, request, enterprise_id, *args, **kwargs):
        enter = enterprise_repo.get_enterprise_by_enterprise_id(enterprise_id=enterprise_id)
        ent = enter.to_dict()
        is_ent = False
        try:
            res, body = region_api.get_api_version_v2(self.team.tenant_name, self.response_region)
            if res.status == 200 and body is not None and "enterprise" in body["raw"]:
                is_ent = True
        except region_api.CallApiError as e:
            logger.warning("数据中心{0}不可达,无法获取相关信息: {1}".format(self.response_region.region_name, e.message))
        ent["is_enterprise"] = is_ent

        result = general_message(200, "success", "查询成功", bean=ent)
        return Response(result, status=result["code"])


class EnterpriseAppOverView(JWTAuthApiView):
    def get(self, request, enterprise_id, *args, **kwargs):
        try:
            service_groups = enterprise_repo.get_enterprise_apps(enterprise_id)
            service_groups_nums = len(service_groups)
            service_groups_running_nums = 0
            service_nums = 0
            service_running_nums = 0
            if service_groups:
                for service_group in service_groups:
                    try:
                        team = team_repo.get_team_by_team_id(service_group.tenant_id)
                    except Exception:
                        continue
                    try:
                        group_service_list = service_repo.get_group_service_by_group_id(
                            service_group.ID, service_group.region_name,
                            service_group.tenant_id, team.tenant_name, enterprise_id
                        )
                    except Exception:
                        continue
                    before_service_nums = service_running_nums
                    service_nums += len(group_service_list)
                    if group_service_list:
                        for group_service in group_service_list:
                            if group_service["status"] == "running":
                                service_running_nums += 1
                    if service_running_nums > before_service_nums:
                        service_groups_running_nums += 1
            data = {
                "service_groups": {
                    "total": service_groups_nums,
                    "running": service_groups_running_nums,
                    "closed": service_groups_nums - service_groups_running_nums
                },
                "components": {
                    "total": service_nums,
                    "running": service_running_nums,
                    "closed": service_nums - service_running_nums
                }
            }
        except Exception as e:
            logger.debug(e)
            result = general_message(400, e, None)
            return Response(result, status=status.HTTP_200_OK)

        result = general_message(200, "success", "查询成功", bean=data)
        return Response(result, status=status.HTTP_200_OK)


class EnterpriseOverview(JWTAuthApiView):
    def get(self, request, enterprise_id, *args, **kwargs):
        users = enterprise_repo.get_enterprise_users(enterprise_id)
        user_nums = len(users)
        team = enterprise_repo.get_enterprise_teams(enterprise_id)
        team_nums = len(team)
        shared_service_nums = enterprise_repo.get_enterprise_shared_service_nums(enterprise_id)
        data = {
            "shared_components": shared_service_nums,
            "total_teams": team_nums,
            "total_users": user_nums
        }
        result = general_message(200, "success", None, bean=data)
        return Response(result, status=status.HTTP_200_OK)


class EnterpriseTeams(JWTAuthApiView):
    def get(self, request, enterprise_id, *args, **kwargs):
        if not user_services.is_user_admin_in_current_enterprise(request.user, enterprise_id):
            result = general_message(401, "is not admin", "用户'{}'不是企业管理员".format(request.user.user_id))
            return Response(result, status=status.HTTP_200_OK)
        teams_list = []
        teams = enterprise_repo.get_enterprise_teams(enterprise_id)
        if teams:
            for team in teams:
                teams_list.append({
                    "tenant_id": team.tenant_id,
                    "team_alias": team.tenant_alias,
                    "owner": team.creater,
                    "enterprise_id": enterprise_id,
                    "create_time": team.create_time,
                    "team_name": team.tenant_name,
                    "region": team.region,
                })
            result = general_message(200, "success", None, list=teams_list)
        else:
            result = general_message(404, "no found", None)
        return Response(result, status=status.HTTP_200_OK)


class EnterpriseUserTeams(JWTAuthApiView):
    def get(self, request, enterprise_id, user_id, *args, **kwargs):
        user = request.user
        print user_id, user.user_id
        code = 200
        if int(user_id) != int(user.user_id):
            result = general_message(400, "failed", "请求失败")
            return Response(result, status=code)
        try:
            tenants = enterprise_repo.get_enterprise_user_teams(enterprise_id, user_id)
            if tenants:
                teams_list = list()
                for tenant in tenants:
                    teams_list.append({
                        "team_name": tenant.tenant_name,
                        "team_alias": tenant.tenant_alias,
                        "team_id": tenant.tenant_id,
                        "create_time": tenant.create_time,
                        "region": tenant.region,
                        "enterprise_id": tenant.enterprise_id,
                        "owner": tenant.creater,
                    })
                result = general_message(200, "team query success", "成功获取该用户加入的团队", list=teams_list)
            else:
                teams_list = []
                result = general_message(200, "team query success", "该用户没有加入团队", bean=teams_list)
        except Exception as e:
            logger.exception(e)
            code = 400
            result = general_message(code, "failed", "请求失败")
        return Response(result, status=code)


class EnterpriseTeamOverView(JWTAuthApiView):
    def get(self, request, enterprise_id, *args, **kwargs):
        code = 200
        try:
            tenant = enterprise_repo.get_enterprise_user_teams(enterprise_id, request.user.user_id).first()
            active_tenants = enterprise_repo.get_user_active_teams(enterprise_id, request.user.user_id)
            if tenant:
                data = {
                    "active_teams": active_tenants,
                    "new_join_team": {
                        "team_name": tenant.tenant_name,
                        "team_alias": tenant.tenant_alias,
                        "team_id": tenant.tenant_id,
                        "create_time": tenant.create_time,
                        "region": tenant.region,
                        "enterprise_id": tenant.enterprise_id,
                        "owner": tenant.creater,
                    },
                }
                result = general_message(200, "success", None, bean=data)
            else:
                result = general_message(200, "success", "该用户没有加入团队")
        except Exception as e:
            logger.exception(e)
            code = 400
            result = general_message(code, "failed", "请求失败")
        return Response(result, status=code)


class EnterpriseMonitor(RegionTenantHeaderView):
    def get(self, request, enterprise_id, *args, **kwargs):
        region_memory_total = 0
        region_memory_used = 0
        region_cpu_total = 0
        region_cpu_used = 0
        regions = RegionConfig.objects.filter(status=1)
        if not regions:
            result = general_message(404, "no found", None)
            return Response(result, status=status.HTTP_200_OK)
        region_num = len(regions)
        for region in regions:
            res, body = region_api.get_region_resources(self.team.tenant_name, region.region_name)
            if res.get("status") == 200:
                region_memory_total += body["bean"]["health_cap_mem"]
                region_memory_used += body["bean"]["health_req_mem"]
                region_cpu_total += body["bean"]["health_cap_cpu"]
                region_cpu_used += body["bean"]["health_req_cpu"]
        data = {
            "total_regions": region_num,
            "memory": {
                "used": region_memory_used,
                "total": region_memory_total
            },
            "cpu": {
                "used": region_cpu_used,
                "total": region_cpu_total
            }
        }
        result = general_message(200, "success", None, bean=data)
        return Response(result, status=status.HTTP_200_OK)
