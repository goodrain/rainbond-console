# -*- coding: utf8 -*-
"""
  Created on 18/1/15.
"""
import logging
import json
from django.views.decorators.cache import never_cache
from rest_framework.response import Response

from console.exception.main import ResourceNotEnoughException, AccountOverdueException
from console.services.app_actions import app_manage_service
from console.services.app_config.env_service import AppEnvVarService
from console.views.app_config.base import AppBaseView
from console.views.base import RegionTenantHeaderView
from www.decorator import perm_required
from www.utils.return_message import general_message, error_message
from console.services.app_actions import event_service
from console.services.app import app_service
from console.services.team_services import team_services
from console.repositories.app import service_repo, service_source_repo
from www.apiclient.regionapi import RegionInvokeApi
from console.services.app_config import volume_service
from console.repositories.group import tenant_service_group_repo
from console.repositories.market_app_repo import rainbond_app_repo


logger = logging.getLogger("default")

env_var_service = AppEnvVarService()
region_api = RegionInvokeApi()


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
                                                           "start_app")
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
        except AccountOverdueException as re:
            logger.exception(re)
            return Response(general_message(10410, "resource is not enough", re.message), status=412)
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
            group_version = request.data.get("group_version", None)
            is_upgrade = request.data.get("is_upgrade", True)
            allow_create, tips = app_service.verify_source(self.tenant, self.service.service_region, 0, "start_app")
            if not allow_create:
                return Response(general_message(412, "resource is not enough", "资源不足，无法部署"))
            code, msg, event = app_manage_service.deploy(self.tenant, self.service, self.user, is_upgrade, group_version)
            bean = {}
            if event:
                bean = event.to_dict()
                bean["type_cn"] = event_service.translate_event_type(event.type)
            if code != 200:
                return Response(general_message(code, "deploy app error", msg, bean=bean), status=code)
            result = general_message(code, "success", "操作成功", bean=bean)
        except ResourceNotEnoughException as re:
            logger.exception(re)
            return Response(general_message(10406, "resource is not enough", re.message), status=412)
        except AccountOverdueException as re:
            logger.exception(re)
            return Response(general_message(10410, "resource is not enough", re.message), status=412)
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
            upgrade_or_rollback = request.data.get("upgrade_or_rollback", None)
            if not deploy_version or not upgrade_or_rollback:
                return Response(general_message(400, "deploy version is not found", "请指明版本及操作类型"), status=400)

            allow_create, tips = app_service.verify_source(self.tenant, self.service.service_region, 0, "start_app")
            if not allow_create:
                return Response(general_message(412, "resource is not enough", "资源不足，无法操作"))
            code, msg, event = app_manage_service.roll_back(self.tenant, self.service, self.user, deploy_version, upgrade_or_rollback)
            bean = {}
            if event:
                bean = event.to_dict()
                bean["type_cn"] = event_service.translate_event_type(event.type)
            if code != 200:
                return Response(general_message(code, "roll back app error", msg, bean=bean), status=code)
            result = general_message(code, "success", "操作成功", bean=bean)
        except ResourceNotEnoughException as re:
            logger.exception(re)
            return Response(general_message(10406, "resource is not enough", re.message), status=412)
        except AccountOverdueException as re:
            logger.exception(re)
            return Response(general_message(10410, "resource is not enough", re.message), status=412)
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
            new_add_memory = (int(new_memory) * self.service.min_node) - self.service.min_node * self.service.min_memory
            if new_add_memory < 0:
                new_add_memory = 0
            allow_create, tips = app_service.verify_source(self.tenant, self.service.service_region, new_add_memory,
                                                           "start_app")
            if not allow_create:
                return Response(general_message(412, "resource is not enough", "资源不足，无法升级"))
            code, msg, event = app_manage_service.vertical_upgrade(self.tenant, self.service, self.user,
                                                                   int(new_memory))
            bean = {}
            if event:
                bean = event.to_dict()
                bean["type_cn"] = event_service.translate_event_type(event.type)
            if code != 200:
                return Response(general_message(code, "vertical upgrade error", msg, bean=bean), status=code)
            result = general_message(code, "success", "操作成功", bean=bean)
        except ResourceNotEnoughException as re:
            logger.exception(re)
            return Response(general_message(10406, "resource is not enough", re.message), status=412)
        except AccountOverdueException as re:
            logger.exception(re)
            return Response(general_message(10410, "resource is not enough", re.message), status=412)
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
            new_add_memory = (int(new_node) - self.service.min_node) * self.service.min_memory
            if new_add_memory < 0:
                new_add_memory = 0
            allow_create, tips = app_service.verify_source(self.tenant, self.service.service_region, new_add_memory,
                                                           "start_app")
            if not allow_create:
                return Response(general_message(412, "resource is not enough", "资源不足，无法升级"))

            code, msg, event = app_manage_service.horizontal_upgrade(self.tenant, self.service, self.user,
                                                                     int(new_node))
            bean = {}
            if event:
                bean = event.to_dict()
                bean["type_cn"] = event_service.translate_event_type(event.type)
            if code != 200:
                return Response(general_message(code, "horizontal upgrade error", msg, bean=bean), status=code)
            result = general_message(code, "success", "操作成功", bean=bean)
        except ResourceNotEnoughException as re:
            logger.exception(re)
            return Response(general_message(10406, "resource is not enough", re.message), status=412)
        except AccountOverdueException as re:
            logger.exception(re)
            return Response(general_message(10410, "resource is not enough", re.message), status=412)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class BatchActionView(RegionTenantHeaderView):
    @never_cache
    @perm_required('stop_service')
    @perm_required('start_service')
    @perm_required('restart_service')
    @perm_required('manage_group')
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
              description: 操作名称 stop| start|restart|delete|move
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
            move_group_id = request.data.get("move_group_id", None)
            if action not in ("stop", "start", "restart", "move"):
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
            if action == "move":
                if "manage_group" not in perm_tuple and "owner" not in identitys and "admin" not in identitys and "developer" not in identitys:
                    return Response(general_message(400, "Permission denied", "没有变更应用分组权限"), status=400)
            service_id_list = service_ids.split(",")
            code, msg = app_manage_service.batch_action(self.tenant, self.user, action, service_id_list, move_group_id)
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


