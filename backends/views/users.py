# -*- coding: utf8 -*-
import logging

from rest_framework.response import Response

from backends.services.exceptions import *
from backends.services.resultservice import *
from backends.services.tenantservice import tenant_service
from backends.services.userservice import user_service
from base import BaseAPIView
from goodrain_web.tools import JuncheePaginator
from www.models import Tenants
from console.services.team_services import team_services as console_team_service
from console.services.enterprise_services import enterprise_services as console_enterprise_service
from console.utils.timeutil import time_to_str

logger = logging.getLogger("default")


class TenantUserView(BaseAPIView):
    def get(self, request, tenant_name, *args, **kwargs):
        """
        获取某团队下的所有用户
        ---
        parameters:
            - name: tenant_name
              description: 租户名称
              required: true
              type: string
              paramType: path

        """
        result = {}
        try:
            user_list = tenant_service.get_tenant_users(tenant_name)
            list = []
            for user in user_list:
                result_map = {}
                result_map["user_id"] = user.user_id
                result_map["email"] = user.email
                result_map["nick_name"] = user.nick_name
                tenant_list = user_service.get_user_tenants(user.user_id)
                result_map["tenants"] = tenant_list
                list.append(result_map)

            result = generate_result(
                "0000", "success", "查询成功", list=list
            )
        except Tenants.DoesNotExist as e:
            logger.exception(e)
            result = generate_result("1001", "tenant not exist", "租户{}不存在".format(tenant_name))
        except Exception as e:
            logger.exception(e)
            result = generate_result("9999", "system error", "系统异常")
        return Response(result)

    def post(self, request, tenant_name, *args, **kwargs):
        """
        添加用户
        ---
        parameters:
            - name: tenant_name
              description: 租户名称
              required: true
              type: string
              paramType: path
            - name: user_name
              description: 用户名
              required: true
              type: string
              paramType: form
            - name: phone
              description: 手机号
              required: true
              type: string
              paramType: form
            - name: email
              description: 邮件地址
              required: true
              type: string
              paramType: form
            - name: password
              description: 密码
              required: true
              type: string
              paramType: form
            - name: re_password
              description: 重复密码
              required: true
              type: string
              paramType: form
            - name: identity
              description: 用户在租户的身份
              required: true
              type: string
              paramType: form

        """
        try:
            user_name = request.data.get("user_name", None)
            phone = request.data.get("phone", None)
            email = request.data.get("email", None)
            password = request.data.get("password", None)
            re_password = request.data.get("re_password", None)
            identity = request.data.get("identity", "viewer")
            is_pass, msg = user_service.check_params(user_name,phone,email,password,re_password)
            if not is_pass:
                return Response(generate_result("0403", "params error", msg))
            client_ip = user_service.get_client_ip(request)
            team = console_team_service.get_tenant_by_tenant_name(tenant_name)
            if not team:
                return Response(generate_result("0404", "team not exist", "团队{0}不存在".format(tenant_name)))
            enterprise = console_enterprise_service.get_enterprise_by_enterprise_id(team.enterprise_id)

            user = user_service.create_user(user_name, phone, email, password, "backend", enterprise, client_ip)
            tenant_service.add_user_to_tenant(team, user, identity, enterprise)
            user.is_active = True
            user.save()
            result = generate_result("0000", "success", "添加用户成功")
        except Exception as e:
            logger.exception(e)
            result = generate_result("9999", "system error", "系统异常")
        return Response(result)


class UserView(BaseAPIView):
    def delete(self, request, tenant_name, user_id, *args, **kwargs):
        """
        删除用户
        ---
        parameters:
            - name: tenant_name
              description: 租户名称
              required: true
              type: string
              paramType: path
            - name: user_id
              description: 用户名
              required: true
              type: string
              paramType: path

        """
        try:
            user_service.delete_user(user_id)
            result = generate_result(
                "0000", "success", "删除成功"
            )
        except Exception as e:
            logger.exception(e)
            result = generate_result("9999", "system error", "系统异常")
        return Response(result)

    def put(self, request, tenant_name, user_id, *args, **kwargs):
        """
        修改用户
        ---
        parameters:
            - name: tenant_name
              description: 租户名称
              required: true
              type: string
              paramType: path
            - name: user_id
              description: 用户名
              required: true
              type: string
              paramType: path
            - name: new_password
              description: 新密码
              required: true
              type: string
              paramType: form

        """
        try:
            new_password = request.data.get("new_password", None)
            if not new_password:
                result = generate_result("1006", "no password", "密码不能为空")
            else:
                user_service.update_user_password(user_id, new_password)
                result = generate_result(
                    "0000", "success", "密码修改成功"
                )
        except PasswordTooShortError as e:
            result = generate_result("1007", "password too short", "{}".format(e.message))
        except Exception as e:
            logger.exception(e)
            result = generate_error_result()
        return Response(result)


