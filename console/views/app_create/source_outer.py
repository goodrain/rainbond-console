# -*- coding: utf8 -*-
"""
  Created by leon on 19/2/13.
"""
import os
import base64
import pickle
import json

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
from console.views.base import AlowAnyApiView


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
class ThirdPartyServiceApiView(AlowAnyApiView):
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
            api_endpoints_list = []
            for endpoints in endpoints_list:
                endpoints_dict = dict()
                endpoints_dict["status"] = 0
                endpoints_dict["endpoint"] = endpoints
                api_endpoints_list.append(endpoints_dict)

            endpoint = service_endpoints_repo.get_service_endpoints_by_service_id(self.service.service_id)
            endpoint.endpoints_info = api_endpoints_list
            endpoint.save()
            logger.debug('-------------endpoint.endpoints_info------------->{0}'.format(endpoint.endpoints_info))
            body = dict()
            body["static"] = api_endpoints_list
            data = {"endpoints": body}
            import json
            logger.debug('------------data------------>{0}'.format(json.dumps(data)))
            region_api.put_third_party_service_endpoints(self.response_region, self.tenant.tenant_name, self.service.service_alias,
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
class ThirdPartyUpdateSecretKeyView(AppBaseView):
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


# 三方服务pod信息
class ThirdPartyAppPodsView(AppBaseView):
    @never_cache
    @perm_required('manage_service_container')
    def get(self, request, *args, **kwargs):
        """
        获取三方服务实例信息
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 服务别名
              required: true
              type: string
              paramType: path
        """
        try:
            res, data = region_api.get_third_party_service_pods(self.service.service_region, self.tenant.tenant_name,
                                               self.service.service_alias)
            if res.status != 200:
                return Response(general_message(412, "region error", "数据中心查询失败"), status=412)
            endpoint_list = data["list"]
            bean = {"endpoint_num": len(endpoint_list)}

            result = general_message(200, "success", "查询成功", list=endpoint_list, bean=bean)

        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result)

    @never_cache
    @perm_required('tripartite_service_manage')
    def post(self, request, *args, **kwargs):
        """
        添加endpoint实例
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        ip = request.data.get("ip", None)
        is_online = request.data.get("is_online", True)
        if not ip:
            return Response(general_message(400, "end_point is null", "end_point未指明"), status=400)
        try:
            data = list()
            endpoint_dict = dict()
            endpoint_dict["ip"] = ip
            endpoint_dict["is_online"] = is_online
            data.append(endpoint_dict)
            res, body = region_api.post_third_party_service_endpoints(self.response_region, self.tenant.tenant_name,
                                                                     self.service.service_alias, data)
            # 返回暂定
            if res.status != 200:
                return Response(general_message(412, "region delete error", "数据中心删除失败"), status=412)
            result = general_message(200, "success", "删除成功")

        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result)

    @never_cache
    @perm_required('tripartite_service_manage')
    def delete(self, request, *args, **kwargs):
        """
        删除endpoint实例
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        ep_id = request.data.get("ep_id", None)
        if not ep_id:
            return Response(general_message(400, "end_point is null", "end_point未指明"), status=400)
        try:
            data = list()
            endpoints_list = ep_id.split("-")
            for endpoint in endpoints_list:
                endpoint_dict = dict()
                endpoint_dict["ep_id"] = endpoint
                data.append(endpoint_dict)
            res, body = region_api.delete_third_party_service_endpoints(self.response_region, self.tenant.tenant_name,
                                                         self.service.service_alias, data)
            # 返回暂定
            if res.status != 200:
                return Response(general_message(412, "region delete error", "数据中心删除失败"), status=412)
            result = general_message(200, "success", "删除成功")

        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result)

    @never_cache
    @perm_required('tripartite_service_manage')
    def put(self, request, *args, **kwargs):
        """
        修改实例上下线
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        is_online = request.data.get("is_online", True)
        ep_id = request.data.get("ep_id", None)
        if not ep_id:
            return Response(general_message(400, "end_point is null", "end_point未指明"), status=400)
        try:
            data = list()
            endpoint_dict = dict()
            endpoint_dict["ep_id"] = ep_id
            endpoint_dict["is_online"] = is_online
            data.append(endpoint_dict)
            res, body = region_api.put_third_party_service_endpoints(self.response_region, self.tenant.tenant_name,
                                                                     self.service.service_alias, data)
            logger.debug('-------res------->{0}'.format(res))
            logger.debug('=======body=======>{0}'.format(body))

            # 返回暂定
            if res.status != 200:
                return Response(general_message(412, "region delete error", "数据中心修改失败"), status=412)

            result = general_message(200, "success", "修改成功")

        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result)


# 三方服务健康检测
class ThirdPartyHealthzView(AppBaseView):
    @never_cache
    @perm_required('manage_service_container')
    def get(self, request, *args, **kwargs):
        """
        获取三方服务健康检测结果
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        try:
            res, data = region_api.get_third_party_service_health(self.service.service_region, self.tenant.tenant_name,
                                                   self.service.service_alias)

            if res.status != 200:
                return Response(general_message(412, "region error", "数据中心查询失败"), status=412)
            bean = data["bean"]

            result = general_message(200, "success", "查询成功", bean=bean)

        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result)

    @never_cache
    @perm_required('tripartite_service_manage')
    def put(self, request, *args, **kwargs):
        """
        编辑三方服务的健康检测
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        model = request.data.get("model", None)
        port = request.data.get("port", 0)
        time_internal = request.data.get("time_internal", 0)
        max_error_num = request.data.get("max_error_num", 0)
        action = request.data.get("action", None)
        path = request.data.get("path", None)
        if not model:
            return Response(general_message(400, "model is null", "检测方式未指明"), status=400)
        if not port:
            return Response(general_message(400, "address is null", "端口未指明"), status=400)
        try:
            detection_dict = {
                "model": model,
                "port": port,
                "time_internal": time_internal,
                "max_error_num": max_error_num,
                "action": action if action else '',
                "path": path if path else ''
            }

            res, data = region_api.put_third_party_service_health(self.service.service_region, self.tenant.tenant_name,
                                                   self.service.service_alias, detection_dict)

            msg = data["bean"]
            if msg != "success":
                return Response(general_message(412, "region error", "数据中心修改失败"), status=412)

            result = general_message(200, "success", "修改成功")

        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result)






