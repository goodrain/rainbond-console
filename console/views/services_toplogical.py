# -*- coding: utf8 -*-
"""
  Created on 2018/3/21.
"""
import logging

from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from console.models.main import EnterpriseUserPerm
from console.models.main import PermsInfo
from console.models.main import RoleInfo
from console.models.main import RolePerms
from console.models.main import UserRole
from console.repositories.group import group_repo
from console.repositories.service_repo import service_repo
from console.services.app_actions.app_log import AppEventService
from console.services.team_services import team_services
from console.services.topological_services import topological_service
from console.views.base import RegionTenantHeaderView
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import TenantEnterprise
from www.utils.return_message import general_message

event_service = AppEventService()

region_api = RegionInvokeApi()

logger = logging.getLogger('default')


class ToplogicalBaseView(RegionTenantHeaderView):
    def __init__(self, *args, **kwargs):
        super(ToplogicalBaseView, self).__init__(*args, **kwargs)
        self.response_region = None
        self.tenant_name = None
        self.team_name = None
        self.tenant = None
        self.team = None
        self.user = None
        self.service = None

    def initial(self, request, *args, **kwargs):

        super(ToplogicalBaseView, self).initial(request, *args, **kwargs)
        self.tenant_name = kwargs.get("tenantName", None)
        service_alias = kwargs.get("serviceAlias", None)
        self.user = request.user
        if kwargs.get("team_name", None):
            self.tenant_name = kwargs.get("team_name", None)
            self.team_name = self.tenant_name
        if not self.response_region:
            self.response_region = request.GET.get('region', None)

        if not self.response_region:
            raise ImportError("region_name not found !")
        if not self.tenant_name:
            raise ImportError("team_name not found !")
        if self.tenant_name:
            tenant = team_services.get_tenant_by_tenant_name(self.tenant_name)
            if tenant:
                self.tenant = tenant
                self.team = tenant
            else:
                raise NotFound("tenant {0} not found".format(self.tenant_name))

        if service_alias:
            self.service = service_repo.get_service_by_tenant_and_alias(self.tenant.tenant_id, service_alias)

        if self.user.user_id == self.tenant.creater:
            self.is_team_owner = True
        self.enterprise = TenantEnterprise.objects.filter(enterprise_id=self.tenant.enterprise_id).first()
        self.is_enterprise_admin = False
        enterprise_user_perms = EnterpriseUserPerm.objects.filter(
            enterprise_id=self.tenant.enterprise_id, user_id=self.user.user_id).first()
        if enterprise_user_perms:
            self.is_enterprise_admin = True
        self.user_perms = []
        if self.is_enterprise_admin:
            self.user_perms = list(set(PermsInfo.objects.filter(kind="enterprise").values_list("code", flat=True)))
            self.user_perms.append(100000)
        else:
            ent_roles = RoleInfo.objects.filter(kind="enterprise", kind_id=self.user.enterprise_id)
            if ent_roles:
                ent_role_ids = ent_roles.values_list("ID", flat=True)
                ent_user_roles = UserRole.objects.filter(user_id=self.user.user_id, role_id__in=ent_role_ids)
                if ent_user_roles:
                    ent_user_role_ids = ent_user_roles.values_list("role_id", flat=True)
                    ent_role_perms = RolePerms.objects.filter(role_id__in=ent_user_role_ids)
                    if ent_role_perms:
                        self.user_perms = list(set(ent_role_perms.values_list("perm_code", flat=True)))

        if self.is_team_owner:
            team_perms = list(set(PermsInfo.objects.filter(kind="team").values_list("code", flat=True)))
            self.user_perms.extend(team_perms)
            self.user_perms.append(200000)
        else:
            team_roles = RoleInfo.objects.filter(kind="team", kind_id=self.tenant.tenant_id)
            if team_roles:
                role_ids = team_roles.values_list("ID", flat=True)
                team_user_roles = UserRole.objects.filter(user_id=self.user.user_id, role_id__in=role_ids)
                if team_user_roles:
                    team_user_role_ids = team_user_roles.values_list("role_id", flat=True)
                    team_role_perms = RolePerms.objects.filter(role_id__in=team_user_role_ids)
                    if team_role_perms:
                        self.user_perms.extend(list(set(team_role_perms.values_list("perm_code", flat=True))))
        self.check_perms(request, *args, **kwargs)

        self.initial_header_info(request)

    def initial_header_info(self, request):
        pass


