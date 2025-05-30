# -*- coding: utf8 -*-
"""
  Created on 18/1/15.
"""
import json
import logging
from datetime import datetime

from django.views.decorators.cache import never_cache
from rest_framework.response import Response

from console.enum.component_enum import is_state, is_support, ComponentType
from console.exception.main import (AbortRequest, AccountOverdueException, CallRegionAPIException, RbdAppNotFound,
                                    ResourceNotEnoughException, ServiceHandleException)
from console.repositories.app import service_repo
from console.repositories.app_config import port_repo
from console.repositories.group import group_repo, GroupServiceRelationRepository
from console.services.app_actions import app_manage_service
from console.services.app_actions.app_deploy import AppDeployService
from console.services.app_actions.exception import ErrServiceSourceNotFound
from console.services.app_config.env_service import AppEnvVarService
from console.services.group_service import group_service
from console.services.market_app_service import market_app_service
from console.services.operation_log import operation_log_service, OperationType, InformationType, Operation
from console.services.region_services import region_services
from console.services.upgrade_services import upgrade_service
from console.views.app_config.base import (AppBaseCloudEnterpriseCenterView, AppBaseView)
from console.views.base import (CloudEnterpriseCenterView, JWTAuthApiView, RegionTenantHeaderCloudEnterpriseCenterView,
                                RegionTenantHeaderView)
from console.utils.reqparse import parse_item
from www.apiclient.regionapi import RegionInvokeApi
from www.utils.return_message import general_message

logger = logging.getLogger("default")

env_var_service = AppEnvVarService()
app_deploy_service = AppDeployService()
region_api = RegionInvokeApi()
group_service_relation_repo = GroupServiceRelationRepository()


class AppsPorConsoletView(RegionTenantHeaderView):
    def get(self, req, *args, **kwargs):
        app_id = req.GET.get('appID')
        ports = port_repo.get_tenant_services(self.team.tenant_id)
        component_list = service_repo.get_service_by_tenant(self.team.tenant_id)
        component_dict = {component.service_id: component.service_cname for component in component_list}
        port_list = list()
        tcp_domain = region_services.get_region_tcpdomain(region_name=self.region_name)
        if ports:
            tenant_groups = group_service_relation_repo.get_relation_by_tenant_id(self.team.tenant_id)
            component_groups_dict = {tg.service_id: tg.group_id for tg in tenant_groups}
            for port in ports:
                port_dict = dict()
                if not port.is_inner_service:
                    continue
                port_dict["port"] = port.container_port
                port_dict["service_name"] = port.k8s_service_name
                port_dict["namespace"] = self.team.namespace
                for component in component_list:
                    if port.service_id == component.service_id:
                        port_dict["service_id"] = component.service_id
                        port_dict["service_type"] = component.namespace
                        port_dict["service_alias"] = component.service_alias
                        port_dict["app_id"] = component_groups_dict.get(component.service_id)
                port_dict["component_name"] = component_dict.get(port.service_id)
                if app_id is None or app_id == "":
                    port_list.append(port_dict)
                    continue
                group_port = group_service_relation_repo.get_group_by_service_id(port.service_id)
                if group_port and group_port.group_id == int(app_id):
                    port_list.append(port_dict)
        ret_data = {"outer_url": tcp_domain, "namespace": self.team.namespace, "ports": port_list}
        result = general_message(200, "success", "查询成功", bean=ret_data)
        return Response(result, status=result["code"])


