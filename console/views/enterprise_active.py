# -*- coding: utf8 -*-
"""
  Created on 18/3/15.
"""
import logging
import os

from django.conf import settings
from django.views.decorators.cache import never_cache
from rest_framework.response import Response

from console.services.enterprise_services import enterprise_services
from console.views.base import RegionTenantHeaderView
from www.apiclient.baseclient import client_auth_service
from www.apiclient.marketclient import MarketOpenAPI
from www.decorator import perm_required
from www.utils.return_message import general_message, error_message

logger = logging.getLogger("default")


class BindMarketEnterpriseAccessTokenView(RegionTenantHeaderView):
    @never_cache
    @perm_required("tenant.tenant_access")
    def post(self, request, *args, **kwargs):
        """
        云市绑定企业账号
        ---
        parameters:
            - name: tenantName
              description: 团队名称
              required: true
              type: string
              paramType: path
            - name: enterprise_id
              description: 云帮本地企业id
              required: true
              type: string
              paramType: form
            - name: market_client_id
              description: 云市授予的企业身份id
              required: true
              type: string
              paramType: form
            - name: market_client_token
              description: 云市授予的企业访问的token
              required: true
              type: string
              paramType: form

        """
        try:
            logger.debug("bind market access token")
            enterprise_id = request.data.get('enterprise_id')
            market_client_id = request.data.get('market_client_id')
            market_client_token = request.data.get('market_client_token')
            if not enterprise_id or not market_client_id or not market_client_token:
                return Response(general_message(400, "param error", "请填写相关信息"), status=400)
            enter = enterprise_services.get_enterprise_by_enterprise_id(enterprise_id)
            if not enter:
                return Response(general_message(404, "enterprise not found", "指定的企业未找到"), status=404)

            try:
                market_api = MarketOpenAPI()
                domain = os.getenv('GOODRAIN_APP_API', settings.APP_SERVICE_API["url"])
                market_api.confirm_access_token(domain, market_client_id, market_client_token)
            except Exception as e:
                logger.exception(e)
                return Response(general_message(500, "bind access token fail", "企业认证失败"), status=500)

            token_info = client_auth_service.get_market_access_token_by_access_token(market_client_id,
                                                                                     market_client_token)
            if token_info and token_info.enterprise_id != enter.ID:
                return Response(general_message(409, "illegal operation", "非法绑定操作"), status=409)

            client_auth_service.save_market_access_token(enterprise_id, domain, market_client_id, market_client_token)
            result = general_message(200, "success", "绑定成功")
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])
