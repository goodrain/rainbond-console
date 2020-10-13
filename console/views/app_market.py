# -*- coding: utf8 -*-

import logging

from rest_framework.response import Response

from console.services.app import app_market_service
from console.views.base import JWTAuthApiView
from www.utils.return_message import general_message
from console.exception.main import AbortRequest

logger = logging.getLogger("default")


class BindableMarketsView(JWTAuthApiView):
    def get(self, request, enterprise_id, *args, **kwargs):
        market_name = request.GET.get("market_name", None)
        market_url = request.GET.get("market_url", None)
        access_key = request.GET.get("access_key", None)
        if market_url is None and market_name is None:
            raise AbortRequest("the field 'market_name' or 'market_url' is required")
        markets = app_market_service.list_bindable_markets(enterprise_id, market_name, market_url, access_key)
        return Response(general_message(200, "success", "获取成功", list=markets))
