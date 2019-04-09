# -*- coding: utf8 -*-

import logging

from rest_framework.response import Response

from console.views.base import EnterpriseHeaderView
from console.views.enterprise_active import enterprise_services
from www.utils.return_message import general_message, error_message

logger = logging.getLogger("default")


class BaseGuidance(EnterpriseHeaderView):
    def get(self, request, *args, **kwargs):
        try:
            data = enterprise_services.list_base_tasks(self.enterprise.enterprise_id)
            result = general_message(200, "success", "请求成功", list=data)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])
