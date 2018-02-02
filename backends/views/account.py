# -*- coding: utf8 -*-

import logging
import os

from django.conf import settings
from rest_framework.response import Response

from api.views.base import BaseAPIView
from backends.services.enterpriseservice import enterprise_service
from backends.services.resultservice import *
from backends.services.userservice import user_service
from www.apiclient.baseclient import client_auth_service
from www.services import enterprise_svc

logger = logging.getLogger("default")


class AccountCreateView(BaseAPIView):
    def post(self, request, *args, **kwargs):
        """
        管理后台初始化云帮账户

        ---
        parameters:
            - name: body
              description: json内容
              required: true
              type: string
              paramType: body

        """
        result = {}
        try:
            user_info = request.data.get("user_info")
            enterprise_info = request.data.get("enterprise_info")
            username = user_info["username"]
            password = user_info["password"]
            email = user_info["email"]
            phone = user_info["phone"]
            eid = enterprise_info["eid"]
            name = enterprise_info["name"]
            is_active = enterprise_info["is_active"]
            logger.debug("user info {0} enterprise info {1}".format(user_info, enterprise_info))
            is_user_exist = user_service.is_user_exist(username)
            if is_user_exist:
                result = generate_result("1002", "user exist", "用户已存在")
                return Response(result)
            if_ent_exist = enterprise_service.is_enterprise_exist(name)
            if if_ent_exist:
                result = generate_result("1004", "exterprise exist", "企业已存在")
                return Response(result)
            logger.debug("create tenant enterprise")
            # 创建企业
            enterprise = enterprise_service.create_enterprise(eid, name, name, "", is_active)
            # 创建用户
            logger.debug("create tenant user")
            user = user_service.create_user(username, password, email or '', phone or '', enterprise.enterprise_id,
                                            "backend")
            logger.debug("create tenant and init tenant")
            enterprise_svc.create_and_init_tenant(user_id=user.user_id, enterprise_id=user.enterprise_id)
            user.is_active = True
            user.save()
            result = generate_result("0000", "success", "初始化成功")

        except Exception as e:
            logger.exception(e)
            result = generate_error_result()
        return Response(result)


class TenantEnterpriseView(BaseAPIView):
    def put(self, request, enterprise_id, *args, **kwargs):
        """
        更新企业信息
        ---
        parameters:
            - name: enterprise_id
              description: 企业ID
              required: true
              type: string
              paramType: path
            - name: market_client_id
              description: 云市客户端id
              required: true
              type: string
              paramType: form
            - name: market_client_token
              description: 云市客户端token
              required: true
              type: string
              paramType: form
        """
        try:
            market_client_id = request.data.get("market_client_id")
            market_client_token = request.data.get("market_client_token")
            domain = os.getenv('GOODRAIN_APP_API', settings.APP_SERVICE_API["url"])
            is_success = client_auth_service.save_market_access_token(enterprise_id, domain, market_client_id,
                                                                      market_client_token)
            if is_success:
                result = generate_result("0000", "success", "企业{0}信息更新成功".format(enterprise_id))
            else:
                result = generate_result("7878", "enterprise not exist", "企业{0} 信息不存在".format(enterprise_id))
        except Exception as e:
            logger.exception(e)
            result = generate_error_result()
        return Response(result)
