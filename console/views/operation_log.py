# -*- coding: utf8 -*-
import logging

from rest_framework.response import Response

from www.utils.return_message import general_message
from console.views.base import JWTAuthApiView
from console.services.operation_log import operation_log_service
from console.services.user_services import user_services
from console.views.base import RegionTenantHeaderView, ApplicationView
from console.services.group_service import service_repo
from console.repositories.group import group_repo

logger = logging.getLogger("default")


class OperationLogView(JWTAuthApiView):
    def get(self, request, enterprise_id, *args, **kwargs):
        params = get_query_params(request)
        logs, total = operation_log_service.list(enterprise_id, params)
        logs = extend_user_info(enterprise_id, logs)
        result = general_message(200, "success", "查询成功", list=logs, total=total)
        return Response(result, status=result["code"])


class TeamOperationLogView(RegionTenantHeaderView):
    def get(self, request, *args, **kwargs):
        params = get_query_params(request)
        logs, total = operation_log_service.list_team_logs(self.user.enterprise_id, self.tenant, params)
        logs = extend_user_info(self.user.enterprise_id, logs)
        result = general_message(200, "success", "查询成功", list=logs, total=total)
        return Response(result, status=result["code"])


class AppOperationLogView(ApplicationView):
    def get(self, request, *args, **kwargs):
        params = get_query_params(request)
        logs, total = operation_log_service.list_app_logs(self.user.enterprise_id, self.tenant, self.app, params)
        logs = extend_user_info(self.user.enterprise_id, logs)
        result = general_message(200, "success", "查询成功", list=logs, total=total)
        return Response(result, status=result["code"])


def get_query_params(request):
    params = {
        "start_time": request.GET.get("start_time", None),
        "end_time": request.GET.get("end_time", None),
        "username": request.GET.get("username", None),
        "operation_type": request.GET.get("operation_type", None),
        "service_alias": request.GET.get("service_alias", None),
        "app_id": request.GET.get("app_id", None),
        "page": request.GET.get("page", 1),
        "page_size": request.GET.get("page_size", 10),
        "query": request.GET.get("query", None)
    }
    return params


def extend_user_info(enterprise_id, logs):
    if not logs:
        return
    for log in logs:
        try:
            log["is_delete"] = True
            if log.get("username"):
                user = user_services.get_enterprise_user_by_username(log["username"], enterprise_id)
                log["real_name"] = user.get_name()
                log["email"] = user.email
                log["phone"] = user.phone
            if log.get("app_id"):
                app = group_repo.get_app_by_pk(log["app_id"])
                if app:
                    log["is_delete"] = False
                    log["app_name"] = app.app_name
            if log.get("service_alias"):
                service = service_repo.get_service_by_service_alias(log["service_alias"])
                log["is_delete"] = True
                if service:
                    log["is_delete"] = False
                    log["service_cname"] = service.service_cname
        except Exception as e:
            log["real_name"] = log.get("username")
            logger.exception(e)
    return logs