class StartAppView(AppBaseCloudEnterpriseCenterView):
    @never_cache
    def post(self, request, *args, **kwargs):
        """
        启动组件
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 组件别名
              required: true
              type: string
              paramType: path

        """
        try:
            code, msg = app_manage_service.start(self.tenant, self.service, self.user, oauth_instance=self.oauth_instance)
            bean = {}
            if code != 200:
                return Response(general_message(code, "start app error", msg, bean=bean), status=code)
            result = general_message(code, "success", "操作成功", bean=bean)
            comment = operation_log_service.generate_component_comment(
                operation=Operation.START,
                module_name=self.service.service_cname,
                region=self.service.service_region,
                team_name=self.tenant.tenant_name,
                service_alias=self.service.service_alias)
            operation_log_service.create_component_log(
                user=self.user,
                comment=comment,
                enterprise_id=self.user.enterprise_id,
                team_name=self.tenant.tenant_name,
                app_id=self.app.ID,
                service_alias=self.service.service_alias)
            self.service.update_time = datetime.now()
            self.service.save()
        except ResourceNotEnoughException as re:
            raise re
        except AccountOverdueException as re:
            logger.exception(re)
            return Response(general_message(10410, "resource is not enough", re.message), status=412)
        return Response(result, status=result["code"])


class StopAppView(AppBaseView):
    @never_cache
    def post(self, request, *args, **kwargs):
        """
        停止组件
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 组件别名
              required: true
              type: string
              paramType: path

        """
        app_manage_service.stop(self.tenant, self.service, self.user)
        result = general_message(200, "success", "操作成功", bean={})
        comment = operation_log_service.generate_component_comment(
            operation=Operation.STOP,
            module_name=self.service.service_cname,
            region=self.service.service_region,
            team_name=self.tenant.tenant_name,
            service_alias=self.service.service_alias)
        operation_log_service.create_component_log(
            user=self.user,
            comment=comment,
            enterprise_id=self.user.enterprise_id,
            team_name=self.tenant.tenant_name,
            app_id=self.app.ID,
            service_alias=self.service.service_alias,
        )
        self.service.update_time = datetime.now()
        self.service.save()
        return Response(result, status=result["code"])


class PauseAppView(AppBaseView):
    @never_cache
    def post(self, request, *args, **kwargs):
        """
        挂起组件
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 组件别名
              required: true
              type: string
              paramType: path

        """
        app_manage_service.pause(self.tenant, self.service, self.user)
        result = general_message(200, "success", "操作成功", bean={})
        self.service.update_time = datetime.now()
        self.service.save()
        return Response(result, status=result["code"])


class UNPauseAppView(AppBaseView):
    @never_cache
    def post(self, request, *args, **kwargs):
        """
        恢复组件
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 组件别名
              required: true
              type: string
              paramType: path

        """
        app_manage_service.un_pause(self.tenant, self.service, self.user)
        result = general_message(200, "success", "操作成功", bean={})
        self.service.update_time = datetime.now()
        self.service.save()
        return Response(result, status=result["code"])


class ReStartAppView(AppBaseCloudEnterpriseCenterView):
    @never_cache
    def post(self, request, *args, **kwargs):
        """
        重启组件
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 组件别名
              required: true
              type: string
              paramType: path

        """
        code, msg = app_manage_service.restart(self.tenant, self.service, self.user, oauth_instance=self.oauth_instance)
        bean = {}
        if code != 200:
            return Response(general_message(code, "restart app error", msg, bean=bean), status=code)
        result = general_message(code, "success", "操作成功", bean=bean)
        comment = operation_log_service.generate_component_comment(
            operation=Operation.RESTART,
            module_name=self.service.service_cname,
            region=self.service.service_region,
            team_name=self.tenant.tenant_name,
            service_alias=self.service.service_alias)
        operation_log_service.create_component_log(
            user=self.user,
            comment=comment,
            enterprise_id=self.user.enterprise_id,
            team_name=self.tenant.tenant_name,
            app_id=self.app.ID,
            service_alias=self.service.service_alias)
        self.service.update_time = datetime.now()
        self.service.save()
        return Response(result, status=result["code"])


