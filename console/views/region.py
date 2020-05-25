# -*- coding: utf8 -*-
import logging

from rest_framework.response import Response

from console.services.region_services import region_services
from console.services.team_services import team_services
from console.views.base import JWTAuthApiView
from console.views.base import RegionTenantHeaderView
from www.apiclient.marketclient import MarketOpenAPI
from www.utils.return_message import error_message
from www.utils.return_message import general_message

logger = logging.getLogger("default")
market_api = MarketOpenAPI()


class RegQuyView(RegionTenantHeaderView):
    def get(self, request, team_name, *args, **kwargs):
        """
        获取团队数据中心(详细)
        ---
        parameters:
            - name: team_name
              description: 当前团队名字
              required: true
              type: string
              paramType: path
        """
        try:
            code = 200
            region_name_list = region_services.get_region_all_list_by_team_name(team_name=team_name)
            result = general_message(code, "query the data center is successful.", "数据中心获取成功", list=region_name_list)
        except Exception as e:
            code = 500
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=code)


class RegUnopenView(RegionTenantHeaderView):
    def get(self, request, team_name, *args, **kwargs):
        """
        获取团队未开通的数据中心
        ---
        parameters:
            - name: team_name
              description: 当前团队名字
              required: true
              type: string
              paramType: path
        """
        code = 200
        unopen_regions = region_services.get_team_unopen_region(team_name=team_name)
        result = general_message(code, "query the data center is successful.", "数据中心获取成功", list=unopen_regions)
        return Response(result, status=code)


class OpenRegionView(RegionTenantHeaderView):
    def post(self, request, team_name, *args, **kwargs):
        """
        为团队开通数据中心
        ---
        parameters:
            - name: team_name
              description: 当前团队名字
              required: true
              type: string
              paramType: path
            - name: region_name
              description: 要开通的数据中心名称
              required: true
              type: string
              paramType: body
        """
        region_name = request.data.get("region_name", None)
        if not region_name:
            return Response(general_message(400, "params error", "参数异常"), status=400)
        team = team_services.get_tenant_by_tenant_name(team_name)
        if not team:
            return Response(general_message(404, "team is not found", "团队{0}不存在".format(team_name)), status=403)
        # is_admin = user_services.is_user_admin_in_current_enterprise(self.user, team.enterprise_id)
        # if not is_admin:
        #     return Response(
        #         general_message(403, "current user is not admin in current enterprise", "用户不为当前企业管理员"), status=403)
        code, msg, tenant_region = region_services.create_tenant_on_region(team_name, region_name)
        if code != 200:
            return Response(general_message(code, "open region error", msg), status=code)
        result = general_message(code, "success", "数据中心{0}开通成功".format(region_name))
        return Response(result, result["code"])

    def patch(self, request, team_name, *args, **kwargs):
        """
        为团队批量开通数据中心
        ---
        parameters:
            - name: team_name
              description: 当前团队名字
              required: true
              type: string
              paramType: path
            - name: region_names
              description: 要开通的数据中心名称 多个数据中心以英文逗号隔开
              required: true
              type: string
              paramType: body
        """
        region_names = request.data.get("region_names", None)
        if not region_names:
            result = general_message(400, "params error", "参数异常")
            return Response(result, result["code"])

        team = team_services.get_tenant_by_tenant_name(team_name)
        if not team:
            return Response(general_message(404, "team is not found", "团队{0}不存在".format(team_name)), status=403)
        region_list = region_names.split(",")
        for region_name in region_list:
            code, msg, tenant_region = region_services.create_tenant_on_region(team_name, region_name)
            if code != 200:
                return Response(general_message(code, "open region error", msg), status=code)
        result = general_message(200, "success", "批量开通数据中心成功")
        return Response(result, result["code"])

    def delete(self, request, team_name, *args, **kwargs):
        """
        为团队关闭数据中心
        ---
        parameters:
            - name: team_name
              description: 当前团队名字
              required: true
              type: string
              paramType: path
            - name: region_name
              description: 要关闭的数据中心名称
              required: true
              type: string
              paramType: body
        """
        region_name = request.data.get("region_name", None)
        if not region_name:
            return Response(general_message(400, "params error", "参数异常"), status=400)
        team = team_services.get_tenant_by_tenant_name(team_name)
        if not team:
            return Response(general_message(404, "team is not found", "团队{0}不存在".format(team_name)), status=403)
        code, msg, tenant_region = region_services.close_tenant_on_region(team_name, region_name)
        if code != 200:
            return Response(general_message(code, "open region error", msg), status=code)
        result = general_message(code, "success", "数据中心{0}关闭成功".format(region_name))
        return Response(result, result["code"])


