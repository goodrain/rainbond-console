# coding=utf-8
from console.services.login_event import log_event_service
from console.views.base import EnterpriseHeaderView
from console.views.operation_log import extend_user_info
from rest_framework.response import Response
from www.utils.return_message import general_message


class LoginEventView(EnterpriseHeaderView):
    def get(self, request, *args, **kwargs):
        start_time = request.GET.get("start_time", None)
        end_time = request.GET.get("end_time", None)
        username = request.GET.get("username", None)
        event_type = request.GET.get("event_type", None)
        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 10))

        resp, total = log_event_service.list_log_events(self.enterprise_id, username, event_type, start_time, end_time, page,
                                                        page_size)
        resp = extend_user_info(self.enterprise_id, resp)
        result = general_message(200, "success", "查询成功", list=resp, total=total)
        return Response(result, status=result["code"])
