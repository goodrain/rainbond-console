# -*- coding: utf8 -*-
import logging

from console.exception.main import ServiceHandleException
from console.services.region_services import region_services
from console.services.team_services import team_services
from console.views.base import (JWTAuthApiView, RegionTenantHeaderView, TenantHeaderView)
from rest_framework.response import Response
from www.apiclient.marketclient import MarketOpenAPI
from www.apiclient.regionapi import RegionInvokeApi
from www.apiclient.regionapibaseclient import RegionApiBaseHttpClient
from www.utils.return_message import error_message, general_message

region_api = RegionInvokeApi()
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


class RegUnopenView(TenantHeaderView):
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
        team = team_services.get_tenant_by_tenant_name(team_name)
        if not team:
            result = general_message(404, "team no found", "团队不存在")
            return Response(result, status=code)
        unopen_regions = region_services.get_team_unopen_region(team_name, team.enterprise_id)
        result = general_message(code, "query the data center is successful.", "数据中心获取成功", list=unopen_regions)
        return Response(result, status=code)


class OpenRegionView(TenantHeaderView):
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
        region_services.create_tenant_on_region(self.enterprise.enterprise_id, team_name, region_name, team.namespace)
        result = general_message(200, "success", "数据中心{0}开通成功".format(region_name))
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
            region_services.create_tenant_on_region(self.enterprise.enterprise_id, team_name, region_name, team.namespace)
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
        region_services.delete_tenant_on_region(self.enterprise.enterprise_id, team_name, region_name, self.user)
        result = general_message(200, "success", "团队关闭数据中心{0}成功".format(region_name))
        return Response(result, result["code"])


class QyeryRegionView(JWTAuthApiView):
    def get(self, request, enterprise_id, *args, **kwargs):
        """
        获取当前可用全部数据中心
        ---

        """
        regions = region_services.get_open_regions(enterprise_id)
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


class GetRegionFeature(RegionTenantHeaderView):
    def get(self, request, region_name, *args, **kwargs):
        """
        获取指定数据中心的授权功能列表
        ---

        """
        features = region_services.get_region_license_features(self.team, region_name)
        result = general_message(200, 'query success', '集群授权功能获取成功', list=features)
        return Response(result, status=200)


class PublicRegionListView(JWTAuthApiView):
    def get(self, request, *args, **kwargs):
        """
        团队管理员可以获取公有云的数据中心列表
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
        """
        try:
            team_name = request.GET.get("team_name", None)
            if not team_name:
                return Response(general_message(400, "params error", "参数错误"), status=400)
            perm_list = team_services.get_user_perm_identitys_in_permtenant(user_id=request.user.user_id, tenant_name=team_name)

            role_name_list = team_services.get_user_perm_role_in_permtenant(user_id=request.user.user_id, tenant_name=team_name)
            perm = "owner" not in perm_list and "admin" not in perm_list
            if perm and "owner" not in role_name_list and "admin" not in role_name_list:
                code = 400
                result = general_message(code, "no identity", "您不是owner或admin，没有权限做此操作")
                return Response(result, status=code)

            team = team_services.get_tenant_by_tenant_name(tenant_name=team_name, exception=True)
            res, data = market_api.get_public_regions_list(tenant_id=team.tenant_id, enterprise_id=team.enterprise_id)
            if res["status"] == 200:
                code = 200
                result = general_message(code, "query the data center is successful.", "公有云数据中心获取成功", list=data)
            else:
                code = 400
                result = general_message(code, msg="query the data center failed", msg_show="公有云数据中心获取失败")
        except Exception as e:
            code = 500
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=code)


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

            res, data = market_api.get_enterprise_regions_resource(tenant_id=team.tenant_id,
                                                                   enterprise_id=team.enterprise_id,
                                                                   region=region)
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


