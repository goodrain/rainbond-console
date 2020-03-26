# -*- coding: utf8 -*-
import logging
import json

from rest_framework import status
from rest_framework.response import Response

from www.apiclient.regionapi import RegionInvokeApi
from www.utils.return_message import general_message

from console.exception.exceptions import UserNotExistError
from console.services.user_services import user_services
from console.services.enterprise_services import enterprise_services
from console.exception.exceptions import ExterpriseNotExistError
from console.repositories.enterprise_repo import enterprise_repo
from console.repositories.exceptions import UserRoleNotFoundException
from console.repositories.team_repo import team_repo
from console.repositories.user_repo import user_repo
from console.repositories.region_repo import region_repo
from console.repositories.user_role_repo import user_role_repo
from console.views.base import JWTAuthApiView

region_api = RegionInvokeApi()
logger = logging.getLogger("default")


class Enterprises(JWTAuthApiView):
    def get(self, request, *args, **kwargs):
        enterprises_list = []
        try:
            enterprises = enterprise_repo.get_enterprises_by_user_id(request.user.user_id)
        except ExterpriseNotExistError as e:
            logger.debug(e)
            data = general_message(404, "success", "该用户未加入任何团队")
            return Response(data, status=status.HTTP_404_NOT_FOUND)
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


class EnterpriseInfo(JWTAuthApiView):
    def get(self, request, enterprise_id, *args, **kwargs):
        enter = enterprise_repo.get_enterprise_by_enterprise_id(enterprise_id=enterprise_id)
        ent = enter.to_dict()
        result = general_message(200, "success", "查询成功", bean=ent)
        return Response(result, status=result["code"])


class EnterpriseAppOverView(JWTAuthApiView):
    def get(self, request, enterprise_id, *args, **kwargs):
        regions = region_repo.get_usable_regions()
        if not regions:
            result = general_message(404, "no found regions", None)
            return Response(result, status=result.get("code"))
        data = enterprise_services.get_enterprise_runing_service(enterprise_id, regions)
        result = general_message(200, "success", "查询成功", bean=data)
        return Response(result, status=status.HTTP_200_OK)


class EnterpriseOverview(JWTAuthApiView):
    def get(self, request, enterprise_id, *args, **kwargs):
        users = enterprise_repo.get_enterprise_users(enterprise_id)
        user_nums = len(users)
        team = enterprise_repo.get_enterprise_teams(enterprise_id)
        team_nums = len(team)
        shared_app_nums = enterprise_repo.get_enterprise_shared_app_nums(enterprise_id)
        data = {
            "shared_apps": shared_app_nums,
            "total_teams": team_nums,
            "total_users": user_nums
        }
        result = general_message(200, "success", None, bean=data)
        return Response(result, status=status.HTTP_200_OK)


class EnterpriseTeams(JWTAuthApiView):
    def get(self, request, enterprise_id, *args, **kwargs):
        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 10))
        name = request.GET.get("name", None)
        if not user_services.is_user_admin_in_current_enterprise(request.user, enterprise_id):
            result = general_message(401, "is not admin", "用户'{}'不是企业管理员".format(request.user.nick_name))
            return Response(result, status=status.HTTP_200_OK)
        teams_list = []
        teams = enterprise_repo.get_enterprise_teams(enterprise_id, name)
        if teams:
            try:
                rst_teams = teams[(page-1)*page_size:page*page_size]
            except Exception:
                rst_teams = []
            if rst_teams:
                for team in rst_teams:
                    try:
                        user = user_repo.get_user_by_user_id(team.creater)
                        nick_name = user.nick_name
                    except UserNotExistError:
                        nick_name = None
                    try:
                        role = user_role_repo.get_role_names(team.creater, team.tenant_id)
                    except UserRoleNotFoundException:
                        role = "owner"
                    region_name_list = []
                    region_list = team_repo.get_team_regions(team.tenant_id)
                    if region_list:
                        region_name_list = region_list.values_list("region_name", flat=True)
                    teams_list.append({
                        "tenant_id": team.tenant_id,
                        "team_alias": team.tenant_alias,
                        "owner": team.creater,
                        "owner_name": nick_name,
                        "enterprise_id": enterprise_id,
                        "create_time": team.create_time,
                        "team_name": team.tenant_name,
                        "region": team.region,
                        "region_list": region_name_list,
                        "role": role,
                    })
            data = {
                "total_count": len(teams),
                "page": page,
                "page_size": page_size,
                "list": teams_list
            }
            result = general_message(200, "success", None, bean=data)
        else:
            result = general_message(404, "no found", None)
        return Response(result, status=status.HTTP_200_OK)


