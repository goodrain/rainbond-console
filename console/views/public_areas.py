# -*- coding: utf-8 -*-
import logging

from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.views.decorators.cache import never_cache
from rest_framework.response import Response
from django.db import connection

from backends.services.exceptions import GroupNotExistError
from console.repositories.group import group_repo, group_service_relation_repo
from console.repositories.service_repo import service_repo
from console.services.app_actions.app_log import AppEventService
from console.services.common_services import common_services
from console.services.event_services import service_event_dynamic
from console.services.service_services import base_service
from console.services.team_services import team_services
from goodrain_web.tools import JuncheePaginator
from www.utils.status_translate import get_status_info_map
from console.views.base import RegionTenantHeaderView
from www.apiclient.regionapi import RegionInvokeApi
from www.decorator import perm_required
from www.utils.return_message import general_message, error_message
from console.services.group_service import group_service
from console.repositories.region_repo import region_repo
from console.repositories.app_config import tcp_domain, domain_repo
from console.repositories.share_repo import share_repo
from console.repositories.backup_repo import backup_record_repo
from www.models import TenantServiceInfo


event_service = AppEventService()

region_api = RegionInvokeApi()

logger = logging.getLogger('default')


class AllServiceInfo(RegionTenantHeaderView):

    def post(self, request, *args, **kwargs):
        """
        查看总览分页页面应用状态信息(弃)
        ---
        parameters:
            - name: team_name
              description: 团队名
              required: true
              type: string
              paramType: path
            - name: service_ids
              description: 当前页面应用ID列表 格式{"service_ids": ["1","2"]}
              required: true
              type: string
              paramType: form
        """
        try:
            code = 200
            service_ids = request.data["service_ids"]
            print(service_ids)
            if len(service_ids) > 0:
                status_list = base_service.status_multi_service(region=self.response_region, tenant_name=self.team_name,
                                                                service_ids=service_ids,
                                                                enterprise_id=self.team.enterprise_id)
                result = general_message(code, "success", "批量获取状态成功", list=status_list)
                return Response(result, status=code)
        except Exception as e:
            code = 500
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=code)


class TeamOverView(RegionTenantHeaderView):
    def get(self, request, *args, **kwargs):
        """
        总览 团队信息
        ---
        parameters:
            - name: team_name
              description: 团队名
              required: true
              type: string
              paramType: path
        """
        try:
            overview_detail = dict()
            users = team_services.get_team_users(self.team)
            if users:
                user_nums = len(users)
                overview_detail["user_nums"] = user_nums
                team_service_num = service_repo.get_team_service_num_by_team_id(team_id=self.team.tenant_id,
                                                                                region_name=self.response_region)
                source = common_services.get_current_region_used_resource(self.team, self.response_region)
                # 获取tcp和http策略数量
                region = region_repo.get_region_by_region_name(self.response_region)
                total_tcp_domain = tcp_domain.get_all_domain_count_by_tenant_and_region(self.team.tenant_id, region.region_id)
                overview_detail["total_tcp_domain"] = total_tcp_domain

                total_http_domain = domain_repo.get_all_domain_count_by_tenant_and_region_id(self.team.tenant_id, region.region_id)
                overview_detail["total_http_domain"] = total_http_domain

                # 获取分享应用数量
                groups = group_repo.get_tenant_region_groups(self.team.tenant_id, region.region_name)
                share_app_num = 0
                if groups:
                    for group in groups:
                        share_record = share_repo.get_service_share_record_by_groupid(group_id=group.ID)
                        if share_record:
                            share_app_num += 1
                overview_detail["share_app_num"] = share_app_num

                if source:
                    team_app_num = group_repo.get_tenant_region_groups_count(self.team.tenant_id, self.response_region)
                    overview_detail["team_app_num"] = team_app_num
                    overview_detail["team_service_num"] = team_service_num
                    overview_detail["team_service_memory_count"] = int(source["memory"])
                    overview_detail["team_service_total_disk"] = int(source["disk"])
                    overview_detail["team_service_total_cpu"] = int(source["limit_cpu"])
                    overview_detail["team_service_total_memory"] = int(source["limit_memory"])
                    overview_detail["team_service_use_cpu"] = int(source["cpu"])
                    cpu_usage = 0
                    memory_usage = 0
                    if int(source["limit_cpu"]) != 0:
                        cpu_usage = float(int(source["cpu"])) / float(int(source["limit_cpu"])) * 100
                    if int(source["limit_memory"]) != 0:
                        memory_usage = float(int(source["memory"])) / float(int(source["limit_memory"])) * 100
                    overview_detail["cpu_usage"] = round(cpu_usage, 2)
                    overview_detail["memory_usage"] = round(memory_usage, 2)

                return Response(general_message(200, "success", "查询成功", bean=overview_detail))
            else:
                data = {"user_nums": 1, "team_service_num": 0, "total_memory": 0}
                result = general_message(200, "success", "团队信息总览获取成功", bean=data)
                return Response(result, status=200)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=500)