class BatchDelete(RegionTenantHeaderView):
    @never_cache
    @perm_required('delete_service')
    def delete(self, request, *args, **kwargs):
        """
        批量删除应用
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: service_ids
              description: 批量操作的服务ID 多个以英文逗号分隔
              required: true
              type: string
              paramType: form
        """
        try:
            service_ids = request.data.get("service_ids", None)
            identitys = team_services.get_user_perm_identitys_in_permtenant(user_id=self.user.user_id,
                                                                            tenant_name=self.tenant_name)
            perm_tuple = team_services.get_user_perm_in_tenant(user_id=self.user.user_id, tenant_name=self.tenant_name)
            if "delete_service" not in perm_tuple and "owner" not in identitys and "admin" not in identitys and "developer" not in identitys:
                return Response(general_message(400, "Permission denied", "没有删除应用权限"), status=400)
            service_id_list = service_ids.split(",")
            services = service_repo.get_services_by_service_ids(*service_id_list)
            msg_list = []
            for service in services:
                code, msg, event = app_manage_service.batch_delete(self.user, self.tenant, service, is_force=True)
                msg_dict = dict()
                msg_dict['status'] = code
                msg_dict['msg'] = msg
                msg_dict['service_id'] = service.service_id
                msg_dict['service_cname'] = service.service_cname
                msg_list.append(msg_dict)
            code = 200
            result = general_message(code, "success", "操作成功", list=msg_list)
            return Response(result, status=result['code'])
        except Exception as e:
            logger.exception(e)