class MavenSettingView(RegionTenantHeaderView):
    def get(self, request, enterprise_id, region_name, *args, **kwargs):
        onlyname = request.GET.get("onlyname", True)
        res, body = region_api.list_maven_settings(enterprise_id, region_name)
        redata = body.get("list")
        if redata and isinstance(redata, list) and (onlyname is True or onlyname == "true"):
            newdata = []
            for setting in redata:
                newdata.append({"name": setting["name"], "is_default": setting["is_default"]})
            redata = newdata
        result = general_message(200, 'query success', '数据中心Maven获取成功', list=redata)
        return Response(status=200, data=result)

    def post(self, request, enterprise_id, region_name, *args, **kwargs):
        try:
            res, body = region_api.add_maven_setting(enterprise_id, region_name, request.data)
            result = general_message(200, 'query success', '添加成功', bean=body.get("bean"))
        except RegionApiBaseHttpClient.CallApiError as exc:
            if exc.message.get("httpcode") == 400:
                result = general_message(400, 'maven setting name is exist', '配置名称已存在')
            else:
                logger.exception(exc)
                result = general_message(500, 'add maven setting failure', '配置添加失败')
        except ServiceHandleException as e:
            if e.status_code == 400:
                result = general_message(400, 'maven setting name is exist', '配置名称已存在')
            else:
                logger.exception(e)
                result = general_message(500, 'add maven setting failure', '配置添加失败')
        return Response(status=result["code"], data=result)


class MavenSettingRUDView(RegionTenantHeaderView):
    def get(self, request, enterprise_id, region_name, name, *args, **kwargs):
        try:
            res, body = region_api.get_maven_setting(enterprise_id, region_name, name)
            result = general_message(200, 'query success', '获取成功', bean=body.get("bean"))
        except RegionApiBaseHttpClient.CallApiError as exc:
            if exc.message.get("httpcode") == 404:
                result = general_message(404, 'maven setting is not exist', '配置不存在')
            else:
                logger.exception(exc)
                result = general_message(500, 'add maven setting failure', '获取配置失败')
        except ServiceHandleException as e:
            if e.status_code == 404:
                result = general_message(404, 'maven setting is not exist', '配置不存在')
            else:
                logger.exception(e)
                result = general_message(500, 'add maven setting failure', '获取配置失败')
        return Response(status=result["code"], data=result)

    def put(self, request, enterprise_id, region_name, name, *args, **kwargs):
        try:
            res, body = region_api.update_maven_setting(enterprise_id, region_name, name, request.data)
            result = general_message(200, 'update success', '修改成功', bean=body.get("bean"))
        except RegionApiBaseHttpClient.CallApiError as exc:
            if exc.message.get("httpcode") == 404:
                result = general_message(404, 'maven setting is not exist', '配置不存在')
            else:
                logger.exception(exc)
                result = general_message(500, 'update maven setting failure', '更新配置失败')
        except ServiceHandleException as e:
            if e.status_code == 404:
                result = general_message(404, 'maven setting is not exist', '配置不存在')
            else:
                logger.exception(e)
                result = general_message(500, 'update maven setting failure', '更新配置失败')
        return Response(status=result["code"], data=result)

    def delete(self, request, enterprise_id, region_name, name, *args, **kwargs):
        try:
            res, body = region_api.delete_maven_setting(enterprise_id, region_name, name)
            result = general_message(200, 'delete success', '删除成功', bean=body.get("bean"))
        except RegionApiBaseHttpClient.CallApiError as exc:
            if exc.message.get("httpcode") == 404:
                result = general_message(404, 'maven setting is not exist', '配置不存在')
            else:
                logger.exception(exc)
                result = general_message(500, 'add maven setting failure', '删除配置失败')
        except ServiceHandleException as e:
            if e.status_code == 404:
                result = general_message(404, 'maven setting is not exist', '配置不存在')
            else:
                logger.exception(e)
                result = general_message(500, 'add maven setting failure', '删除配置失败')
        return Response(status=result["code"], data=result)
