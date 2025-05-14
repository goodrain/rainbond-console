# -*- coding: utf8 -*-
import json
import logging

from console.enum.enterprise_enum import EnterpriseRolesEnum
from console.exception.bcode import ErrEnterpriseNotFound, ErrUserNotFound
from console.exception.exceptions import UserNotExistError
from console.exception.main import AbortRequest, ServiceHandleException
from console.login.login_event import LoginEvent
from console.repositories.login_event import login_event_repo
from console.repositories.oauth_repo import oauth_user_repo
from console.repositories.team_repo import team_repo
from console.repositories.user_repo import user_repo
from console.services.auth import login, logout
from console.services.enterprise_services import enterprise_services
from console.services.exception import (ErrAdminUserDoesNotExist, ErrCannotDelLastAdminUser)
from console.services.operation_log import operation_log_service, OperationModule, Operation
from console.services.perm_services import user_kind_role_service
from console.services.region_services import region_services
from console.services.team_services import team_services
from console.services.user_services import user_services
from console.utils.reqparse import parse_item
from console.views.base import (AlowAnyApiView, BaseApiView, EnterpriseAdminView, JWTAuthApiView, TeamOwnerView)
from django.conf import settings
from django.contrib.auth import authenticate
from django.db import transaction
from django.views.decorators.cache import never_cache
from rest_framework.response import Response
from www.apiclient.baseclient import HttpClient
from www.models.main import AnonymousUser
from www.services import user_svc
from www.utils.return_message import error_message, general_message

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
            login_event = LoginEvent(self.user, login_event_repo)
            login_event.logout()
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
                comment = operation_log_service.generate_generic_comment(
                    operation=Operation.EXIT, module=OperationModule.LOGIN, module_name="")
                operation_log_service.create_enterprise_log(user=self.user, comment=comment,
                                                            enterprise_id=self.user.enterprise_id)
                response = Response(result, status=code)
                response.delete_cookie('tenant_name')
                response.delete_cookie('uid', domain='.goodrain.com')
                response.delete_cookie('token', domain='.goodrain.com')
                return response
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=500)


class UserPemTraView(TeamOwnerView):
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
        user_id = request.data.get("user_id")
        self.tenant.creater = user_id
        self.tenant.save()
        result = general_message(msg="success", msg_show="移交成功", code=200)
        user = user_services.get_user_by_user_id(user_id)
        comment = operation_log_service.generate_team_comment(
            operation=Operation.TRUN_OVER,
            module_name=self.tenant.tenant_alias,
            region=self.response_region,
            team_name=self.tenant.tenant_name,
            suffix=" 给用户 {}".format(user.get_name()))
        operation_log_service.create_team_log(
            user=self.user, comment=comment, enterprise_id=self.user.enterprise_id, team_name=self.tenant.tenant_name)
        return Response(result, status=200)


class AdminUserLCView(EnterpriseAdminView):
    def get(self, request, enterprise_id, *args, **kwargs):
        users = user_services.get_admin_users(enterprise_id)
        result = general_message(200, "success", "获取企业管理员列表成功", list=users)
        return Response(result)

    def post(self, request, enterprise_id, *args, **kwargs):
        roles = parse_item(request, "roles", required=True, error="at least one role needs to be specified")
        if not set(roles).issubset(EnterpriseRolesEnum.names()):
            raise AbortRequest("invalid roles", msg_show="角色不正确")

        user_id = request.data.get("user_id")
        if user_id == self.user.user_id:
            raise AbortRequest("cannot edit your own role", msg_show="不可操作自己的角色")
        try:
            user = user_services.get_user_by_user_id(user_id)
        except UserNotExistError:
            raise ErrUserNotFound

        ent = enterprise_services.get_enterprise_by_enterprise_id(enterprise_id)
        if ent is None:
            raise ErrEnterpriseNotFound

        user_services.create_admin_user(user, ent, roles)
        comment = operation_log_service.generate_generic_comment(
            operation=Operation.CREATE, module=OperationModule.ENTERPRISEADMIN,
            module_name=" {}".format(user.get_name()))
        operation_log_service.create_enterprise_log(user=self.user, comment=comment,
                                                    enterprise_id=self.user.enterprise_id)
        return Response(general_message(201, "success", None), status=201)


