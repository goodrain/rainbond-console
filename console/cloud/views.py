# -*- coding: utf8 -*-
import logging

from rest_framework.response import Response

from console.views.base import CloudEnterpriseCenterView
from www.utils.return_message import general_message

logger = logging.getLogger("default")


class EnterpriseSubscribe(CloudEnterpriseCenterView):
    def get(self, request, enterprise_id, *args, **kwargs):
        rst = self.oauth_instance.get_ent_subscribe(eid=enterprise_id)
        result = general_message(
            200, "success", None, bean=rst.to_dict())
        return Response(result, status=200)


class EnterpriseOrdersCLView(CloudEnterpriseCenterView):
    def get(self, request, enterprise_id, *args, **kwargs):
        data = []
        order_list = self.oauth_instance.list_ent_order(eid=enterprise_id)
        for order in order_list:
            data.append(order.to_dict())
        result = general_message(
            200, "success", None, list=data)
        return Response(result, status=200)

    def post(self, request, enterprise_id, *args, **kwargs):
        data = request.data
        order = self.oauth_instance.create_ent_order(eid=enterprise_id, body=data)
        result = general_message(200, "success", None, bean=order.to_dict())
        return Response(result, status=200)


class EnterpriseOrdersRView(CloudEnterpriseCenterView):
    def get(self, request, enterprise_id, order_id, *args, **kwargs):
        order = self.oauth_instance.get_ent_order(eid=enterprise_id, order_id=order_id)
        result = general_message(
            200, "success", None, bean=order.to_dict())
        return Response(result, status=200)


class BankInfoView(CloudEnterpriseCenterView):
    def get(self, request, *args, **kwargs):
        bank = self.oauth_instance.get_bank_info()
        result = general_message(200, "success", None, bean=bank.to_dict())
        return Response(result, status=200)