class DeployAppView(AppBaseCloudEnterpriseCenterView):
    @never_cache
    def post(self, request, *args, **kwargs):
        """
        部署组件
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 组件别名
              required: true
              type: string
              paramType: path

        """
        try:
            group_version = request.data.get("group_version", None)
            code, msg, _ = app_deploy_service.deploy(
                self.tenant, self.service, self.user, version=group_version, oauth_instance=self.oauth_instance)
            bean = {}
            if code != 200:
                return Response(general_message(code, "deploy app error", msg, bean=bean), status=code)
            result = general_message(code, "success", "操作成功", bean=bean)
            comment = operation_log_service.generate_component_comment(
                operation=Operation.DEPLOY,
                module_name=self.service.service_cname,
                region=self.service.service_region,
                team_name=self.tenant.tenant_name,
                service_alias=self.service.service_alias)
            operation_log_service.create_component_log(
                user=self.user,
                comment=comment,
                enterprise_id=self.user.enterprise_id,
                team_name=self.tenant.tenant_name,
                app_id=self.app.ID,
                service_alias=self.service.service_alias)
            self.service.update_time = datetime.now()
            self.service.save()
        except ErrServiceSourceNotFound as e:
            logger.exception(e)
            return Response(general_message(412, e.message, "无法找到云市应用的构建源"), status=412)
        except ResourceNotEnoughException as re:
            raise re
        except AccountOverdueException as re:
            logger.exception(re)
            return Response(general_message(10410, "resource is not enough", re.message), status=412)
        return Response(result, status=result["code"])


class RollBackAppView(AppBaseView):
    @never_cache
    def post(self, request, *args, **kwargs):
        """
        回滚组件
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 组件别名
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
            upgrade_or_rollback = request.data.get("upgrade_or_rollback", None)
            if not deploy_version or not upgrade_or_rollback:
                return Response(general_message(400, "deploy version is not found", "请指明版本及操作类型"), status=400)

            code, msg = app_manage_service.roll_back(self.tenant, self.service, self.user, deploy_version, upgrade_or_rollback)
            bean = {}
            if code != 200:
                return Response(general_message(code, "roll back app error", msg, bean=bean), status=code)
            result = general_message(code, "success", "操作成功", bean=bean)
            comment = operation_log_service.generate_component_comment(
                operation=Operation.ROLL_BACK,
                module_name=self.service.service_cname,
                region=self.service.service_region,
                team_name=self.tenant.tenant_name,
                service_alias=self.service.service_alias)
            operation_log_service.create_component_log(
                user=self.user,
                comment=comment,
                enterprise_id=self.user.enterprise_id,
                team_name=self.tenant.tenant_name,
                app_id=self.app.ID,
                service_alias=self.service.service_alias)
            self.service.update_time = datetime.now()
            self.service.save()
        except ResourceNotEnoughException as re:
            raise re
        except AccountOverdueException as re:
            logger.exception(re)
            return Response(general_message(10410, "resource is not enough", re.message), status=412)
        return Response(result, status=result["code"])


class VerticalExtendAppView(AppBaseCloudEnterpriseCenterView):
    @never_cache
    def post(self, request, *args, **kwargs):
        """
        垂直升级组件
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 组件别名
              required: true
              type: string
              paramType: path
            - name: new_memory
              description: 内存大小(单位：M)
              required: true
              type: int
              paramType: form
            - name: new_gpu
              description: gpu显存数量(单位：MiB)
              required: false
              type: int
              paramType: form
            - name: new_cpu
              description: cpu分配额(单位：1000=1Core)
              required: false
              type: int
              paramType: form

        """
        try:
            new_memory = request.data.get("new_memory", 0)
            new_gpu = request.data.get("new_gpu", None)
            new_cpu = request.data.get("new_cpu", None)
            old_information = json.dumps({
                "内存": "{}M".format(self.service.min_memory),
                "GPU显存": self.service.container_gpu,
                "CPU": self.service.min_cpu
            },
                ensure_ascii=False)
            new_information = json.dumps({"内存": "{}M".format(new_memory), "GPU显存": new_gpu, "CPU": new_cpu},
                                         ensure_ascii=False)
            code, msg = app_manage_service.vertical_upgrade(
                self.tenant,
                self.service,
                self.user,
                int(new_memory),
                oauth_instance=self.oauth_instance,
                new_gpu=new_gpu,
                new_cpu=new_cpu)
            bean = {}
            if code != 200:
                return Response(general_message(code, "vertical upgrade error", msg, bean=bean), status=code)
            result = general_message(code, "success", "操作成功", bean=bean)
            comment = operation_log_service.generate_component_comment(
                operation=Operation.VERTICAL_SCALE,
                module_name=self.service.service_cname,
                region=self.service.service_region,
                team_name=self.tenant.tenant_name,
                service_alias=self.service.service_alias)
            operation_log_service.create_component_log(
                user=self.user,
                comment=comment,
                enterprise_id=self.user.enterprise_id,
                team_name=self.tenant.tenant_name,
                app_id=self.app.ID,
                service_alias=self.service.service_alias,
                old_information=old_information,
                new_information=new_information)
            self.service.update_time = datetime.now()
            self.service.save()
        except ResourceNotEnoughException as re:
            raise re
        except AccountOverdueException as re:
            logger.exception(re)
            return Response(general_message(10410, "resource is not enough", re.message), status=412)
        return Response(result, status=result["code"])


class HorizontalExtendAppView(AppBaseView, CloudEnterpriseCenterView):
    @never_cache
    def post(self, request, *args, **kwargs):
        """
        水平升级组件
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 组件别名
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
            old_information = json.dumps({"实例数量": self.service.min_node}, ensure_ascii=False)
            new_information = json.dumps({"实例数量": new_node}, ensure_ascii=False)
            app_manage_service.horizontal_upgrade(
                self.tenant, self.service, self.user, int(new_node), oauth_instance=self.oauth_instance)
            result = general_message(200, "success", "操作成功", bean={})
            comment = operation_log_service.generate_component_comment(
                operation=Operation.HORIZONTAL_SCALE,
                module_name=self.service.service_cname,
                region=self.service.service_region,
                team_name=self.tenant.tenant_name,
                service_alias=self.service.service_alias)
            operation_log_service.create_component_log(
                user=self.user,
                comment=comment,
                enterprise_id=self.user.enterprise_id,
                team_name=self.tenant.tenant_name,
                app_id=self.app.ID,
                service_alias=self.service.service_alias,
                old_information=old_information,
                new_information=new_information)
            self.service.update_time = datetime.now()
            self.service.save()
        except ResourceNotEnoughException as re:
            raise re
        except AccountOverdueException as re:
            logger.exception(re)
            return Response(general_message(10410, "resource is not enough", re.message), status=412)
        return Response(result, status=result["code"])


