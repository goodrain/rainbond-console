# -*- coding: utf8 -*-
import json
import logging

from django.conf import settings
from django.views.decorators.cache import never_cache
from rest_framework.response import Response

from console.exception.exceptions import SameIdentityError
from console.exception.exceptions import UserNotExistError
from console.repositories.user_repo import user_repo
from console.repositories.team_repo import team_repo
from console.services.team_services import team_services
from console.services.user_services import user_services
from console.services.enterprise_services import enterprise_services
from console.services.exception import ErrAdminUserDoesNotExist
from console.services.exception import ErrCannotDelLastAdminUser
from console.views.base import BaseApiView, JWTAuthApiView, AlowAnyApiView
from www.apiclient.baseclient import HttpClient
from console.services.auth import login, logout
from django.contrib.auth import authenticate
from www.models.main import AnonymousUser
from www.services import user_svc
from www.utils.return_message import general_message, error_message

logger = logging.getLogger("default")


class CheckSourceView(AlowAnyApiView):
    def get(self, request, *args, **kwargs):
        """
        判断是sso还是私有云
        ---

        """
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
    allowed_methods = ('POST', )

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
                default_headers = {'Connection': 'keep-alive', 'Content-Type': 'application/json'}
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
            perm_list = team_services.get_user_perm_identitys_in_permtenant(user_id=request.user.user_id, tenant_name=team_name)
            role_list = team_services.get_user_perm_role_in_permtenant(user_id=request.user.user_id, tenant_name=team_name)

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
                    code, msg = team_services.change_tenant_admin(
                        user_id=request.user.user_id, other_user_id=other_user.user_id, tenant_name=team_name)
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
            perm_info = [{
                "key": "admin",
                "name": u"管理员"
            }, {
                "key": "developer",
                "name": u"开发者"
            }, {
                "key": "viewer",
                "name": u"观察者"
            }, {
                "key": "access",
                "name": u"访问者"
            }]
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
            perm_list = team_services.get_user_perm_identitys_in_permtenant(user_id=request.user.user_id, tenant_name=team_name)
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
                    team_services.change_tenant_identity(
                        user_id=other_user.user_id, tenant_name=team_name, new_identitys=new_identitys)
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


class AdminUserLCView(JWTAuthApiView):
    def get(self, request, enterprise_id, *args, **kwargs):
        users = user_services.get_admin_users(enterprise_id)
        result = general_message(200, "success", "获取企业管理员列表成功", list=users)
        return Response(result)

    def post(self, request, enterprise_id, *args, **kwargs):
        user_id = request.data.get("user_id")
        try:
            user = user_services.get_user_by_user_id(user_id)
            ent = enterprise_services.get_enterprise_by_enterprise_id(enterprise_id)
            if ent is None:
                result = general_message(404, "no found", "未找到该企业")
            else:
                user_services.create_admin_user(user, ent)
                result = general_message(201, "success", None)
        except UserNotExistError:
            result = general_message(404, "no found", "未找到该用户")
        return Response(result, status=201)


class AdminUserDView(JWTAuthApiView):
    def delete(self, request, enterprise_id, user_id, *args, **kwargs):
        if str(request.user.user_id) == user_id:
            result = general_message(400, "fail", "不可删除自己")
            return Response(result, 400)
        try:
            user_services.delete_admin_user(user_id)
            result = general_message(200, "success", None)
            return Response(result, 200)
        except ErrAdminUserDoesNotExist as e:
            logger.debug(e)
            result = general_message(400, "用户'{}'不是企业管理员".format(user_id), None)
            return Response(result, 400)
        except ErrCannotDelLastAdminUser as e:
            logger.debug(e)
            result = general_message(400, "fail", None)
            return Response(result, 400)


