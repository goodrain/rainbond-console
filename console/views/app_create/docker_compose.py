# -*- coding: utf8 -*-
"""
  Created by leon on 18/1/12.
"""
import logging
from typing import Any

from console.exception.main import (AccountOverdueException, BusinessException, ResourceNotEnoughException,
                                    ServiceHandleException)
from console.repositories.compose_repo import compose_repo
from console.repositories.group import group_repo
from console.services.app_check_service import app_check_service
from console.services.compose_service import compose_service
from console.services.enterprise_first_deploy_service import enterprise_first_deploy_service
from console.services.group_service import group_service
from console.services.team_services import team_services
from console.views.base import RegionTenantHeaderView
from django.db import transaction
from console.utils.cache_decorators import never_cache
from rest_framework.request import Request
from rest_framework.response import Response
from console.models.main import ComposeGroup
from www.models.main import ServiceGroup
from www.utils.return_message import general_message

logger = logging.getLogger("default")


class ComposeGroupBaseView(RegionTenantHeaderView):
    group: ServiceGroup

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super(ComposeGroupBaseView, self).__init__(*args, **kwargs)
        self.group = None  # type: ignore[assignment]

    def initial(self, request: Request, *args: Any, **kwargs: Any) -> None:
        super(ComposeGroupBaseView, self).initial(request, *args, **kwargs)
        group_id = kwargs.get("group_id", None)
        if not group_id:
            raise ImportError("You url not contains args - group_id -")
        group = group_repo.get_group_by_pk(self.tenant.tenant_id, self.response_region, group_id)
        if group:
            self.group = group
        else:
            raise BusinessException(Response(general_message(404, "group not found", "组ID{0}不存在".format(group_id)), status=404))
        self.initial_header_info(request)

    def initial_header_info(self, request: Request) -> None:
        pass


class ComposeBaseView(RegionTenantHeaderView):
    group_compose: ComposeGroup

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super(ComposeBaseView, self).__init__(*args, **kwargs)
        self.group_compose = None  # type: ignore[assignment]

    def initial(self, request: Request, *args: Any, **kwargs: Any) -> None:
        super(ComposeBaseView, self).initial(request, *args, **kwargs)
        compose_id = kwargs.get("compose_id", None)
        if not compose_id:
            raise ImportError("You url not contains args - compose_id -")
        group_compose = compose_repo.get_group_compose_by_compose_id(compose_id)
        if group_compose:
            self.group_compose = group_compose
        else:
            raise BusinessException(
                Response(general_message(404, "compose not found", "compose组{0}不存在".format(compose_id)), status=404))
        self.initial_header_info(request)

    def initial_header_info(self, request: Request) -> None:
        pass


class DockerComposeCreateView(RegionTenantHeaderView):
    @never_cache
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """
        docker-compose创建组件
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
            - name: user_name
              description: 镜像仓库名称
              required: true
              type: string
              paramType: form
            - name: password
              description: 镜像仓库密码
              required: true
              type: string
              paramType: form
            - name: event_id
              description: 上传事件ID
              required: true
              type: string
              paramType: form
            - name: compose_file_path
              description: compose文件路径
              required: false
              type: string
              paramType: form

        """

        group_id = request.data.get("group_id", None)
        hub_user = request.data.get("user_name", "")
        hub_pass = request.data.get("password", "")
        registry_auth_id = request.data.get("registry_auth_id", "")
        if registry_auth_id:
            registry_auth = team_services.resolve_registry_auth(self.user, registry_auth_id)
            hub_user = registry_auth.username
            hub_pass = registry_auth.password
        event_id = request.data.get("event_id", "")
        compose_file_path = request.data.get("compose_file_path", "docker-compose.yml")
        group_note = request.data.get("group_note", "")
        if group_note and len(group_note) > 2048:
            return Response(general_message(400, "node too long", "应用备注长度限制2048"), status=400)
        if not event_id:
            return Response(general_message(400, "params error", "未指明上传事件ID"), status=400)
        # 创建组
        group = group_repo.get_group_by_pk(self.tenant.tenant_id, self.response_region, group_id)  # type: ignore[arg-type]
        if not group:
            return Response(general_message(404, "group not found", "应用组不存在"), status=404)
        group_info = group.to_dict()
        group_info["group_id"] = group.ID
        group_info['app_id'] = group.ID
        group_info['app_name'] = group.group_name
        group_info['k8s_app'] = group.k8s_app
        code, msg, group_compose = compose_service.create_group_compose(
            self.tenant, self.response_region, group_info["group_id"], event_id, compose_file_path, hub_user, hub_pass)
        if code != 200:
            return Response(general_message(code, "create group compose error", msg), status=code)
        bean: dict = dict()
        bean["group_id"] = group_compose.group_id
        bean["compose_id"] = group_compose.compose_id
        bean["app_name"] = group_info["app_name"]
        result = general_message(200, "operation success", "compose组创建成功", bean=bean)
        return Response(result, status=result["code"])


