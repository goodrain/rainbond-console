# -*- coding: utf-8 -*-
import logging

from console.services.team_services import team_services
from console.utils.timeutil import current_time_to_str
from console.views.base import RegionTenantHeaderView, JWTAuthApiView
from www.apiclient.marketclient import MarketOpenAPI
from www.utils.return_message import general_message, error_message
from rest_framework.response import Response

logger = logging.getLogger("default")
open_api = MarketOpenAPI()


class EnterpriseAccountInfoView(JWTAuthApiView):
    def get(self, request, team_name, *args, **kwargs):
        """
        企业账户信息查询接口
        ---
        parameters:
            - name: team_name
              description: 当前团队名字
              required: true
              type: string
              paramType: path
        """
        try:
            team = team_services.get_tenant_by_tenant_name(tenant_name=team_name, exception=True)
            res, data = open_api.get_enterprise_account_info(tenant_id=team.tenant_id,
                                                             enterprise_id=team.enterprise_id)
            if res["status"] == 200:
                code = 200
                result = general_message(code=code, msg="corporate account information is successful.",
                                         msg_show="企业账户信息获取成功", bean=data)
            else:
                code = 400
                result = general_message(code=code, msg="corporate account information failed",
                                         msg_show="企业账户信息获取失败")
        except Exception as e:
            code = 500
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=code)


class EnterpriseTeamFeeView(RegionTenantHeaderView):
    def get(self, request, *args, **kwargs):
        """
        企业资源费用账单查询接口
        ---
        parameters:
            - name: team_name
              description: 当前团队名字
              required: true
              type: string
              paramType: path
            - name: date
              description: 日期(格式：2018-01-30)
              required: true
              type: string
              paramType: query
        """
        try:
            default_time = current_time_to_str()
            date = request.GET.get("date", default_time)
            if not date:
                return Response(data=general_message(400, "date query failed", "日期接收失败"), status=400)
            res, data = open_api.get_enterprise_team_fee(region=self.response_region,
                                                         enterprise_id=self.team.enterprise_id,
                                                         team_id=self.team.tenant_id, date=date)
            if res["status"] == 200:
                code = 200
                result = general_message(code=code, msg="enterprise expense account query is successful.",
                                         msg_show="企业资源费用账单查询成功", list=data)
            else:
                code = 400
                result = general_message(code=code, msg="enterprise expense account query failed.",
                                         msg_show="企业资源费用账单查询失败")
        except Exception as e:
            code = 500
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=code)
