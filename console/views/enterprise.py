# -*- coding: utf8 -*-
import json
import logging
import os
import time

import requests
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
from console.services.gateway_api import gateway_api
from console.services.app_actions import ws_service
from console.services.app_config.component_logs import component_log_service
from console.services.config_service import EnterpriseConfigService
from console.services.enterprise_services import enterprise_services
from console.services.operation_log import operation_log_service, Operation, OperationModule
from console.services.perm_services import user_kind_role_service
from console.services.region_lang_version import region_lang_version
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
from goodrain_web.settings import LOG_PATH, DATA_DIR
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import PermRelTenant, Tenants
from www.utils.return_message import general_message

region_api = RegionInvokeApi()
logger = logging.getLogger("default")

LANGUAGE = "language"
VERSION = "version"
CONTENT = "content"
NAMESPACE = "namespace"
EVENT_ID = "event_id"
FILE_NAME = "file_name"

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
            regions = region_repo.get_regions_by_enterprise_id(self.enterprise.enterprise_id, 1)
            default_region = {}
            if os.getenv("ENABLE_CLUSTER") == "true" and not regions:
                region = region_services.create_default_region(self.enterprise.enterprise_id, request.user)
                if region:
                    ent["disable_install_cluster_log"] = True
                    _, total = team_services.get_enterprise_teams(self.enterprise.enterprise_id)
                    if total == 0:
                        region_services.create_sample_application(enter, region, request.user)
                default_region = region.to_dict()
            ent["default_region"] = default_region
            ent.update(EnterpriseConfigService(enterprise_id, self.user.user_id).initialization_or_get_config)
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
        ent_config_servier = EnterpriseConfigService(enterprise_id, self.user.user_id)
        key = key.upper()
        if key in ent_config_servier.base_cfg_keys + ent_config_servier.cfg_keys:
            try:
                data = ent_config_servier.update_config(key, value)
                result = general_message(200, "success", "更新成功", bean=data)
                comment = operation_log_service.generate_generic_comment(
                    operation=Operation.CHANGE, module=OperationModule.CERTSIGN, module_name="的配置")
                operation_log_service.create_enterprise_log(
                    user=self.user, comment=comment, enterprise_id=self.user.enterprise_id)
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
        ent_config_servier = EnterpriseConfigService(enterprise_id, self.user.user_id)
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


# 等待优化
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


class EnterpriseTeamNames(JWTAuthApiView):
    def get(self, request, enterprise_id, *args, **kwargs):
        tenants = Tenants.objects.filter()
        tenant_namespaces = [tenant.namespace for tenant in tenants]
        data = {"tenant_names": tenant_namespaces}
        result = general_message(200, "success", None, bean=data)
        return Response(result, status=status.HTTP_200_OK)


class EnterpriseTeams(JWTAuthApiView):
    def get(self, request, enterprise_id, *args, **kwargs):
        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 10))
        name = request.GET.get("name", None)
        teams, total = team_services.get_enterprise_teams_fenye(
            enterprise_id, query=name, page=page, page_size=page_size)
        jg_teams = team_services.jg_teams(enterprise_id, teams)
        data = {"total_count": total, "page": page, "page_size": page_size, "list": jg_teams}
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
        new_information = json.dumps({"集群ID": region_name, "集群名称": region_alias, "备注": desc, "配置文件": token}, ensure_ascii=False)
        if region:
            data = region_services.get_enterprise_region(enterprise_id, region.region_id, check_status=False)
            result = general_message(200, "success", "创建成功", bean=data)
            comment = operation_log_service.generate_generic_comment(
                operation=Operation.CREATE, module=OperationModule.CLUSTER, module_name="{}".format(region_alias))
            operation_log_service.create_cluster_log(
                user=self.user, comment=comment, enterprise_id=self.user.enterprise_id, new_information=new_information)
            return Response(result, status=status.HTTP_200_OK)
        else:
            result = general_message(500, "failed", "创建失败")
            return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EnterpriseRegionGatewayBatch(JWTAuthApiView):
    def get(self, request, enterprise_id, region_name, *args, **kwargs):
        data = gateway_api.list_gateways(enterprise_id, region_name)
        result = general_message(200, "success", "获取成功", list=data["list"])
        return Response(result, status=status.HTTP_200_OK)


class EnterpriseRegionNamespace(JWTAuthApiView):
    def get(self, request, enterprise_id, region_id, *args, **kwargs):
        content = request.GET.get("content", "all")
        data = region_resource.get_namespaces(enterprise_id, region_id, content)
        result = general_message(200, "success", "获取成功", bean=data["list"])
        return Response(result, status=status.HTTP_200_OK)