class GetComposeCheckUUID(ComposeGroupBaseView):
    @never_cache
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        compose_id = request.GET.get("compose_id", None)
        if not compose_id:
            return Response(general_message(400, "params error", "参数错误，请求参数应该包含compose ID"), status=400)
        group_compose = compose_service.get_group_compose_by_compose_id(compose_id)
        if group_compose:
            result = general_message(200, "success", "获取成功", bean={"check_uuid": group_compose.check_uuid})
        else:
            result = general_message(404, "success", "compose不存在", bean={"check_uuid": ""})
        return Response(result, status=200)


class ComposeCheckView(ComposeGroupBaseView):
    def _report_compose_check_failure(self, compose_id: str, check_uuid: str, reason: str) -> None:
        app_context = enterprise_first_deploy_service.build_service_app_context(self.group)
        app_context["compose_id"] = compose_id or ""
        tracker = enterprise_first_deploy_service.safe_begin_tracking(
            enterprise_id=self.tenant.enterprise_id,
            tenant_name=self.tenant.tenant_name,
            region_name=self.response_region,
            deploy_type=enterprise_first_deploy_service.DEPLOY_TYPE_IMAGE,
            operator=getattr(self.user, "nick_name", ""),
            source_language="docker-compose",
            trigger="compose_check",
            app_context=app_context,
            workload_context={
                "source_type": "docker-compose",
                "compose_id": compose_id or "",
                "check_uuid": check_uuid or "",
            })
        enterprise_first_deploy_service.safe_mark_failure(
            tracker,
            reason=reason or "Docker Compose 检测失败",
            failure_stage=enterprise_first_deploy_service.FAILURE_STAGE_BUILD)

    @staticmethod
    def _compose_check_failure_reason(data: dict, default_reason: str = "") -> str:
        error_infos = data.get("error_infos") or []
        first_error = error_infos[0] if error_infos else {}
        return first_error.get("error_info") or first_error.get("solve_advice") or default_reason or "Docker Compose 检测失败"

    @never_cache
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """
        docker-compose组件检测
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: group_id
              description: 组ID
              required: true
              type: string
              paramType: path
            - name: compose_id
              description: group_compose ID
              required: true
              type: string
              paramType: form
        """
        compose_id = request.data.get("compose_id", None)

        if not compose_id:
            return Response(general_message(400, "params error", "需要检测的compose ID "), status=400)
        code, msg, compose_bean = compose_service.check_compose(self.response_region, self.tenant, compose_id)
        if code != 200:
            self._report_compose_check_failure(compose_id, "", msg)
            return Response(general_message(code, "check compose error", msg))
        result = general_message(code, "compose check task send success", "检测任务发送成功", bean=compose_bean)
        return Response(result, status=result["code"])

    @never_cache
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """
        获取compose文件检测信息
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: group_id
              description: 组ID
              required: true
              type: string
              paramType: path
            - name: check_uuid
              description: 检测id
              required: true
              type: string
              paramType: query
            - name: compose_id
              description: group_compose ID
              required: true
              type: string
              paramType: query

        """
        sid = None
        try:
            check_uuid = request.GET.get("check_uuid", None)
            compose_id = request.GET.get("compose_id", None)
            arch = request.GET.get("arch", None)
            if not check_uuid:
                return Response(general_message(400, "params error", "参数错误，请求参数应该包含请求的ID"), status=400)
            if not compose_id:
                return Response(general_message(400, "params error", "参数错误，请求参数应该包含compose ID"), status=400)
            group_compose = compose_service.get_group_compose_by_compose_id(compose_id)
            code, msg, data = app_check_service.get_service_check_info(
                self.tenant, self.response_region, check_uuid)  # type: ignore[arg-type]
            # NOTE: get_group_compose_by_compose_id may return None; backlog
            logger.debug("start save compose info ! {0}".format(group_compose.create_status))  # type: ignore[union-attr]
            save_code, save_msg, service_list = compose_service.save_compose_services(
                self.tenant, self.user, self.response_region, group_compose, data, arch)  # type: ignore[arg-type]
            if save_code != 200:
                data["check_status"] = "failure"
                save_error = {
                    "error_type": "check info save error",
                    "solve_advice": "修改相关信息后重新尝试",
                    "error_info": "{}".format(save_msg)
                }
                if data["error_infos"]:
                    data["error_infos"].append(save_error)
                else:
                    data["error_infos"] = [save_error]
            else:
                # NOTE: sid is always None (savepoint never created); savepoint_commit(None); latent bug, backlog
                transaction.savepoint_commit(sid)  # type: ignore[arg-type]
            if data.get("check_status") == "failure":
                self._report_compose_check_failure(
                    compose_id,
                    check_uuid,
                    self._compose_check_failure_reason(data, save_msg))
            compose_check_brief = compose_service.wrap_compose_check_info(data)
            result = general_message(200, "success", "请求成功", bean=compose_check_brief, list=[s.to_dict() for s in service_list])
        except ResourceNotEnoughException as re:
            raise re
        except AccountOverdueException as re:
            logger.exception(re)
            # NOTE: py2-style Exception.message
            return Response(general_message(10410, "resource is not enough", re.message), status=412)  # type: ignore[attr-defined]
        return Response(result, status=result["code"])


