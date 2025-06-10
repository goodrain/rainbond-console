# -*- coding: utf-8 -*-
import json
import logging
import os
import re
import time
from datetime import datetime, timedelta

from console.exception.exceptions import UserFavoriteNotExistError
from console.forms.users_operation import RegisterForm
from console.login.login_event import LoginEvent
from console.models.main import UserRole
from console.repositories.login_event import login_event_repo
from console.repositories.oauth_repo import oauth_user_repo
from console.repositories.perm_repo import perms_repo
from console.repositories.region_repo import region_repo
from console.repositories.team_repo import team_invitation_repo, team_repo
from console.repositories.user_repo import user_repo
from console.services.enterprise_services import enterprise_services
from console.services.operation_log import operation_log_service, Operation, OperationModule
from console.services.perm_services import (user_kind_perm_service, user_kind_role_service)
from console.services.region_services import region_services
from console.services.team_services import team_services
from console.services.user_services import user_services
from console.utils.perms import list_enterprise_perms_by_roles
from console.utils.validation import normalize_name_for_k8s_namespace
from console.views.base import BaseApiView, JWTAuthApiView
from django import forms
from rest_framework import status
from rest_framework.response import Response
from rest_framework_jwt.settings import api_settings
from www.models.main import Users
from www.utils.crypt import AuthCode, make_uuid
from www.utils.mail import send_reset_pass_mail
from www.utils.return_message import error_message, general_message
from console.login.jwt_manager import JwtManager
from console.services.user_service import user_service
from console.exception.main import ServiceHandleException
from rest_framework_jwt.views import jwt_response_payload_handler

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
            querydict["user_name"] = normalize_name_for_k8s_namespace(querydict["user_name"])
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
                    team = team_services.create_team(user, enterprise, ["rainbond"], "", "default", "")
                    region_services.create_tenant_on_region(enterprise.enterprise_id, team.tenant_name, "rainbond",
                                                                team.namespace)
                if os.getenv("USE_SAAS"):
                    regions = region_repo.get_usable_regions(enterprise.enterprise_id)
                    # 转换nick_name为符合k8s命名空间规范的名称
                    team = team_services.create_team(user, enterprise, None, None, nick_name)
                    region_services.create_tenant_on_region(enterprise.enterprise_id, team.tenant_name,
                                                            regions[0].region_name,
                                                            team.namespace)
                    # 默认短信注册的用户创建的团队，限额 4 Core 8 GB
                    limit_quota = {"limit_memory": 10240, "limit_cpu": 4000, "limit_storage": 0}
                    team_services.set_tenant_resource_limit(enterprise.enterprise_id, regions[0].region_id,
                                                            team.tenant_name, limit_quota)

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
                comment = operation_log_service.generate_generic_comment(
                    operation=Operation.FINISH, module=OperationModule.REGISTER, module_name="")
                operation_log_service.create_enterprise_log(user=user, comment=comment,
                                                            enterprise_id=user.enterprise_id)
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
        team_name = request.GET.get("team_name", "")
        code = 200
        user = self.user
        tenants = team_services.get_current_user_tenants(user_id=user.user_id, team_name=team_name)
        user_detail = dict()
        user_detail["user_id"] = user.user_id
        user_detail["user_name"] = user.nick_name
        user_detail["real_name"] = user.real_name
        user_detail["logo"] = user.logo
        user_detail["email"] = user.email
        user_detail["enterprise_id"] = user.enterprise_id
        user_detail["phone"] = user.phone
        user_detail["is_sys_admin"] = user.is_sys_admin
        enterprise = enterprise_services.get_enterprise_by_enterprise_id(user.enterprise_id)
        user_detail["is_enterprise_active"] = enterprise.is_active
        user_detail["is_enterprise_admin"] = self.is_enterprise_admin
        # enterprise roles
        user_detail["roles"] = user_services.list_roles(user.enterprise_id, user.user_id)
        # enterprise permissions
        user_detail["permissions"] = list_enterprise_perms_by_roles(user_detail["roles"])
        owner_tenant_list = []
        member_tenant_list = []
        for tenant in tenants:
            tenant_info = dict()
            is_team_owner = False
            team_region_list = region_services.get_region_list_by_team_name(team_name=tenant.tenant_name)
            if not team_region_list:
                continue
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
            # 分别添加到所有者列表和成员列表
            if is_team_owner:
                owner_tenant_list.append(tenant_info)
            else:
                member_tenant_list.append(tenant_info)
        # 合并列表，所有者列表在前
        tenant_list = owner_tenant_list + member_tenant_list
        user_detail["teams"] = tenant_list
        oauth_services = oauth_user_repo.get_user_oauth_services_info(
            eid=request.user.enterprise_id, user_id=request.user.user_id)
        user_detail["oauth_services"] = oauth_services
        result = general_message(code, "Obtain my details to be successful.", "获取我的详情成功", bean=user_detail)
        return Response(result, status=code)

    def post(self, request, *args, **kwargs):
        self.user.real_name = request.data.get("real_name")
        self.user.email = request.data.get("email")
        self.user.logo = request.data.get("logo")
        self.user.save()
        result = general_message(200, "success", "用户信息更新成功")
        return Response(result, status=status.HTTP_200_OK)

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
                comment = operation_log_service.generate_generic_comment(
                    operation=Operation.ADD, module=OperationModule.FAVORITE, module_name=" {}".format(name))
                operation_log_service.create_enterprise_log(
                    user=self.user, comment=comment, enterprise_id=self.user.enterprise_id)
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
            comment = operation_log_service.generate_generic_comment(
                operation=Operation.DELETE, module=OperationModule.FAVORITE, module_name=" {}".format(favorite.name))
            operation_log_service.create_enterprise_log(user=self.user, comment=comment,
                                                        enterprise_id=self.user.enterprise_id)
        except UserFavoriteNotExistError as e:
            logger.debug(e)
            result = general_message(404, "fail", "收藏视图不存在")
        return Response(result, status=status.HTTP_200_OK)


