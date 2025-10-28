# -*- coding: utf8 -*-
"""
  Created by leon on 18/1/5.
"""
import json
import logging

from console.enum.app import GovernanceModeEnum
from console.exception.main import AbortRequest, ServiceHandleException
from console.exception.bcode import ErrQualifiedName
from console.repositories.app import service_repo
from console.repositories.group import group_service_relation_repo, group_repo
from console.repositories.region_app import region_app_repo
from console.services.app_config_group import app_config_group_service
from console.services.helm_app import helm_app_service
from console.services.app_actions import app_manage_service
from console.services.group_service import group_service
from console.services.application import application_service
from console.services.market_app_service import market_app_service
from console.services.k8s_resource import k8s_resource_service
from console.services.operation_log import operation_log_service, Operation
from console.utils.reqparse import parse_item
from console.utils.validation import is_qualified_name
from console.views.base import (ApplicationView, RegionTenantHeaderCloudEnterpriseCenterView, RegionTenantHeaderView,
                                ApplicationViewCloudEnterpriseCenterView)
from rest_framework.response import Response
from urllib3.exceptions import MaxRetryError
from www.apiclient.regionapi import RegionInvokeApi
from www.utils.return_message import general_message

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
        app_name = request.data.get("app_name", None)
        note = request.data.get("note", "")
        logo = request.data.get("logo", "")
        k8s_app = request.data.get("k8s_app", "")
        if len(note) > 2048:
            return Response(general_message(400, "node too long", "应用备注长度限制2048"), status=400)
        app_store_name = request.data.get("app_store_name", None)
        app_store_url = request.data.get("app_store_url", None)
        app_template_name = request.data.get("app_template_name", None)
        version = request.data.get("version", None)
        region_name = request.data.get("region_name", self.response_region)
        if app_template_name:
            k8s_app = app_template_name
        if not is_qualified_name(k8s_app):
            raise ErrQualifiedName(msg_show="应用英文名称只能由小写字母、数字或“-”组成，并且必须以字母开始、以数字或字母结尾")
        data = group_service.create_app(
            self.tenant,
            region_name,
            app_name,
            note,
            self.user.get_username(),
            app_store_name,
            app_store_url,
            app_template_name,
            version,
            self.user.enterprise_id,
            logo,
            k8s_app=k8s_app)
        new_information = group_service.json_app(app_name=app_name, k8s_app=k8s_app, logo=logo, note=note)
        result = general_message(200, "success", "创建成功", bean=data)
        app_name = operation_log_service.process_app_name(app_name, region_name, self.tenant.tenant_name, data["app_id"])
        comment = operation_log_service.generate_team_comment(
            operation=Operation.IN,
            module_name=self.tenant.tenant_alias,
            region=region_name,
            team_name=self.tenant.tenant_name,
            suffix=" 中创建了应用 {}".format(app_name))
        operation_log_service.create_team_log(
            user=self.user,
            comment=comment,
            enterprise_id=self.user.enterprise_id,
            team_name=self.tenant.tenant_name,
            new_information=new_information)
        return Response(result, status=result["code"])


