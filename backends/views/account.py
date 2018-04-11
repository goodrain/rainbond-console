# -*- coding: utf8 -*-

import logging
import os

from django.conf import settings
from rest_framework.response import Response

from backends.services.enterpriseservice import enterprise_service
from backends.services.resultservice import *
from backends.services.userservice import user_service
from backends.views.base import BaseAPIView
from console.views.base import AlowAnyApiView
from www.apiclient.baseclient import client_auth_service
from www.services import enterprise_svc
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User as TokenAuthUser
from console.services.enterprise_services import enterprise_services

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


class AuthUserTokenView(AlowAnyApiView):
    def post(self, request, *args, **kwargs):
        """
        生成访问token
        ---
        parameters:
            - name: username
              description: 用户名
              required: true
              type: string
              paramType: path
            - name: password
              description: 密码
              required: true
              type: string
              paramType: form
        """
        try:
            username = request.data.get("username", None)
            password = request.data.get("password", None)
            if not username or not password:
                return Response(generate_result(
                    "1003", "params error", "参数错误"))
            if TokenAuthUser.objects.all():
                return Response(generate_result(
                    "0000", "auth user already generate", "验证的用户信息已生成"))
            app_user = TokenAuthUser.objects.create(username=username)
            app_user.set_password(password)
            app_user.is_staff = True
            app_user.is_superuser = True
            app_user.save()
            token = Token.objects.create(user=app_user)
            result = generate_result("0000", "success", "验证用户信息创建成功 token为{0}".format(token.key))
        except Exception as e:
            logger.exception(e)
            result = generate_error_result()
        return Response(result)


class AllEnterpriseView(BaseAPIView):
    def get(self, request):
        """
        查询企业信息
        ---
        """
        try:
            enterprise = enterprise_services.get_enterprise_first()
            is_enterprise_exist = False
            if enterprise:
                is_enterprise_exist = True
                enterprise_bean = enterprise.to_dict()
                rt_bean = {"is_enterprise_exist": is_enterprise_exist, "enterprise_info": enterprise_bean}
                msg_show = "查询成功，云帮已有企业信息已存在"
            else:
                rt_bean = {"is_enterprise_exist": is_enterprise_exist, "enterprise_info": None}
                msg_show = "查询成功，云帮没有企业信息，可以初始化"
            result = generate_result("0000", "success", msg_show, rt_bean)
        except Exception as e:
            logger.exception(e)
            result = generate_error_result()
        return Response(result)

    def post(self, request):
        """
        添加企业信息
        ---
        parameters:
            - name: enterprise_id
              description: 企业id
              required: true
              type: string
              paramType: form
            - name: enterprise_alias
              description: 企业别名
              required: true
              type: string
              paramType: form
        """
        try:
            enterprise_id = request.data.get("enterprise_id", None)
            enterprise_alias = request.data.get("enterprise_alias", None)
            if not enterprise_id or not enterprise_alias:
                return Response(generate_result("1003", "params error", "参数错误"))
            enter = enterprise_services.get_enterprise_by_enterprise_id(enterprise_id)
            if enter:
                return Response(generate_result("1003", "params error", "企业id:{0}已存在".format(enterprise_id)))
            enterprise = enterprise_services.create_enterprise("", enterprise_alias)
            result = generate_result("0000", "add enterprise success", "添加信息成功", enterprise.to_dict())

        except Exception as e:
            logger.exception(e)
            result = generate_error_result()
        return Response(result)
