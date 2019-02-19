# -*- coding: utf8 -*-
"""
  Created by leon on 19/2/13.
"""
import os
import base64
import pickle
from django.views.decorators.cache import never_cache
from rest_framework.response import Response

from console.exception.main import ResourceNotEnoughException
from console.views.base import RegionTenantHeaderView
from www.decorator import perm_required
import logging
from www.utils.return_message import general_message, error_message
from console.services.app import app_service
from console.services.group_service import group_service
from console.repositories.deploy_repo import deploy_repo
from console.views.app_config.base import AppBaseView
from console.repositories.app_config import service_endpoints_repo
from www.apiclient.regionapi import RegionInvokeApi


logger = logging.getLogger("default")
region_api = RegionInvokeApi()


class ThirdPartyServiceCreateView(RegionTenantHeaderView):
    @never_cache
    @perm_required('create_service')
    def post(self, request, *args, **kwargs):
        """
        创建三方服务

        """

        group_id = request.data.get("group_id", -1)
        service_cname = request.data.get("service_cname", None)
        endpoints = request.data.get("endpoints", None)
        endpoints_type = request.data.get("endpoints_type", None)

        try:
            if not service_cname:
                return Response(general_message(400, "service_cname is null", "服务名未指明"), status=400)
            if not endpoints and endpoints_type != "api":
                return Response(general_message(400, "end_point is null", "end_point未指明"), status=400)

            code, msg_show, new_service = app_service.create_third_party_app(self.response_region, self.tenant,
                                                                             self.user, service_cname,
                                                                             endpoints, endpoints_type)
            if code != 200:
                return Response(general_message(code, "service create fail", msg_show), status=code)

            # 添加服务所在组
            code, msg_show = group_service.add_service_to_group(self.tenant, self.response_region, group_id,
                                                                new_service.service_id)
            if code != 200:
                logger.debug("service.create", msg_show)
            bean = new_service.to_dict()

            if endpoints_type == "api":
                # 生成秘钥
                deploy = deploy_repo.get_deploy_relation_by_service_id(service_id=new_service.service_id)
                api_secret_key = pickle.loads(base64.b64decode(deploy)).get("secret_key")
                # 从环境变量中获取域名，没有在从请求中获取
                host = os.environ.get('DEFAULT_DOMAIN', request.get_host())
                api_url = "http://" + host + "/console/" + "teams/{0}/third_party/".format(self.tenant.tenant_name) + new_service.service_alias
                bean["api_service_key"] = api_secret_key
                bean["url"] = api_url

            result = general_message(200, "success", "创建成功", bean=bean)
        except ResourceNotEnoughException as re:
            logger.exception(re)
            return Response(general_message(10406, "resource is not enough", re.message), status=412)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


# 三方服务中api注册方式回调接口
class ThirdPartyServiceApiView(AppBaseView):
    def post(self, request, *args, **kwargs):
        secret_key = request.data.get("secret_key")
        # 加密
        deploy_key = deploy_repo.get_secret_key_by_service_id(service_id=self.service.service_id)
        deploy_key_decode = pickle.loads(base64.b64decode(deploy_key)).get("secret_key")
        if secret_key != deploy_key_decode:
            result = general_message(400, "failed", "密钥错误")
            return Response(result, status=400)
        endpoints_list = request.data.get("endpoints_list", None)
        if not endpoints_list:
            return Response(general_message(400, "end_point is null", "end_point未指明"), status=400)
        try:
            endpoint = service_endpoints_repo.get_service_endpoints_by_service_id(self.service.service_id)
            endpoint.endpoints_info = endpoints_list
            endpoint.save()
            body = dict()
            body["static"] = endpoint.endpoints_info
            data = {"endpoints": body}
            region_api.add_third_party_service_endpoints(self.response_region, self.tenant.tenant_name, self.service.service_alias,
                                                  data)
            result = general_message(200, "success", "操作成功")
        except Exception as e:
            logger.exception(e)
            endpoint = service_endpoints_repo.get_service_endpoints_by_service_id(self.service.service_id)
            endpoint.endpoints_info = ''
            endpoint.save()
            result = error_message(e.message)
        return Response(result, status=result["code"])


# 三方服务中api注册方式重置秘钥
class ThirdPartyUpdateSecretKey(AppBaseView):
    def put(self, request, *args, **kwargs):
        try:
            key_repo = deploy_repo.get_service_key_by_service_id(service_id=self.service.service_id)
            if not key_repo:
                return Response(general_message(412, "service_key is null", "秘钥不存在"), status=412)
            key_repo.delete()
            # 生成秘钥
            deploy = deploy_repo.get_deploy_relation_by_service_id(service_id=self.service.service_id)
            api_secret_key = pickle.loads(base64.b64decode(deploy)).get("secret_key")
            result = general_message(200, "success", "重置成功", bean={"api_service_key": api_secret_key})
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result)
