# -*- coding: utf8 -*-
import json
import logging
import os
import time

from django.http import StreamingHttpResponse, FileResponse

from console.exception.exceptions import (ExterpriseNotExistError, TenantNotExistError, UserNotExistError)
from console.exception.main import ServiceHandleException, AbortRequest
from console.models.main import RegionConfig
from console.repositories.config_repo import cfg_repo
from console.repositories.enterprise_repo import enterprise_repo
from console.repositories.group import group_repo
from console.repositories.region_repo import region_repo
from console.repositories.team_repo import team_repo
from console.repositories.user_repo import user_repo
from console.services.app_actions import ws_service
from console.services.app_config.component_logs import component_log_service
from console.services.config_service import EnterpriseConfigService
from console.services.enterprise_services import enterprise_services
from console.services.perm_services import user_kind_role_service
from console.services.region_resource_processing import region_resource
from console.services.region_services import region_services
from console.services.team_services import team_services
from console.views.base import EnterpriseAdminView, JWTAuthApiView, EnterpriseHeaderView, AlowAnyApiView
from rest_framework import status
from rest_framework.response import Response
from console.services.app_actions import event_service
from console.services.group_service import group_service
from console.repositories.app import service_repo

from default_region import make_uuid
from goodrain_web.settings import LOG_PATH
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import PermRelTenant, Tenants
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
        regions = region_repo.get_regions_by_enterprise_id(enterprise_id, 1)
        ent["disable_install_cluster_log"] = False
        if regions:
            ent["disable_install_cluster_log"] = True
            _, total = team_services.get_enterprise_teams(enterprise_id)
            if total == 0:
                region_services.create_sample_application(enter, regions[0], request.user)
        if not regions and os.getenv("ENABLE_CLUSTER") == "true":
            region_services.create_default_region(enterprise_id, request.user)
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
        tenant_names = {tenant["team_name"]: tenant for tenant in teams}
        usable_regions = region_repo.get_usable_regions(enterprise_id)
        user_id_list = PermRelTenant.objects.filter().values("tenant_id", "user_id")
        user_id_dict = dict()
        tenants = Tenants.objects.filter()
        tenant_ids = {tenant_id.ID: tenant_id.tenant_id for tenant_id in tenants}
        for user_id in user_id_list:
            user_id_dict[tenant_ids.get(user_id["tenant_id"])] = user_id_dict.get(tenant_ids.get(user_id["tenant_id"]), 0) + 1
        for usable_region in usable_regions:
            try:
                region_tenants, _ = team_services.get_tenant_list_by_region(
                    enterprise_id, usable_region.region_id, page=1, page_size=9999)
                for region_tenant in region_tenants:
                    tenant = tenant_names.get(region_tenant["tenant_name"])
                    if tenant:
                        tenant["user_number"] = user_id_dict.get(region_tenant["tenant_id"])
                        tenant["running_apps"] = tenant.get("running_apps", 0) + region_tenant["running_applications"]
                        tenant["memory_request"] = tenant.get("memory_request", 0) + region_tenant["memory_request"]
                        tenant["cpu_request"] = tenant.get("cpu_request", 0) + region_tenant["cpu_request"]
                        tenant["set_limit_memory"] = tenant.get("set_limit_memory", 0) + region_tenant["set_limit_memory"]
            except Exception as e:
                logger.exception(e)
        teams = sorted(teams, key=lambda team: team.get("memory_request", 0), reverse=True)
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
        use_region = request.GET.get("use_region", False)
        tenants = team_services.get_teams_region_by_user_id(enterprise_id, self.user, name, use_region=use_region)
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
        region = region_services.add_region(region_data, request.user)
        if region:
            data = region_services.get_enterprise_region(enterprise_id, region.region_id, check_status=False)
            result = general_message(200, "success", "创建成功", bean=data)
            return Response(result, status=status.HTTP_200_OK)
        else:
            result = general_message(500, "failed", "创建失败")
            return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EnterpriseRegionNamespace(JWTAuthApiView):
    def get(self, request, enterprise_id, region_id, *args, **kwargs):
        content = request.GET.get("content", "all")
        data = region_resource.get_namespaces(enterprise_id, region_id, content)
        result = general_message(200, "success", "获取成功", bean=data["list"])
        return Response(result, status=status.HTTP_200_OK)


