# -*- coding: utf8 -*-
"""
  Created by leon on 18/1/12.
"""
import logging

from django.db import transaction
from django.views.decorators.cache import never_cache
from rest_framework.response import Response

from console.exception.main import BusinessException, ResourceNotEnoughException, AccountOverdueException
from console.services.app_check_service import app_check_service
from console.services.compose_service import compose_service
from console.services.group_service import group_service
from console.views.base import RegionTenantHeaderView
from www.utils.return_message import general_message
from console.repositories.group import group_repo
from console.repositories.compose_repo import compose_repo

logger = logging.getLogger("default")


class ComposeGroupBaseView(RegionTenantHeaderView):
    def __init__(self, *args, **kwargs):
        super(ComposeGroupBaseView, self).__init__(*args, **kwargs)
        self.group = None

    def initial(self, request, *args, **kwargs):
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

    def initial_header_info(self, request):
        pass


class ComposeBaseView(RegionTenantHeaderView):
    def __init__(self, *args, **kwargs):
        super(ComposeBaseView, self).__init__(*args, **kwargs)
        self.group_compose = None

    def initial(self, request, *args, **kwargs):
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

    def initial_header_info(self, request):
        pass


class DockerComposeCreateView(RegionTenantHeaderView):
    @never_cache
    def post(self, request, *args, **kwargs):
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
            - name: yaml_content
              description: compose文件内容
              required: true
              type: string
              paramType: form

        """

        group_name = request.data.get("group_name", None)
        hub_user = request.data.get("user_name", "")
        hub_pass = request.data.get("password", "")
        yaml_content = request.data.get("yaml_content", "")
        group_note = request.data.get("group_note", "")
        if group_note and len(group_note) > 2048:
            return Response(general_message(400, "node too long", "应用备注长度限制2048"), status=400)
        if not group_name:
            return Response(general_message(400, 'params error', "请指明需要创建的compose组名"), status=400)
        if not yaml_content:
            return Response(general_message(400, "params error", "未指明yaml内容"), status=400)
        # Parsing yaml determines whether the input is illegal
        code, msg, json_data = compose_service.yaml_to_json(yaml_content)
        if code != 200:
            return Response(general_message(code, "parse yaml error", msg), status=code)
        # 创建组
        group_info = group_service.add_group(self.tenant, self.response_region, group_name, group_note)
        code, msg, group_compose = compose_service.create_group_compose(self.tenant, self.response_region, group_info.ID,
                                                                        yaml_content, hub_user, hub_pass)
        if code != 200:
            return Response(general_message(code, "create group compose error", msg), status=code)
        bean = dict()
        bean["group_id"] = group_compose.group_id
        bean["compose_id"] = group_compose.compose_id
        bean["group_name"] = group_info.group_name
        result = general_message(200, "operation success", "compose组创建成功", bean=bean)
        return Response(result, status=result["code"])


class GetComposeCheckUUID(ComposeGroupBaseView):
    @never_cache
    def get(self, request, *args, **kwargs):
        compose_id = request.GET.get("compose_id", None)
        if not compose_id:
            return Response(general_message(400, "params error", "参数错误，请求参数应该包含compose ID"), status=400)
        group_compose = compose_service.get_group_compose_by_compose_id(compose_id)
        if group_compose:
            result = general_message(200, u"success", "获取成功", bean={"check_uuid": group_compose.check_uuid})
        else:
            result = general_message(404, u"success", "compose不存在", bean={"check_uuid": ""})
        return Response(result, status=200)


class ComposeCheckView(ComposeGroupBaseView):
    @never_cache
    def post(self, request, *args, **kwargs):
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
            return Response(general_message(code, "check compose error", msg))
        result = general_message(code, "compose check task send success", "检测任务发送成功", bean=compose_bean)
        return Response(result, status=result["code"])

    @never_cache
    def get(self, request, *args, **kwargs):
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
            if not check_uuid:
                return Response(general_message(400, "params error", "参数错误，请求参数应该包含请求的ID"), status=400)
            if not compose_id:
                return Response(general_message(400, "params error", "参数错误，请求参数应该包含compose ID"), status=400)
            group_compose = compose_service.get_group_compose_by_compose_id(compose_id)
            code, msg, data = app_check_service.get_service_check_info(self.tenant, self.response_region, check_uuid)
            logger.debug("start save compose info ! {0}".format(group_compose.create_status))
            save_code, save_msg, service_list = compose_service.save_compose_services(self.tenant, self.user,
                                                                                      self.response_region, group_compose, data)
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
                transaction.savepoint_commit(sid)
            compose_check_brief = compose_service.wrap_compose_check_info(data)
            result = general_message(200, "success", "请求成功", bean=compose_check_brief, list=[s.to_dict() for s in service_list])
        except ResourceNotEnoughException as re:
            raise re
        except AccountOverdueException as re:
            logger.exception(re)
            return Response(general_message(10410, "resource is not enough", re.message), status=412)
        return Response(result, status=result["code"])


class ComposeCheckUpdate(ComposeGroupBaseView):
    @never_cache
    def put(self, request, *args, **kwargs):
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
            group_service.update_group(self.tenant, self.response_region, group_id, group_name)
        if yaml_content:
            code, msg, json_data = compose_service.yaml_to_json(yaml_content)
            if code != 200:
                return Response(general_message(code, "parse yaml error", msg), status=code)
            code, msg, new_compose = compose_service.update_compose(group_id, json_data)
            if code != 200:
                return Response(general_message(code, "save yaml content error", msg), status=code)
        result = general_message(200, u"success", "修改成功")
        return Response(result, status=result["code"])


class ComposeDeleteView(ComposeGroupBaseView):
    """放弃创建compose"""

    @never_cache
    def delete(self, request, *args, **kwargs):
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
        if group_id:
            if group_id < 1:
                return Response(general_message(400, "params error", "所在组参数错误 "), status=400)
        else:
            return Response(general_message(400, "params error", "请指明需要删除的组标识 "), status=400)
        if not compose_id:
            return Response(general_message(400, "params error", "请指明需要删除的compose ID "), status=400)
        compose_service.give_up_compose_create(self.tenant, group_id, compose_id)
        result = general_message(200, "compose delete success", "删除成功")
        return Response(result, status=result["code"])


class ComposeServicesView(ComposeBaseView):
    @never_cache
    def get(self, request, *args, **kwargs):
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
    def get(self, request, *args, **kwargs):
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