class AgainDelete(RegionTenantHeaderView):
    @never_cache
    @perm_required('delete_service')
    def delete(self, request, *args, **kwargs):
        """
        二次确认删除应用
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: service_id
              description: 应用id
              required: true
              type: string
              paramType: form
        """
        try:
            service_id = request.data.get("service_id", None)
            identitys = team_services.get_user_perm_identitys_in_permtenant(user_id=self.user.user_id,
                                                                            tenant_name=self.tenant_name)
            perm_tuple = team_services.get_user_perm_in_tenant(user_id=self.user.user_id, tenant_name=self.tenant_name)
            if "delete_service" not in perm_tuple and "owner" not in identitys and "admin" not in identitys and "developer" not in identitys:
                return Response(general_message(400, "Permission denied", "没有删除应用权限"), status=400)
            service = service_repo.get_service_by_service_id(service_id)
            code, msg, event = app_manage_service.delete_again(self.user, self.tenant, service, is_force=True)
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


class ChangeServiceTypeView(AppBaseView):
    @never_cache
    @perm_required('manage_service_extend')
    def put(self, request, *args, **kwargs):
        """
        修改服务的应用类型标签
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        try:
            extend_method = request.data.get("extend_method", None)
            if not extend_method:
                return Response(general_message(400, "select the application type", "请选择应用类型"), status=400)

            old_extend_method = self.service.extend_method
            # 状态从有到无，并且有本地存储的不可修改
            is_mnt_dir = 0
            tenant_service_volumes = volume_service.get_service_volumes(self.tenant, self.service)
            if tenant_service_volumes:
                for tenant_service_volume in tenant_service_volumes:
                    if tenant_service_volume.volume_type == "local":
                        is_mnt_dir = 1
            if old_extend_method != "stateless" and extend_method == "stateless" and is_mnt_dir:
                return Response(general_message(400, "local storage cannot be modified to be stateless", "本地存储不可修改为无状态"), status=400)
            label_dict = dict()
            body = dict()
            # made ...
            body["label_key"] = "service-type"
            body["label_value"] = "StatelessServiceType" if extend_method == "stateless" else "StatefulServiceType"
            label_list = list()
            label_list.append(body)
            label_dict["labels"] = label_list
            logger.debug('---------------label_dict------------->{0}'.format(label_dict))

            res, body = region_api.update_service_state_label(self.service.service_region, self.tenant.tenant_name, self.service.service_alias,
                                                              label_dict)

            if int(res.status) != 200:
                result = general_message(500, "region faild", "数据中心请求失败")
                return Response(result, status=500)
            self.service.extend_method = extend_method
            self.service.save()
            result = general_message(200, "success", "操作成功")
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


# 更新服务组件
class UpgradeAppView(AppBaseView):
    @never_cache
    @perm_required('deploy_service')
    def post(self, request, *args, **kwargs):
        """
        更新
        """
        try:
            allow_create, tips = app_service.verify_source(self.tenant, self.service.service_region, 0, "start_app")
            if not allow_create:
                return Response(general_message(412, "resource is not enough", "资源不足，无法更新"))
            code, msg, event = app_manage_service.upgrade(self.tenant, self.service, self.user)
            bean = {}
            if event:
                bean = event.to_dict()
                bean["type_cn"] = event_service.translate_event_type(event.type)
            if code != 200:
                return Response(general_message(code, "upgrade app error", msg, bean=bean), status=code)
            result = general_message(code, "success", "操作成功", bean=bean)
        except ResourceNotEnoughException as re:
            logger.exception(re)
            return Response(general_message(10406, "resource is not enough", re.message), status=412)
        except AccountOverdueException as re:
            logger.exception(re)
            return Response(general_message(10410, "resource is not enough", re.message), status=412)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


# 修改服务名称
class ChangeServiceNameView(AppBaseView):
    @never_cache
    @perm_required('manage_service_extend')
    def put(self, request, *args, **kwargs):
        """
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        try:
            service_name = request.data.get("service_name", None)
            if not service_name:
                return Response(general_message(400, "select the application type", "请输入修改后的名称"), status=400)
            extend_method = self.service.extend_method
            if extend_method == "stateless":
                return Response(
                    general_message(400, "stateless applications cannot be modified", "无状态应用不可修改"),
                    status=400)
            self.service.service_name = service_name
            self.service.save()
            result = general_message(200, "success", "操作成功")
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


