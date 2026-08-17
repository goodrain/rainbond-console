# -*- coding: utf-8 -*-
from typing import Any

from rest_framework.request import Request
from rest_framework.response import Response

from console.services.user_services import user_services
from console.views.base import JWTAuthApiView
from www.utils.return_message import general_message


class AgentFeishuEligibleUsersView(JWTAuthApiView):
    """Return the minimum employee fields required by the Feishu binding UI."""

    def get(self, request: Request, enterprise_id: str, *args: Any, **kwargs: Any) -> Response:
        if not self.is_enterprise_admin or str(getattr(self.user, "enterprise_id", "")) != enterprise_id:
            return Response(general_message(403, "forbidden", "无权限管理飞书员工绑定"), status=403)
        try:
            page = max(1, int(request.GET.get("page", 1)))
            page_size = max(1, min(100, int(request.GET.get("page_size", 20))))
        except (TypeError, ValueError):
            return Response(general_message(400, "invalid_pagination", "分页参数无效"), status=400)
        query = str(request.GET.get("query") or "").strip()[:128]
        users, total = user_services.get_user_by_eid(enterprise_id, query, page, page_size)
        items = [{
            "user_id": user.user_id,
            "display_name": user.real_name or user.nick_name or str(user.user_id),
            "username": user.nick_name or "",
            "is_active": bool(user.is_active),
        } for user in users if bool(user.is_active)]
        result = general_message(
            200, "success", "查询成功", list=items,
            page=page, page_size=page_size, total=total)
        return Response(result, status=200)
