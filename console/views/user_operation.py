# -*- coding: utf-8 -*-
import json
import logging
import re
import time

from console.exception.exceptions import UserFavoriteNotExistError
from console.forms.users_operation import RegisterForm
from console.repositories.oauth_repo import oauth_user_repo
from console.repositories.perm_repo import perms_repo
from console.repositories.user_repo import user_repo
from console.services.enterprise_services import enterprise_services
from console.services.perm_services import (user_kind_perm_service, user_kind_role_service)
from console.services.region_services import region_services
from console.services.team_services import team_services
from console.services.user_services import user_services
from console.utils.perms import list_enterprise_perms_by_roles
from console.views.base import BaseApiView, JWTAuthApiView
from django import forms
from rest_framework import status
from rest_framework.response import Response
from rest_framework_jwt.settings import api_settings
from www.models.main import SuperAdminUser, Users
from www.utils.crypt import AuthCode
from www.utils.mail import send_reset_pass_mail
from www.utils.return_message import error_message, general_message
from console.login.jwt_manager import JwtManager

jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER

logger = logging.getLogger("default")


def password_len(value):
    if len(value) < 8:
        raise forms.ValidationError("密码长度至少为8位")


class PasswordResetForm(forms.Form):
    password = forms.CharField(required=True, label='', widget=forms.PasswordInput, validators=[password_len])
    password_repeat = forms.CharField(required=True, label='', widget=forms.PasswordInput, validators=[password_len])

    error_messages = {
        'password_repeat': "两次输入的密码不一致",
    }

    def __init__(self, *args, **kwargs):
        super(PasswordResetForm, self).__init__(*args, **kwargs)
        self.helper.form_tag = False
        self.helper.help_text_inline = True
        self.helper.error_text_inline = True

    def clean(self):
        password = self.cleaned_data.get('password')
        password_repeat = self.cleaned_data.get('password_repeat')

        if password_repeat != password:
            raise forms.ValidationError(
                self.error_messages['password_repeat'],
                code='password_repeat',
            )


class TenantServiceView(BaseApiView):
    allowed_methods = ('POST', )

    def post(self, request, *args, **kwargs):
        """
        注册用户、需要先访问captcha路由来获取验证码
        ---
        parameters:
            - name: user_name
              description: 用户名
              required: true
              type: string
              paramType: body
            - name: email
              description: 邮箱
              required: true
              type: string
              paramType: body
            - name: password
              description: 密码，最少八位
              required: true
              type: string
              paramType: body
            - name: password_repeat
              description: 确认密码
              required: true
              type: string
              paramType: body
            - name: captcha_code
              description: 验证码
              required: true
              type: string
              paramType: body
            - name: register_type
              description: 注册方式 暂: 邀请注册 invitation 其它方式暂无 有拓展再修改
              required: false
              type: string
              paramType: body
            - name: value
              description: 数值 此处需要 team_id
              required: false
              type: string
              paramType: body
            - name: enter_name
              description: 企业名称
              required: false
              type: string
              paramType: body
        """
        try:
            import copy
            querydict = copy.copy(request.data)
            client_ip = request.META.get("REMOTE_ADDR", None)
            register_form = RegisterForm(querydict)

            if register_form.is_valid():
                nick_name = register_form.cleaned_data["user_name"]
                email = register_form.cleaned_data["email"]
                password = register_form.cleaned_data["password"]
                # 创建一个用户
                user_info = dict()
                user_info["email"] = email
                user_info["nick_name"] = nick_name
                user_info["is_active"] = 1
                user_info["phone"] = register_form.cleaned_data["phone"]
                user_info["real_name"] = register_form.cleaned_data["real_name"]
                user = Users(**user_info)
                user.set_password(password)
                user.save()
                enterprise = enterprise_services.get_enterprise_first()
                if not enterprise:
                    enter_name = request.data.get("enter_name", None)
                    enterprise = enterprise_services.create_enterprise(enterprise_name=None, enterprise_alias=enter_name)
                    # 创建用户在企业的权限
                    user_services.make_user_as_admin_for_enterprise(user.user_id, enterprise.enterprise_id)
                user.enterprise_id = enterprise.enterprise_id
                user.save()

                if Users.objects.count() == 1:
                    user.sys_admin = True
                    user.save()
                enterprise = enterprise_services.get_enterprise_first()
                register_type = request.data.get("register_type", None)
                value = request.data.get("value", None)
                if register_type == "invitation":
                    perm = perms_repo.add_user_tenant_perm(perm_info={
                        "user_id": user.user_id,
                        "tenant_id": value,
                        "identity": "viewer",
                        "enterprise_id": enterprise.ID
                    })
                    if not perm:
                        result = general_message(400, "invited failed", "团队关联失败，注册失败")
                        return Response(result, status=400)
                data = dict()
                data["user_id"] = user.user_id
                data["nick_name"] = user.nick_name
                data["email"] = user.email
                data["phone"] = user.phone
                data["real_name"] = user.real_name
                data["enterprise_id"] = user.enterprise_id
                payload = jwt_payload_handler(user)
                token = jwt_encode_handler(payload)
                data["token"] = token
                jwt_manager = JwtManager()
                jwt_manager.set(token, user.user_id)
                result = general_message(200, "register success", "注册成功", bean=data)
                response = Response(result, status=200)
                return response
            else:
                error = {"error": list(json.loads(register_form.errors.as_json()).values())[0][0].get("message", "参数错误")}
                result = general_message(400, "failed", "{}".format(error["error"]))
                return Response(result, status=400)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message if hasattr(e, 'message') else '')
            return Response(result, status=500)