class EnterpriseNamespaceResource(JWTAuthApiView):
    def get(self, request, enterprise_id, region_id, *args, **kwargs):
        content = request.GET.get("content", "all")
        namespace = request.GET.get("namespace", "")
        data = region_resource.get_namespaces_resource(enterprise_id, region_id, content, namespace)
        move = data["bean"].pop('unclassified')
        data["bean"]["unclassified"] = move
        result = general_message(200, "success", "获取成功", bean=data["bean"])
        return Response(result, status=status.HTTP_200_OK)


class EnterpriseConvertResource(JWTAuthApiView):
    def get(self, request, enterprise_id, region_id, *args, **kwargs):
        content = request.GET.get("content", "all")
        namespace = request.GET.get("namespace", "")
        data = region_resource.convert_resource(enterprise_id, region_id, namespace, content)
        move = data["bean"].pop('unclassified')
        data["bean"]["unclassified"] = move
        result = general_message(200, "success", "获取成功", bean=data["bean"])
        return Response(result, status=status.HTTP_200_OK)

    def post(self, request, enterprise_id, region_id, *args, **kwargs):
        content = request.data.get("content", "all")
        namespace = request.data.get("namespace", "")
        data = region_resource.resource_import(enterprise_id, region_id, namespace, content)
        rs = data.get("bean", {})
        regions = region_repo.get_regions_by_region_ids(enterprise_id, [region_id])
        if rs:
            if regions:
                tenant = rs["tenant"]
                tenant = region_resource.create_tenant(tenant, enterprise_id, namespace, self.user.user_id,
                                                       regions[0].region_name)
                apps = rs.get("app", {})
                region_resource.create_app(tenant, apps, regions[0], self.user)
                data["bean"]["tenant"]["region_name"] = regions[0].region_name
        result = general_message(200, "success", "获取成功", bean=data["bean"]["tenant"])
        return Response(result, status=status.HTTP_200_OK)


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


class EnterpriseUserTeamRoleView(EnterpriseHeaderView):
    def post(self, request, eid, user_id, tenant_name, *args, **kwargs):
        role_ids = request.data.get('role_ids', [])
        res = enterprise_services.create_user_roles(eid, user_id, tenant_name, role_ids)
        result = general_message(200, "ok", "设置成功", bean=res)
        return Response(result, status=200)


class HelmTokenView(JWTAuthApiView):
    def get(self, request, *args, **kwargs):
        eid = request.GET.get("eid")
        timestamp = str(int(time.time()))
        token = make_uuid()
        cfg_repo.create_token_record("token-" + timestamp, token, eid)
        result = general_message(200, "ok", "获取token成功", bean=token)
        return Response(result, status=status.HTTP_200_OK)


class HelmAddReginInfo(AlowAnyApiView):
    def post(self, request, *args, **kwargs):
        token = request.data.get("token")
        enterprise_id = request.data.get("enterpriseId", "")
        try:
            token_item = cfg_repo.get_by_value_eid(token, enterprise_id)
            region_alias = request.data.get("regionAlias", "")
            region_id = make_uuid()
            region_data = {
                "region_alias": region_alias,
                "region_name": request.data.get("regionName", ""),
                "region_type": json.dumps(request.data.get("regionType", [])),
                "ssl_ca_cert": request.data.get("sslCaCert", ""),
                "key_file": request.data.get("keyFile", ""),
                "cert_file": request.data.get("certFile", ""),
                "url": request.data.get("url", ""),
                "wsurl": request.data.get("wsUrl", ""),
                "httpdomain": request.data.get("httpDomain", ""),
                "tcpdomain": request.data.get("tcpDomain", ""),
                "enterprise_id": enterprise_id,
                "desc": request.data.get("desc", ""),
                "provider": request.data.get("provider", ""),
                "provider_cluster_id": request.data.get("providerClusterId", ""),
                "region_id": region_id,
                "token": token
            }
            region_data["status"] = "1"
            region = region_repo.create_region(region_data)
            if region:
                data = region_services.get_enterprise_region(enterprise_id, region_id, check_status=False)
                result = general_message(200, "success", "创建成功", bean=data)
                token_item.enable = False
                token_item.save()
                return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception(e)
        result = general_message(500, "failed", "创建失败")
        return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class HelmInstallStatus(JWTAuthApiView):
    def get(self, request, *args, **kwargs):
        eid = request.GET.get("eid", "")
        token = request.GET.get("token", "")
        try:
            region = region_repo.get_region_by_token(eid=eid, token=token)
            region_resource = region_services.conver_region_info(region, "yes")
            if region_resource["health_status"] == "ok":
                result = general_message(200, "success", "对接成功")
                return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception(e)
        result = general_message(200, "failed", "对接失败")
        return Response(result, status=status.HTTP_200_OK)


