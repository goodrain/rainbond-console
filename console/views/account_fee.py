# -*- coding: utf-8 -*-
import logging

from rest_framework.response import Response

from console.services.region_services import region_services
from console.services.team_services import team_services
from console.utils.timeutil import current_time_to_str
from console.views.base import JWTAuthApiView
from www.apiclient.marketclient import MarketOpenAPI
from www.utils.return_message import general_message, error_message
from console.services.enterprise_services import enterprise_services

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
                res, data = market_api.get_enterprise_account_info(tenant_id=team.tenant_id, enterprise_id=team.enterprise_id)
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
                                                                    team_id=team.tenant_id,
                                                                    date=date)
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

                result = general_message(200, "success", "查询成功", bean=bean, list=rt_list)
            except Exception as e:
                logger.exception(e)
                result = general_message(400, "enterprise expense account query failed.", "企业资源费用账单查询失败")
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class EnterpriseRechargeRecordsView(JWTAuthApiView):
    def get(self, request, team_name):
        """
        查询企业的充值记录
        ---
        parameters:
            - name: start
              description: 开始时间
              required: true
              type: string
              paramType: query
            - name: end
              description: 结束时间
              required: true
              type: string
              paramType: query
            - name: page
              description: 页数(默认第一页)
              required: false
              type: string
              paramType: query
            - name: page_size
              description: 每页展示个数(默认10个)
              required: false
              type: string
              paramType: query
        """
        try:
            start_time = request.GET.get("start")
            end_time = request.GET.get("end")
            page = request.GET.get("page", 1)
            page_size = request.GET.get("page_size", 10)
            team = team_services.get_tenant_by_tenant_name(team_name)
            if not team:
                return Response(general_message(404, "team not found", "团队{0}不存在".format(team_name)), status=404)

            enterprise = enterprise_services.get_enterprise_by_enterprise_id(team.enterprise_id)
            res, data = market_api.get_enterprise_recharge_records(team.tenant_id, enterprise.enterprise_id, start_time,
                                                                   end_time, page, page_size)

            result = general_message(200,
                                     "get recharge record success",
                                     "查询成功",
                                     list=data["data"]["list"],
                                     total=data["data"]["total"])

        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class EnterpriseAllRegionFeeView(JWTAuthApiView):
    def get(self, request, team_name):
        """
        企业所有信息
        ---
        parameters:
            - name: date
              description: 日期(格式：2018-01-30)
              required: true
              type: string
              paramType: query
        """
        try:
            default_time = current_time_to_str()
            date = request.GET.get("date", default_time)
            team = team_services.get_tenant_by_tenant_name(team_name)
            if not team:
                return Response(general_message(404, "team not exist", "指定的团队不存在"), status=404)

            regions = region_services.get_regions_by_enterprise_id(team.enterprise_id)
            total_list = []
            for region in regions:
                try:
                    res, dict_body = market_api.get_enterprise_region_fee(region=region.region_name,
                                                                          enterprise_id=team.enterprise_id,
                                                                          team_id=team.tenant_id,
                                                                          date=date)

                    rt_list = dict_body["data"]["list"]
                    enter_total = {}
                    for rt in rt_list:
                        bean = enter_total.get(rt['time'])
                        if bean:
                            if rt["total_fee"] > 0:
                                bean['disk_fee'] += rt["disk_fee"]
                                bean['disk_limit'] += rt["disk_limit"]
                                bean['disk_over'] += rt["disk_over"]
                                bean['disk_usage'] += rt["disk_usage"]
                                bean['memory_fee'] += rt["memory_fee"]
                                bean['memory_limit'] += rt["memory_limit"]
                                bean['memory_over'] += rt["memory_over"]
                                bean['memory_usage'] += rt["memory_usage"]
                                bean['net_fee'] += rt["net_fee"]
                                bean['net_usage'] += rt["net_usage"]
                                bean['total_fee'] += rt["total_fee"]
                        else:
                            if rt["total_fee"] > 0:
                                rt["region"] = region.region_alias
                                enter_total[rt['time']] = rt

                    total_list[0:0] = [v for v in enter_total.values() if v["total_fee"] > 0]

                except Exception as e:
                    logger.exception(e)
                    continue
            result_list = sorted(total_list, key=lambda b: (b['time'], b['region']), reverse=True)
            result = general_message(200, "success", "查询成功", list=result_list)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class EnterprisePurchaseDetails(JWTAuthApiView):
    def get(self, request, team_name):
        """
        企业购买明细
        ---
        parameters:
            - name: start
              required: true
              type: string
              location: 'query'
              description: 开始时间
            - name: end
              required: true
              type: string
              location: 'query'
              description: 结束时间
            - name: page
              required: true
              type: string
              location: 'query'
              description: 第几页
            - name: page_size
              required: true
              type: string
              location: 'query'
              description: 每页条数
        """
        try:
            start = request.GET.get('start')
            end = request.GET.get('end')
            page = request.GET.get('page', 1)
            page_size = request.GET.get('page_size', 10)
            team = team_services.get_tenant_by_tenant_name(team_name)
            if not team:
                return Response(general_message(404, "team not exist", "指定的团队不存在"), status=404)
            total = 0
            result_list = []
            try:
                res, dict_body = market_api.get_enterprise_purchase_detail(team.tenant_id, team.enterprise_id, start, end, page,
                                                                           page_size)
                result_list = dict_body["data"]["list"]
                total = dict_body["data"]["total"]
            except Exception as ex:
                logger.exception(ex)
            result = general_message(200, "success", "查询成功", list=result_list, total=total)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])