class TenantGroupOperationView(ApplicationView):
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
        app_name = request.data.get("app_name", None)
        k8s_app = request.data.get("k8s_app", "")
        note = request.data.get("note", "")
        logo = request.data.get("logo", "")
        if k8s_app and not is_qualified_name(k8s_app):
            raise ErrQualifiedName(msg_show="集群内应用名称只能由小写字母、数字或“-”组成，并且必须以字母开始、以数字或字母结尾")
        if note and len(note) > 2048:
            return Response(general_message(400, "node too long", "应用备注长度限制2048"), status=400)
        username = request.data.get("username", None)
        overrides = request.data.get("overrides", [])
        version = request.data.get("version", "")
        revision = request.data.get("revision", 0)
        old_app = group_repo.get_tenant_group_on_region(app_id)
        old_information = group_service.json_app(
            app_name=self.app.app_name, k8s_app=k8s_app, logo=old_app.logo, note=old_app.note)
        new_information = group_service.json_app(app_name=app_name, k8s_app=k8s_app, logo=logo, note=note)
        group_service.update_group(
            self.tenant,
            self.response_region,
            app_id,
            app_name,
            note,
            username,
            overrides=overrides,
            version=version,
            revision=revision,
            logo=logo,
            k8s_app=k8s_app)
        result = general_message(200, "success", "修改成功")
        handle_app_name = operation_log_service.process_app_name(self.app.app_name, self.region_name, self.tenant_name,
                                                                 self.app.app_id)
        comment = "更新了应用{}的信息".format(handle_app_name)
        if self.app.group_name != app_name:
            app_name = operation_log_service.process_app_name(app_name, self.region_name, self.tenant_name,
                                                              self.app.app_id)
            comment = "修改了应用{}的名称为{app}".format(self.app.app_name, app=app_name)
        operation_log_service.create_app_log(
            self, comment, format_app=False, old_information=old_information, new_information=new_information)
        return Response(result, status=result["code"])

    def delete(self, request, app_id, *args, **kwargs):
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
        old_app = group_repo.get_tenant_group_on_region(app_id)
        old_information = group_service.json_app(
            app_name=self.app.app_name, k8s_app=old_app.k8s_app, logo=old_app.logo, note=old_app.note)
        group_service.delete_app(self.tenant, self.region_name, self.app)
        result = general_message(200, "success", "删除成功")
        operation_log_service.create_app_log(
            self, "删除了应用 {app}".format(app=self.app.group_name), format_app=False, old_information=old_information)
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
        app = group_service.get_app_detail(self.tenant, self.region, app_id)
        result = general_message(200, "success", "success", bean=app)
        return Response(result, status=result["code"])


class TenantGroupHandleView(ApplicationView):
    def get(self, request, app_id, *args, **kwargs):
        '''
        获取应用下资源信息
        '''
        res = group_service.get_app_resource(self.tenant.tenant_id, self.region_name, app_id)
        result = general_message(200, "success", "success", bean=res)
        return Response(result, status=result["code"])

    def delete(self, request, app_id, *args, **kwargs):
        """
        删除应用及所有资源
        """
        # delete services
        services = group_service.batch_delete_app_services(self.user, self.tenant.tenant_id, self.region_name, app_id)
        # delete k8s resource
        k8s_resources = k8s_resource_service.list_by_app_id(str(app_id))
        resource_ids = [k8s_resource.ID for k8s_resource in k8s_resources]
        k8s_resource_service.batch_delete_k8s_resource(self.user.enterprise_id, self.tenant.tenant_name, str(app_id),
                                                       self.region_name, resource_ids)
        # delete configs
        app_config_group_service.batch_delete_config_group(self.region_name, self.tenant.tenant_name, app_id)
        # delete records
        group_service.delete_app_share_records(self.tenant.tenant_name, app_id)
        # delete app
        group_service.delete_app(self.tenant, self.region_name, self.app)
        component_names = []
        comment = ""
        old_information = list()
        if services:
            app = self.app
            if app:
                app_name = operation_log_service.process_app_name(app.app_name, self.region_name, self.team_name,
                                                                  app.app_id)
                for svc in services:
                    component_names.append(svc.service_cname)
                    old_information.append({"组件名": svc.service_cname, "操作": "删除"})
                if len(component_names) > 2:
                    component_names = ",".join(component_names[0:2]) + "等"
                else:
                    component_names = ",".join(component_names)
                comment = "删除了应用 {app}, 以及应用下的组件 {component_names}".format(app=app_name, component_names=component_names)

        old_information = json.dumps(old_information, ensure_ascii=False)
        operation_log_service.create_app_log(ctx=self, comment=comment, format_app=False, old_information=old_information)

        result = general_message(200, "success", "删除成功")
        return Response(result, status=result["code"])


class TenantAppUpgradableNumView(ApplicationView):
    def get(self, request, app_id, *args, **kwargs):
        data = dict()
        data['upgradable_num'] = 0
        try:
            data['upgradable_num'] = market_app_service.count_upgradeable_market_apps(self.tenant, self.region_name, self.app)
        except MaxRetryError as e:
            logger.warning("get the number of upgradable app: {}".format(e))
        except ServiceHandleException as e:
            logger.warning("get the number of upgradable app: {}".format(e))
            if e.status_code != 404:
                raise e

        result = general_message(200, "success", "success", bean=data)
        return Response(result, status=result["code"])