class ServiceGroupView(RegionTenantHeaderView):
    def get(self, request, *args, **kwargs):
        """
        应用组列表
        ---
        parameters:
            - name: team_name
              description: 团队名
              required: true
              type: string
              paramType: path
        """
        try:
            code = 200

            groups_services = group_service.get_groups_and_services(self.tenant, self.response_region)
            return Response(general_message(200, "success", "查询成功", list=groups_services), status=code)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=500)


class GroupServiceView(RegionTenantHeaderView):
    @never_cache
    @perm_required("view_service")
    def get(self, request, *args, **kwargs):
        """
        应用组应用列表、状态展示
        ---
        parameters:
            - name: team_name
              description: 团队名
              required: true
              type: string
              paramType: path
            - name: page
              description: 页数(默认第一页)
              required: false
              type: string
              paramType: query
            - name: page_size
              description: 每页展示个数(默认10个)
              required: false
              type: string
              paramType: query
            - name: group_id
              description: 应用组id
              required: true
              type: string
              paramType: query
        """
        try:
            code = 200
            page = request.GET.get("page", 1)
            page_size = request.GET.get("page_size", 10)
            group_id = request.GET.get("group_id", None)
            tenant_actions = list(self.user.actions.tenant_actions)
            service_actions = list(self.user.actions.service_actions)
            if group_id != "-1":
                if group_id is None or not group_id.isdigit():
                    code = 400
                    result = general_message(code, "group_id is missing or not digit!", "group_id缺失或非数字")
                    return Response(result, status=code)
                team_id = self.team.tenant_id
                group_count = group_repo.get_group_count_by_team_id_and_group_id(team_id=team_id, group_id=group_id)
                if group_count == 0:
                    code = 202
                    result = general_message(code, "group is not yours!", "当前组已删除或您无权限查看！", bean={})
                    return Response(result, status=200)
                group_service_list = service_repo.get_group_service_by_group_id(group_id=group_id,
                                                                                region_name=self.response_region,
                                                                                team_id=self.team.tenant_id,
                                                                                team_name=self.team_name,
                                                                                enterprise_id=self.team.enterprise_id)
                paginator = Paginator(group_service_list, page_size)
                try:
                    group_service_list = paginator.page(page).object_list
                except PageNotAnInteger:
                    group_service_list = paginator.page(1).object_list
                except EmptyPage:
                    group_service_list = paginator.page(paginator.num_pages).object_list
                result = general_message(code, "query success", "应用组查询成功", list=group_service_list,
                                         total=paginator.count)
            else:
                no_group_service_list = service_repo.get_no_group_service_status_by_group_id(team_name=self.team_name,
                                                                                             team_id=self.team.tenant_id,
                                                                                             region_name=
                                                                                             self.response_region,
                                                                                             enterprise_id=
                                                                                             self.team.enterprise_id)
                paginator = Paginator(no_group_service_list, page_size)
                try:
                    no_group_service_list = paginator.page(page).object_list
                except PageNotAnInteger:
                    no_group_service_list = paginator.page(1).object_list
                except EmptyPage:
                    no_group_service_list = paginator.page(paginator.num_pages).object_list
                result = general_message(code, "query success", "应用组查询成功", list=no_group_service_list,
                                         total=paginator.count)
            result["data"]["bean"] = {"tenant_actions": tenant_actions, "service_actions": service_actions}
            return Response(result, status=code)
        except GroupNotExistError as e:
            logger.exception(e)
            result = general_message(400, "query success", "该应用组不存在")
            return Response(result, status=400)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=500)