class AllUserView(BaseAPIView):
    def get(self, request, *args, **kwargs):
        """
        获取所有用户信息
        ---
        parameters:
            - name: page_num
              description: 页码
              required: false
              type: string
              paramType: query
            - name: page_size
              description: 每页数量
              required: false
              type: string
              paramType: query
            - name: user_name
              description: 用户名称（可以是邮箱，用户名，手机号）
              required: false
              type: string
              paramType: query

        """
        result = {}
        try:
            page = request.GET.get("page_num", 1)
            page_size = request.GET.get("page_size", 20)
            user_name = request.GET.get("user_name", None)
            user_list = user_service.get_by_username_or_phone_or_email(user_name)
            user_paginator = JuncheePaginator(user_list, int(page_size))
            users = user_paginator.page(int(page))
            list = []
            uid_eid_map = {u.user_id: u.enterprise_id for u in users}
            eids = [u.enterprise_id for u in users]
            enterprises = console_enterprise_service.get_enterprise_by_eids(eids)
            eid_enterprise_map = {e.enterprise_id: e.enterprise_alias for e in enterprises}
            for user in users:
                result_map = {}
                result_map["user_id"] = user.user_id
                result_map["email"] = user.email
                result_map["nick_name"] = user.nick_name
                result_map["phone"] = user.phone if user.phone else "暂无"
                result_map["create_time"] = time_to_str(user.create_time, "%Y-%m-%d %H:%M:%S")
                tenant_list = user_service.get_user_tenants(user.user_id)
                result_map["tenants"] = tenant_list
                eid = uid_eid_map.get(user.user_id, None)
                if eid:
                    result_map["enterprise_alias"] = eid_enterprise_map.get(eid, "暂无企业信息")
                else:
                    result_map["enterprise_alias"] = "暂无企业信息"
                list.append(result_map)

            result = generate_result(
                "0000", "success", "查询成功", list=list, total=user_paginator.count
            )

        except Exception as e:
            logger.debug(e)
            result = generate_error_result()
        return Response(result)


class UserQueryView(BaseAPIView):
    def get(self, request, *args, **kwargs):
        """
        模糊查询指定团队下的用户
        ---
        parameters:
            - name: tenant_name
              description: 团队名称
              required: false
              type: string
              paramType: query
            - name: user_name
              description: 模糊用户名
              required: true
              type: string
              paramType: query

        """
        try:
            tenant_name = request.GET.get("tenant_name", None)
            user_name = request.GET.get("user_name", None)
            user_list = []
            if user_name:
                user_list = user_service.get_fuzzy_users(tenant_name, user_name)

            users = []
            for user in user_list:
                user_info = {}
                user_info["nick_name"] = user.nick_name
                user_info["user_id"] = user.user_id
                if tenant_name:
                    user_info["tenant_name"] = tenant_name
                users.append(user_info)
            result = generate_result("0000", "success", "查询成功", list=users)
        except Exception as e:
            logger.exception(e)
            result = generate_error_result()
        return Response(result)


class UserBatchDeleteView(BaseAPIView):
    def delete(self, request, tenant_name, *args, **kwargs):
        """
        批量删除租户内的用户
        ---
        parameters:
            - name: tenant_name
              description: 团队名称
              required: true
              type: string
              paramType: path
            - name: user_ids
              description: 用户名 userId1,userID2 ...
              required: true
              type: string
              paramType: form
        """
        user_ids = request.data.get("user_ids", None)
        try:
            user_id_list = user_ids.split(",")
            user_service.batch_delete_users(tenant_name, user_id_list)
            code = "0000"
            msg = "success"
            msg_show = "删除成功"
            result = generate_result(code, msg, msg_show)
        except Tenants.DoesNotExist as e:
            result = generate_result("1003", "tenant not exist", "租户{}不存在".format(tenant_name))
        except Exception as e:
            result = generate_error_result()
            logger.exception(e)
        return Response(result)