class EnterpriseRegionLangVersion(JWTAuthApiView):
    def get(self, request, enterprise_id, region_id, *args, **kwargs):
        language = request.GET.get("language", "")
        data = region_lang_version.show_long_version(enterprise_id, region_id, language)
        result = general_message(200, "success", "获取成功", list=data["list"])
        return Response(result, status=status.HTTP_200_OK)

    def post(self, request, enterprise_id, region_id, *args, **kwargs):
        language = request.data.get("language", "")
        version = request.data.get("version", "")
        event_id = request.data.get("event_id", "")
        file_name = request.data.get("file_name", "")
        if ' ' in version:
            data = {"code": 400, "msg": "version format mistake",
                    "msg_show": "版本号格式不正确"}
            return Response(data, status=400)
        extensions = ['zip', 'war', 'jar', 'tar', 'tar.gz', 'rar']
        if any(file_name.endswith(ext) for ext in extensions) or language == "net_runtime" or language == "net_compiler":
            data = region_lang_version.create_long_version(enterprise_id, region_id, language, version, event_id, file_name)
            if data.get("bean") == "exist":
                data = {"code": 409, "msg": "version is exist", "msg_show": "该版本已存在"}
                return Response(data, status=409)
            result = general_message(200, "success", "添加成功")
            return Response(result, status=status.HTTP_200_OK)
        else:
            data = {"code": 400, "msg": "package format mistake", "msg_show": "文件上传格式不正确，支持zip, war, jar, tar, tar.gz, rar"}
            return Response(data, status=400)

    def put(self, request, enterprise_id, region_id, *args, **kwargs):
        language = request.data.get("language", "")
        version = request.data.get("version", "")
        region_lang_version.update_long_version(enterprise_id, region_id, language, version)
        result = general_message(200, "success", "更新成功")
        return Response(result, status=result.get("code", 200))

    def delete(self, request, enterprise_id, region_id, *args, **kwargs):
        language = request.data.get("language", "")
        version = request.data.get("version", "")
        use_components = region_lang_version.delete_long_version(enterprise_id, region_id, language, version)
        if use_components:
            data = {"code": 405, "msg": "version in use", "msg_show": "该版本在使用中，无法删除"}
            return Response(data, status=405)
        result = general_message(200, "success", "删除成功")
        return Response(result, status=result.get("code", 200))


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
        old_region = region_services.get_enterprise_region(enterprise_id, region_id)
        region = region_services.update_enterprise_region(enterprise_id, region_id, request.data)
        result = general_message(200, "success", "更新成功", bean=region)
        old_information = region_services.json_region(old_region)
        new_information = region_services.json_region(region)
        comment = operation_log_service.generate_generic_comment(
            operation=Operation.UPDATE, module=OperationModule.CLUSTER,
            module_name="{}".format(region.get("region_alias", "")))
        operation_log_service.create_cluster_log(
            user=self.user,
            comment=comment,
            enterprise_id=self.user.enterprise_id,
            old_information=old_information,
            new_information=new_information)
        return Response(result, status=result.get("code", 200))

    def delete(self, request, enterprise_id, region_id, *args, **kwargs):
        try:
            region_repo.del_by_enterprise_region_id(enterprise_id, region_id)
        except RegionConfig.DoesNotExist:
            raise ServiceHandleException(status_code=404, msg="集群已不存在")
        region = region_services.get_enterprise_region(enterprise_id, region_id, check_status=False)
        old_information = region_services.json_region(region)
        result = general_message(200, "success", "删除成功")
        comment = operation_log_service.generate_generic_comment(
            operation=Operation.DELETE, module=OperationModule.CLUSTER, module_name="{}".format(region.get("region_alias", "")))
        operation_log_service.create_cluster_log(
            user=self.user, comment=comment, enterprise_id=self.user.enterprise_id, old_information=old_information)
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
        team_services.set_tenant_resource_limit(enterprise_id, region_id, tenant_name, request.data)
        team = team_services.get_tenant_by_tenant_name(tenant_name)
        limit = request.data.get("limit_memory", 0)
        team_alias = operation_log_service.process_team_name(team.tenant_alias, region_id, tenant_name)
        comment = operation_log_service.generate_generic_comment(
            operation=Operation.LIMIT, module=OperationModule.TEAM,
            module_name="{} 的内存使用量为 {} MB".format(team_alias, limit))
        operation_log_service.create_cluster_log(user=self.user, comment=comment, enterprise_id=self.user.enterprise_id)
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
            token_item = cfg_repo.get_by_value_eid(token)
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
        apiHost = request.GET.get("api_host")
        token = request.GET.get("token")
        try:
            response = requests.get("http://{}:6060/helm_install/region_status/{}".format(apiHost, token), timeout=5)
            data = response.json()
            region_info = data.get("bean")
            enterprise_id = self.enterprise.enterprise_id
            region_alias = region_info.get("regionAlias", "")
            region_id = make_uuid()
            region_data = {
                "region_alias": region_alias,
                "region_name": region_info.get("regionName", ""),
                "region_type": json.dumps(region_info.get("regionType", [])),
                "ssl_ca_cert": region_info.get("sslCaCert", ""),
                "key_file": region_info.get("keyFile", ""),
                "cert_file": region_info.get("certFile", ""),
                "url": region_info.get("url", ""),
                "wsurl": region_info.get("wsUrl", ""),
                "httpdomain": region_info.get("httpDomain", ""),
                "tcpdomain": region_info.get("tcpDomain", ""),
                "enterprise_id": enterprise_id,
                "desc": region_info.get("desc", ""),
                "provider": region_info.get("provider", ""),
                "provider_cluster_id": region_info.get("providerClusterId", ""),
                "region_id": region_id,
                "token": token,
            }
            region_data["status"] = "1"
            region = region_repo.create_region(region_data)
            region_resource = region_services.conver_region_info(region, "yes")
            if region_resource["health_status"] == "ok":
                result = general_message(200, "success", "对接成功", bean={"health_status": "installed"})
                return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception(e)
        result = general_message(200, "failed", "等待对接", bean={"health_status": "installing"})
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
        nodes, cluster_role_count = enterprise_services.get_nodes(region_name)
        result = general_message(200, "success", "获取成功", bean=cluster_role_count, list=nodes)
        return Response(result, status=status.HTTP_200_OK)