class ScalingAppView(AppBaseCloudEnterpriseCenterView):
    @never_cache
    def post(self, request, *args, **kwargs):
        """
        组件伸缩（支持水平和垂直伸缩）
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 组件别名
              required: true
              type: string
              paramType: path
            - name: new_memory
              description: 内存大小(单位：M)，用于垂直伸缩
              required: false
              type: int
              paramType: form
            - name: new_gpu
              description: gpu显存数量(单位：MiB)，用于垂直伸缩
              required: false
              type: int
              paramType: form
            - name: new_cpu
              description: cpu分配额(单位：1000=1Core)，用于垂直伸缩
              required: false
              type: int
              paramType: form
            - name: new_node
              description: 节点个数，用于水平伸缩
              required: false
              type: int
              paramType: form
        """
        try:
            # 获取垂直伸缩参数
            new_memory = request.data.get("new_memory", None)
            new_gpu = request.data.get("new_gpu", None)
            new_cpu = request.data.get("new_cpu", None)
            # 获取水平伸缩参数
            new_node = request.data.get("new_node", None)

            # 检查是否有伸缩参数
            has_vertical_params = any(param is not None for param in [new_memory, new_gpu, new_cpu])
            has_horizontal_params = new_node is not None

            if not has_vertical_params and not has_horizontal_params:
                return Response(general_message(400, "parameters error", "请提供伸缩参数"), status=400)

            # 执行垂直伸缩
            if has_vertical_params:
                code, msg = app_manage_service.vertical_upgrade(
                    self.tenant,
                    self.service,
                    self.user,
                    int(new_memory) if new_memory else 0,
                    oauth_instance=self.oauth_instance,
                    new_gpu=new_gpu,
                    new_cpu=new_cpu)
                if code != 200:
                    return Response(general_message(code, "vertical upgrade error", msg, bean={}), status=code)

            # 执行水平伸缩
            if has_horizontal_params and new_node != self.service.min_node:
                app_manage_service.horizontal_upgrade(
                    self.tenant, self.service, self.user, int(new_node), oauth_instance=self.oauth_instance)
            self.service.update_time = datetime.now()
            self.service.save()
        except ResourceNotEnoughException as re:
            raise re
        except AccountOverdueException as re:
            logger.exception(re)
            return Response(general_message(10410, "resource is not enough", re.message), status=412)
        except ServiceHandleException as e:
            # 节点没有变化的错误码为 10104，不需要抛出异常
            if e.error_code != 10104:
                raise e
        result = general_message(200, "success", "操作成功", bean={})
        return Response(result, status=result["code"])


