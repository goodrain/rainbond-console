# -*- coding: utf-8 -*-
import logging

from rest_framework.response import Response

from console.services.team_services import team_services
from console.utils.timeutil import current_time_to_str
from console.views.base import JWTAuthApiView
from www.apiclient.marketclient import MarketOpenAPI
from www.utils.return_message import general_message, error_message

logger = logging.getLogger("default")
market_api = MarketOpenAPI()


class EnterpriseAccountInfoView(JWTAuthApiView):
    def get(self, request, *args, **kwargs):
        """
        企业账户信息查询接口
        ---
        parameters:
            - name: enterprise_id
              description: 企业ID
              required: true
              type: string
              paramType: path
            - name: team_name
              description: 团队名称
              required: true
              type: string
              paramType: query
        """
        try:
            team_name = request.GET.get("team_name", None)
            if not team_name:
                return Response(general_message(400, "team name is null", "参数错误"), status=400)

            team = team_services.get_tenant_by_tenant_name(tenant_name=team_name, exception=True)
            try:
                res, data = market_api.get_enterprise_account_info(tenant_id=team.tenant_id,
                                                                   enterprise_id=team.enterprise_id)
                result = general_message(200, "success", "查询成功", bean=data)
            except Exception as e:
                logger.exception(e)
                result = general_message(400, "corporate account information failed", "企业账户信息获取失败")
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class EnterpriseTeamFeeView(JWTAuthApiView):
    def get(self, request, team_name):
        """
        企业下某团队资源费用账单查询接口
        ---
        parameters:
            - name: date
              description: 日期(格式：2018-01-30)
              required: true
              type: string
              paramType: query
            - name: region
              description: 数据中心
              required: true
              type: string
              paramType: query
        """
        try:
            default_time = current_time_to_str()
            date = request.GET.get("date", default_time)
            region = request.GET.get("region", None)
            if not region:
                return Response(general_message(400, "region not specified", "数据中心未指定"), status=400)
            team = team_services.get_tenant_by_tenant_name(team_name)
            if not team:
                return Response(general_message(404, "team not exist", "指定的团队不存在"), status=404)

            try:
                res, dict_body = market_api.get_enterprise_team_fee(region=region,
                                                                    enterprise_id=team.enterprise_id,
                                                                    team_id=team.tenant_id, date=date)
                data_body = dict_body['data']
                if 'data' not in dict_body:
                    return Response(general_message(400, "{0}".format(data_body), "查询异常"), status=400)
                bean = dict()
                rt_list = []
                data_body = dict_body['data']
                if 'bean' in data_body and data_body['bean']:
                    bean = data_body['bean']
                elif 'list' in data_body and data_body['list']:
                    rt_list = data_body['list']

                result = general_message(200, "success", "查询成功",bean=bean, list=rt_list)
            except Exception as e:
                logger.exception(e)
                result = general_message(400, "enterprise expense account query failed.", "企业资源费用账单查询失败")
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])
