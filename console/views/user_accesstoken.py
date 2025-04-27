# -*- coding: utf8 -*-
import logging

from console.exception.main import ServiceHandleException
from console.services.operation_log import operation_log_service, OperationModule, Operation
from console.services.user_accesstoken_services import user_access_services
from console.views.base import JWTAuthApiView
from django.db import IntegrityError
from rest_framework.response import Response
from www.apiclient.regionapi import RegionInvokeApi
from www.utils.return_message import general_message

region_api = RegionInvokeApi()
logger = logging.getLogger("default")


class UserAccessTokenCLView(JWTAuthApiView):
    def post(self, request, *args, **kwargs):
        note = request.data.get("note")
        age = request.data.get("age")
        if not note:
            raise ServiceHandleException(msg="note can't be null", msg_show="注释不能为空")
        try:
            access_key = user_access_services.create_user_access_key(note, request.user.user_id, age)
            result = general_message(200, None, None, bean=access_key.to_dict())
            comment = operation_log_service.generate_generic_comment(
                operation=Operation.CREATE, module=OperationModule.ACCESSKEY, module_name=note)
            operation_log_service.create_enterprise_log(user=self.user, comment=comment,
                                                        enterprise_id=self.user.enterprise_id)
            return Response(result, status=200)
        except ValueError as e:
            logger.exception(e)
            raise ServiceHandleException(msg="params error", msg_show="请检查参数是否合法")
        except IntegrityError:
            raise ServiceHandleException(msg="note duplicate", msg_show="令牌用途不能重复")

    def get(self, request, *args, **kwargs):
        access_key_list = user_access_services.get_user_access_key(request.user.user_id)
        result = general_message(200, "success", None, list=access_key_list.values("note", "expire_time", "user_id", "ID"))
        return Response(result, status=200)


class UserAccessTokenRUDView(JWTAuthApiView):
    def get(self, request, id, **kwargs):
        access_key = user_access_services.get_user_access_key_by_id(request.user.user_id, id).values(
            "note", "expire_time", "user_id", "ID").first()
        if not access_key:
            result = general_message(404, "no found access key", "未找到该凭证")
            return Response(result, status=404)
        result = general_message(200, "success", None, bean=access_key)
        return Response(result, status=200)

    def put(self, request, id, **kwargs):
        try:
            access_key = user_access_services.update_user_access_key_by_id(request.user.user_id, id)
        except IntegrityError as e:
            logger.exception(e)
            raise ServiceHandleException(msg="access key duplicate", msg_show="刷新失败，请重试")
        if not access_key:
            result = general_message(404, "no found access key", "未找到该凭证")
            return Response(result, status=404)
        result = general_message(200, "success", None, bean=access_key.to_dict())
        comment = operation_log_service.generate_generic_comment(
            operation=Operation.REGENERATED, module=OperationModule.ACCESSKEY, module_name=access_key.note)
        operation_log_service.create_enterprise_log(user=self.user, comment=comment,
                                                    enterprise_id=self.user.enterprise_id)
        return Response(result, status=200)

    def delete(self, request, id, **kwargs):
        user_access_services.delete_user_access_key_by_id(request.user.user_id, id)
        result = general_message(200, "success", None)
        comment = operation_log_service.generate_generic_comment(
            operation=Operation.DELETE, module=OperationModule.ACCESSKEY,
            module_name=access_key.note if access_key else "")
        operation_log_service.create_enterprise_log(user=self.user, comment=comment,
                                                    enterprise_id=self.user.enterprise_id)
        return Response(result, status=200)