class BatchActionView(RegionTenantHeaderCloudEnterpriseCenterView):
    @never_cache
    # TODO 修改权限验证
    def post(self, request, *args, **kwargs):
        """
        批量操作组件
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: action
              description: 操作名称 stop| start|restart|delete|move|upgrade|deploy
              required: true
              type: string
              paramType: form
            - name: service_ids
              description: 批量操作的组件ID 多个以英文逗号分隔
              required: true
              type: string
              paramType: form

        """
        action = request.data.get("action", None)
        service_ids = request.data.get("service_ids", None)
        move_group_id = request.data.get("move_group_id", None)
        if action not in ("stop", "start", "restart", "move", "upgrade", "deploy"):
            return Response(general_message(400, "param error", "操作类型错误"), status=400)

        action_zh = ""
        if action == "stop":
            action_zh = "关闭"
        if action == "start":
            action_zh = "启动"
        if action == "restart":
            action_zh = "重启"
        if action == "move":
            action_zh = "移动"
        if action == "upgrade":
            action_zh = "更新"
        if action == "deploy":
            action_zh = "构建"
        comment = "批量" + action_zh + "了应用{app}下的组件"
        service_id_list = service_ids.split(",")
        app = group_service.get_service_group_info(service_id_list[0])
        code, msg, services = app_manage_service.batch_action(self.region_name, self.tenant, self.user, action, service_id_list,
                                                    move_group_id, self.oauth_instance)

        app_name = operation_log_service.process_app_name(app.app_name, self.region_name, self.team_name, app.app_id)
        comment = comment.format(app=app_name)
        component_names = []
        idx = 0
        new_json_service_list = []
        for svc in services:
            if idx <= 2:
                component_names.append(
                    operation_log_service.process_component_name(svc.service_cname, self.region_name, self.team_name,
                                                                 svc.service_alias))
            new_json_services_dict = dict()
            new_json_services_dict["组件名"] = svc.service_cname
            new_json_services_dict["操作"] = action_zh
            new_json_service_list.append(new_json_services_dict)
            idx += 1
        new_information = json.dumps(new_json_service_list, ensure_ascii=False)
        component_names = ",".join(component_names)
        if idx >= 2:
            component_names += "等"
        comment += component_names

        if code != 200:
            result = general_message(code, "batch manage error", msg)
        else:
            result = general_message(200, "success", "操作成功")

        operation_log_service.create_log(
            self.user,
            operation_type=OperationType.APPLICATION_MANAGE,
            comment=comment,
            enterprise_id=self.user.enterprise_id,
            team_name=self.team_name,
            app_id=app.app_id,
            new_information=new_information,
            information_type=InformationType.INFORMATION_ADDS.value)

        return Response(result, status=result["code"])