class AdminUserView(EnterpriseAdminView):
    def delete(self, request, enterprise_id, user_id, *args, **kwargs):
        if str(request.user.user_id) == user_id:
            result = general_message(400, "fail", "不可删除自己")
            return Response(result, 400)
        try:
            user = user_services.get_user_by_user_id(user_id)
            user_services.delete_admin_user(user_id)
            result = general_message(200, "success", None)
            comment = operation_log_service.generate_generic_comment(
                operation=Operation.DELETE, module=OperationModule.ENTERPRISEADMIN,
                module_name=" {}".format(user.get_name()))
            operation_log_service.create_enterprise_log(user=self.user, comment=comment,
                                                        enterprise_id=self.user.enterprise_id)
            return Response(result, 200)
        except ErrAdminUserDoesNotExist as e:
            logger.debug(e)
            result = general_message(400, "用户'{}'不是企业管理员".format(user_id), None)
            return Response(result, 400)
        except ErrCannotDelLastAdminUser as e:
            logger.debug(e)
            result = general_message(400, "fail", None)
            return Response(result, 400)

    def put(self, request, enterprise_id, user_id, *args, **kwargs):
        roles = parse_item(request, "roles", required=True, error="at least one role needs to be specified")
        if not set(roles).issubset(EnterpriseRolesEnum.names()):
            raise AbortRequest("invalid roles", msg_show="角色不正确")
        if str(request.user.user_id) == user_id:
            raise AbortRequest("changing your role is not allowed", "不可修改自己的角色")
        user_services.update_roles(enterprise_id, user_id, roles)
        result = general_message(200, "success", None)
        return Response(result, 200)


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
                    "real_name": (user.nick_name if user.real_name is None else user.real_name),
                    "user_id": user.user_id,
                    "phone": user.phone,
                    "create_time": user.create_time,
                    "default_favorite_name": default_favorite_name,
                    "default_favorite_url": default_favorite_url,
                })
        result = general_message(200, "success", None, list=data, page_size=page_size, page=page, total=total)
        return Response(result, status=200)

    def post(self, request, enterprise_id, *args, **kwargs):

        tenant_name = request.data.get("tenant_name", None)
        user_name = request.data.get("user_name", None)
        email = request.data.get("email", None)
        password = request.data.get("password", None)
        re_password = request.data.get("re_password", None)
        role_ids = request.data.get("role_ids", None)
        phone = request.data.get("phone", None)
        real_name = request.data.get("real_name", None)
        tenant = team_services.get_tenant_by_tenant_name(tenant_name)
        if len(password) < 8:
            result = general_message(400, "len error", "密码长度最少为8位")
            return Response(result)
        # check user info
        user_services.check_params(user_name, email, password, re_password, request.user.enterprise_id, phone)
        client_ip = user_services.get_client_ip(request)
        enterprise = enterprise_services.get_enterprise_by_enterprise_id(enterprise_id)
        # create user
        oauth_instance, _ = user_services.check_user_is_enterprise_center_user(request.user.user_id)

        if oauth_instance:
            user = user_services.create_enterprise_center_user_set_password(user_name, email, password, "admin add", enterprise,
                                                                            client_ip, phone, real_name, oauth_instance)
        else:
            user = user_services.create_user_set_password(user_name, email, password, "admin add", enterprise, client_ip, phone,
                                                          real_name)
        result = general_message(200, "success", "添加用户成功")
        if tenant:
            create_perm_param = {
                "user_id": user.user_id,
                "tenant_id": tenant.ID,
                "identity": "",
                "enterprise_id": enterprise.ID,
            }
            team_repo.create_team_perms(**create_perm_param)
            if role_ids:
                user_kind_role_service.update_user_roles(kind="team", kind_id=tenant.tenant_id, user=user, role_ids=role_ids)
                user.is_active = True
                user.save()
                result = general_message(200, "success", "添加用户成功")
        comment = operation_log_service.generate_generic_comment(
            operation=Operation.ADD, module=OperationModule.USER, module_name="{}".format(user.get_name()))
        operation_log_service.create_enterprise_log(user=self.user, comment=comment, enterprise_id=self.user.enterprise_id)
        return Response(result)


class EnterPriseUsersUDView(JWTAuthApiView):
    @transaction.atomic()
    def put(self, request, enterprise_id, user_id, *args, **kwargs):
        password = request.data.get("password", None)
        real_name = request.data.get("real_name", None)
        phone = request.data.get("phone", None)

        user = user_services.update_user_set_password(enterprise_id, user_id, password, real_name, phone)
        user.save()
        oauth_instance, _ = user_services.check_user_is_enterprise_center_user(request.user.user_id)
        if oauth_instance:
            data = {
                "password": password,
                "real_name": real_name,
                "phone": phone,
            }
            oauth_instance.update_user(enterprise_id, user.enterprise_center_user_id, data)
        result = general_message(200, "success", "更新用户成功")
        comment = operation_log_service.generate_generic_comment(
            operation=Operation.CHANGE, module=OperationModule.USER, module_name="{} 的信息".format(user.get_name()))
        operation_log_service.create_enterprise_log(user=self.user, comment=comment,
                                                    enterprise_id=self.user.enterprise_id)
        return Response(result, status=200)

    def delete(self, request, enterprise_id, user_id, *args, **kwargs):
        user = user_repo.get_enterprise_user_by_id(enterprise_id, user_id)
        if not user:
            result = general_message(400, "fail", "未找到该用户")
            return Response(result, 403)
        user_services.delete_user(user_id)
        oauth_instance, oauth_user = user_services.check_user_is_enterprise_center_user(user_id)
        if oauth_instance:
            oauth_instance.delete_user(enterprise_id, user.enterprise_center_user_id)
        all_oauth_user = oauth_user_repo.get_all_user_oauth(user_id)
        all_oauth_user.delete()
        result = general_message(200, "success", "删除用户成功")
        comment = operation_log_service.generate_generic_comment(
            operation=Operation.DELETE, module=OperationModule.USER, module_name="{}".format(user.get_name()))
        operation_log_service.create_enterprise_log(user=self.user, comment=comment, enterprise_id=self.user.enterprise_id)
        return Response(result, status=200)


class AdministratorJoinTeamView(EnterpriseAdminView):
    def post(self, request, *args, **kwargs):
        nojoin_user_ids = []
        team_name = request.data.get("team_name")
        team = team_services.get_enterprise_tenant_by_tenant_name(self.user.enterprise_id, team_name)
        if not team:
            raise ServiceHandleException(msg="no found team", msg_show="团队不存在", status_code=404)
        users = team_services.get_team_users(team)
        if users:
            nojoin_user_ids = users.values_list("user_id", flat=True)
        if self.user.user_id not in nojoin_user_ids:
            team_services.add_user_role_to_team(tenant=team, user_ids=[self.user.user_id], role_ids=[])
        result = general_message(200, "success", None)
        return Response(result, status=200)


class AdminRolesView(JWTAuthApiView):
    def get(self, request, *args, **kwargs):
        from console.utils.perms import ENTERPRISE
        roles = list()
        for role in ENTERPRISE:
            roles.append(role)
        result = general_message(200, "success", None, list=roles)
        return Response(result, status=200)