class ServiceEventsView(RegionTenantHeaderView):
    def get(self, request, *args, **kwargs):
        """
        应用事件动态
        ---
        parameters:
            - name: team_name
              description: 团队名
              required: true
              type: string
              paramType: path
            - name: page
              description: 页数(默认第一页)
              required: false
              type: string
              paramType: query
            - name: page_size
              description: 每页展示个数(默认3个)
              required: false
              type: string
              paramType: query
        """
        try:
            page = request.GET.get("page", 1)
            page_size = request.GET.get("page_size", 3)
            total = 0
            event_service_dynamic_list = service_event_dynamic.get_current_region_service_events(self.response_region,
                                                                                                 self.tenant)
            # event_service_dynamic_list = event_repo.get_evevt_by_tenant_id_region(self.tenant.tenant_id)
            event_service_list = []
            for event in event_service_dynamic_list:
                type_cn = event_service.translate_event_type(event["type"])
                event["type_cn"] = type_cn
                event_service_list.append(event)
            event_paginator = JuncheePaginator(event_service_list, int(page_size))
            event_page_list = event_paginator.page(page)
            total = event_paginator.count
            event_list = [event for event in event_page_list]
            result = general_message(200, 'success', "查询成功", list=event_list, total=total)
            return Response(result, status=result["code"])

        except Exception as e:
            code = 500
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=code)


class TeamServiceOverViewView(RegionTenantHeaderView):
    def get(self, request, *args, **kwargs):
        """
        总览 团队应用信息 + 分页 + 排序 + 模糊查询
        ---
        parameters:
            - name: team_name
              description: 团队名
              required: true
              type: string
              paramType: path
            - name: page
              description: 页数(默认第一页)
              required: false
              type: string
              paramType: query
            - name: page_size
              description: 每页展示个数(默认10个)
              required: false
              type: string
              paramType: query
            - name: order
              description: 排序规则 desc(从大到小)或者asc(从小到大) 默认desc
              required: false
              type: string
              paramType: query
            - name: fields
              description: 排序字段 默认 update_time 可用(update_time, min_memory)
              required: false
              type: string
              paramType: query
            - name: query_key
              description: 模糊应用名 默认为空，查到所有应用
              required: false
              type: string
              paramType: query
            - name: service_status
              description: 应用状态 默认all 可用(running, closed, all)
              required: true
              type: string
              paramType: query
        """
        try:
            code = 200
            page = request.GET.get("page", 1)
            page_size = request.GET.get("page_size", 10)
            order = request.GET.get('order_type', 'desc')
            fields = request.GET.get('fields', 'update_time')
            query_key = request.GET.get("query_key", '')
            service_status = request.GET.get("service_status", 'all')
            if not self.team:
                result = general_message(400, "failed", "该团队不存在")
                return Response(result, status=400)
            services_list = base_service.get_fuzzy_services_list(team_id=self.team.tenant_id,
                                                                 region_name=self.response_region,
                                                                 query_key=query_key, fields=fields, order=order)
            if services_list:
                try:
                    service_ids = [service["service_id"] for service in services_list]
                    status_list = base_service.status_multi_service(region=self.response_region,
                                                                    tenant_name=self.team_name,
                                                                    service_ids=service_ids,
                                                                    enterprise_id=self.team.enterprise_id)
                    status_cache = {}
                    statuscn_cache = {}
                    for status in status_list:
                        status_cache[status["service_id"]] = status["status"]
                        statuscn_cache[status["service_id"]] = status["status_cn"]
                    result = []
                    for service in services_list:
                        if service["group_id"] is None:
                            service["group_name"] = "未分组"
                            service["group_id"] = "-1"
                        if service_status == "all":
                            service["status_cn"] = statuscn_cache.get(service["service_id"], "未知")
                            status = status_cache.get(service["service_id"], "unknow")
                            if status == "unknow" and service["create_status"] != "complete":
                                service["status"] = "creating"
                                service["status_cn"] = "创建中"
                            else:
                                service["status"] = status_cache.get(service["service_id"], "unknow")
                                service["status_cn"] = get_status_info_map(service["status"]).get("status_cn")
                            if service["status"] == "closed" or service["status"] == "undeploy":
                                service["min_memory"] = 0
                            result.append(service)
                        else:
                            if status_cache.get(service.service_id) == service_status:
                                service["status"] = status_cache.get(service.service_id, "unknow")
                                service["status_cn"] = get_status_info_map(service["status"]).get("status_cn")
                                if service["status"] == "closed" or service["status"] == "undeploy":
                                    service["min_memory"] = 0
                                result.append(service)
                    paginator = Paginator(result, page_size)
                    try:
                        result = paginator.page(page).object_list
                    except PageNotAnInteger:
                        result = paginator.page(1).object_list
                    except EmptyPage:
                        result = paginator.page(paginator.num_pages).object_list
                    result = general_message(200, "query user success", "查询用户成功", list=result, total=paginator.count)
                except Exception as e:
                    logger.exception(e)
                    return Response(services_list, status=200)
                return Response(result, status=code)
            else:
                result = general_message(200, "success", "当前团队没有创建应用")
                return Response(result, status=200)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=500)


