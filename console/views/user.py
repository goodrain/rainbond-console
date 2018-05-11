# -*- coding: utf8 -*-
import json
import logging

from django.conf import settings
from django.views.decorators.cache import never_cache
from rest_framework.response import Response

from backends.services.exceptions import SameIdentityError, UserNotExistError
from console.services.team_services import team_services
from console.services.user_services import user_services
from console.views.base import BaseApiView, JWTAuthApiView, AlowAnyApiView
from www.apiclient.baseclient import HttpClient
from www.auth import login, authenticate, logout
from www.models import AnonymousUser
from www.services import user_svc
from www.utils.return_message import general_message, error_message

logger = logging.getLogger("default")


class CheckSourceView(AlowAnyApiView):
    def get(self, request, *args, **kwargs):
        """
        判断是sso还是私有云
        ---

        """
        user = request.user
        try:
            # if isinstance(user, AnonymousUser):
            if settings.MODULES.get('SSO_LOGIN'):
                code = 200
                data = dict()
                url = "https://sso.goodrain.com/#/login/"
                data["url"] = url
                data["is_public"] = True
                data["redirect"] = "redirect to the sso login page!"
                result = general_message(code, "The user is a public rainbond user.", "该用户是共有云用户", bean=data)
                return Response(result, status=code)
            else:
                code = 200
                data = dict()
                url = "https://" + request.get_host() + '/index#/user/login'
                data["url"] = url
                data["redirect"] = "redirect to the private rainbond login page!"
                data["is_public"] = False
                result = general_message(code, "This user is a private cloud user.", "该用户是私有云用户", bean=data)
                return Response(result, status=code)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=500)


class UserLoginView(BaseApiView):
    allowed_methods = ('POST',)

    @never_cache
    def post(self, request):
        """
        用户登录接口
        ---
        parameters:
            - name: nick_name
              description: 用户名
              required: true
              type: string
              paramType: form
            - name: password
              description: 密码
              required: true
              type: string
              paramType: form
        """
        user_name = request.POST.get("nick_name", None)
        raw_passwd = request.POST.get("password", None)
        try:
            if not user_name or not raw_passwd:
                code = 405
                result = general_message(code, "username is missing", "请填写用户名")
                return Response(result, status=code)
            elif not raw_passwd:
                code = 405
                result = general_message(code, "password is missing", "请填写密码")
                return Response(result, status=code)
            user, msg, code = user_svc.is_exist(user_name, raw_passwd)
            if not user:
                code = 400
                result = general_message(code, "authorization fail ", msg)
                return Response(result, status=code)
            else:
                u = authenticate(username=user_name, password=raw_passwd)
                http_client = HttpClient()
                url = "http://" + request.get_host() + '/console/api-token-auth'
                default_headers = {
                    'Connection': 'keep-alive',
                    'Content-Type': 'application/json'
                }
                data = {"nick_name": user_name, "password": raw_passwd}
                res, body = http_client._post(url, default_headers, json.dumps(data))
                if res.get("status", 400) != 200:
                    code = 400
                    result = general_message(code, "login failed", "登录失败")
                    return Response(result, status=code)
                logger.debug("res {0} body {1}".format(res, body))
                token = body.get("token", "")
                data = {'token': token}
                login(request, u)
                code = 200
                result = general_message(code, "login success", "登录成功", bean=data)
        except Exception as e:
            logger.exception(e)
            code = 500
            result = error_message(e.message)
        return Response(result, status=code)


class UserLogoutView(JWTAuthApiView):

    def get(self, request, *args, **kwargs):
        """
        用户登出
        ---

        """
        try:
            user = request.user
            logger.debug(type(user))
            if isinstance(user, AnonymousUser):
                code = 405
                result = general_message(code, "not login", "未登录状态, 不需注销")
                return Response(result, status=code)
            else:
                logout(request)
                code = 200
                result = general_message(code, "logout success", "登出成功")
                response = Response(result, status=code)
                response.delete_cookie('tenant_name')
                response.delete_cookie('uid', domain='.goodrain.com')
                response.delete_cookie('token', domain='.goodrain.com')
                return response
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=500)