class GetNode(EnterpriseAdminView):
    def get(self, request, region_name, node_name, *args, **kwargs):
        res = enterprise_services.get_node_detail(region_name, node_name)
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
        component_list = enterprise_services.get_rbdcomponents(region_name)
        result = general_message(200, "success", "获取成功", list=component_list)
        return Response(result, status=status.HTTP_200_OK)


class ContainerDisk(EnterpriseAdminView):
    def get(self, request, region_name, *args, **kwargs):
        container_runtime = request.GET.get("container_runtime", "")
        container = container_runtime.split(":")[0]
        res, body = region_api.get_container_disk(region_name, container)
        container_disk = body["bean"]
        res = {
            "path": container_disk["path"],
            "total": container_disk["total"] / 1024 / 1024 / 1024,
            "used": container_disk["used"] / 1024 / 1024 / 1024
        }
        result = general_message(200, "success", "获取成功", bean=res)
        return Response(result, status=status.HTTP_200_OK)


class EnterpriseMenuManage(JWTAuthApiView):
    def get(self, request, enterprise_id, *args, **kwargs):
        menus_res = enterprise_services.get_enterprise_menus(enterprise_id)
        result = general_message(200, "success", "获取成功", list=menus_res)
        return Response(result, status=status.HTTP_200_OK)

    def post(self, request, enterprise_id, *args, **kwargs):
        title = request.data.get("title", "")
        path = request.data.get("path", "")
        parent_id = request.data.get("parent_id", 0)
        iframe = request.data.get("iframe", False)
        data = {
            "eid": enterprise_id,
            "title": title,
            "path": path,
            "parent_id": parent_id,
            "iframe": iframe,
        }
        menus = enterprise_services.get_menus_by_parent_id(enterprise_id, parent_id)
        for menu in menus:
            if menu.title == title:
                return Response(general_message(400, "The menu already exists", "菜单名已经存在"), status=400)
        enterprise_services.add_enterprise_menu(**data)
        result = general_message(200, "success", "添加成功")
        return Response(result, status=status.HTTP_200_OK)

    def put(self, request, enterprise_id, *args, **kwargs):
        id = request.data.get("id", "")
        title = request.data.get("title", "")
        path = request.data.get("path", "")
        parent_id = request.data.get("parent_id", 0)
        iframe = request.data.get("iframe", False)
        data = {
            "title": title,
            "path": path,
            "parent_id": parent_id,
            "iframe": iframe,
        }
        enterprise_services.update_enterprise_menu(enterprise_id, id, **data)
        result = general_message(200, "success", "更新成功")
        return Response(result, status=status.HTTP_200_OK)

    def delete(self, request, enterprise_id, *args, **kwargs):
        id = request.data.get("id", "")
        enterprise_services.delete_enterprise_menu(enterprise_id, id)
        result = general_message(200, "success", "删除成功")
        return Response(result, status=status.HTTP_200_OK)