class EnterPriseUsersCLView(JWTAuthApiView):
    def get(self, request, enterprise_id, *args, **kwargs):
        name = request.GET.get("query")
        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 10))
        data = []
        try:
            users, total = user_services.get_user_by_eid(enterprise_id, name, page, page_size)
        except Exception as e:
            logger.debug(e)
            users = []
            total = 0
        if users:
            for user in users:
                default_favorite_name = None
                default_favorite_url = None
                user_default_favorite = user_repo.get_user_default_favorite(user.user_id)
                if user_default_favorite:
                    default_favorite_name = user_default_favorite.name
                    default_favorite_url = user_default_favorite.url
                data.append({
                    "email": user.email,
                    "nick_name": user.nick_name,
                    "user_id": user.user_id,
                    "create_time": user.create_time,
                    "default_favorite_name": default_favorite_name,
                    "default_favorite_url": default_favorite_url,
                })
        result = general_message(200, "success", None, list=data, page_size=page_size, page=page, total=total)
        return Response(result, status=200)

    def post(self, request, enterprise_id, *args, **kwargs):
        try:
            tenant_name = request.data.get("tenant_name", None)
            user_name = request.data.get("user_name", None)
            email = request.data.get("email", None)
            password = request.data.get("password", None)
            re_password = request.data.get("re_password", None)
            role_ids = request.data.get("role_ids", None)
            if len(password) < 8:
                result = general_message(400, "len error", "密码长度最少为8位")
                return Response(result)
            # 校验用户信息
            is_pass, msg = user_services.check_params(user_name, email, password, re_password)
            if not is_pass:
                result = general_message(403, "user information is not passed", msg)
                return Response(result)
            client_ip = user_services.get_client_ip(request)
            enterprise = enterprise_services.get_enterprise_by_enterprise_id(enterprise_id)
            # 创建用户
            user = user_services.create_user_set_password(
                user_name, email, password, "admin add", enterprise, client_ip)
            result = general_message(200, "success", "添加用户成功")
            if role_ids:
                try:
                    role_id_list = [int(id) for id in role_ids.split(",")]
                except Exception as e:
                    logger.exception(e)
                    code = 400
                    result = general_message(code, "params is empty", "参数格式不正确")
                    return Response(result, status=code)
                for id in role_id_list:
                    if id not in team_services.get_all_team_role_id(tenant_name=tenant_name):
                        code = 400
                        result = general_message(code, "The role does not exist", "该角色在团队中不存在")
                        return Response(result, status=code)
                # 创建用户团队关系表
                if tenant_name:
                    team_services.create_tenant_role(
                        user_id=user.user_id, tenant_name=tenant_name, role_id_list=role_id_list)
                user.is_active = True
                user.save()
                result = general_message(200, "success", "添加用户成功")
        except Exception as e:
            logger.exception(e)
            result = general_message(500, e.message, "系统异常")
        return Response(result)


class EnterPriseUsersUDView(JWTAuthApiView):
    def put(self, request, enterprise_id, user_id, *args, **kwargs):
        user_name = request.data.get("user_name", None)
        email = request.data.get("email", None)
        password = request.data.get("password", None)
        re_password = request.data.get("re_password", None)
        is_pass, msg = user_services.check_params(user_name, email, password, re_password)
        if not is_pass:
            result = general_message(403, "user information is not passed", msg)
            return Response(result, 403)
        user = user_services.update_user_set_password(enterprise_id, user_id, user_name, email, password)
        user.save()
        result = general_message(200, "success", "更新用户成功")
        return Response(result, status=200)

    def delete(self, request, enterprise_id, user_id, *args, **kwargs):
        user = user_repo.get_enterprise_user_by_id(enterprise_id, user_id)
        if not user:
            result = general_message(400, "fail", "未找到该用户")
            return Response(result, 403)
        teams = team_repo.get_tenants_by_user_id(user_id)
        if teams:
            result = general_message(400, "fail", "该用户拥有团队，或加入其他团队，不能删除")
            return Response(result, 403)
        user.delete()
        result = general_message(200, "success", "删除用户成功")
        return Response(result, status=200)