class UserInviteView(JWTAuthApiView):
    def post(self, request, *args, **kwargs):
        try:
            team_id = request.data.get("team_id")
            role_id = request.data.get("role_id", "")
            expired_days = request.data.get("expired_days", 1)
            
            if not team_id:
                result = general_message(400, "params error", "参数错误")
                return Response(result, status=400)
                
            # 验证团队是否存在
            team = team_repo.get_team_by_team_id(team_id)
            if not team:
                result = general_message(404, "team not found", "团队不存在")
                return Response(result, status=404)
                
            # 创建邀请时保存role_id
            invite = team_invitation_repo.create_invitation(
                tenant_id=team_id,
                inviter_id=self.user.user_id,
                invitation_id=make_uuid(),
                role_id=role_id,  # 添加role_id
                expired_time=datetime.now() + timedelta(days=expired_days)
            )

            result = general_message(200, "success", "邀请创建成功", 
                                  bean={"invite_id": invite.invitation_id})
            return Response(result, status=200)
            
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=500)


class UserInviteJoinView(JWTAuthApiView):
    def get(self, request, invitation_id, *args, **kwargs):
        """
        获取用户邀请信息
        ---
        """
        try:
            invite = team_invitation_repo.get_invitation_by_id(invitation_id)
            
            # 检查邀请是否过期
            if invite.expired_time < datetime.now():
                result = general_message(400, "invitation expired", "邀请已过期")
                return Response(result, status=400)
            
            team = team_repo.get_team_by_team_id(invite.tenant_id)
            inviter = user_repo.get_user_by_user_id(invite.inviter_id)
            # 检查用户是否已加入团队
            is_member = team_repo.get_tenant_perms(team.ID, request.user.user_id)
            invite_info = {
                "invite_id": invite.invitation_id,
                "team_name": team.tenant_name, 
                "team_alias": team.tenant_alias,
                "invite_time": invite.create_time,
                "inviter": inviter.real_name if inviter.real_name else inviter.nick_name,
                "expired_time": invite.expired_time,
                "is_member": bool(is_member),  # 添加是否已是团队成员的标识
                "is_accepted": invite.is_accepted,
            }
            result = general_message(200, "success", "获取邀请信息成功", bean=invite_info)
            return Response(result, status=200)
        
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=500)

    def post(self, request, invitation_id, *args, **kwargs):
        """
        处理用户邀请
        ---
        parameters:
            - name: invite_id
              description: 邀请ID
              required: true
              type: string
              paramType: form
            - name: action
              description: 操作(accept/reject)
              required: true
              type: string
              paramType: form
        """
        try:
            action = request.data.get("action")

            if not invitation_id or not action:
                result = general_message(400, "params error", "参数错误")
                return Response(result, status=400)

            if action not in ["accept", "reject"]:
                result = general_message(400, "params error", "无效的操作类型")
                return Response(result, status=400)

            # 获取邀请信息
            invite = team_invitation_repo.get_invitation_by_id(invitation_id)
            if not invite:
                result = general_message(404, "not found", "邀请不存在")
                return Response(result, status=404)

            # 处理邀请
            if action == "accept":
                team = team_repo.get_team_by_team_id(invite.tenant_id)
                # 使用邀请中的role_id添加用户到团队
                perm = team_repo.create_team_perms(
                    user_id=self.user.user_id,
                    tenant_id=team.ID,
                    identity="owner",
                    enterprise_id=self.enterprise.ID,
                    role_id=invite.role_id,
                )
                if not perm:
                    result = general_message(400, "failed", "加入团队失败")
                    return Response(result, status=400)
                ur = UserRole(user_id=self.user.user_id, role_id=invite.role_id)
                ur.save()
                msg = "已接受邀请"
            else:
                msg = "已拒绝邀请"

            # 更新邀请状态
            team_invitation_repo.update_invitation(invitation_id, is_accepted=(action == "accept"))

            result = general_message(200, "success", msg)
            return Response(result, status=200)

        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=500)


