# -*- coding: utf8 -*-
"""
  Created by leon on 18/1/5.
"""
import logging

from console.enum.app import GovernanceModeEnum
from console.exception.main import AbortRequest, ServiceHandleException
from console.repositories.app import service_repo
from console.repositories.group import group_service_relation_repo
from console.services.helm_app import helm_app_service
from console.services.app_actions import app_manage_service
from console.services.group_service import group_service
from console.services.application import application_service
from console.services.market_app_service import market_app_service
from console.utils.reqparse import parse_item
from console.views.base import (ApplicationView, RegionTenantHeaderCloudEnterpriseCenterView, RegionTenantHeaderView)
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
        if len(note) > 2048:
            return Response(general_message(400, "node too long", "应用备注长度限制2048"), status=400)
        app_store_name = request.data.get("app_store_name", None)
        app_store_url = request.data.get("app_store_url", None)
        app_template_name = request.data.get("app_template_name", None)
        version = request.data.get("version", None)
        region_name = request.data.get("region_name", self.response_region)
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
        )
        result = general_message(200, "success", "创建成功", bean=data)
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
        note = request.data.get("note", "")
        logo = request.data.get("logo", "")
        if note and len(note) > 2048:
            return Response(general_message(400, "node too long", "应用备注长度限制2048"), status=400)
        username = request.data.get("username", None)
        overrides = request.data.get("overrides", [])
        version = request.data.get("version", "")
        revision = request.data.get("revision", 0)

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
            logo=logo)
        result = general_message(200, "success", "修改成功")
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
        group_service.delete_app(self.tenant, self.region_name, self.app)
        result = general_message(200, "success", "删除成功")
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
        app = group_service.get_app_detail(self.tenant, self.region_name, app_id)
        result = general_message(200, "success", "success", bean=app)
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
class TenantGroupCommonOperationView(RegionTenantHeaderCloudEnterpriseCenterView):
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
        app_manage_service.batch_operations(self.tenant, self.region_name, self.user, action, service_ids, self.oauth_instance)
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
    def put(self, request, app_id, *args, **kwargs):
        governance_mode = parse_item(request, "governance_mode", required=True)
        if governance_mode not in GovernanceModeEnum.names():
            raise AbortRequest("governance_mode not in ({})".format(GovernanceModeEnum.names()))

        group_service.update_governance_mode(self.tenant, self.region_name, app_id, governance_mode)
        result = general_message(200, "success", "更新成功", bean={"governance_mode": governance_mode})
        return Response(result)


class AppGovernanceModeCheckView(ApplicationView):
    def get(self, request, app_id, *args, **kwargs):
        governance_mode = request.GET.get("governance_mode", "")
        if governance_mode not in GovernanceModeEnum.names():
            raise AbortRequest("governance_mode not in ({})".format(GovernanceModeEnum.names()))

        group_service.check_governance_mode(self.tenant, self.region_name, app_id, governance_mode)
        result = general_message(200, "success", "更新成功", bean={"governance_mode": governance_mode})
        return Response(result)


class AppKubernetesServiceView(ApplicationView):
    def get(self, request, app_id, *args, **kwargs):
        res = group_service.list_kubernetes_services(self.tenant.tenant_id, self.region_name, app_id)
        result = general_message(200, "success", "查询成功", list=res)
        return Response(result)

    def put(self, request, app_id, *args, **kwargs):
        k8s_services = request.data

        # data validation
        for k8s_service in k8s_services:
            if not k8s_service.get("service_id"):
                raise AbortRequest("the field 'service_id' is required")
            if not k8s_service.get("port"):
                raise AbortRequest("the field 'port' is required")
            if not k8s_service.get("port_alias"):
                raise AbortRequest("the field 'port_alias' is required")

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