class Goodrainlog(EnterpriseAdminView):
    def get(self, request, *args, **kwargs):
        filepath = LOG_PATH + '/goodrain.log'
        res = list()
        with open(filepath, 'r', errors='ignore') as f:
            lines = f.readlines()[-1000:]
            for line in lines:
                res.append(line)
        result = general_message(200, "success", "获取成功", bean=res)
        return Response(result, status=status.HTTP_200_OK)


class Downlodlog(EnterpriseAdminView):
    def get(self, request):
        def file_iterator(fn, chunk_size=512):
            while True:
                c = fn.read(chunk_size)
                if c:
                    yield c
                else:
                    break

        filepath = LOG_PATH + '/goodrain.log'
        fn = open(filepath, 'rb')
        response = FileResponse(file_iterator(fn))
        response['Content-Type'] = 'application/octet-stream'
        response['Content-Disposition'] = 'attachment;filename=goodrain.log'
        return response


class RbdPods(EnterpriseAdminView):
    def get(self, request, region_name, *args, **kwargs):
        pods_info = region_api.get_rbd_pods(region_name)
        result = general_message(200, "success", "获取成功", bean=pods_info)
        return Response(result, status=status.HTTP_200_OK)


class RbdPodLog(EnterpriseAdminView):
    def get(self, request, region_name, *args, **kwargs):
        pod_name = request.GET.get("pod_name", "")
        if not pod_name:
            raise AbortRequest("the field 'pod_name' is required")
        follow = True if request.GET.get("follow") == "true" else False
        stream = component_log_service.get_rbd_log_stream(region_name, pod_name, follow)
        response = StreamingHttpResponse(stream, content_type="text/plain")
        # disabled the GZipMiddleware on this call by inserting a fake header into the StreamingHttpResponse
        response['Content-Encoding'] = 'identity'
        return response


class RbdComponentLogs(EnterpriseAdminView):
    def get(self, request, region_name, *args, **kwargs):
        lines = request.GET.get("lines", 100)
        rbd_name = request.GET.get("rbd_name", "")
        body = region_api.get_rbd_component_logs(region_name, rbd_name, lines)
        log_list = body["list"]
        result = general_message(200, "success", "获取成功", bean=log_list)
        return Response(result, status=status.HTTP_200_OK)


class RbdLogFiles(EnterpriseAdminView):
    def get(self, request, region_name, *args, **kwargs):
        rbd_name = request.GET.get("rbd_name", "")
        body = region_api.get_rbd_log_files(region_name, rbd_name)
        file_list = body["list"]
        log_domain_url = ws_service.get_log_domain(request, region_name)
        file_urls = [{"file_name": f["filename"], "file_url": log_domain_url + "/" + f["relative_path"]} for f in file_list]
        result = general_message(200, "success", "获取成功", bean=file_urls)
        return Response(result, status=status.HTTP_200_OK)


class ShellPod(EnterpriseAdminView):
    def post(self, request, *args, **kwargs):
        region_name = request.data.get("region_name", "")
        body = region_api.create_shell_pod(region_name)
        result = general_message(200, "success", "创建成功", bean=body)
        return Response(result, status=status.HTTP_200_OK)

    def delete(self, request, *args, **kwargs):
        region_name = request.data.get("region_name", "")
        pod_name = request.data.get("pod_name", "")
        body = region_api.delete_shell_pod(region_name, pod_name)
        result = general_message(200, "success", "删除成功", bean=body)
        return Response(result, status=status.HTTP_200_OK)


class MyEventsView(JWTAuthApiView):
    def get(self, request, *args, **kwargs):
        eid = kwargs.get("enterprise_id", "")
        region_names = request.GET.get("region_names", "")
        page = request.GET.get("page", 1)
        page_size = request.GET.get("page_size", 10)
        res_events = []
        for region_name in eval(region_names):
            my_tenant_ids = team_repo.get_tenants_by_user_id(self.user.user_id).values_list("tenant_id", flat=True)
            tenant_id_list = {"tenant_ids": list(my_tenant_ids)}
            events = event_service.get_myteams_events("tenant", json.dumps(tenant_id_list), eid, region_name, int(page),
                                                      int(page_size))
            if events:
                res_events += events
        result = general_message(200, "success", "查询成功", list=res_events)
        return Response(result, status=result["code"])