class DeleteAppView(AppBaseView):
    @never_cache
    def delete(self, request, *args, **kwargs):
        """
        删除组件
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 组件别名
              required: true
              type: string
              paramType: path
            - name: is_force
              description: true直接删除，false进入回收站
              required: true
              type: boolean
              paramType: form

        """
        is_force = request.data.get("is_force", False)

        code, msg = app_manage_service.delete(self.user, self.tenant, self.service, is_force)
        bean = {}
        if code != 200:
            return Response(general_message(code, "delete service error", msg, bean=bean), status=code)
        result = general_message(code, "success", "操作成功", bean=bean)
        comment = operation_log_service.generate_component_comment(
            operation=Operation.DELETE, module_name=self.service.service_cname)
        operation_log_service.create_component_log(
            user=self.user,
            comment=comment,
            enterprise_id=self.user.enterprise_id,
            team_name=self.tenant.tenant_name,
            app_id=self.app.ID,
            service_alias=self.service.service_alias,
            service_cname=self.service.service_cname)
        return Response(result, status=result["code"])


class BatchDelete(RegionTenantHeaderView):
    @never_cache
    def delete(self, request, *args, **kwargs):
        """
        批量删除组件
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: service_ids
              description: 批量操作的组件ID 多个以英文逗号分隔
              required: true
              type: string
              paramType: form
        """
        service_ids = request.data.get("service_ids", None)
        service_id_list = service_ids.split(",")
        services = service_repo.get_services_by_service_ids(service_id_list)

        if not services:
            result = general_message(200, "success", "未指定需要删除的组件", list=[])
            return Response(result, status=result['code'])
        component_names = []
        comment = ""
        app = None
        old_information = list()
        if services:
            app = group_service.get_service_group_info(service_id_list[0])
            if app:
                app_name = operation_log_service.process_app_name(app.app_name, self.region_name, self.team_name, app.app_id)
                for svc in services:
                    component_names.append(svc.service_cname)
                    old_information.append({"组件名": svc.service_cname, "操作": "删除"})
                if len(component_names) > 2:
                    component_names = ",".join(component_names[0:2]) + "等"
                else:
                    component_names = ",".join(component_names)
                comment = "批量删除应用 {app} 中的组件 {component_names}".format(app=app_name, component_names=component_names)
        msg_list = []
        for service in services:
            code, msg = app_manage_service.batch_delete(self.user, self.tenant, service, is_force=True)
            msg_dict = dict()
            msg_dict['status'] = code
            msg_dict['msg'] = msg
            msg_dict['service_id'] = service.service_id
            msg_dict['service_cname'] = service.service_cname
            msg_list.append(msg_dict)
        if app:
            self.app = app
            old_information = json.dumps(old_information, ensure_ascii=False)
            operation_log_service.create_app_log(ctx=self, comment=comment, format_app=False, old_information=old_information)
        code = 200
        result = general_message(code, "success", "操作成功", list=msg_list)
        return Response(result, status=result['code'])


class AgainDelete(RegionTenantHeaderView):
    @never_cache
    def delete(self, request, *args, **kwargs):
        """
        二次确认删除组件
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: service_id
              description: 组件id
              required: true
              type: string
              paramType: form
        """
        service_id = request.data.get("service_id", None)
        service = service_repo.get_service_by_service_id(service_id)
        app = group_service.get_service_group_info(service_id)
        app_manage_service.delete_again(self.user, self.tenant, service, is_force=True)
        result = general_message(200, "success", "操作成功", bean={})
        comment = operation_log_service.generate_component_comment(
            operation=Operation.DELETE, module_name=service.service_cname)
        operation_log_service.create_component_log(
            user=self.user,
            comment=comment,
            enterprise_id=self.user.enterprise_id,
            team_name=self.tenant.tenant_name,
            app_id=app.ID if app else 0,
            service_alias=service.service_alias,
            service_cname=service.service_cname)
        return Response(result, status=result["code"])