class SendResetEmail(BaseApiView):
    def post(self, request, *args, **kwargs):
        """
        发送忘记密码邮件
        ---
        parameters:
            - name: email
              description: 邮箱
              required: true
              type: string
              paramType: form
        """
        email = request.POST.get("email", None)
        code = 200
        try:
            if email:
                if len(email) > 5:
                    rerule = "^.+\\@(\\[?)[a-zA-Z0-9\\-\\.]+\\.([a-zA-Z]{2,3}|[0-9]{1,3})(\\]?)$"
                    if re.match(rerule, email):
                        if Users.objects.filter(email=email).exists():
                            # TODO 生成 url 并发送一封邮件
                            domain = self.request.META.get('HTTP_HOST')
                            timestamp = str(int(time.time()))
                            tag = AuthCode.encode(','.join([email, timestamp]), 'password')
                            link_url = 'http://%s/console/users/begin_password_reset?tag=%s' % (domain, tag)
                            content = "请点击下面的链接重置您的密码，%s" % link_url
                            try:
                                send_reset_pass_mail(email, content)
                            except Exception as e:
                                logger.error("account.passwdreset", "send email to {0} failed".format(email))
                                logger.exception("account.passwdreset", e)
                            result = general_message(code, "success", "邮件发送成功")
                        else:
                            code = 400
                            result = general_message(code, "failed！", "当前用户没有注册！")
                        return Response(result, status=code)
                    else:
                        code = 400
                        result = general_message(code, "failed", "邮箱不合法!")
                        return Response(result, status=code)
            else:
                code = 400
                result = general_message(code, "failed", "邮件发送失败")
                return Response(result, status=code)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=500)