# 应用（组）常见操作【停止，重启， 启动， 重新构建】
class TenantGroupCommonOperationView(ApplicationViewCloudEnterpriseCenterView):
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
        services = group_service_relation_repo.list_service_groups(group_id)
        if not services:
            result = general_message(400, "not service", "当前组内无组件，无法操作")
            return Response(result)
        service_ids = [service.service_id for service in services]
        if action not in ("stop", "start", "upgrade", "deploy"):
            return Response(general_message(400, "param error", "操作类型错误"), status=400)
        app_manage_service.batch_operations(self.tenant, self.region_name, self.user, action, service_ids, self.oauth_instance)
        action_zh = ""
        if action == "stop":
            self.has_perms([300006])
            action_zh = "停止"
        if action == "start":
            action_zh = "启动"
            self.has_perms([300005])
        if action == "upgrade":
            action_zh = "更新"
            self.has_perms([300007])
        if action == "deploy":
            action_zh = "构建"
            self.has_perms([300008])
            # 批量操作
        result = general_message(200, "success", "操作成功")
        comment = action_zh + "了应用{app}"
        operation_log_service.create_app_log(self, comment)
        return Response(result, status=result["code"])


# 应用（组）状态
class GroupStatusView(RegionTenantHeaderView):
    def get(self, request, *args, **kwargs):
        group_id = request.GET.get("group_id", None)
        region_name = request.GET.get("region_name", None)
        if not group_id or not region_name:
            result = general_message(400, "not group_id", "参数缺失")
            return Response(result)
        services = group_service_relation_repo.list_service_groups(group_id)
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


class AppGovernanceModeView(ApplicationView):
    def get(self, *args, **kwargs):
        data = region_api.list_governance_mode(self.response_region, self.tenant_name)
        result = general_message(200, "success", "获取成功", list=data)
        return Response(result, status=result["code"])

    def put(self, request, app_id, *args, **kwargs):
        governance_mode = parse_item(request, "governance_mode", required=True)
        action = parse_item(request, "action")
        bean = {"governance_mode": governance_mode}
        governance_cr = group_service.update_governance_mode(self.tenant, self.region_name, app_id, governance_mode, action)
        if governance_cr:
            bean["governance_cr"] = governance_cr
        result = general_message(200, "success", "更新成功", bean=bean)
        app_name = operation_log_service.process_app_name(self.app.app_name, self.region_name, self.tenant_name,
                                                          self.app.app_id)
        comment = "修改了应用{}的治理模式".format(app_name)
        operation_log_service.create_app_log(self, comment, format_app=False)
        return Response(result)


class AppGovernanceModeCRView(ApplicationView):
    def post(self, request, *args, **kwargs):
        governance_cr = request.data.get("governance_cr", {})
        k8s_resource_service.create_governance_resource(self.app, governance_cr)
        return Response(general_message(200, "success", "创建成功", bean=governance_cr))

    def put(self, request, *args, **kwargs):
        governance_cr = request.data.get("governance_cr", {})
        k8s_resource_service.update_governance_resource(self.app, governance_cr)
        result = general_message(200, "success", "更新成功", bean=governance_cr)
        return Response(result)

    def delete(self, request, *args, **kwargs):
        k8s_resource_service.delete_governance_resource(self.app)
        result = general_message(200, "success", "删除成功")
        return Response(result)


class AppGovernanceModeCheckView(ApplicationView):
    def get(self, request, app_id, *args, **kwargs):
        governance_mode = request.GET.get("governance_mode", "")
        if governance_mode not in GovernanceModeEnum.names():
            raise AbortRequest("governance_mode not in ({})".format(GovernanceModeEnum.names()))

        group_service.check_governance_mode(self.tenant, self.region_name, app_id, governance_mode)
        result = general_message(200, "success", "检查通过", bean={"governance_mode": governance_mode})
        return Response(result)