class ChangeServiceTypeView(AppBaseView):
    @never_cache
    def put(self, request, *args, **kwargs):
        """
        修改组件的组件类型标签
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        try:
            extend_method = request.data.get("extend_method", None)
            if not extend_method:
                raise AbortRequest(msg="select the application type", msg_show="请选择组件类型")

            if not is_support(extend_method):
                raise AbortRequest(msg="do not support service type", msg_show="组件类型非法")
            new_information = json.dumps({
                "组件": self.service.service_cname,
                "组件部署类型": app_manage_service.get_extend_method_name(self.service.extend_method)
            },
                                         ensure_ascii=False)
            app_manage_service.change_service_type(self.tenant, self.service, extend_method, self.user.nick_name)
            old_information = json.dumps({
                "组件": self.service.service_cname,
                "组件部署类型": app_manage_service.get_extend_method_name(self.service.extend_method)
            },
                                         ensure_ascii=False)
            logger.debug("tenant: {0}, service:{1}, extend_method:{2}".format(self.tenant, self.service, extend_method))
            app_manage_service.change_service_type(self.tenant, self.service, extend_method, self.user.nick_name)
            result = general_message(200, "success", "操作成功")
            comment = operation_log_service.generate_component_comment(
                operation=Operation.CHANGE,
                module_name=self.service.service_cname,
                region=self.service.service_region,
                team_name=self.tenant.tenant_name,
                service_alias=self.service.service_alias,
                suffix=" 的类型为'{}'".format(ComponentType.to_zh(extend_method)))
            operation_log_service.create_component_log(
                user=self.user,
                comment=comment,
                enterprise_id=self.user.enterprise_id,
                team_name=self.tenant.tenant_name,
                app_id=self.app.ID,
                service_alias=self.service.service_alias,
                old_information=old_information,
                new_information=new_information)
        except CallRegionAPIException as e:
            result = general_message(e.code, "failure", e.message)
        return Response(result, status=result["code"])


# 更新组件组件
class UpgradeAppView(AppBaseView, CloudEnterpriseCenterView):
    @never_cache
    def post(self, request, *args, **kwargs):
        """
        更新
        """
        try:
            code, msg, _ = app_manage_service.upgrade(self.tenant, self.service, self.user, oauth_instance=self.oauth_instance)
            bean = {}
            if code != 200:
                return Response(general_message(code, "upgrade app error", msg, bean=bean), status=code)
            result = general_message(code, "success", "操作成功", bean=bean)
            comment = operation_log_service.generate_component_comment(
                operation=Operation.UPGRADE,
                module_name=self.service.service_cname,
                region=self.service.service_region,
                team_name=self.tenant.tenant_name,
                service_alias=self.service.service_alias)
            operation_log_service.create_component_log(
                user=self.user,
                comment=comment,
                enterprise_id=self.user.enterprise_id,
                team_name=self.tenant.tenant_name,
                app_id=self.app.ID,
                service_alias=self.service.service_alias)
            self.service.update_time = datetime.now()
            self.service.save()
        except ResourceNotEnoughException as re:
            raise re
        except AccountOverdueException as re:
            logger.exception(re)
            return Response(general_message(10410, "resource is not enough", re.message), status=412)
        return Response(result, status=result["code"])


# 修改组件名称
class ChangeServiceNameView(AppBaseView):
    @never_cache
    def put(self, request, *args, **kwargs):
        """
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        service_name = request.data.get("service_name", None)
        if not service_name:
            return Response(general_message(400, "select the application type", "请输入修改后的名称"), status=400)
        extend_method = self.service.extend_method
        if not is_state(extend_method):
            return Response(general_message(400, "stateless applications cannot be modified", "无状态组件不可修改"), status=400)
        self.service.service_name = service_name
        self.service.save()
        result = general_message(200, "success", "操作成功")
        return Response(result, status=result["code"])