class RegisterByPhoneView(BaseApiView):
    def post(self, request, *args, **kwargs):
        """
        手机号注册
        ---
        parameters:
            - name: phone
              description: 手机号
              required: true
              type: string
              paramType: form
            - name: code
              description: 验证码
              required: true
              type: string
              paramType: form
            - name: nick_name
              description: 用户名
              required: true
              type: string
              paramType: form
        """
        try:
            phone = request.data.get("phone")
            code = request.data.get("code")
            nick_name = request.data.get("nick_name")

            if not all([phone, code, nick_name]):
                result = general_message(400, "参数错误", "参数不完整")
                return Response(result, status=status.HTTP_400_BAD_REQUEST)

            # 用户名格式校验
            if not re.match(r'^[a-zA-Z0-9_-]{3,24}$', nick_name):
                result = general_message(400, "参数错误", "用户名只能包含字母、数字、下划线和中划线,长度在3-24位之间")
                return Response(result, status=status.HTTP_400_BAD_REQUEST)
            # 获取企业信息
            enterprise = enterprise_services.get_enterprise_first()
            if not enterprise:
                raise ServiceHandleException(
                    msg="enterprise not found",
                    msg_show="企业信息不存在",
                    status_code=404
                )
            user = user_service.register_by_phone(enterprise.enterprise_id, phone, code, nick_name)

            try:
                regions = region_repo.get_usable_regions(enterprise.enterprise_id)
                # 转换nick_name为符合k8s命名空间规范的名称
                normalized_namespace = normalize_name_for_k8s_namespace(nick_name)
                team = team_services.create_team(user, enterprise, None, None, normalized_namespace)
                region_services.create_tenant_on_region(enterprise.enterprise_id, team.tenant_name,
                                                            regions[0].region_name,
                                                            team.namespace)
                # 默认短信注册的用户创建的团队，限额 4 Core 8 GB
                limit_quota = {"limit_memory": 10240, "limit_cpu": 4000, "limit_storage": 0}
                team_services.set_tenant_resource_limit(enterprise.enterprise_id, regions[0].region_id, team.tenant_name, limit_quota)
            except Exception as e:
                logger.warning("create default team failed", e)
            # 生成token
            jwt_manager = JwtManager()
            payload = jwt_payload_handler(user)
            token = jwt_encode_handler(payload)
            jwt_manager.set(token, user.user_id)

            data = {
                "user_id": user.user_id,
                "nick_name": user.nick_name,
                "phone": user.phone,
                "enterprise_id": user.enterprise_id,
                "token": token
            }

            result = general_message(200, "success", "注册成功", bean=data)
            return Response(result, status=status.HTTP_200_OK)
        except ServiceHandleException as e:
            raise e
        except Exception as e:
            logger.exception(e)
            result = general_message(500, "注册失败", str(e))
            return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LoginByPhoneView(BaseApiView):
    def post(self, request, *args, **kwargs):
        """
        手机号登录
        ---
        parameters:
            - name: phone
              description: 手机号
              required: true
              type: string
              paramType: form
            - name: code
              description: 验证码
              required: true
              type: string
              paramType: form
        """
        try:
            phone = request.data.get("phone")
            code = request.data.get("code")

            if not all([phone, code]):
                result = general_message(400, "参数错误", "参数不完整")
                return Response(result, status=status.HTTP_400_BAD_REQUEST)

            user = user_service.login_by_phone(phone, code)
            login_event = LoginEvent(user, login_event_repo, request=request)
            login_event.login()
            # 生成token
            payload = jwt_payload_handler(user)
            token = jwt_encode_handler(payload)
            response_data = jwt_response_payload_handler(token, user, request)
            result = general_message(200, "login success", "登录成功", bean=response_data)
            response = Response(result)
            if api_settings.JWT_AUTH_COOKIE:
                expiration = (datetime.now() + timedelta(days=30))
                response.set_cookie(api_settings.JWT_AUTH_COOKIE, token, expires=expiration)
            jwt_manager = JwtManager()
            jwt_manager.set(response_data["token"], user.user_id)
            return Response(result, status=status.HTTP_200_OK)
        except ServiceHandleException as e:
            raise e
        except Exception as e:
            logger.exception(e)
            result = general_message(500, "登录失败", str(e))
            return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