class UserPemTraView(JWTAuthApiView):
    def post(self, request, team_name, *args, **kwargs):
        """
        移交团队管理权
        ---
        parameters:
            - name: team_name
              description: 团队名
              required: true
              type: string
              paramType: path
            - name: user_name
              description: 被赋予权限的用户名
              required: true
              type: string
              paramType: body
        """
        try:
            perm_list = team_services.get_user_perm_identitys_in_permtenant(
                user_id=request.user.user_id,
                tenant_name=team_name
            )
            role_list = team_services.get_user_perm_role_in_permtenant(
                user_id=request.user.user_id,
                tenant_name=team_name
            )

            no_auth = "owner" not in perm_list and "owner" not in role_list

            if no_auth:
                code = 400
                result = general_message(code, "no identity", "你不是最高管理员")
            else:
                user_name = request.data.get("user_name", None)
                other_user = user_services.get_user_by_username(user_name=user_name)
                if other_user.nick_name != user_name:
                    code = 400
                    result = general_message(code, "identity modify failed", "{}不能修改自己的权限".format(user_name))
                else:
                    code, msg = team_services.change_tenant_admin(user_id=request.user.user_id,
                                                                  other_user_id=other_user.user_id,
                                                                  tenant_name=team_name)
                    if code == 200:
                        result = general_message(code, "identity modify success", msg)
                    else:
                        result = general_message(code, "Authorization failure", "授权失败")
        except Exception as e:
            code = 500
            result = error_message(e.message)
            logger.exception(e)
        return Response(result, status=code)


class UserPemView(JWTAuthApiView):
    def get(self, request, *args, **kwargs):
        """
        可选权限展示
        ---

        """
        try:
            perm_info = [
                {"key": "admin", "name": u"管理员"},
                {"key": "developer", "name": u"开发者"},
                {"key": "viewer", "name": u"观察者"},
                {"key": "access", "name": u"访问者"}
            ]
            result = general_message(200, "get permissions success", "获取权限成功", list=perm_info)
            return Response(result, status=200)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=500)


class UserAddPemView(JWTAuthApiView):
    def post(self, request, team_name, user_name, *args, **kwargs):
        """
        修改成员权限
        ---
        parameters:
            - name: team_name
              description: 团队名
              required: true
              type: string
              paramType: path
            - name: user_name
              description: 被修改权限的团队成员
              required: true
              type: string
              paramType: path
            - name: identitys
              description: 权限  格式 {"identitys": "viewer,access"}
              required: true
              type: string
              paramType: body
        """
        try:
            perm_list = team_services.get_user_perm_identitys_in_permtenant(
                user_id=request.user.user_id,
                tenant_name=team_name
            )
            perm_tuple = team_services.get_user_perm_in_tenant(user_id=request.user.user_id, tenant_name=team_name)
            no_auth = ("owner" not in perm_list) and ("admin" not in perm_list)
            if no_auth:
                code = 400
                result = general_message(code, "no identity", "您不是管理员，没有权限做此操作")
            else:
                code = 200
                new_identitys = request.data.get("identitys", None)
                if new_identitys:
                    new_identitys = new_identitys.split(',') if new_identitys else []
                    other_user = user_services.get_user_by_username(user_name=user_name)
                    if other_user.user_id == request.user.user_id:
                        result = general_message(400, "failed", "您不能修改自己的权限！")
                        return Response(result, status=400)
                    team_services.change_tenant_identity(user_id=other_user.user_id, tenant_name=team_name,
                                                         new_identitys=new_identitys)
                    result = general_message(code, "identity modify success", "{}权限修改成功".format(user_name))
                else:
                    result = general_message(400, "identity failed", "修改权限时，权限不能为空")
        except SameIdentityError as e:
            logger.exception(e)
            code = 400
            result = general_message(code, "identity exist", "该用户已拥有此权限")
        except UserNotExistError as e:
            logger.exception(e)
            code = 400
            result = general_message(code, "users not exist", "该用户不存在")
        except Exception as e:
            logger.exception(e)
            code = 500
            result = error_message(e.message)
        return Response(result, status=code)