class PasswordResetBegin(BaseApiView):
    def post(self, request, *args, **kwargs):
        """
        忘记密码
        ---
        parameters:
            - name: password
              description: 新密码
              required: true
              type: string
              paramType: form
            - name: password_repeat
              description: 确认密码
              required: true
              type: string
              paramType: form
        """
        try:
            tag = str(request.GET.get('tag'))
            email, old_timestamp = AuthCode.decode(tag, 'password').split(',')
            timestamp = int(time.time())
            if (timestamp - int(old_timestamp)) > 3600:
                logger.info("account.passwdreset", "link expired, email: {0}, link_timestamp: {1}".format(email, old_timestamp))
                result = general_message(400, "failed", "链接已失效")
                return Response(result, status=400)
            user = Users.objects.get(email=email)
            form = PasswordResetForm(request.POST)
            if form.is_valid():
                raw_password = request.POST.get('password')
                user.set_password(raw_password)
                user.save()
                result = general_message(200, "success", "修改密码成功")
                return Response(result, status=200)
            else:
                error = {"error": list(json.loads(form.errors.as_json()).values())[0][0].get("message", "参数错误")}
                result = general_message(400, "failed", "参数错误,{}".format(error["error"]))
                return Response(result, status=400)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=500)


class ChangeLoginPassword(JWTAuthApiView):
    def post(self, request, *args, **kwargs):
        """
        修改密码
        ---
        parameters:
            - name: password
              description: 原密码
              required: true
              type: string
              paramType: form
            - name: new_password
              description: 新密码
              required: true
              type: string
              paramType: form
            - name: new_password2
              description: 确认密码
              required: true
              type: string
              paramType: form
        """
        try:
            password = request.data.get("password", None)
            new_password = request.data.get("new_password", None)
            new_password2 = request.data.get("new_password2", None)
            u = request.user
            code = 400
            if not user_services.check_user_password(user_id=u.user_id, password=password):
                result = general_message(400, "old password error", "旧密码错误")
            elif new_password != new_password2:
                result = general_message(400, "two password disagree", "两个密码不一致")
            elif password == new_password:
                result = general_message(400, "old and new password agree", "新旧密码一致")
            else:
                status, info = user_services.update_password(user_id=u.user_id, new_password=new_password)
                oauth_instance, _ = user_services.check_user_is_enterprise_center_user(request.user.user_id)
                if oauth_instance:
                    data = {
                        "password": new_password,
                        "real_name": request.user.real_name,
                    }
                    oauth_instance.update_user(request.user.enterprise_id, request.user.enterprise_center_user_id, data)
                if status:
                    code = 200
                    result = general_message(200, "change password success", "密码修改成功")
                else:
                    result = general_message(400, "password change failed", "密码修改失败")
            return Response(result, status=code)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=500)


class UserDetailsView(JWTAuthApiView):
    def get(self, request, *args, **kwargs):
        """
        查询我的详情
        ---
        """
        code = 200
        user = self.user
        tenants = team_services.get_current_user_tenants(user_id=user.user_id)
        user_detail = dict()
        user_detail["user_id"] = user.user_id
        user_detail["user_name"] = user.nick_name
        user_detail["real_name"] = user.real_name
        user_detail["email"] = user.email
        user_detail["enterprise_id"] = user.enterprise_id
        user_detail["phone"] = user.phone
        user_detail["git_user_id"] = user.git_user_id
        user_detail["is_sys_admin"] = user.is_sys_admin
        enterprise = enterprise_services.get_enterprise_by_enterprise_id(user.enterprise_id)
        user_detail["is_enterprise_active"] = enterprise.is_active
        user_detail["is_enterprise_admin"] = self.is_enterprise_admin
        # enterprise roles
        user_detail["roles"] = user_services.list_roles(user.enterprise_id, user.user_id)
        # enterprise permissions
        user_detail["permissions"] = list_enterprise_perms_by_roles(user_detail["roles"])
        tenant_list = list()
        for tenant in tenants:
            tenant_info = dict()
            is_team_owner = False
            team_region_list = region_services.get_region_list_by_team_name(team_name=tenant.tenant_name)
            tenant_info["team_id"] = tenant.ID
            tenant_info["team_name"] = tenant.tenant_name
            tenant_info["team_alias"] = tenant.tenant_alias
            tenant_info["limit_memory"] = tenant.limit_memory
            tenant_info["region"] = team_region_list
            tenant_info["creater"] = tenant.creater
            tenant_info["create_time"] = tenant.create_time
            tenant_info["namespace"] = tenant.namespace
            if tenant.creater == user.user_id:
                is_team_owner = True
            role_list = user_kind_role_service.get_user_roles(kind="team", kind_id=tenant.tenant_id, user=user)
            tenant_info["role_name_list"] = role_list["roles"]
            perms = user_kind_perm_service.get_user_perms(
                kind="team", kind_id=tenant.tenant_id, user=user, is_owner=is_team_owner, is_ent_admin=self.is_enterprise_admin)
            tenant_info["tenant_actions"] = perms["permissions"]
            tenant_info["is_team_owner"] = is_team_owner
            tenant_list.append(tenant_info)
        user_detail["teams"] = tenant_list
        oauth_services = oauth_user_repo.get_user_oauth_services_info(
            eid=request.user.enterprise_id, user_id=request.user.user_id)
        user_detail["oauth_services"] = oauth_services
        result = general_message(code, "Obtain my details to be successful.", "获取我的详情成功", bean=user_detail)
        return Response(result, status=code)


