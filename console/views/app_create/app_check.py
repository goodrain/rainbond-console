# -*- coding: utf8 -*-
"""
  Created on 18/2/1.
"""
from django.views.decorators.cache import never_cache
from rest_framework.response import Response

from console.views.app_config.base import AppBaseView
from console.services.app_check_service import app_check_service
from console.services.app import app_service
from www.decorator import perm_required
from www.utils.return_message import general_message, error_message
import logging
from console.serializer import TenantServiceUpdateSerilizer

logger = logging.getLogger("default")


class AppCheck(AppBaseView):
    @never_cache
    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        """
        获取服务检测信息
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
            - name: check_uuid
              description: 检测id
              required: true
              type: string
              paramType: query

        """
        check_uuid = request.GET.get("check_uuid", None)
        if not check_uuid:
            return Response(
                general_message(400, "params error", "参数错误，请求参数应该包含请求的ID"),
                status=400)
        code, msg, data = app_check_service.get_service_check_info(
            self.tenant, self.service.service_region, check_uuid)
        # 如果已创建完成
        if self.service.create_status == "complete":
            app_check_service.update_service_check_info(
                self.tenant, self.service, data)
            check_brief_info = app_check_service.wrap_service_check_info(
                self.service, data)
            return Response(
                general_message(200, "success", "请求成功", bean=check_brief_info))

        if data["service_info"] and len(data["service_info"]) < 2:
            # No need to save env, ports and other information for multiple services here.
            logger.debug("start save check info ! {0}".format(
                self.service.create_status))
            save_code, save_msg = app_check_service.save_service_check_info(
                self.tenant, self.service, data)
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
        check_brief_info = app_check_service.wrap_service_check_info(
            self.service, data)
        result = general_message(200, "success", "请求成功", bean=check_brief_info)
        return Response(result, status=result["code"])

    @never_cache
    @perm_required('view_service')
    def post(self, request, *args, **kwargs):
        """
        服务信息检测
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
            is_again = request.data.get("is_again", False)
            code, msg, service_info = app_check_service.check_service(
                self.tenant, self.service, is_again)
            if code != 200:
                result = general_message(code, "check service error", msg)
            else:
                result = general_message(
                    200, "success", "操作成功", bean=service_info)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class GetCheckUUID(AppBaseView):
    @never_cache
    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        result = general_message(
            200,
            u"success",
            "获取成功",
            bean={"check_uuid": self.service.check_uuid})
        return Response(result, status=200)


class AppCheckUpdate(AppBaseView):
    @never_cache
    @perm_required('create_service')
    def put(self, request, *args, **kwargs):
        """
        服务检测信息修改
        ---
        serializer: TenantServiceUpdateSerilizer
        """
        try:
            data = request.data

            serializer = TenantServiceUpdateSerilizer(data=data)
            if not serializer.is_valid():
                result = general_message(400, "{0}".format(serializer.errors),
                                         "参数异常")
                return Response(result, status=result["code"])
            params = dict(serializer.data)

            code, msg = app_service.update_check_app(self.tenant, self.service,
                                                     params)
            if code != 200:
                return Response(
                    general_message(code, "update service info error", msg),
                    status=code)
            result = general_message(200, u"success", "修改成功")
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])