class TopologicalGraphView(ToplogicalBaseView):
    def get(self, request, *args, **kwargs):
        """
        应用拓扑图(未分组应用无拓扑图, 直接返回列表展示)
        ---
        parameters:
            - name: team_name
              description: 团队名
              required: true
              type: string
              paramType: path
            - name: group_id
              description: 应用id
              required: true
              type: string
              paramType: query
        """
        group_id = request.GET.get("group_id", None)
        code = 200
        if group_id == "-1":
            code = 200
            no_service_list = service_repo.get_no_group_service_status_by_group_id(
                team_name=self.team_name, region_name=self.response_region)
            result = general_message(200, "query success", "应用查询成功", list=no_service_list)
        else:
            if group_id is None or not group_id.isdigit():
                code = 400
                result = general_message(code, "group_id is missing or not digit!", "group_id缺失或非数字")
                return Response(result, status=code)
            team_id = self.team.tenant_id
            group_count = group_repo.get_group_count_by_team_id_and_group_id(team_id=team_id, group_id=group_id)
            if group_count == 0:
                code = 202
                result = general_message(code, "group is not yours!", "当前组已删除或您无权限查看!", bean={})
                return Response(result, status=200)
            topological_info = topological_service.get_group_topological_graph(
                group_id=group_id,
                region=self.response_region,
                team_name=self.team_name,
                enterprise_id=self.team.enterprise_id)
            result = general_message(code, "Obtain topology success.", "获取拓扑图成功", bean=topological_info)
        return Response(result, status=code)


class GroupServiceDetView(ToplogicalBaseView):
    def get(self, request, *args, **kwargs):
        """
        拓扑图中组件详情
        ---
        parameters:
            - name: team_name
              description: 团队名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 组件别名
              required: true
              type: string
              paramType: path
        """
        if not self.service:
            return Response(general_message(400, "service not found", "参数错误"), status=400)
        result = topological_service.get_group_topological_graph_details(
            team=self.team,
            team_id=self.team.tenant_id,
            team_name=self.team_name,
            service=self.service,
            region_name=self.service.service_region)
        result = general_message(200, "success", "成功", bean=result)
        return Response(result, status=200)


class TopologicalInternetView(ToplogicalBaseView):
    def get(self, request, team_name, group_id, *args, **kwargs):
        """
        拓扑图中Internet详情
        ---
        parameters:
            - name: team_name
              description: 团队名
              required: true
              type: string
              paramType: path
            - name: group_id
              description: 应用id
              required: true
              type: string
              paramType: path
        """
        # logger.debug("query topological graph from:{0}".format(group_id))
        if group_id == "-1":
            code = 200
            no_service_list = service_repo.get_no_group_service_status_by_group_id(
                team_name=self.team_name, region_name=self.response_region)
            result = general_message(200, "query success", "应用获取成功", list=no_service_list)
        else:
            code = 200
            if group_id is None or not group_id.isdigit():
                code = 400
                result = general_message(code, "group_id is missing or not digit!", "group_id缺失或非数字")
                return Response(result, status=code)
            team_id = self.team.tenant_id
            group_count = group_repo.get_group_count_by_team_id_and_group_id(team_id=team_id, group_id=group_id)
            if group_count == 0:
                code = 202
                result = general_message(
                    code, "group is not yours!", "当前组已删除或您无权限查看!", bean={
                        "json_svg": {},
                        "json_data": {}
                    })
                return Response(result, status=200)
            else:
                data = topological_service.get_internet_topological_graph(group_id=group_id, team_name=team_name)
                result = general_message(code, "Obtain topology internet success.", "获取拓扑图Internet成功", bean=data)
        return Response(result, status=code)