class EnterpriseUserTeams(JWTAuthApiView):
    def get(self, request, enterprise_id, user_id, *args, **kwargs):
        user = request.user
        name = request.GET.get("name", None)
        code = 200
        if int(user_id) != int(user.user_id):
            result = general_message(400, "failed", "请求失败")
            return Response(result, status=code)
        try:
            tenants = enterprise_repo.get_enterprise_user_teams(enterprise_id, user_id, name)
            if tenants:
                teams_list = list()
                for tenant in tenants:
                    user = user_repo.get_user_by_user_id(tenant.creater)
                    try:
                        role = user_role_repo.get_role_names(user.user_id, tenant.tenant_id)
                    except UserRoleNotFoundException:
                        if tenant.creater == user.user_id:
                            role = "owner"
                        else:
                            role = None
                    region_name_list = []
                    region_list = team_repo.get_team_regions(tenant.tenant_id)
                    if region_list:
                        region_name_list = region_list.values_list("region_name", flat=True)
                    teams_list.append({
                        "team_name": tenant.tenant_name,
                        "team_alias": tenant.tenant_alias,
                        "team_id": tenant.tenant_id,
                        "create_time": tenant.create_time,
                        "region": tenant.region,
                        "region_list": region_name_list,
                        "enterprise_id": tenant.enterprise_id,
                        "owner": tenant.creater,
                        "owner_name": user.nick_name,
                        "role": role
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
        new_join_team = []
        request_join_team = []
        try:
            tenants = enterprise_repo.get_enterprise_user_teams(enterprise_id, request.user.user_id)
            join_tenants = enterprise_repo.get_enterprise_user_join_teams(enterprise_id, request.user.user_id)
            active_tenants = enterprise_repo.get_enterprise_user_active_teams(enterprise_id, request.user.user_id)
            request_tenants = enterprise_repo.get_enterprise_user_request_join(enterprise_id, request.user.user_id)
            if tenants:
                for tenant in tenants[:3]:
                    region_name_list = []
                    user = user_repo.get_user_by_user_id(tenant.creater)
                    region_list = team_repo.get_team_regions(tenant.tenant_id)
                    if region_list:
                        region_name_list = region_list.values_list("region_name", flat=True)
                    try:
                        role = user_role_repo.get_role_names(user.user_id, tenant.tenant_id)
                    except UserRoleNotFoundException:
                        if tenant.creater == user.user_id:
                            role = "owner"
                        else:
                            role = None
                    new_join_team.append({
                        "team_name": tenant.tenant_name,
                        "team_alias": tenant.tenant_alias,
                        "team_id": tenant.tenant_id,
                        "create_time": tenant.create_time,
                        "region": tenant.region,
                        "region_list": region_name_list,
                        "enterprise_id": tenant.enterprise_id,
                        "owner": tenant.creater,
                        "owner_name": user.nick_name,
                        "role": role,
                        "is_pass": True,
                    })
            if join_tenants:
                for tenant in join_tenants:
                    region_name_list = []
                    region_list = team_repo.get_team_regions(tenant.team_id)
                    if region_list:
                        region_name_list = region_list.values_list("region_name", flat=True)
                    tenant_info = team_repo.get_team_by_team_id(tenant.team_id)
                    try:
                        user = user_repo.get_user_by_user_id(tenant_info.creater)
                        nick_name = user.nick_name
                    except UserNotExistError:
                        nick_name = None
                    new_join_team.append({
                        "team_name": tenant.team_name,
                        "team_alias": tenant.team_alias,
                        "team_id": tenant.team_id,
                        "create_time": tenant_info.create_time,
                        "region": tenant_info.region,
                        "region_list": region_name_list,
                        "enterprise_id": tenant_info.enterprise_id,
                        "owner": tenant_info.creater,
                        "owner_name": nick_name,
                        "role": None,
                        "is_pass": tenant.is_pass,
                    })
            if request_tenants:
                for request_tenant in request_tenants:
                    region_name_list = []
                    region_list = team_repo.get_team_regions(request_tenant.team_id)
                    if region_list:
                        region_name_list = region_list.values_list("region_name", flat=True)
                    tenant_info = team_repo.get_team_by_team_id(request_tenant.team_id)
                    try:
                        user = user_repo.get_user_by_user_id(tenant_info.creater)
                        nick_name = user.nick_name
                    except UserNotExistError:
                        nick_name = None
                    request_join_team.append({
                        "team_name": request_tenant.team_name,
                        "team_alias": request_tenant.team_alias,
                        "team_id": request_tenant.team_id,
                        "apply_time": request_tenant.apply_time,
                        "user_id": request_tenant.user_id,
                        "user_name": request_tenant.user_name,
                        "region": team_repo.get_team_by_team_id(request_tenant.team_id).region,
                        "region_list": region_name_list,
                        "enterprise_id": enterprise_id,
                        "owner": tenant_info.creater,
                        "owner_name": nick_name,
                        "role": "viewer",
                        "is_pass": request_tenant.is_pass,
                    })
            data = {
                "active_teams": active_tenants,
                "new_join_team": new_join_team,
                "request_join_team": request_join_team,
            }
            result = general_message(200, "success", None, bean=data)
        except Exception as e:
            logger.exception(e)
            code = 400
            result = general_message(code, "failed", "请求失败")
        return Response(result, status=code)


class EnterpriseMonitor(JWTAuthApiView):
    def get(self, request, enterprise_id, *args, **kwargs):
        regions = region_repo.get_usable_regions()
        region_memory_total = 0
        region_memory_used = 0
        region_cpu_total = 0
        region_cpu_used = 0
        if not regions:
            result = general_message(404, "no found", None)
            return Response(result, status=status.HTTP_200_OK)
        region_num = len(regions)
        for region in regions:
            res, body = region_api.get_region_resources(enterprise_id, region.region_name)
            if res.get("status") == 200:
                region_memory_total += body["bean"]["cap_mem"]
                region_memory_used += body["bean"]["req_mem"]
                region_cpu_total += body["bean"]["cap_cpu"]
                region_cpu_used += body["bean"]["req_cpu"]
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


class EnterpriseAppsLView(JWTAuthApiView):
    def get(self, request, enterprise_id, *args, **kwargs):
        data = []
        name = request.GET.get("name", None)
        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 10))
        enterprise_apps, apps_count = enterprise_repo.get_enterprise_app_list(
            enterprise_id, self.user, name, page, page_size)
        if enterprise_apps:
            for app in enterprise_apps:
                data.append({
                    "ID": app.ID,
                    "group_name": app.group_name,
                    "tenant_id": app.tenant_id,
                    "tenant_name": app.tenant_name,
                    "region_name": app.region_name,
                    "service_list": json.loads(app.service_list) if app.service_list else []
                })
        result = general_message(200, "success", "获取成功", list=data,
                                 total_count=apps_count, page=page, page_size=page_size)
        return Response(result, status=status.HTTP_200_OK)
