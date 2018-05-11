# -*- coding: utf8 -*-
"""
  Created on 18/1/15.
"""
import logging

from django.views.decorators.cache import never_cache
from rest_framework.response import Response

from console.exception.main import ResourceNotEnoughException
from console.services.app_actions import app_manage_service
from console.services.app_config.env_service import AppEnvVarService
from console.views.app_config.base import AppBaseView
from console.views.base import RegionTenantHeaderView
from www.decorator import perm_required
from www.utils.return_message import general_message, error_message
from console.services.app_actions import event_service
from console.services.app import app_service
from console.services.team_services import team_services

logger = logging.getLogger("default")

env_var_service = AppEnvVarService()


class StartAppView(AppBaseView):
    @never_cache
    @perm_required('start_service')
    def post(self, request, *args, **kwargs):
        """
        启动服务
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 服务别名
              required: true
              type: string
              paramType: path

        """
        try:
            new_add_memory = self.service.min_memory * self.service.min_node
            allow_create, tips = app_service.verify_source(self.tenant, self.service.service_region, new_add_memory,
                                                           "启动应用")
            if not allow_create:
                return Response(general_message(412, "resource is not enough", "资源不足，无法启动"))
            code, msg, event = app_manage_service.start(self.tenant, self.service, self.user)
            bean = {}
            if event:
                bean = event.to_dict()
                bean["type_cn"] = event_service.translate_event_type(event.type)
            if code != 200:
                return Response(general_message(code, "start app error", msg, bean=bean), status=code)
            result = general_message(code, "success", "操作成功", bean=bean)
        except ResourceNotEnoughException as re:
            logger.exception(re)
            return Response(general_message(10406, "resource is not enough", re.message), status=412)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class StopAppView(AppBaseView):
    @never_cache
    @perm_required('stop_service')
    def post(self, request, *args, **kwargs):
        """
        停止服务
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 服务别名
              required: true
              type: string
              paramType: path

        """
        try:
            code, msg, event = app_manage_service.stop(self.tenant, self.service, self.user)
            bean = {}
            if event:
                bean = event.to_dict()
                bean["type_cn"] = event_service.translate_event_type(event.type)
            if code != 200:
                return Response(general_message(code, "stop app error", msg, bean=bean), status=code)
            result = general_message(code, "success", "操作成功", bean=bean)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class ReStartAppView(AppBaseView):
    @never_cache
    @perm_required('restart_service')
    def post(self, request, *args, **kwargs):
        """
        重启服务
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 服务别名
              required: true
              type: string
              paramType: path

        """
        try:
            code, msg, event = app_manage_service.restart(self.tenant, self.service, self.user)
            bean = {}
            if event:
                bean = event.to_dict()
                bean["type_cn"] = event_service.translate_event_type(event.type)
            if code != 200:
                return Response(general_message(code, "restart app error", msg, bean=bean), status=code)
            result = general_message(code, "success", "操作成功", bean=bean)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class DeployAppView(AppBaseView):
    @never_cache
    @perm_required('deploy_service')
    def post(self, request, *args, **kwargs):
        """
        部署服务
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 服务别名
              required: true
              type: string
              paramType: path

        """
        try:
            code, msg, event = app_manage_service.deploy(self.tenant, self.service, self.user)
            bean = {}
            if event:
                bean = event.to_dict()
                bean["type_cn"] = event_service.translate_event_type(event.type)
            if code != 200:
                return Response(general_message(code, "deploy app error", msg, bean=bean), status=code)
            result = general_message(code, "success", "操作成功", bean=bean)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class RollBackAppView(AppBaseView):
    @never_cache
    @perm_required('rollback_service')
    def post(self, request, *args, **kwargs):
        """
        回滚服务
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 服务别名
              required: true
              type: string
              paramType: path
            - name: deploy_version
              description: 回滚的版本
              required: true
              type: string
              paramType: form

        """
        try:
            deploy_version = request.data.get("deploy_version", None)
            if not deploy_version:
                return Response(general_message(400, "deploy version is not found", "请指明回滚的版本"), status=400)
            code, msg, event = app_manage_service.roll_back(self.tenant, self.service, self.user, deploy_version)
            bean = {}
            if event:
                bean = event.to_dict()
                bean["type_cn"] = event_service.translate_event_type(event.type)
            if code != 200:
                return Response(general_message(code, "roll back app error", msg, bean=bean), status=code)
            result = general_message(code, "success", "操作成功", bean=bean)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class VerticalExtendAppView(AppBaseView):
    @never_cache
    @perm_required('manage_service_extend')
    def post(self, request, *args, **kwargs):
        """
        垂直升级服务
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 服务别名
              required: true
              type: string
              paramType: path
            - name: new_memory
              description: 内存大小(单位：M)
              required: true
              type: int
              paramType: form

        """
        try:
            new_memory = request.data.get("new_memory", None)
            if not new_memory:
                return Response(general_message(400, "memory is null", "请选择升级内存"), status=400)
            code, msg, event = app_manage_service.vertical_upgrade(self.tenant, self.service, self.user,
                                                                   int(new_memory))
            bean = {}
            if event:
                bean = event.to_dict()
                bean["type_cn"] = event_service.translate_event_type(event.type)
            if code != 200:
                return Response(general_message(code, "vertical upgrade error", msg, bean=bean), status=code)
            result = general_message(code, "success", "操作成功", bean=bean)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class HorizontalExtendAppView(AppBaseView):
    @never_cache
    @perm_required('manage_service_extend')
    def post(self, request, *args, **kwargs):
        """
        水平升级服务
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 服务别名
              required: true
              type: string
              paramType: path
            - name: new_node
              description: 节点个数
              required: true
              type: int
              paramType: form

        """
        try:
            new_node = request.data.get("new_node", None)
            if not new_node:
                return Response(general_message(400, "node is null", "请选择节点个数"), status=400)
            code, msg, event = app_manage_service.horizontal_upgrade(self.tenant, self.service, self.user,
                                                                     int(new_node))
            bean = {}
            if event:
                bean = event.to_dict()
                bean["type_cn"] = event_service.translate_event_type(event.type)
            if code != 200:
                return Response(general_message(code, "horizontal upgrade error", msg, bean=bean), status=code)
            result = general_message(code, "success", "操作成功", bean=bean)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class BatchActionView(RegionTenantHeaderView):
    @never_cache
    @perm_required('stop_service')
    @perm_required('start_service')
    @perm_required('restart_service')
    def post(self, request, *args, **kwargs):
        """
        批量操作服务
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: action
              description: 操作名称 stop| start|restart
              required: true
              type: string
              paramType: form
            - name: service_ids
              description: 批量操作的服务ID 多个以英文逗号分隔
              required: true
              type: string
              paramType: form

        """
        try:
            action = request.data.get("action", None)
            service_ids = request.data.get("service_ids", None)
            if action not in ("stop", "start", "restart"):
                return Response(general_message(400, "param error", "操作类型错误"), status=400)
            identitys = team_services.get_user_perm_identitys_in_permtenant(user_id=self.user.user_id,
                                                                            tenant_name=self.tenant_name)
            perm_tuple = team_services.get_user_perm_in_tenant(user_id=self.user.user_id, tenant_name=self.tenant_name)

            if action == "stop":
                if "stop_service" not in perm_tuple and "owner" not in identitys and "admin" not in identitys and "developer" not in identitys:
                    return Response(general_message(400, "Permission denied", "没有关闭应用权限"), status=400)
            if action == "start":
                if "start_service" not in perm_tuple and "owner" not in identitys and "admin" not in identitys and "developer" not in identitys:
                    return Response(general_message(400, "Permission denied", "没有启动应用权限"), status=400)
            if action == "restart":
                if "restart_service" not in perm_tuple and "owner" not in identitys and "admin" not in identitys and "developer" not in identitys:
                    return Response(general_message(400, "Permission denied", "没有重启应用权限"), status=400)

            service_id_list = service_ids.split(",")
            code, msg = app_manage_service.batch_action(self.tenant, self.user, action, service_id_list)
            if code != 200:
                result = general_message(code, "batch manage error", msg)
            else:
                result = general_message(200, "success", "操作成功")
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class DeleteAppView(AppBaseView):
    @never_cache
    @perm_required('delete_service')
    def delete(self, request, *args, **kwargs):
        """
        删除服务
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 服务别名
              required: true
              type: string
              paramType: path
            - name: is_force
              description: true直接删除，false进入回收站
              required: true
              type: boolean
              paramType: form

        """
        try:
            is_force = request.data.get("is_force", False)

            code, msg, event = app_manage_service.delete(self.user, self.tenant, self.service, is_force)
            bean = {}
            if event:
                bean = event.to_dict()
                bean["type_cn"] = event_service.translate_event_type(event.type)
            if code != 200:
                return Response(general_message(code, "delete service error", msg, bean=bean), status=code)
            result = general_message(code, "success", "操作成功", bean=bean)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])