class ComposeCheckUpdate(ComposeGroupBaseView):
    @never_cache
    def put(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """
        compose文件内容修改
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: group_id
              description: 组ID
              required: true
              type: string
              paramType: path
            - name: group_name
              description: 组名称
              required: false
              type: string
              paramType: form
            - name: compose_content
              description: yaml文件内容
              required: false
              type: string
              paramType: form

        """
        group_id = kwargs.get("group_id", None)
        yaml_content = request.data.get("compose_content", None)
        group_name = request.data.get("group_name", None)
        if not yaml_content and not group_name:
            return Response(general_message(400, "params error", "请填入需要修改的参数"), status=400)
        if group_name:
            group_service.update_group(self.tenant, self.response_region, group_id, group_name)  # type: ignore[arg-type]
        if yaml_content:
            code, msg, json_data = compose_service.yaml_to_json(yaml_content)
            if code != 200:
                return Response(general_message(code, "parse yaml error", msg), status=code)
            code, msg, new_compose = compose_service.update_compose(group_id, json_data)  # type: ignore[arg-type]
            if code != 200:
                return Response(general_message(code, "save yaml content error", msg), status=code)
        result = general_message(200, "success", "修改成功")
        return Response(result, status=result["code"])


class ComposeDeleteView(ComposeGroupBaseView):
    """放弃创建compose"""

    @never_cache
    def delete(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """
        放弃创建compose组组件
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: group_id
              description: 组ID
              required: true
              type: string
              paramType: path
            - name: compose_id
              description: group_compose id
              required: true
              type: string
              paramType: form
        """
        compose_id = request.data.get("compose_id", None)
        group_id = kwargs.get("group_id", None)
        app_name = request.data.get("app_name", "")
        try:
            group_id = int(group_id)  # type: ignore[arg-type]
        except ValueError:
            raise ServiceHandleException(msg="group id is invalid", msg_show="参数不合法")
        if group_id:
            if group_id < 1:
                return Response(general_message(400, "params error", "所在组参数错误 "), status=400)
        else:
            return Response(general_message(400, "params error", "请指明需要删除的组标识 "), status=400)
        if not compose_id:
            return Response(general_message(400, "params error", "请指明需要删除的compose ID "), status=400)
        compose_service.give_up_compose_create(self.tenant, compose_id)
        result = general_message(200, "compose delete success", "删除成功")
        return Response(result, status=result["code"])


class ComposeServicesView(ComposeBaseView):
    @never_cache
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """
        获取compose组下的组件
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: compose_id
              description: 组ID
              required: true
              type: string
              paramType: path
        """
        services = compose_service.get_compose_services(self.group_compose.compose_id)
        s_list = [s.to_dict() for s in services]
        result = general_message(200, "success", "查询成功", list=s_list)
        return Response(result, status=result["code"])


class ComposeContentView(ComposeBaseView):
    @never_cache
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """
        获取compose文件内容
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: compose_id
              description: 组ID
              required: true
              type: string
              paramType: path
        """
        # try:
        result = general_message(200, "success", "查询成功", bean=self.group_compose.to_dict())
        return Response(result, status=result["code"])
