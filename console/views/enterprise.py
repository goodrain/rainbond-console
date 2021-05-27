# -*- coding: utf8 -*-
import json
import logging

from console.exception.exceptions import (ExterpriseNotExistError, TenantNotExistError, UserNotExistError)
from console.exception.main import ServiceHandleException
from console.models.main import RegionConfig
from console.repositories.enterprise_repo import enterprise_repo
from console.repositories.group import group_repo
from console.repositories.region_repo import region_repo
from console.repositories.team_repo import team_repo
from console.repositories.user_repo import user_repo
from console.services.config_service import EnterpriseConfigService
from console.services.enterprise_services import enterprise_services
from console.services.perm_services import user_kind_role_service
from console.services.region_services import region_services
from console.services.team_services import team_services
from console.views.base import EnterpriseAdminView, JWTAuthApiView
from rest_framework import status
from rest_framework.response import Response
from www.apiclient.regionapi import RegionInvokeApi
from www.utils.return_message import general_message

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
            data = general_message(404, "no found enterprise", "未找到企业")
            return Response(data, status=status.HTTP_404_NOT_FOUND)


class EnterpriseRUDView(JWTAuthApiView):
    def get(self, request, enterprise_id, *args, **kwargs):
        enter = enterprise_repo.get_enterprise_by_enterprise_id(enterprise_id=enterprise_id)
        ent = enter.to_dict()
        if ent:
            ent.update(EnterpriseConfigService(enterprise_id).initialization_or_get_config)
        result = general_message(200, "success", "查询成功", bean=ent)
        return Response(result, status=result["code"])

    def put(self, request, enterprise_id, *args, **kwargs):
        key = request.GET.get("key")
        if not key:
            result = general_message(404, "no found config key {0}".format(key), "更新失败")
            return Response(result, status=result.get("code", 200))
        value = request.data.get(key)
        if not value:
            result = general_message(404, "no found config value", "更新失败")
            return Response(result, status=result.get("code", 200))
        ent_config_servier = EnterpriseConfigService(enterprise_id)
        key = key.upper()
        if key in ent_config_servier.base_cfg_keys + ent_config_servier.cfg_keys:
            try:
                data = ent_config_servier.update_config(key, value)
                result = general_message(200, "success", "更新成功", bean=data)
            except Exception as e:
                logger.debug(e)
                raise ServiceHandleException(msg="update enterprise config failed", msg_show="更新失败")
        else:
            result = general_message(404, "no found config key", "更新失败")
        return Response(result, status=result.get("code", 200))

    def delete(self, request, enterprise_id, *args, **kwargs):
        key = request.GET.get("key")
        if not key:
            result = general_message(404, "no found config key", "重置失败")
            return Response(result, status=result.get("code", 200))
        value = request.data.get(key)
        if not value:
            result = general_message(404, "no found config value", "重置失败")
            return Response(result, status=result.get("code", 200))
        ent_config_servier = EnterpriseConfigService(enterprise_id)
        key = key.upper()
        if key in ent_config_servier.cfg_keys:
            data = ent_config_servier.delete_config(key)
            try:
                result = general_message(200, "success", "重置成功", bean=data)
            except Exception as e:
                logger.debug(e)
                raise ServiceHandleException(msg="update enterprise config failed", msg_show="重置失败")
        else:
            result = general_message(404, "can not delete key value", "该配置不可重置")
        return Response(result, status=result.get("code", 200))


class EnterpriseAppOverView(JWTAuthApiView):
    def get(self, request, enterprise_id, *args, **kwargs):
        regions = region_repo.get_usable_regions(enterprise_id)
        if not regions:
            result = general_message(404, "no found regions", "查询成功")
            return Response(result, status=200)
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
        data = {"shared_apps": shared_app_nums, "total_teams": team_nums, "total_users": user_nums}
        result = general_message(200, "success", None, bean=data)
        return Response(result, status=status.HTTP_200_OK)


class EnterpriseTeams(JWTAuthApiView):
    def get(self, request, enterprise_id, *args, **kwargs):
        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 10))
        name = request.GET.get("name", None)
        teams, total = team_services.get_enterprise_teams(
            enterprise_id, query=name, page=page, page_size=page_size, user=self.user)
        data = {"total_count": total, "page": page, "page_size": page_size, "list": teams}
        result = general_message(200, "success", None, bean=data)
        return Response(result, status=status.HTTP_200_OK)


class EnterpriseUserTeams(EnterpriseAdminView):
    def get(self, request, enterprise_id, user_id, *args, **kwargs):
        name = request.GET.get("name", None)
        user = user_repo.get_user_by_user_id(user_id)
        teams = team_services.list_user_teams(enterprise_id, user, name)
        result = general_message(200, "team query success", "查询成功", list=teams)
        return Response(result, status=200)