class EnterpriseInfoFileView(AlowAnyApiView):
    def get(self, request, enterprise_id, *args, **kwargs):
        data = enterprise_services.get_enterprise_by_enterprise_id(enterprise_id)
        ent = {
            "enterprise_id": data.enterprise_id,
            "enterprise_name": data.enterprise_name,
            "enterprise_alias": data.enterprise_alias,
        }
        json_dir = "{0}/{1}.json".format(DATA_DIR, data.enterprise_alias)
        file = os.path.exists(json_dir)
        if file:
            os.remove(json_dir)
        with open(json_dir, "w") as f:
            json.dump(ent, f)

        def file_iterator(fn, chunk_size=512):
            while True:
                c = fn.read(chunk_size)
                if c:
                    yield c
                else:
                    break

        fn = open(json_dir, 'rb')
        response = FileResponse(file_iterator(fn))
        response['Content-Type'] = 'application/octet-stream'
        response['Content-Disposition'] = 'attachment;filename={}.json'.format(data.enterprise_alias)
        return response


class EnterpriseRegionLangVersion(JWTAuthApiView):
    """
        企业区域语言版本视图。

        处理企业区域语言版本的相关请求。

        Args:
            request: HTTP 请求对象。
            enterprise_id: 企业 ID。
            region_id: 区域 ID。
            *args: 可变长度参数。
            **kwargs: 关键字参数。

        Returns:
            Response: 包含企业区域语言版本信息的 HTTP 响应。
        """
    def get(self, request, enterprise_id, region_id, *args, **kwargs):
        language = request.GET.get(LANGUAGE, "")
        data = region_lang_version.show_long_version(enterprise_id, region_id, language)
        result = general_message(200, "success", "获取成功", list=data["list"])
        return Response(result, status=status.HTTP_200_OK)

    def post(self, request, enterprise_id, region_id, *args, **kwargs):
        language = request.data.get(LANGUAGE, "")
        version = request.data.get(VERSION, "")
        event_id = request.data.get(EVENT_ID, "")
        file_name = request.data.get(FILE_NAME, "")
        # 检查版本号格式是否正确
        if not region_lang_version.is_valid_version(version):
            data = general_message(400,"version format mistake","版本号格式不正确")
            return Response(data, status=200)
        # 检查镜像格式是否正确
        if (language == "net_runtime" or language == "net_sdk") and not region_lang_version.is_valid_image(file_name):
            data = general_message(400,"image name format mistake","镜像格式不正确")
            return Response(data, status=200)
        # 检查文件上传格式是否正确
        extensions = ['jar', 'tar.gz']
        if any(file_name.endswith(ext) for ext in extensions) or language == "net_runtime" or language == "net_sdk":
            data = region_lang_version.create_long_version(enterprise_id, region_id, language, version, event_id, file_name)
            if data.get("bean") == "exist":
                data = general_message(409,"version is exist","该版本已存在")
                return Response(data, status=409)
            result = general_message(200, "success", "添加成功")
            return Response(result, status=status.HTTP_200_OK)
        else:
            data = general_message(400,"package format mistake","文件上传格式不正确，支持jar, tar.gz")
            return Response(data, status=400)

    def put(self, request, enterprise_id, region_id, *args, **kwargs):
        language = request.data.get(LANGUAGE, "")
        version = request.data.get(VERSION, "")
        first_choice = request.data.get("first_choice", True)
        show = request.data.get("show", True)
        region_lang_version.update_long_version(enterprise_id, region_id, language, version, show,first_choice)
        result = general_message(200, "success", "更新成功")
        return Response(result, status=result.get("code", 200))

    def delete(self, request, enterprise_id, region_id, *args, **kwargs):
        language = request.data.get(LANGUAGE, "")
        version = request.data.get(VERSION, "")
        use_components = region_lang_version.delete_long_version(enterprise_id, region_id, language, version)
        if use_components:
            data = general_message(405,"version in use","该版本在使用中，无法删除")
            return Response(data, status=405)
        result = general_message(200, "success", "删除成功")
        return Response(result, status=result.get("code", 200))
