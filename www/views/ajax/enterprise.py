# -*- coding:utf-8 -*-

import logging
import os

from django.http import JsonResponse
from django.conf import settings

from www.apiclient.baseclient import client_auth_service
from www.apiclient.marketclient import MarketOpenAPI
from www.views import AuthedView

logger = logging.getLogger('default')


class MarketEnterpriseAccessTokenBindView(AuthedView):
    def post(self, request):
        """
        添加或修改企业访问云市的认证信息接口
        ---
        parameters:
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
        enterprise_id = request.POST.get('enterprise_id')
        market_client_id = request.POST.get('market_client_id')
        market_client_token = request.POST.get('market_client_token')
        if not enterprise_id or not market_client_id or not market_client_token:
            return JsonResponse({'ok': False, 'message': 'missing post parameter!'}, status=400)

        enter = client_auth_service.get_enterprise_by_id(enterprise_id)
        if not enter:
            return JsonResponse({'ok': False, 'message': 'specify enterprise does not existed!'}, status=500)

        try:
            market_api = MarketOpenAPI()
            domain = os.getenv('GOODRAIN_APP_API', settings.APP_SERVICE_API["url"])
            market_api.confirm_access_token(domain, market_client_id, market_client_token)
        except Exception:
            return JsonResponse({'ok': False, 'message': '认证企业信息失败'})

        token_info = client_auth_service.get_market_access_token_by_access_token(market_client_id, market_client_token)
        if token_info and token_info.enterprise_id != enter.ID:
            return JsonResponse({'ok': False, 'message': '非法绑定操作!'})

        client_auth_service.save_market_access_token(enterprise_id, domain, market_client_id, market_client_token)
        return JsonResponse({'ok': True, 'message': 'ok'})