# 修改服务名称
class ChangeServiceUpgradeView(AppBaseView):
    @never_cache
    @perm_required('manage_service_extend')
    def put(self, request, *args, **kwargs):
        """
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        try:
            build_upgrade = request.data.get("build_upgrade", True)

            self.service.build_upgrade = build_upgrade
            self.service.save()
            result = general_message(200, "success", "操作成功", bean={"build_upgrade": self.service.build_upgrade})
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


# 判断云市安装的应用是否有（小版本，大版本）更新
class MarketServiceUpgradeView(AppBaseView):
    @never_cache
    @perm_required('deploy_service')
    def get(self, request, *args, **kwargs):
        try:
            bean = dict()
            upgrate_version_list = []
            if self.service.service_source != "market":
                return Response(general_message(400, "non-cloud installed applications require no judgment", "非云市安装的应用无需判断"), status=400)
            # 获取组对象
            group_obj = tenant_service_group_repo.get_group_by_service_group_id(self.service.tenant_service_group_id)
            if group_obj:
                # 获取内部市场对象
                rain_app = rainbond_app_repo.get_rainbond_app_by_key_and_version(group_obj.group_key,
                                                                                 group_obj.group_version)
                if not rain_app:
                    result = general_message(200, "success", "当前云市应用已删除")
                    return Response(result, status=result["code"])
                else:
                    apps_template = json.loads(rain_app.app_template)
                    apps_list = apps_template.get("apps")
                    for app in apps_list:
                        if app["service_key"] == self.service.service_key:
                            if app["deploy_version"] > self.service.deploy_version:
                                self.service.is_upgrate = True
                                self.service.save()
                    try:
                        apps_template = json.loads(rain_app.app_template)
                        apps_list = apps_template.get("apps")
                        service_source = service_source_repo.get_service_source(self.service.tenant_id,
                                                                                self.service.service_id)
                        if service_source and service_source.extend_info:
                            extend_info = json.loads(service_source.extend_info)
                            if extend_info:
                                for app in apps_list:
                                    logger.debug('---------====app===============>{0}'.format(json.dumps(app)))
                                    logger.debug('---------=====extend_info==============>{0}'.format(json.dumps(extend_info)))
                                    if app.has_key("service_share_uuid"):
                                        if app["service_share_uuid"] == extend_info["source_service_share_uuid"]:
                                            new_version = int(app["deploy_version"])
                                            old_version = int(extend_info["source_deploy_version"])
                                            if new_version > old_version:
                                                self.service.is_upgrate = True
                                                self.service.save()
                                    elif not app.has_key("service_share_uuid") and app.has_key("service_key"):
                                        if app["service_key"] == extend_info["source_service_share_uuid"]:
                                            new_version = int(app["deploy_version"])
                                            old_version = int(extend_info["source_deploy_version"])
                                            if new_version > old_version:
                                                self.service.is_upgrate = True
                                                self.service.save()
                        bean["is_upgrate"] = self.service.is_upgrate
                    except Exception as e:
                        logger.exception(e)
                        result = error_message(e.message)
                        return Response(result, status=result["code"])

                # 通过group_key获取不同版本的应用市场对象
                rain_apps = rainbond_app_repo.get_rainbond_app_by_key(group_obj.group_key)
                if rain_apps:
                    for r_app in rain_apps:
                        if r_app.version > group_obj.group_version and r_app.version not in upgrate_version_list:
                            upgrate_version_list.append(r_app.version)
                        elif r_app.version == group_obj.group_version and self.service.is_upgrate:
                            upgrate_version_list.append(r_app.version)

            upgrate_version_list.sort()
            result = general_message(200, "success", "查询成功", bean=bean, list=upgrate_version_list)

        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])



