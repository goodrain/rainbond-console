import logging

from console.services.app_security_context import app_security_context, app_inspect
from console.views.app_config.base import AppBaseView
from rest_framework.response import Response

from www.apiclient.regionapi import RegionInvokeApi
from www.utils.return_message import general_message

logger = logging.getLogger("default")
region_api = RegionInvokeApi()


class AppSecurityContext(AppBaseView):
    def get(self, request, *args, **kwargs):
        security_context = app_security_context.get_security_context(self.service.service_id)
        msg_show = "组件安全状态关闭"
        if security_context:
            msg_show = "组件安全状态开启"
            security_context = security_context.to_dict()
        result = general_message(200, "success", msg_show, bean=security_context)
        return Response(result, status=result["code"])

    def post(self, request, *args, **kwargs):
        app_security_context.open_security_context(self.region_name, self.tenant_name, self.service.service_id,
                                                   self.service.service_alias)
        result = general_message(200, "success", "开启组件安全", bean="开启组件安全")
        return Response(result, status=result["code"])

    def put(self, request, *args, **kwargs):
        seccomp_profile = request.data.get("seccomp_profile", {})
        run_as_non_root = request.data.get("run_as_non_root", True)
        allow_privilege_escalation = request.data.get("allow_privilege_escalation", False)
        run_as_user = request.data.get("run_as_user", 10001)
        run_as_group = request.data.get("run_as_group", 10001)
        capabilities = request.data.get("capabilities", {})
        read_only_root_filesystem = request.data.get("read_only_root_filesystem", True)
        app_security_context.update_security_context(
            self.region_name, self.tenant_name, self.service.service_id, self.service.service_alias, seccomp_profile,
            run_as_non_root, allow_privilege_escalation, run_as_user, run_as_group, capabilities, read_only_root_filesystem)
        result = general_message(200, "success", "修改成功", bean="修改成功")
        return Response(result, status=result["code"])

    def delete(self, request, *args, **kwargs):
        app_security_context.close_security_context(self.region_name, self.tenant_name, self.service.service_id,
                                                    self.service.service_alias)
        result = general_message(200, "success", "组件安全已关闭", bean="组件安全已关闭")
        return Response(result, status=result["code"])


class AppInspection(AppBaseView):
    def get(self, request, *args, **kwargs):
        inspection = app_inspect.get_inspection(self.service.service_id)
        msg_show = "检测开关一览"
        if inspection:
            inspection = inspection.to_dict()
        result = general_message(200, "success", msg_show, bean=inspection)
        return Response(result, status=result["code"])

    def post(self, request, *args, **kwargs):
        operation_type = request.data.get("operation_type", False)
        inspection_type = request.data.get("inspection_type", "")
        app_inspect.operation_inspection(self.region_name, self.tenant_name, self.service.service_id, operation_type,
                                         self.service.service_alias, inspection_type)
        result = general_message(200, "success", "修改成功", bean="修改成功")
        return Response(result, status=result["code"])


class AppInspectionReport(AppBaseView):
    def get(self, request, *args, **kwargs):
        p = request.GET.get("p", 1)
        ps = request.GET.get("ps", 100)
        scan_type = request.GET.get("scan_type", "code")
        url = request.GET.get("url", "")
        if scan_type == "code" or scan_type == "normative":
            ret_data = app_inspect.get_inspection_report(self.service.service_id, p, ps, scan_type, url)
        else:
            ret_data = app_inspect.leak_or_config_inspection(self.tenant_name, self.service.service_alias, scan_type, p, ps,
                                                             url)
        result = general_message(200, "success", "获取成功", bean=ret_data)
        return Response(result, status=result["code"])