class UserFavoriteLCView(JWTAuthApiView):
    def get(self, request, enterprise_id):
        data = []
        try:
            user_favorites = user_repo.get_user_favorite(request.user.user_id)
            if user_favorites:
                for user_favorite in user_favorites:
                    data.append({
                        "name": user_favorite.name,
                        "url": user_favorite.url,
                        "favorite_id": user_favorite.ID,
                        "custom_sort": user_favorite.custom_sort,
                        "is_default": user_favorite.is_default
                    })
        except Exception as e:
            logger.debug(e)
            result = general_message(400, "fail", "获取失败")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        result = general_message(200, "success", None, list=data)
        return Response(result, status=status.HTTP_200_OK)

    def post(self, request, enterprise_id):
        name = request.data.get("name")
        url = request.data.get("url")
        is_default = request.data.get("is_default", False)
        if name and url:
            try:

                old_favorite = user_repo.get_user_favorite_by_name(request.user.user_id, name)
                if old_favorite:
                    result = general_message(400, "fail", "收藏视图名称已存在")
                    return Response(result, status=status.HTTP_400_BAD_REQUEST)
                user_repo.create_user_favorite(request.user.user_id, name, url, is_default)
                result = general_message(200, "success", "收藏视图创建成功")
                return Response(result, status=status.HTTP_200_OK)
            except Exception as e:
                logger.debug(e)
                result = general_message(400, "fail", "收藏视图创建失败")
                return Response(result, status=status.HTTP_400_BAD_REQUEST)
        else:
            result = general_message(400, "fail", "参数错误")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)


class UserFavoriteUDView(JWTAuthApiView):
    def put(self, request, enterprise_id, favorite_id):
        result = general_message(200, "success", "更新成功")
        name = request.data.get("name")
        url = request.data.get("url")
        custom_sort = request.data.get("custom_sort")
        is_default = request.data.get("is_default", False)
        if not (name and url):
            result = general_message(400, "fail", "参数错误")
        try:
            user_favorite = user_repo.get_user_favorite_by_ID(request.user.user_id, favorite_id)
            rst = user_repo.update_user_favorite(user_favorite, name, url, custom_sort, is_default)
            if not rst:
                result = general_message(200, "fail", "更新视图失败")
        except UserFavoriteNotExistError as e:
            logger.debug(e)
            result = general_message(404, "fail", "收藏视图不存在")
        return Response(result, status=status.HTTP_200_OK)

    def delete(self, request, enterprise_id, favorite_id):
        result = general_message(200, "success", "删除成功")
        try:
            user_repo.delete_user_favorite_by_id(request.user.user_id, favorite_id)
        except UserFavoriteNotExistError as e:
            logger.debug(e)
            result = general_message(404, "fail", "收藏视图不存在")
        return Response(result, status=status.HTTP_200_OK)
