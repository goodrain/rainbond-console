# -*- coding: utf8 -*-
"""
  Created by leon on 18/1/5.
"""
import logging
from rest_framework.response import Response

from console.repositories.group import group_repo, group_service_relation_repo
from console.views.base import RegionTenantHeaderView
from www.decorator import perm_required
from www.utils.return_message import general_message, error_message
from console.services.group_service import group_service
from console.services.compose_service import compose_service
from console.services.team_services import team_services
from console.services.app_actions import app_manage_service
from www.apiclient.regionapi import RegionInvokeApi
from console.repositories.region_repo import region_repo
from console.services.enterprise_services import enterprise_services
from console.repositories.app import service_repo


logger = logging.getLogger("default")
region_api = RegionInvokeApi()


class TenantGroupView(RegionTenantHeaderView):
    @perm_required("view_service")
    def get(self, request, *args, **kwargs):
        """
        查询租户在指定数据中心下的组
        ---
        """
        try:
            groups = group_service.get_tenant_groups_by_region(self.tenant, self.response_region)
            data = []
            for group in groups:
                data.append({"group_name": group.group_name, "group_id": group.ID})
            # data.append({"group_name": "未分组", "group_id": -1})
            result = general_message(200, "success", "查询成功", list=data)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @perm_required("manage_group")
    def post(self, request, *args, **kwargs):
        """
        添加组信息
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: group_name
              description: 组名称
              required: true
              type: string
              paramType: form

        """
        try:
            group_name = request.data.get("group_name", None)
            code, msg, data = group_service.add_group(self.tenant, self.response_region, group_name)
            if code != 200:
                result = general_message(code, "group add error", msg)
            else:
                result = general_message(code, "success", msg, bean=data.to_dict())
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class TenantGroupOperationView(RegionTenantHeaderView):
    @perm_required("manage_group")
    def put(self, request, *args, **kwargs):
        """
            修改组信息
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
                - name: group_name
                  description: 组名称
                  required: true
                  type: string
                  paramType: form

        """
        try:
            group_name = request.data.get("group_name", None)
            group_id = int(kwargs.get("group_id", None))
            code, msg, data = group_service.update_group(self.tenant, self.response_region, group_id, group_name)
            if code != 200:
                result = general_message(code, "group add error", msg)
            else:
                result = general_message(code, "success", msg)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @perm_required("manage_group")
    def delete(self, request, *args, **kwargs):
        """
            删除组信息
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
        try:
            group_id = int(kwargs.get("group_id", None))
            service = group_service_relation_repo.get_service_by_group(group_id)
            group_object = group_repo.get_group_by_id(group_id)
            if group_object.is_default:
                result = general_message(400, "默认应用不允许删除", None)
                return Response(result, status=result["code"])
            if not service:
                code, msg, data = group_service.delete_group_no_service(group_id)
            else:
                code = 400
                msg = '当前组内有应用，无法删除'
                result = general_message(code, msg, None)
                return Response(result, status=result["code"])
            if code != 200:
                result = general_message(code, "delete group error", msg)
            else:
                result = general_message(code, "success", msg)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    def get(self, request, *args, **kwargs):
        """
            查询组信息
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
        try:
            group_id = int(kwargs.get("group_id", None))
            code, msg, data = group_service.get_group_by_id(self.tenant, self.response_region, int(group_id))
            data["create_status"] = "complete"
            data["compose_id"] = None
            if group_id != -1:
                compose_group = compose_service.get_group_compose_by_group_id(group_id)
                if compose_group:
                    data["create_status"] = compose_group.create_status
                    data["compose_id"] = compose_group.compose_id

            if code != 200:
                result = general_message(code, "group query error", msg)
            else:
                result = general_message(code, "success", msg, bean=data)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


# 应用（组）常见操作【停止，重启， 启动， 重新构建】
class TenantGroupCommonOperationView(RegionTenantHeaderView):

    @perm_required('stop_service')
    @perm_required('start_service')
    @perm_required('restart_service')
    @perm_required('deploy_service')
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
        try:
            action = request.data.get("action", None)

            group_id = int(kwargs.get("group_id", None))
            services = group_service_relation_repo.get_services_obj_by_group(group_id)
            if not services:
                result = general_message(400, "not service", "当前组内无应用，无法操作")
                return Response(result)

            if action not in ("stop", "start", "upgrade", "deploy"):
                return Response(general_message(400, "param error", "操作类型错误"), status=400)
            # 去除掉三方服务
            for service in services:
                service_obj = service_repo.get_service_by_service_id(service.service_id)
                if service_obj:
                    if service_obj.service_source == "third_party":
                        services.remove(service)

            # 校验权限
            identitys = team_services.get_user_perm_identitys_in_permtenant(user_id=self.user.user_id,
                                                                            tenant_name=self.tenant_name)
            perm_tuple = team_services.get_user_perm_in_tenant(user_id=self.user.user_id, tenant_name=self.tenant_name)

            if action == "stop":
                if "stop_service" not in perm_tuple and "owner" not in identitys and "admin" not in identitys and "developer" not in identitys:
                    return Response(general_message(400, "Permission denied", "没有关闭应用权限"), status=400)
            if action == "start":
                if "start_service" not in perm_tuple and "owner" not in identitys and "admin" not in identitys and "developer" not in identitys:
                    return Response(general_message(400, "Permission denied", "没有启动应用权限"), status=400)
            if action == "upgrade":
                if "restart_service" not in perm_tuple and "owner" not in identitys and "admin" not in identitys and "developer" not in identitys:
                    return Response(general_message(400, "Permission denied", "没有更新应用权限"), status=400)
            if action == "deploy":
                if "deploy_service" not in perm_tuple and "owner" not in identitys and "admin" not in identitys and "developer" not in identitys:
                    return Response(general_message(400, "Permission denied", "没有重新构建权限"), status=400)
            # 构建service_ids列表
            service_id_list = []
            for service in services:
                service_id_list.append(service.service_id)
                # 批量操作
            code, msg = app_manage_service.batch_operations(self.tenant, self.user, action, service_id_list)
            if code != 200:
                result = general_message(code, "batch manage error", msg)
            else:
                result = general_message(200, "success", "操作成功")

        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
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
            result = general_message(400, "not service", "当前组内无应用，无法操作")
            return Response(result)
        service_id_list = [x.service_id for x in services]
        service_status_list = region_api.service_status(self.response_region, self.tenant_name,
                                                        {"service_ids": service_id_list,
                                                         "enterprise_id": self.user.enterprise_id})
        result = general_message(200, "success", "查询成功", list=service_status_list)
        return Response(result)