class TeamAppSortViewView(RegionTenantHeaderView):
    def get(self, request, *args, **kwargs):
        """
        总览 团队应用信息
        """
        try:
            page = int(request.GET.get("page", 1))
            page_size = int(request.GET.get("page_size", 10))
            groups = group_repo.get_tenant_region_groups(self.team.tenant_id, self.response_region)
            total = len(groups)
            app_num_dict = {"total": total}
            start = (page - 1) * page_size
            end = page * page_size
            app_list = []
            if groups:
                for group in groups:
                    app_dict = dict()
                    app_dict["group_name"] = group.group_name
                    app_dict["group_id"] = group.ID
                    # 分享记录和备份记录
                    share_record_num = share_repo.get_app_share_record_count_by_groupid(group_id=group.ID)
                    app_dict["share_record_num"] = share_record_num
                    backup_records = backup_record_repo.get_group_backup_records(self.team.tenant_id,
                                                                                 self.response_region, group.ID)
                    backup_record_num = len(backup_records)
                    app_dict["backup_record_num"] = backup_record_num
                    # 服务数量记录
                    services = group_service_relation_repo.get_services_by_group(group.ID)
                    services_num = len(services)
                    app_dict["services_num"] = services_num

                    run_service_num = 0
                    if services:
                        service_ids = []
                        for service in services:
                            service_ids.append(service.service_id)

                        status_list = base_service.status_multi_service(region=self.response_region,
                                                                        tenant_name=self.team_name,
                                                                        service_ids=service_ids,
                                                                        enterprise_id=self.team.enterprise_id)
                        for status in status_list:
                            if status["status"] in ["running", "upgrade", "starting", "some_abnormal"]:
                                run_service_num += 1

                    app_dict["run_service_num"] = run_service_num
                    app_list.append(app_dict)

                # 排序
                app_list.sort(key=lambda x: x['run_service_num'], reverse=True)

            apps_list = app_list[start: end]
            result = general_message(200, "success", "查询成功", list=apps_list, bean=app_num_dict)
            return Response(result, status=200)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=500)


# 团队下应用环境变量模糊查询
class TenantServiceEnvsView(RegionTenantHeaderView):

    def get(self, request, *args, **kwargs):
        attr_name = request.GET.get("attr_name", None)
        attr_value = request.GET.get("attr_value", None)
        if not attr_name and not attr_value:
            result = general_message(400, "parameter is null", "参数缺失")
            return Response(result)
        if attr_name and attr_value:
            result = general_message(400, "faild", "变量名和值不能同时存在")
            return Response(result)
        try:
            # 查询变量名
            if attr_name:
                attr_name_list = []
                cursor = connection.cursor()
                cursor.execute("select attr_name from tenant_service_env_var where tenant_id='{0}' and attr_name like '%{1}%' order by attr_name;".format(self.team.tenant_id, attr_name))
                service_envs = cursor.fetchall()
                if len(service_envs) > 0:
                    for service_env in service_envs:
                        if service_env[0] not in attr_name_list:
                            attr_name_list.append(service_env[0])
                result = general_message(200, "success", "查询成功", list=attr_name_list)
                return Response(result)

            # 查询变量值
            if attr_value:
                attr_value_list = []
                cursor = connection.cursor()
                cursor.execute("select attr_value from tenant_service_env_var where tenant_id='{0}' and attr_value like '%{1}%' order by attr_value;".format(self.team.tenant_id, attr_value))
                service_envs = cursor.fetchall()
                if len(service_envs) > 0:
                    for service_env in service_envs:
                        if service_env[0] not in attr_value_list:
                            attr_value_list.append(service_env[0])
                result = general_message(200, "success", "查询成功", list=attr_value_list)
                return Response(result)
        except Exception as e:
            logger.exception(e)
            result = general_message(500, e.message, "系统异常")
            return Response(result)







