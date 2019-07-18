# -*- coding: utf-8 -*-
import logging
from www.apiclient.marketclient import MarketOpenAPI
from console.views.base import JWTAuthApiView
from www.utils.return_message import general_message
from console.services.team_services import team_services
from django.http.response import JsonResponse

market_api = MarketOpenAPI()
logger = logging.getLogger('default')


class EnterReceiptAPIView(JWTAuthApiView):
    def get(self, request):
        team_name = request.GET.get('team_name', None)
        if not team_name:
            return JsonResponse(data=general_message(400, 'team name is null', '参数错误'), status=400)

        limit = int(request.GET.get('limit', 10) or 10)
        page = int(request.GET.get('page', 1) or 1)
        receipt_status = request.GET.get('receipt_status', '') or ''
        team = team_services.get_tenant(tenant_name=team_name)
        try:
            body = market_api.get_enterprise_receipts(team.tenant_id, team.enterprise_id, receipt_status, page, limit)
            data = body["data"]
            result = general_message(200, 'success', '查询成功', list=data['list'])
        except Exception as e:
            logger.exception(e)
            result = general_message(500, 'receipt info query failed', '企业发票信息查询失败')
        return JsonResponse(data=result, status=result["code"])

    def post(self, request):
        team_name = request.data.get('team_name', None)
        if not team_name:
            return JsonResponse(data=general_message(400, 'team name is null', '参数错误'), status=400)

        team = team_services.get_tenant(tenant_name=team_name)
        data = {
            'order_nos': request.data.get('orders').split(',') if 'orders' in request.data else [],
            'receipt_type': request.data.get('receipt_type'),
            'user_name': request.data.get('user_name'),
            'subject': request.data.get('subject'),
            'taxes_id': request.data.get('taxes_id'),
            'content': request.data.get('content'),
            'bank': request.data.get('bank'),
            'bank_account': request.data.get('bank_account'),
            'phone': request.data.get('phone'),
            'address': request.data.get('address'),
            'post_address': request.data.get('post_address'),
            'post_contact': request.data.get('post_contact'),
            'post_contact_phone': request.data.get('post_contact_phone')
        }
        try:
            data = market_api.create_enterprise_receipts(team.tenant_id, team.enterprise_id, data)
            result = general_message(200, 'success', '创建成功', bean=data)
        except Exception as e:
            logger.exception(e)
            result = general_message(500, 'proxy receipt api failed', '创建新发票接口调用失败')
        return JsonResponse(data=result, status=result["code"])


class EnterReceiptDetailAPIView(JWTAuthApiView):
    def get(self, request, receipt_id):
        team_name = request.GET.get('team_name', None)
        if not team_name:
            return JsonResponse(data=general_message(400, 'team name is null', '参数错误'), status=400)

        team = team_services.get_tenant(tenant_name=team_name)
        try:
            data = market_api.get_enterprise_receipt(team.tenant_id, team.enterprise_id, receipt_id)
            result = general_message(200, 'success', '查询成功', bean=data)
        except Exception as e:
            logger.exception(e)
            result = general_message(500, 'proxy receipt api failed', '获取发票详情接口调用失败')
        return JsonResponse(data=result, status=result["code"])


class EnterReceiptOrdersAIPView(JWTAuthApiView):
    def get(self, request):

        team_name = request.GET.get('team_name', None)
        if not team_name:
            return JsonResponse(data=general_message(400, 'team name is null', '参数错误'), status=400)

        start = request.GET.get('start')
        end = request.GET.get('end')
        team = team_services.get_tenant(tenant_name=team_name)
        try:
            body = market_api.get_enterprise_receipt_orders(team.tenant_id, team.enterprise_id, start, end)
            data = body["data"]
            result = general_message(200, 'success', '查询成功', list=data['list'])
        except Exception as e:
            logger.exception(e)
            result = general_message(500, 'proxy receipt api failed', '获取未开发票订单接口调用失败')
        return JsonResponse(data=result, status=result["code"])


class EnterReceiptConfirmAPIView(JWTAuthApiView):
    def post(self, request):
        team_name = request.data.get('team_name', None)
        if not team_name:
            return JsonResponse(data=general_message(400, 'team name is null', '参数错误'), status=400)

        orders = request.data.get('orders')
        data = {'order_nos': orders.split(',')}
        team = team_services.get_tenant(tenant_name=team_name)
        try:
            data = market_api.confirm_enterprise_receipts(team.tenant_id, team.enterprise_id, data)
            result = general_message(200, 'success', '查询成功', bean=data)
        except Exception as e:
            logger.exception(e)
            result = general_message(500, 'proxy receipt api failed', '获取企业发票信息接口调用失败')
        return JsonResponse(data=result, status=result["code"])