class EnterpriseMyTeams(JWTAuthApiView):
    def get(self, request, enterprise_id, *args, **kwargs):
        name = request.GET.get("name", None)
        tenants = team_services.get_teams_region_by_user_id(enterprise_id, self.user, name)
        result = general_message(200, "team query success", "查询成功", list=tenants)
        return Response(result, status=200)


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
                    region_name_list = team_repo.get_team_region_names(tenant.tenant_id)
                    user_role_list = user_kind_role_service.get_user_roles(
                        kind="team", kind_id=tenant.tenant_id, user=request.user)
                    roles = [x["role_name"] for x in user_role_list["roles"]]
                    if tenant.creater == request.user.user_id:
                        roles.append("owner")
                    owner = user_repo.get_by_user_id(tenant.creater)
                    if len(region_name_list) > 0:
                        team_item = {
                            "team_name": tenant.tenant_name,
                            "team_alias": tenant.tenant_alias,
                            "team_id": tenant.tenant_id,
                            "create_time": tenant.create_time,
                            "region": region_name_list[0],  # first region is default
                            "region_list": region_name_list,
                            "enterprise_id": tenant.enterprise_id,
                            "owner": tenant.creater,
                            "owner_name": (owner.get_name() if owner else None),
                            "roles": roles,
                            "is_pass": True,
                        }
                        new_join_team.append(team_item)
            if join_tenants:
                for tenant in join_tenants:
                    region_name_list = team_repo.get_team_region_names(tenant.team_id)
                    tenant_info = team_repo.get_team_by_team_id(tenant.team_id)
                    try:
                        user = user_repo.get_user_by_user_id(tenant_info.creater)
                        nick_name = user.nick_name
                    except UserNotExistError:
                        nick_name = None
                    if len(region_name_list) > 0:
                        team_item = {
                            "team_name": tenant.team_name,
                            "team_alias": tenant.team_alias,
                            "team_id": tenant.team_id,
                            "create_time": tenant_info.create_time,
                            "region": region_name_list[0],
                            "region_list": region_name_list,
                            "enterprise_id": tenant_info.enterprise_id,
                            "owner": tenant_info.creater,
                            "owner_name": nick_name,
                            "role": None,
                            "is_pass": tenant.is_pass,
                        }
                        new_join_team.append(team_item)
            if request_tenants:
                for request_tenant in request_tenants:
                    region_name_list = team_repo.get_team_region_names(request_tenant.team_id)
                    tenant_info = team_repo.get_team_by_team_id(request_tenant.team_id)
                    try:
                        user = user_repo.get_user_by_user_id(tenant_info.creater)
                        nick_name = user.nick_name
                    except UserNotExistError:
                        nick_name = None
                    if len(region_name_list) > 0:
                        team_item = {
                            "team_name": request_tenant.team_name,
                            "team_alias": request_tenant.team_alias,
                            "team_id": request_tenant.team_id,
                            "apply_time": request_tenant.apply_time,
                            "user_id": request_tenant.user_id,
                            "user_name": request_tenant.user_name,
                            "region": region_name_list[0],
                            "region_list": region_name_list,
                            "enterprise_id": enterprise_id,
                            "owner": tenant_info.creater,
                            "owner_name": nick_name,
                            "role": "viewer",
                            "is_pass": request_tenant.is_pass,
                        }
                        request_join_team.append(team_item)
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
        regions = region_repo.get_usable_regions(enterprise_id)
        region_memory_total = 0
        region_memory_used = 0
        region_cpu_total = 0
        region_cpu_used = 0
        if not regions:
            result = general_message(404, "no found", None)
            return Response(result, status=status.HTTP_200_OK)
        region_num = len(regions)
        for region in regions:
            try:
                res, body = region_api.get_region_resources(enterprise_id, region=region.region_name)
                if res.get("status") == 200:
                    region_memory_total += body["bean"]["cap_mem"]
                    region_memory_used += body["bean"]["req_mem"]
                    region_cpu_total += body["bean"]["cap_cpu"]
                    region_cpu_used += body["bean"]["req_cpu"]
            except Exception as e:
                logger.debug(e)
                continue
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
        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 10))
        enterprise_apps, apps_count = enterprise_repo.get_enterprise_app_list(enterprise_id, self.user, page, page_size)
        if enterprise_apps:
            for app in enterprise_apps:
                try:
                    tenant = team_services.get_team_by_team_id(app.tenant_id)
                    tenant_name = tenant.tenant_name
                except TenantNotExistError:
                    tenant_name = None
                data.append({
                    "ID": app.ID,
                    "group_name": app.group_name,
                    "tenant_id": app.tenant_id,
                    "tenant_name": tenant_name,
                    "region_name": app.region_name
                })
        result = general_message(200, "success", "获取成功", list=data, total_count=apps_count, page=page, page_size=page_size)
        return Response(result, status=status.HTTP_200_OK)