class AppComponentNameView(ApplicationView):
    def get(self, request, app_id, *args, **kwargs):
        service_ids = group_service_relation_repo.list_serivce_ids_by_app_id(self.tenant.tenant_id, self.region_name, app_id)
        services = list()
        if service_ids:
            services = service_repo.list_by_ids(service_ids)
        component_names = [service.k8s_component_name for service in services]
        data = {"component_names": component_names}
        result = general_message(200, "success", "查询成功", bean=data)
        return Response(result)


class AppKubernetesServiceView(ApplicationView):
    def get(self, request, app_id, *args, **kwargs):
        res = group_service.list_kubernetes_services(self.tenant.tenant_id, self.region_name, app_id)
        result = general_message(200, "success", "查询成功", list=res)
        return Response(result)

    def put(self, request, app_id, *args, **kwargs):
        k8s_services = request.data
        port_aliases = {}
        # data validation
        for k8s_service in k8s_services:
            if not k8s_service.get("service_id"):
                raise AbortRequest("the field 'service_id' is required")
            if not k8s_service.get("port"):
                raise AbortRequest("the field 'port' is required")
            if not k8s_service.get("port_alias"):
                raise AbortRequest("the field 'port_alias' is required")
            port_aliases[k8s_service["port_alias"]] = k8s_service["port"]
        if len(port_aliases) != len(k8s_services):
            raise AbortRequest(msg="the 'port_alias' exists", msg_show="端口别名已存在")
        group_service.update_kubernetes_services(self.tenant, self.region_name, self.app, k8s_services)

        result = general_message(200, "success", "更新成功", list=k8s_services)
        return Response(result)


class ApplicationStatusView(ApplicationView):
    def get(self, request, app_id, *args, **kwargs):
        status = group_service.get_app_status(self.tenant, self.region_name, app_id)
        result = general_message(200, "success", "查询成功", list=status)
        return Response(result)


class ApplicationDetectPrecessView(ApplicationView):
    def get(self, request, app_id, *args, **kwargs):
        processes = group_service.get_detect_process(self.tenant, self.region_name, app_id)
        result = general_message(200, "success", "查询成功", list=processes)
        return Response(result)


class ApplicationInstallView(ApplicationView):
    def post(self, request, app_id, *args, **kwargs):
        overrides = request.data.get("overrides")
        group_service.install_app(self.tenant, self.region_name, app_id, overrides)
        result = general_message(200, "success", "安装成功")
        return Response(result)


class ApplicationPodView(ApplicationView):
    def get(self, request, app_id, pod_name, *args, **kwargs):
        pod = group_service.get_pod(self.tenant, self.region_name, pod_name)
        result = general_message(200, "success", "安装成功", bean=pod)
        return Response(result)


class ApplicationHelmAppComponentView(ApplicationView):
    def get(self, request, app_id, *args, **kwargs):
        components, err = helm_app_service.list_components(self.tenant, self.region_name, self.user, self.app)
        return Response(general_message(err.get("code", 200), err.get("msg", "success"), "查询成功", list=components))


class ApplicationParseServicesView(ApplicationView):
    def post(self, request, app_id, *args, **kwargs):
        values = parse_item(request, "values", required=True)
        services = application_service.parse_services(self.region_name, self.tenant, app_id, values)
        return Response(general_message(200, "success", "查询成功", list=services))


class ApplicationReleasesView(ApplicationView):
    def get(self, request, app_id, *args, **kwargs):
        releases = application_service.list_releases(self.region_name, self.tenant, app_id)
        return Response(general_message(200, "success", "查询成功", list=releases))


class ApplicationIngressesView(ApplicationView):
    def get(self, request, app_id, *args, **kwargs):
        result = application_service.list_access_info(self.tenant, app_id)
        return Response(general_message(200, "success", "查询成功", list=result))


class ApplicationVolumesView(ApplicationView):
    def put(self, request, app_id, *args, **kwargs):
        region_app_id = region_app_repo.get_region_app_id(self.region_name, app_id)
        region_api.change_application_volumes(self.tenant.tenant_name, self.region_name, region_app_id)
        result = general_message(200, "success", "存储路径修改成功")
        return Response(result)