class QyeryRegionView(JWTAuthApiView):
    def get(self, request, *args, **kwargs):
        """
        获取当前可用全部数据中心
        ---

        """
        regions = region_services.get_open_regions()
        result = general_message(200, 'query success', '数据中心获取成功', list=[r.to_dict() for r in regions])
        return Response(result, status=200)


class GetRegionPublicKeyView(RegionTenantHeaderView):
    def get(self, request, region_name, *args, **kwargs):
        """
        获取指定数据中心的Key
        ---

        """
        key = region_services.get_public_key(self.team, region_name)
        result = general_message(200, 'query success', '数据中心key获取成功', bean=key)
        return Response(result, status=200)


class RegionResourceDetailView(JWTAuthApiView):
    def get(self, request, *args, **kwargs):
        """
        公有云数据中心资源详情
        ---
        parameters:
            - name: enterprise_id
              description: 企业id
              required: true
              type: string
              paramType: path
            - name: team_name
              description: 当前团队名字
              required: true
              type: string
              paramType: query
            - name: region
              description: 数据中心名称
              required: true
              type: string
              paramType: query
        """
        try:
            team_name = request.GET.get("team_name", None)
            region = request.GET.get("region", None)

            team = team_services.get_tenant_by_tenant_name(tenant_name=team_name, exception=True)
            if not team:
                return Response(general_message(404, "team not found", "指定团队不存在"), status=404)

            res, data = market_api.get_enterprise_regions_resource(
                tenant_id=team.tenant_id, enterprise_id=team.enterprise_id, region=region)
            if isinstance(data, list):
                result = general_message(200, "success", "查询成功", list=data)
            elif isinstance(data, dict):
                result = general_message(200, "success", "查询成功", bean=data)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class RegionResPrice(JWTAuthApiView):
    def post(self, request, region_name):
        """资源费用计算"""

        team_name = request.data.get('team_name')

        team = team_services.get_tenant_by_tenant_name(tenant_name=team_name, exception=True)
        if not team:
            return Response(general_message(404, "team not found", "指定团队不存在"), status=404)

        try:
            memory = int(request.data.get('memory', 0))
            disk = int(request.data.get('disk', 0))
            rent_time = request.data.get('rent_time')

            ret, msg, status = market_api.get_region_res_price(region_name, team.tenant_id, team.enterprise_id, memory, disk,
                                                               rent_time)

            return Response(status=status, data=general_message(status, msg, msg, ret))
        except Exception as e:
            logger.exception(e)
            data = general_message(500, "cal fee error", "无法计算费用")
            return Response(status=500, data=data)


class RegionResPurchage(JWTAuthApiView):
    def post(self, request, region_name):
        """资源购买"""

        team_name = request.data.get('team_name')

        team = team_services.get_tenant_by_tenant_name(tenant_name=team_name, exception=True)
        if not team:
            return Response(general_message(404, "team not found", "指定团队不存在"), status=404)

        try:
            memory = int(request.data.get('memory', 0))
            disk = int(request.data.get('disk', 0))
            rent_time = request.data.get('rent_time')

            ret, msg, status = market_api.buy_region_res(region_name, team.tenant_id, team.enterprise_id, memory, disk,
                                                         rent_time)
            if status == 10408:
                return Response(status=412, data=general_message(status, msg, msg, ret))
            return Response(status=status, data=general_message(status, msg, msg, ret))
        except Exception as e:
            logger.exception(e)
            data = general_message(500, "buy res error", "资源购买失败")
            return Response(status=500, data=data)