class ServiceAlarm(EnterpriseAdminView):
    def get(self, request, enterprise_id, *args, **kwargs):
        res_service = []
        # 获取企业下团队数量
        if team_repo.get_team_by_enterprise_id(enterprise_id).count() > 0:
            # 获取企业下可用集群
            usable_regions = region_repo.get_usable_regions(enterprise_id)
            # 获取异常组件
            all_abnormal_service_id = []
            for usable_region in usable_regions:
                abnormal_service_id = region_api.get_user_service_abnormal_status(usable_region.region_name, enterprise_id)
                all_abnormal_service_id += abnormal_service_id["service_ids"]
            # 根据组件id获取应用信息
            result_map = group_service.get_services_group_name(all_abnormal_service_id)
            # 根据组件id获取组件信息
            serivce_infos = service_repo.get_services_by_service_ids(all_abnormal_service_id)
            for serivce in serivce_infos:
                # 获取团队信息
                team = team_repo.get_team_by_team_id(serivce.tenant_id)
                res_service.append({
                    "service_cname": serivce.service_cname,
                    "group_id": result_map[serivce.service_id]["group_id"],
                    "group_name": result_map[serivce.service_id]["group_name"],
                    "service_alias": serivce.service_alias,
                    "service_id": serivce.service_id,
                    "tenant_id": serivce.tenant_id,
                    "region_name": serivce.service_region,
                    "tenant_name": team.tenant_name,
                    "tenant_alias": team.tenant_alias
                })
        result = general_message(200, "team query success", "查询成功", list=res_service)
        return Response(result, status=200)


class GetNodes(EnterpriseAdminView):
    def get(self, request, region_name, *args, **kwargs):
        res, body = region_api.get_cluster_nodes(region_name)
        nodes = body["list"]
        node_list = []
        all_node_roles = []
        cluster_role_count = {}
        node_status = "NotReady"
        for node in nodes:
            for cond in node["conditions"]:
                if cond["type"] == "Ready" and cond["status"] == "True":
                    node_status = "Ready"
            schedulable = node["unschedulable"]
            if schedulable:
                node_status = node_status + ",SchedulingDisabled"
            node_list.append({
                "name": node["name"],
                "status": node_status,
                "role": node["roles"],
                "unschedulable": schedulable,
                "req_cpu": node["resource"]["req_cpu"],
                "cap_cpu": node["resource"]["cap_cpu"],
                "req_memory": node["resource"]["req_memory"] / 1000,
                "cap_memory": node["resource"]["cap_memory"] / 1000
            })
            all_node_roles += node["roles"]
        for node_role in all_node_roles:
            cluster_role_count[node_role] = all_node_roles.count(node_role)
        result = general_message(200, "success", "获取成功", bean=cluster_role_count, list=node_list)
        return Response(result, status=status.HTTP_200_OK)


class GetNode(EnterpriseAdminView):
    def get(self, request, region_name, node_name, *args, **kwargs):
        res, body = region_api.get_node_info(region_name, node_name)
        node = body["bean"]
        node_status = "NotReady"
        res = {
            "name": node["name"],
            "ip": node["external_ip"] if node["external_ip"] else node["internal_ip"],
            "container_runtime": node["container_run_time"],
            "architecture": node["architecture"],
            "roles": node["roles"],
            "os_version": node["os_version"],
            "unschedulable": node["unschedulable"],
            "create_time": node["create_time"],
            "kernel": node["kernel_version"],
            "os_type": node["operating_system"],
            "req_cpu": node["resource"]["req_cpu"],
            "cap_cpu": node["resource"]["cap_cpu"],
            "req_memory": node["resource"]["req_memory"] / 1000,
            "cap_memory": node["resource"]["cap_memory"] / 1000,
            "req_root_partition": node["resource"]["req_disk"] / 1024 / 1024 / 1024,
            "cap_root_partition": node["resource"]["cap_disk"] / 1024 / 1024 / 1024,
            "req_docker_partition": node["resource"]["cap_container_disk"],
            "cap_docker_partition": node["resource"]["req_container_disk"]
        }
        for cond in node["conditions"]:
            if cond["type"] == "Ready" and cond["status"] == "True":
                node_status = "Ready"
        if res["unschedulable"]:
            node_status = node_status + ",SchedulingDisabled"
        res["status"] = node_status
        result = general_message(200, "success", "获取成功", bean=res)
        return Response(result, status=status.HTTP_200_OK)


