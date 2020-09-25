# -*- coding: utf8 -*-
"""
  Created by leon on 18/1/5.
"""
import logging

from rest_framework.response import Response

from console.exception.main import ServiceHandleException
from console.repositories.app import service_repo
from console.repositories.group import group_service_relation_repo
from console.services.app_actions import app_manage_service
from console.services.group_service import group_service
from console.views.base import (CloudEnterpriseCenterView, RegionTenantHeaderView)
from www.apiclient.regionapi import RegionInvokeApi
from www.utils.return_message import general_message
from console.utils.reqparse import parse_item
from console.enum.app import GovernanceModeEnum
from console.exception.main import AbortRequest

logger = logging.getLogger("default")
region_api = RegionInvokeApi()


class TenantGroupView(RegionTenantHeaderView):
    def get(self, request, *args, **kwargs):
        """
        查询租户在指定数据中心下的应用
        ---
        """
        groups = group_service.get_tenant_groups_by_region(self.tenant, self.response_region)
        data = []
        for group in groups:
            data.append({"group_name": group.group_name, "group_id": group.ID, "group_note": group.note})
        result = general_message(200, "success", "查询成功", list=data)
        return Response(result, status=result["code"])

    def post(self, request, *args, **kwargs):
        """
        添加应用信息
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: group_name
              description: 应用名称
              required: true
              type: string
              paramType: form
            - name: group_note
              description: 应用备注
              required: false
              type: string
              paramType: form

        """
        group_name = request.data.get("group_name", None)
        group_note = request.data.get("group_note", "")
        if group_note and len(group_note) > 2048:
            return Response(general_message(400, "node too long", "应用备注长度限制2048"), status=400)

        data = group_service.add_group(self.tenant, self.response_region, group_name, group_note)
        bean = {
            "group_note": data.note,
            "region_name": data.region_name,
            "tenant_id": data.tenant_id,
            "group_name": data.group_name,
            "is_default": data.is_default,
            "group_id": data.ID,
        }
        result = general_message(200, "success", "创建成功", bean=bean)
        return Response(result, status=result["code"])


class TenantGroupOperationView(RegionTenantHeaderView):
    def put(self, request, app_id, *args, **kwargs):
        """
            修改组信息
            ---
            parameters:
                - name: tenantName
                  description: 租户名
                  required: true
                  type: string
                  paramType: path
                - name: app_id
                  description: 组id
                  required: true
                  type: string
                  paramType: path
                - name: group_name
                  description: 组名称
                  required: true
                  type: string
                  paramType: form

        """
        group_name = request.data.get("group_name", None)
        app_id = int(app_id)
        group_note = request.data.get("group_note", "")
        if group_note and len(group_note) > 2048:
            return Response(general_message(400, "node too long", "应用备注长度限制2048"), status=400)
        group_service.update_group(self.tenant, self.response_region, app_id, group_name, group_note)
        result = general_message(200, "success", "修改成功")
        return Response(result, status=result["code"])

    def delete(self, request, *args, **kwargs):
        """
            删除应用
            ---
            parameters:
                - name: tenantName
                  description: 租户名
                  required: true
                  type: string
                  paramType: path
                - name: group_id
                  description: 组id
                  required: true
                  type: string
                  paramType: path

        """
        group_id = int(kwargs.get("group_id", None))
        service = group_service_relation_repo.get_service_by_group(group_id)
        if not service:
            code, msg, data = group_service.delete_group_no_service(group_id)
        else:
            code = 400
            msg = '当前应用内存在组件，无法删除'
            result = general_message(code, msg, None)
            return Response(result, status=result["code"])
        if code != 200:
            result = general_message(code, "delete group error", msg)
        else:
            result = general_message(code, "success", msg)
        return Response(result, status=result["code"])

    def get(self, request, app_id, *args, **kwargs):
        """
        查询组信息
        ---
        parameters:
            - name: tenantName
                description: 租户名
                required: true
                type: string
                paramType: path
            - name: app_id
                description: 组id
                required: true
                type: string
                paramType: path
        """
        app = group_service.get_app_detail(self.tenant, self.response_region, app_id)
        result = general_message(200, "success", "success", bean=app)
        return Response(result, status=result["code"])


# 应用（组）常见操作【停止，重启， 启动， 重新构建】
class TenantGroupCommonOperationView(RegionTenantHeaderView, CloudEnterpriseCenterView):
    def post(self, request, *args, **kwargs):
        """
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: action
              description: 操作名称 stop| start|upgrade|deploy
              required: true
              type: string
              paramType: form
            - name: group_id
              description: 组id
              required: true
              type: string
              paramType: path

        """
        action = request.data.get("action", None)
        group_id = int(kwargs.get("group_id", None))
        services = group_service_relation_repo.get_services_obj_by_group(group_id)
        if not services:
            result = general_message(400, "not service", "当前组内无组件，无法操作")
            return Response(result)
        service_ids = [service.service_id for service in services]
        if action not in ("stop", "start", "upgrade", "deploy"):
            return Response(general_message(400, "param error", "操作类型错误"), status=400)
        # 去除掉第三方组件
        for service_id in service_ids:
            service_obj = service_repo.get_service_by_service_id(service_id)
            if service_obj and service_obj.service_source == "third_party":
                service_ids.remove(service_id)

        if action == "stop":
            self.has_perms([300006, 400008])
        if action == "start":
            self.has_perms([300005, 400006])
        if action == "upgrade":
            self.has_perms([300007, 400009])
        if action == "deploy":
            self.has_perms([300008, 400010])
            # 批量操作
        code, msg = app_manage_service.batch_operations(self.tenant, self.user, action, service_ids, self.oauth_instance)
        if code != 200:
            result = general_message(code, "batch manage error", msg)
        else:
            result = general_message(200, "success", "操作成功")
        return Response(result, status=result["code"])


# 应用（组）状态
class GroupStatusView(RegionTenantHeaderView):
    def get(self, request, *args, **kwargs):
        group_id = request.GET.get("group_id", None)
        region_name = request.GET.get("region_name", None)
        if not group_id or not region_name:
            result = general_message(400, "not group_id", "参数缺失")
            return Response(result)
        services = group_service_relation_repo.get_services_obj_by_group(group_id)
        if not services:
            result = general_message(400, "not service", "当前组内无组件，无法操作")
            return Response(result)
        service_id_list = [x.service_id for x in services]
        try:
            service_status_list = region_api.service_status(self.response_region, self.tenant_name, {
                "service_ids": service_id_list,
                "enterprise_id": self.user.enterprise_id
            })
            result = general_message(200, "success", "查询成功", list=service_status_list)
            return Response(result)
        except (region_api.CallApiError, ServiceHandleException) as e:
            logger.debug(e)
            raise ServiceHandleException(msg="region error", msg_show="访问数据中心失败")


class AppGovernanceModeView(RegionTenantHeaderView):
    def put(self, r, app_id, *args, **kwargs):
        governance_mode = parse_item(r, "governance_mode", required=True)
        if governance_mode not in GovernanceModeEnum.choices():
            raise AbortRequest("governance_mode not in ({})".format(GovernanceModeEnum.choices()))

        group_service.update_governance_mode(governance_mode)
        result = general_message(200, "success", "更新成功", bean={"governance_mode": governance_mode})
        return Response(result)
