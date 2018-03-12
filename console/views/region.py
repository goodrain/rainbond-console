# -*- coding: utf8 -*-

import logging

from rest_framework.response import Response

from backends.services.resultservice import *
from console.services.region_services import region_services
from console.services.team_services import team_services
from console.views.base import JWTAuthApiView, RegionTenantHeaderView
from www.apiclient.marketclient import MarketOpenAPI
from www.utils.return_message import error_message, general_message

logger = logging.getLogger("default")
open_api = MarketOpenAPI()


class RegSimQuyView(JWTAuthApiView):
    def get(self, request, team_name, *args, **kwargs):
        """
        获取团队数据中心(简表)
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
            region_name_list = region_services.get_region_list_by_team_name(request, team_name=team_name)
            result = generate_result(code, "query the data center is successful.", "数据中心获取成功", list=region_name_list)
        except Exception as e:
            code = 500
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=code)


class RegQuyView(JWTAuthApiView):
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
            region_name_list = region_services.get_region_name_list_by_team_name(team_name=team_name)
            result = generate_result(code, "query the data center is successful.", "数据中心获取成功", list=region_name_list)
        except Exception as e:
            code = 500
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=code)


class RegUnopenView(JWTAuthApiView):
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
        try:
            code = 200
            unopen_regions = region_services.get_team_unopen_region(team_name=team_name)
            result = generate_result(code, "query the data center is successful.", "数据中心获取成功", list=unopen_regions)
        except Exception as e:
            code = 500
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=code)


class OpenRegionView(JWTAuthApiView):
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
        try:
            region_name = request.data.get("region_name", None)
            if not region_name:
                return Response(general_message(400, "params error", "参数异常"), status=400)

            code, msg, tenant_region = region_services.open_team_region(team_name, region_name)
            if code != 200:
                return Response(general_message(code, "open region error", msg), status=code)
            result = generate_result(code, "success", "数据中心{0}开通成功".format(region_name))
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
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
        try:
            region_names = request.data.get("region_names", None)
            if not region_names:
                result = general_message(400, "params error", "参数异常")
                return Response(result, result["code"])
            region_list = region_names.split(",")
            for region_name in region_list:
                code, msg, tenant_region = region_services.open_team_region(team_name, region_name)
                if code != 200:
                    return Response(general_message(code, "open region error", msg), status=code)
            result = generate_result(200, "success", "批量开通数据中心成功")
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, result["code"])


class QyeryRegionView(JWTAuthApiView):
    def get(self, request, *args, **kwargs):
        """
        获取当前可用全部数据中心
        ---

        """
        try:
            regions = region_services.get_open_regions()
            result = general_message(200, 'query success', '数据中心获取成功', list=[r.to_dict() for r in regions])
            return Response(result, status=200)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=500)


class GetRegionPublicKeyView(RegionTenantHeaderView):
    def get(self, request, region_name, *args, **kwargs):
        """
        获取指定数据中心的Key
        ---

        """
        try:
            key = region_services.get_public_key(self.team, region_name)
            result = general_message(200, 'query success', '数据中心key获取成功', bean=key)
            return Response(result, status=200)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=500)


class PublicRegionListView(JWTAuthApiView):
    def get(self, request, team_name, *args, **kwargs):
        """
        团队管理员可以获取公有云的数据中心列表
        ---
        parameters:
            - name: team_name
              description: 当前团队名字
              required: true
              type: string
              paramType: path
        """
        try:
            perm_list = team_services.get_user_perm_identitys_in_permtenant(
                user_id=request.user.user_id,
                tenant_name=team_name
            )
            no_auth = ("owner" not in perm_list) and ("admin" not in perm_list)
            if no_auth:
                code = 400
                result = general_message(code, "no identity", "您不是管理员或拥有者，没有权限做此操作")
                return Response(result, status=code)
            else:
                team = team_services.get_tenant_by_tenant_name(tenant_name=team_name, exception=True)
                res, data = open_api.get_public_regions_list(tenant_id=team.tenant_id, enterprise_id=team.enterprise_id)
                if res["status"] == 200:
                    code = 200
                    result = generate_result(code, "query the data center is successful.", "公有云数据中心获取成功",
                                             list=data)
                else:
                    code = 400
                    result = general_message(code, msg="query the data center failed", msg_show="公有云数据中心获取失败")
        except Exception as e:
            code = 500
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=code)


class RegionResourceDetailView(RegionTenantHeaderView):
    def get(self, request, *args, **kwargs):
        """
        数据中心资源详情
        ---
        parameters:
            - name: team_name
              description: 当前团队名字
              required: true
              type: string
              paramType: path
        """
        try:
            res, data = open_api.get_enterprise_regions_resource(tenant_id=self.team.tenant_id,
                                                                 region=self.response_region,
                                                                 enterprise_id=self.team.enterprise_id)
            if res["status"] == 200:
                code = 200
                result = general_message(code=code, msg="query the region center resource is successful",
                                         msg_show="数据中心资源获取成功", bean=data)
            else:
                code = 400
                result = general_message(code=code, msg="query the region center resource failed",
                                         msg_show="数据中心资源获取失败")
        except Exception as e:
            code = 500
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=code)
