# -*- coding: utf8 -*-
import logging

from rest_framework.response import Response

from console.views.base import JWTAuthApiView
from console.services.user_services import user_services
from www.utils.return_message import general_message

logger = logging.getLogger("default")


class EnterpriseSubscribe(JWTAuthApiView):
    def get(self, request, enterprise_id, *args, **kwargs):
        oauth_instance, oauth_user = user_services.check_user_is_enterprise_center_user(request.user.user_id)
        if not oauth_instance:
            result = general_message(
                10405, "no found enterprise center oauth", "该用户未在企业中心认证，或认证过期")
            return Response(result, status=200)
        rst = oauth_instance.get_ent_subscribe(enterprise_id)
        if rst.code:
            result = general_message(
                rst.code, "failed", "无法获取企业订购信息")
            return Response(result, status=200)
        data = {
            "eid": rst.eid,
            "expired_time": rst.expired_time,
            "memory_limit": rst.memory_limit,
            "name": rst.name,
            "start_time": rst.start_time,
            "type": rst.type,
            "used_memory": rst.used_memory,
        }
        result = general_message(
            200, "success", None, bean=data)
        return Response(result, status=200)


class EnterpriseOrdersCLView(JWTAuthApiView):
    def get(self, request, enterprise_id, *args, **kwargs):
        data = []
        oauth_instance, oauth_user = user_services.check_user_is_enterprise_center_user(request.user.user_id)
        if not oauth_instance:
            result = general_message(
                400, "no found enterprise center oauth", "该用户未在企业中心认证，或认证过期")
            return Response(result, status=200)
        order_list = oauth_instance.list_ent_order(enterprise_id)
        if order_list.code:
            result = general_message(
                order_list.code, "failed", "无法获取企业订单信息")
            return Response(result, status=200)
        for order in order_list:
            data.append({
                "eid": order.eid,
                "create_time": order.create_time,
                "expired_time": order.expired_time,
                "final_price": order.final_price,
                "memory": order.memory,
                "months": order.months,
                "order_id": order.order_id,
                "origin_price": order.origin_price,
                "status": order.status,
                "unit_price": order.unit_price,
                "user_id": order.user_id,
            })
        result = general_message(
            200, "success", None, list=data)
        return Response(result, status=200)

    def post(self, request, enterprise_id, *args, **kwargs):
        data = request.data
        oauth_instance, oauth_user = user_services.check_user_is_enterprise_center_user(request.user.user_id)
        if not oauth_instance:
            result = general_message(
                400, "no found enterprise center oauth", "该用户未在企业中心认证，或认证过期")
            return Response(result, status=200)
        order = oauth_instance.create_ent_order(enterprise_id, data)
        if order.code:
            result = general_message(
                order.code, "failed", "创建订单失败")
            return Response(result, status=200)
        rst = {
            "eid": order.eid,
            "create_time": order.create_time,
            "expired_time": order.expired_time,
            "final_price": order.final_price,
            "memory": order.memory,
            "months": order.months,
            "order_id": order.order_id,
            "origin_price": order.origin_price,
            "status": order.status,
            "unit_price": order.unit_price,
            "user_id": order.user_id,
        }
        result = general_message(
            200, "success", None, bean=rst)
        return Response(result, status=200)


class EnterpriseOrdersRView(JWTAuthApiView):
    def get(self, request, enterprise_id, order_id, *args, **kwargs):
        oauth_instance, oauth_user = user_services.check_user_is_enterprise_center_user(request.user.user_id)
        if not oauth_instance:
            result = general_message(
                400, "no found enterprise center oauth", "该用户未在企业中心认证，或认证过期")
            return Response(result, status=200)
        order = oauth_instance.get_ent_order(enterprise_id, order_id)
        if order.code:
            result = general_message(
                order.code, "failed", "无法获取企业订单信息")
            return Response(result, status=200)
        rst = {
            "eid": order.eid,
            "create_time": order.create_time,
            "expired_time": order.expired_time,
            "final_price": order.final_price,
            "memory": order.memory,
            "months": order.months,
            "order_id": order.order_id,
            "origin_price": order.origin_price,
            "status": order.status,
            "unit_price": order.unit_price,
            "user_id": order.user_id,
        }
        result = general_message(
            200, "success", None, bean=rst)
        return Response(result, status=200)


class BankInfoView(JWTAuthApiView):
    def get(self, request, *args, **kwargs):
        oauth_instance, oauth_user = user_services.check_user_is_enterprise_center_user(request.user.user_id)
        if not oauth_instance:
            result = general_message(
                400, "no found enterprise center oauth", "该用户未在企业中心认证，或认证过期")
            return Response(result, status=200)
        bank = oauth_instance.get_bank_info()
        if bank.code:
            result = general_message(
                bank.code, "failed", "无法获取对公账单信息")
            return Response(result, status=200)
        rst = {
            "account": bank.account,
            "account_name": bank.account_name,
            "bank": bank.bank,
        }
        result = general_message(
            200, "success", None, bean=rst)
        return Response(result, status=200)