# 修改组件名称
class ChangeServiceUpgradeView(AppBaseView):
    @never_cache
    def put(self, request, *args, **kwargs):
        """
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        build_upgrade = request.data.get("build_upgrade", True)
        op = Operation.OPEN if build_upgrade else Operation.CLOSE
        comment = operation_log_service.generate_component_comment(
            operation=op,
            module_name=self.service.service_cname,
            region=self.service.service_region,
            team_name=self.tenant.tenant_name,
            service_alias=self.service.service_alias,
            suffix=" 设置'构建后自动升级'")
        operation_log_service.create_component_log(
            user=self.user,
            comment=comment,
            enterprise_id=self.user.enterprise_id,
            team_name=self.tenant.tenant_name,
            app_id=self.app.ID,
            service_alias=self.service.service_alias)
        self.service.build_upgrade = build_upgrade
        self.service.save()
        result = general_message(200, "success", "操作成功", bean={"build_upgrade": self.service.build_upgrade})
        return Response(result, status=result["code"])


# 判断云市安装的组件是否有（小版本，大版本）更新
class MarketServiceUpgradeView(AppBaseView):
    @never_cache
    def get(self, request, *args, **kwargs):
        versions = []
        try:
            versions = market_app_service.list_upgradeable_versions(self.tenant, self.service)
        except RbdAppNotFound:
            return Response(status=404, data=general_message(404, "service lost", "未找到该组件"))
        except Exception as e:
            logger.debug(e)
            return Response(status=200, data=general_message(200, "success", "查询成功", list=versions))
        return Response(status=200, data=general_message(200, "success", "查询成功", list=versions))

    def post(self, request, *args, **kwargs):
        version = parse_item(request, "group_version", required=True)

        # get app
        app = group_repo.get_by_service_id(self.tenant.tenant_id, self.service.service_id)

        upgrade_service.upgrade_component(self.tenant, self.region, self.user, app, self.service, version)
        return Response(status=200, data=general_message(200, "success", "升级成功"))


class TeamAppsCloseView(JWTAuthApiView):
    def post(self, request, *args, **kwargs):
        region_name = request.data.get("region_name")
        if region_name:
            app_manage_service.close_all_component_in_tenant(self.team, region_name, self.user)
        else:
            app_manage_service.close_all_component_in_team(self.team, self.user)
        comment = operation_log_service.generate_team_comment(
            operation=Operation.CLOSE, module_name=self.team.tenant_alias, team_name=self.team.tenant_name,
            suffix=" 下所有组件")
        operation_log_service.create_enterprise_log(user=self.user, comment=comment,
                                                    enterprise_id=self.user.enterprise_id)
        return Response(status=200, data=general_message(200, "success", "操作成功"))


class PackageToolView(AppBaseCloudEnterpriseCenterView):
    @never_cache
    def post(self, request, *args, **kwargs):
        """
        设置语言和依赖包
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 组件别名
              required: true
              type: string
              paramType: path

        """
        lang = request.data.get("lang", "")
        package_tool = request.data.get("package_tool", "")
        dist = request.data.get("dist", "")
        # 修改语言和包依赖
        if lang:
            code, msg = app_manage_service.change_lang_and_package_tool(self.tenant, self.service, lang, package_tool, dist)
            if code != 200:
                return Response(status=code, data=general_message(code, "failed", "操作失败"))
        return Response(status=200, data=general_message(200, "succeed", "操作成功"))


class TarImageView(AppBaseCloudEnterpriseCenterView):
    @never_cache
    def post(self, request, *args, **kwargs):
        """
        设置语言和依赖包
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 组件别名
              required: true
              type: string
              paramType: path

        """
        image_name = request.data.get("image_name", "")
        # 修改语言和包依赖
        if image_name:
            code, msg = app_manage_service.change_image_tool(self.tenant, self.service, image_name)
            if code != 200:
                return Response(status=code, data=general_message(code, "failed", "操作失败"))
        return Response(status=200, data=general_message(200, "succeed", "操作成功"))