class NodeAction(EnterpriseAdminView):
    def post(self, request, region_name, node_name, *args, **kwargs):
        action = request.data.get("action", "")
        support_action = ["unschedulable", "reschedulable", "down", "up", "evict"]
        if action not in support_action:
            return Response(general_message(400, "failed", "暂不支持当前操作"), status=status.HTTP_400_BAD_REQUEST)
        body = region_api.operate_node_action(region_name, node_name, action)
        result = general_message(200, "success", "操作成功", bean=body)
        return Response(result, status=status.HTTP_200_OK)


class NodeLabelsOperate(EnterpriseAdminView):
    def get(self, request, region_name, node_name, *args, **kwargs):
        res, body = region_api.get_node_labels(region_name, node_name)
        result = general_message(200, "success", "获取成功", bean=body["bean"])
        return Response(result, status=status.HTTP_200_OK)

    def put(self, request, region_name, node_name, *args, **kwargs):
        labels = request.data.get("labels", {})
        res, body = region_api.update_node_labels(region_name, node_name, labels)
        result = general_message(200, "success", "操作成功", bean=body["bean"])
        return Response(result, status=status.HTTP_200_OK)


class NodeTaintOperate(EnterpriseAdminView):
    def get(self, request, region_name, node_name, *args, **kwargs):
        res, body = region_api.get_node_taints(region_name, node_name)
        result = general_message(200, "success", "获取成功", bean=body["list"])
        return Response(result, status=status.HTTP_200_OK)

    def put(self, request, region_name, node_name, *args, **kwargs):
        taints = request.data.get("taints", [])
        res, body = region_api.update_node_taints(region_name, node_name, taints)
        result = general_message(200, "success", "操作成功", list=body["list"])
        return Response(result, status=status.HTTP_200_OK)


class RainbondComponents(EnterpriseAdminView):
    def get(self, request, region_name, *args, **kwargs):
        res, body = region_api.get_rainbond_components(region_name)
        components = body["list"]

        component_list = []
        for component in components:
            component_info = {}
            pod_list = []
            component_info["name"] = component["name"]
            component_info["run_pods"] = component["run_pods"]
            component_info["all_pods"] = component["all_pods"]
            if component["run_pods"] == component["all_pods"]:
                component_info["status"] = "Running"
            else:
                component_info["status"] = "Abnormal"
            for pod in component["pods"]:
                pod_info = {}
                pod_name = pod["metadata"]["name"]
                pod_info["pod_name"] = pod_name
                pod_info["create_time"] = pod["metadata"]["creationTimestamp"]
                pod_info["status"] = pod["status"]["phase"]
                container_status = pod["status"]["containerStatuses"]
                pod_info["pod_ip"] = pod["status"]["podIP"]
                pod_info["all_container"] = len(container_status)
                run_container = 0
                restart_count = 0
                for ctr_status in container_status:
                    restart_count += ctr_status["restartCount"]
                    state = ctr_status["state"]
                    if "running" in state.keys():
                        run_container += 1
                pod_info["run_container"] = run_container
                pod_info["restart_count"] = restart_count
                pod_list.append(pod_info)
            component_info["pods"] = pod_list
            component_list.append(component_info)
        result = general_message(200, "success", "获取成功", list=component_list)
        return Response(result, status=status.HTTP_200_OK)


class ContainerDisk(EnterpriseAdminView):
    def get(self, request, region_name, node_name, *args, **kwargs):
        container_runtime = request.GET.get("container_runtime", "")
        container = container_runtime.split(":")[0]
        res, body = region_api.get_container_disk(region_name, container)
        container_disk = body["bean"]
        res = {
            "path": container_disk["path"],
            "total": container_disk["total"] / 1024 / 1024 / 1024,
            "used": container_disk["userd"] / 1024 / 1024 / 1024
        }
        result = general_message(200, "success", "获取成功", bean=res)
        return Response(result, status=status.HTTP_200_OK)