class EnterpriseRegionsLCView(JWTAuthApiView):
    def get(self, request, enterprise_id, *args, **kwargs):
        region_status = request.GET.get("status", "")
        check_status = request.GET.get("check_status", "")
        data = region_services.get_enterprise_regions(
            enterprise_id, level="safe", status=region_status, check_status=check_status)
        result = general_message(200, "success", "获取成功", list=data)
        return Response(result, status=status.HTTP_200_OK)

    def post(self, request, enterprise_id, *args, **kwargs):
        token = request.data.get("token")
        region_name = request.data.get("region_name")
        region_alias = request.data.get("region_alias")
        desc = request.data.get("desc")
        region_type = json.dumps(request.data.get("region_type", []))
        region_data = region_services.parse_token(token, region_name, region_alias, region_type)
        region_data["enterprise_id"] = enterprise_id
        region_data["desc"] = desc
        region_data["provider"] = request.data.get("provider", "")
        region_data["provider_cluster_id"] = request.data.get("provider_cluster_id", "")
        region_data["status"] = "1"
        region = region_services.add_region(region_data)
        if region:
            data = region_services.get_enterprise_region(enterprise_id, region.region_id, check_status=False)
            result = general_message(200, "success", "创建成功", bean=data)
            return Response(result, status=status.HTTP_200_OK)
        else:
            result = general_message(500, "failed", "创建失败")
            return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EnterpriseRegionsRUDView(JWTAuthApiView):
    def get(self, request, enterprise_id, region_id, *args, **kwargs):
        data = region_services.get_enterprise_region(enterprise_id, region_id, check_status=False)
        result = general_message(200, "success", "获取成功", bean=data)
        return Response(result, status=status.HTTP_200_OK)

    def put(self, request, enterprise_id, region_id, *args, **kwargs):
        region = region_services.update_enterprise_region(enterprise_id, region_id, request.data)
        result = general_message(200, "success", "更新成功", bean=region)
        return Response(result, status=result.get("code", 200))

    def delete(self, request, enterprise_id, region_id, *args, **kwargs):
        try:
            region_repo.del_by_enterprise_region_id(enterprise_id, region_id)
        except RegionConfig.DoesNotExist:
            raise ServiceHandleException(status_code=404, msg="集群已不存在")
        result = general_message(200, "success", "删除成功")
        return Response(result, status=result.get("code", 200))


class EnterpriseRegionTenantRUDView(EnterpriseAdminView):
    def get(self, request, enterprise_id, region_id, *args, **kwargs):
        page = request.GET.get("page", 1)
        page_size = request.GET.get("pageSize", 10)
        tenants, total = team_services.get_tenant_list_by_region(enterprise_id, region_id, page, page_size)
        result = general_message(
            200, "success", "获取成功", bean={
                "tenants": tenants,
                "total": total,
            })
        return Response(result, status=status.HTTP_200_OK)


class EnterpriseRegionTenantLimitView(EnterpriseAdminView):
    def post(self, request, enterprise_id, region_id, tenant_name, *args, **kwargs):
        team_services.set_tenant_memory_limit(enterprise_id, region_id, tenant_name, request.data)
        return Response({}, status=status.HTTP_200_OK)


class EnterpriseAppComponentsLView(JWTAuthApiView):
    def get(self, request, enterprise_id, app_id, *args, **kwargs):
        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 10))
        data = []
        count = 0
        app = group_repo.get_group_by_id(app_id)
        if app:
            try:
                tenant = team_services.get_team_by_team_id(app.tenant_id)
                tenant_name = tenant.tenant_name
            except Exception:
                tenant_name = None
            services, count = enterprise_repo.get_enterprise_app_component_list(app_id, page, page_size)
            if services:
                for service in services:
                    data.append({
                        "service_alias": service.service_alias,
                        "service_id": service.service_id,
                        "tenant_id": app.tenant_id,
                        "tenant_name": tenant_name,
                        "region_name": service.service_region,
                        "service_cname": service.service_cname,
                        "service_key": service.service_key,
                    })
        result = general_message(200, "success", "获取成功", list=data, total_count=count, page=page, page_size=page_size)
        return Response(result, status=status.HTTP_200_OK)


class EnterpriseRegionDashboard(EnterpriseAdminView):
    def dispatch(self, request, enterprise_id, region_id, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        request = self.initialize_request(request, *args, **kwargs)
        self.request = request
        self.headers = self.default_response_headers
        try:
            self.initial(request, *args, **kwargs)
            region = region_services.get_enterprise_region(enterprise_id, region_id, check_status=False)
            if not region:
                return Response({}, status=status.HTTP_404_NOTFOUND)
            full_path = request.get_full_path()
            path = full_path[full_path.index("/dashboard/") + 11:len(full_path)]
            response = region_api.proxy(request, '/kubernetes/dashboard/' + path, region['region_name'])
        except Exception as exc:
            response = self.handle_exception(exc)
        self.response = self.finalize_response(request, response, *args, **kwargs)
        return self.response
